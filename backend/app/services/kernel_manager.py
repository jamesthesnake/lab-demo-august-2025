"""
Kernel Manager Service
Handles creation and management of isolated Jupyter kernels in Docker containers
"""

import asyncio
import json
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from enum import Enum
from dataclasses import dataclass, field
import base64
import subprocess
import tempfile

# Import Docker
try:
    import docker
    from docker.errors import NotFound, APIError
    HAS_DOCKER = True
except ImportError:
    HAS_DOCKER = False
    docker = None
    NotFound = Exception
    APIError = Exception

# Import Jupyter/ZMQ
try:
    import zmq
    import zmq.asyncio
    from jupyter_client import KernelManager as JupyterKernelManager
    from jupyter_client.kernelspec import KernelSpecManager
    HAS_JUPYTER = True
except ImportError:
    HAS_JUPYTER = False
    zmq = None
    JupyterKernelManager = None
    KernelSpecManager = None

# Import aiofiles
try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False
    aiofiles = None

logger = logging.getLogger(__name__)

# ============================================================================
# Enums and Data Classes
# ============================================================================

class KernelStatus(Enum):
    """Kernel status enumeration"""
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    RESTARTING = "restarting"
    SHUTTING_DOWN = "shutting_down"
    DEAD = "dead"

@dataclass
class KernelInfo:
    """Information about a kernel instance"""
    kernel_id: str
    session_id: str
    container_id: Optional[str]
    status: KernelStatus
    created_at: datetime
    last_activity: datetime
    workspace_path: str
    execution_count: int = 0
    kernel_manager: Optional[Any] = None  # JupyterKernelManager
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExecutionResult:
    """Container for code execution results"""
    def __init__(self):
        self.stdout: List[str] = []
        self.stderr: List[str] = []
        self.display_data: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.execution_count: int = 0
        self.status: str = "ok"
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": "\n".join(self.stdout),
            "stderr": "\n".join(self.stderr),
            "display_data": self.display_data,
            "errors": self.errors,
            "execution_count": self.execution_count,
            "status": self.status
        }

class AnalysisContext:
    """Context for code analysis and generation"""
    def __init__(self, 
                 session_id: str,
                 previous_code: List[str] = None,
                 available_files: List[str] = None,
                 variables_in_scope: Dict[str, str] = None,
                 installed_packages: List[str] = None,
                 execution_history: List[Dict[str, Any]] = None):
        self.session_id = session_id
        self.previous_code = previous_code or []
        self.available_files = available_files or []
        self.variables_in_scope = variables_in_scope or {}
        self.installed_packages = installed_packages or ["pandas", "numpy", "matplotlib", "seaborn", "scikit-learn"]
        self.execution_history = execution_history or []

# ============================================================================
# Kernel Manager Class
# ============================================================================
class KernelManager:
    """
    Manages Docker-based Jupyter kernels for isolated code execution
    """
    
    def __init__(self, 
                 docker_image: str = "aido-kernel:latest",
                 workspace_base: str = "/app/workspaces",
                 max_kernels: int = 10,
                 kernel_timeout: int = 3600,  # 1 hour
                 execution_timeout: int = 30):  # 30 seconds
        """
        Initialize the Kernel Manager
        
        Args:
            docker_image: Docker image to use for kernels
            workspace_base: Base directory for session workspaces
            max_kernels: Maximum number of concurrent kernels
            kernel_timeout: Kernel idle timeout in seconds
            execution_timeout: Maximum execution time per cell in seconds
        """
        self.docker_image = docker_image
        self.workspace_base = workspace_base
        self.max_kernels = max_kernels
        self.kernel_timeout = kernel_timeout
        self.execution_timeout = execution_timeout
        
        self.kernels: Dict[str, KernelInfo] = {}
        
        # Initialize Docker client if available
        self.docker_client = None
        if HAS_DOCKER:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized successfully")
            except Exception as e:
                logger.warning(f"Docker not available: {e}. Will use subprocess fallback.")
        else:
            logger.warning("Docker library not installed. Will use subprocess fallback.")
        
        # Initialize ZMQ context if available
        self.context = None
        if HAS_JUPYTER and zmq:
            self.context = zmq.asyncio.Context()
            logger.info("ZMQ context initialized for Jupyter kernels")
        else:
            logger.warning("Jupyter/ZMQ not available. Will use subprocess execution.")
        
        # Ensure workspace directory exists
        os.makedirs(workspace_base, exist_ok=True)
        
        # Build kernel image if Docker is available
        if self.docker_client:
            asyncio.create_task(self._ensure_kernel_image())
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_idle_kernels())
        
        logger.info(f"KernelManager initialized with image: {docker_image}")
    
    async def _ensure_kernel_image(self):
        """Ensure the kernel Docker image exists"""
        if not self.docker_client:
            return
            
        try:
            self.docker_client.images.get(self.docker_image)
            logger.info(f"Kernel image {self.docker_image} found")
        except docker.errors.ImageNotFound:
            logger.info(f"Kernel image {self.docker_image} not found, will pull or build")
            # Try to pull the image first
            try:
                self.docker_client.images.pull(self.docker_image)
                logger.info(f"Pulled kernel image {self.docker_image}")
            except:
                # If pull fails, try to build
                dockerfile_path = "/app/docker/kernels"
                if os.path.exists(dockerfile_path):
                    logger.info(f"Building kernel image {self.docker_image}...")
                    self.docker_client.images.build(
                        path=dockerfile_path,
                        tag=self.docker_image,
                        rm=True
                    )
                    logger.info(f"Kernel image {self.docker_image} built successfully")
                else:
                    logger.warning(f"Cannot find or build kernel image {self.docker_image}")
        except Exception as e:
            logger.error(f"Error checking/building kernel image: {e}")
    
    async def create_kernel(self, session_id: str) -> str:
        """
        Create a new kernel for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Kernel ID
        """
        # Check if kernel already exists for this session
        if session_id in self.kernels:
            kernel_info = self.kernels[session_id]
            if kernel_info.status != KernelStatus.DEAD:
                logger.info(f"Kernel already exists for session {session_id}")
                return kernel_info.kernel_id
        
        # Check max kernels limit
        if len(self.kernels) >= self.max_kernels:
            await self._cleanup_idle_kernels()
            if len(self.kernels) >= self.max_kernels:
                raise RuntimeError(f"Maximum number of kernels ({self.max_kernels}) reached")
        
        kernel_id = str(uuid.uuid4())
        workspace_path = os.path.join(self.workspace_base, session_id)
        
        # Create workspace directory
        os.makedirs(workspace_path, exist_ok=True)
        
        # Create initial notebook file
        notebook_path = os.path.join(workspace_path, "session.ipynb")
        if not os.path.exists(notebook_path):
            initial_notebook = {
                "cells": [],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5
            }
            with open(notebook_path, 'w') as f:
                json.dump(initial_notebook, f, indent=2)
        
        logger.info(f"Creating kernel {kernel_id} for session {session_id}")
        
        container_id = None
        kernel_manager = None
        
        # Try to create Docker container if available
        if self.docker_client and HAS_JUPYTER:
            try:
                # Launch Docker container
                container = self.docker_client.containers.run(
                    self.docker_image,
                    detach=True,
                    name=f"kernel-{kernel_id}",
                    volumes={
                        workspace_path: {"bind": "/workspace", "mode": "rw"}
                    },
                    environment={
                        "KERNEL_ID": kernel_id,
                        "SESSION_ID": session_id,
                        "PYTHONUNBUFFERED": "1"
                    },
                    network_mode="none",  # No network access for security
                    mem_limit="512m",  # 512MB memory limit
                    cpu_quota=50000,  # 50% of one CPU
                    cpu_period=100000,
                    remove=True,  # Auto-remove container when stopped
                    labels={
                        "aido.kernel": "true",
                        "aido.session": session_id,
                        "aido.kernel_id": kernel_id
                    }
                )
                container_id = container.id
                
                # Create kernel manager if Jupyter is available
                if JupyterKernelManager:
                    kernel_manager = JupyterKernelManager(kernel_name='python3')
                    kernel_manager.kernel_id = kernel_id
                    
                    # Wait for container to be ready
                    await asyncio.sleep(2)
                    
                    # Start kernel client
                    kernel_manager.start_kernel()
                    
                logger.info(f"Docker kernel {kernel_id} created for session {session_id}")
                
            except Exception as e:
                logger.error(f"Failed to create Docker kernel: {str(e)}")
                # Clean up on failure
                if container_id:
                    try:
                        container = self.docker_client.containers.get(container_id)
                        container.stop()
                        container.remove()
                    except:
                        pass
                container_id = None
                kernel_manager = None
        
        # Store kernel info
        kernel_info = KernelInfo(
            kernel_id=kernel_id,
            session_id=session_id,
            container_id=container_id,
            status=KernelStatus.IDLE,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            workspace_path=workspace_path,
            kernel_manager=kernel_manager
        )
        
        self.kernels[session_id] = kernel_info
        
        logger.info(f"Kernel {kernel_id} ready for session {session_id}")
        return kernel_id
        async def execute_code(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute code and return structured results
        Compatible with LLM tool calling
        """
        if not self.kernel:
            await self.ensure_kernel()
        
        # Send execute request
        msg_id = self.kernel_client.execute(code)
        
        # Collect results
        stdout_output = []
        stderr_output = []
        display_data = []
        
        # Poll for results with timeout
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                # Check for timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    await self.interrupt_kernel()
                    return {
                        "status": "timeout",
                        "stdout": "\n".join(stdout_output),
                        "stderr": "Execution timed out after {} seconds".format(timeout)
                    }
                
                # Get message from kernel
                msg = self.kernel_client.get_iopub_msg(timeout=0.1)
                
                if msg["parent_header"].get("msg_id") != msg_id:
                    continue
                
                msg_type = msg["header"]["msg_type"]
                content = msg["content"]
                
                if msg_type == "stream":
                    if content["name"] == "stdout":
                        stdout_output.append(content["text"])
                    elif content["name"] == "stderr":
                        stderr_output.append(content["text"])
                
                elif msg_type == "display_data":
                    display_data.append(content["data"])
                
                elif msg_type == "error":
                    return {
                        "status": "error",
                        "stdout": "\n".join(stdout_output),
                        "stderr": "\n".join(content["traceback"])
                    }
                
                elif msg_type == "execute_reply":
                    if content["status"] == "ok":
                        return {
                            "status": "ok",
                            "stdout": "\n".join(stdout_output),
                            "stderr": "\n".join(stderr_output),
                            "display_data": display_data
                        }
                    else:
                        return {
                            "status": "error",
                            "stdout": "\n".join(stdout_output),
                            "stderr": "\n".join(stderr_output)
                        }
            
            except asyncio.TimeoutError:
                await asyncio.sleep(0.01)
                continue
            except Exception as e:
                return {
                    "status": "error",
                    "stdout": "\n".join(stdout_output),
                    "stderr": str(e)
                }
    
    async def ensure_kernel(self):
        """Ensure kernel is running and ready"""
        if not self.kernel:
            await self.start_kernel()
        
        # Test kernel is responsive
        test_result = await self.execute_code("print('ready')", timeout=5)
        if test_result["status"] != "ok":
            await self.restart_kernel()
    
    async def interrupt_kernel(self):
        """Interrupt running execution"""
        if self.kernel_manager:
            self.kernel_manager.interrupt_kernel()
    async def execute_code(self, 
                          session_id: str, 
                          code: str,
                          timeout: Optional[int] = None) -> ExecutionResult:
        """
        Execute code in a kernel
        
        Args:
            session_id: Session identifier
            code: Python code to execute
            timeout: Execution timeout in seconds (overrides default)
            
        Returns:
            ExecutionResult containing output
        """
        # Get or create kernel
        if session_id not in self.kernels:
            await self.create_kernel(session_id)
        
        kernel_info = self.kernels[session_id]
        
        # If we have a Docker kernel with Jupyter, use it
        if kernel_info.kernel_manager and HAS_JUPYTER:
            return await self._execute_jupyter(kernel_info, code, timeout)
        else:
            # Fallback to subprocess execution
            return await self._execute_subprocess(kernel_info, code, timeout)
    
    async def _execute_jupyter(self, kernel_info: KernelInfo, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Execute code using Jupyter kernel"""
        kernel_info.status = KernelStatus.BUSY
        kernel_info.last_activity = datetime.utcnow()
        kernel_info.execution_count += 1
        
        km = kernel_info.kernel_manager
        kc = km.client()
        kc.start_channels()
        
        result = ExecutionResult()
        result.execution_count = kernel_info.execution_count
        
        timeout = timeout or self.execution_timeout
        
        try:
            # Execute the code
            msg_id = kc.execute(code, store_history=True)
            
            # Collect output
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    # Get IOPub messages (output)
                    iopub_msg = kc.get_iopub_msg(timeout=0.5)
                    msg_type = iopub_msg['msg_type']
                    content = iopub_msg['content']
                    
                    if iopub_msg['parent_header'].get('msg_id') != msg_id:
                        continue
                    
                    if msg_type == 'stream':
                        # stdout or stderr
                        if content['name'] == 'stdout':
                            result.stdout.append(content['text'])
                        elif content['name'] == 'stderr':
                            result.stderr.append(content['text'])
                    
                    elif msg_type in ['display_data', 'execute_result']:
                        # Rich output (plots, tables, etc.)
                        display_data = {}
                        
                        if 'text/plain' in content.get('data', {}):
                            display_data['text'] = content['data']['text/plain']
                        
                        if 'text/html' in content.get('data', {}):
                            display_data['html'] = content['data']['text/html']
                        
                        if 'image/png' in content.get('data', {}):
                            display_data['image'] = {
                                'type': 'png',
                                'data': content['data']['image/png']
                            }
                        
                        if 'application/json' in content.get('data', {}):
                            display_data['json'] = content['data']['application/json']
                        
                        if display_data:
                            result.display_data.append(display_data)
                    
                    elif msg_type == 'error':
                        # Execution error
                        result.errors.append({
                            'ename': content.get('ename', 'Error'),
                            'evalue': content.get('evalue', ''),
                            'traceback': content.get('traceback', [])
                        })
                        result.status = 'error'
                    
                    elif msg_type == 'status':
                        # Kernel status update
                        if content.get('execution_state') == 'idle':
                            # Execution complete
                            break
                    
                except Exception as e:
                    # Timeout or other error getting message
                    continue
            
            else:
                # Execution timeout
                km.interrupt_kernel()
                result.status = 'timeout'
                result.errors.append({
                    'ename': 'TimeoutError',
                    'evalue': f'Execution exceeded timeout of {timeout} seconds',
                    'traceback': []
                })
            
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}")
            result.status = 'error'
            result.errors.append({
                'ename': 'ExecutionError',
                'evalue': str(e),
                'traceback': []
            })
        finally:
            kernel_info.status = KernelStatus.IDLE
            kc.stop_channels()
        
        # Save execution to notebook
        await self._save_to_notebook(kernel_info.session_id, code, result)
        
        return result
    
    async def _execute_subprocess(self, kernel_info: KernelInfo, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """Fallback execution using subprocess"""
        kernel_info.status = KernelStatus.BUSY
        kernel_info.last_activity = datetime.utcnow()
        kernel_info.execution_count += 1
        
        result = ExecutionResult()
        result.execution_count = kernel_info.execution_count
        
        timeout = timeout or self.execution_timeout
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute the code
            proc_result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=kernel_info.workspace_path
            )
            
            if proc_result.stdout:
                result.stdout = [proc_result.stdout]
            if proc_result.stderr:
                result.stderr = [proc_result.stderr]
            
            result.status = 'ok' if proc_result.returncode == 0 else 'error'
            
            if proc_result.returncode != 0:
                result.errors.append({
                    'ename': 'SubprocessError',
                    'evalue': f'Process exited with code {proc_result.returncode}',
                    'traceback': proc_result.stderr.split('\n') if proc_result.stderr else []
                })
                
        except subprocess.TimeoutExpired:
            result.status = 'timeout'
            result.errors.append({
                'ename': 'TimeoutError',
                'evalue': f'Execution exceeded timeout of {timeout} seconds',
                'traceback': []
            })
        except Exception as e:
            result.status = 'error'
            result.errors.append({
                'ename': 'ExecutionError',
                'evalue': str(e),
                'traceback': []
            })
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
            
            kernel_info.status = KernelStatus.IDLE
        
        # Save execution to notebook
        await self._save_to_notebook(kernel_info.session_id, code, result)
        
        return result
    
    async def _save_to_notebook(self, session_id: str, code: str, result: ExecutionResult):
        """Save execution to Jupyter notebook"""
        kernel_info = self.kernels.get(session_id)
        if not kernel_info:
            return
            
        notebook_path = os.path.join(kernel_info.workspace_path, "session.ipynb")
        
        # Load or create notebook
        if os.path.exists(notebook_path):
            with open(notebook_path, 'r') as f:
                notebook = json.load(f)
        else:
            notebook = {
                "cells": [],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5
            }
        
        # Create new cell
        cell = {
            "cell_type": "code",
            "execution_count": result.execution_count,
            "metadata": {
                "execution": {
                    "iopub.execute_input": datetime.utcnow().isoformat(),
                    "iopub.status.idle": datetime.utcnow().isoformat()
                }
            },
            "source": code.split('\n'),
            "outputs": []
        }
        
        # Add outputs
        if result.stdout:
            cell["outputs"].append({
                "output_type": "stream",
                "name": "stdout",
                "text": result.stdout
            })
        
        if result.stderr:
            cell["outputs"].append({
                "output_type": "stream",
                "name": "stderr",
                "text": result.stderr
            })
        
        for display in result.display_data:
            output = {"output_type": "display_data", "data": {}}
            
            if 'text' in display:
                output["data"]["text/plain"] = display['text']
            if 'html' in display:
                output["data"]["text/html"] = display['html']
            if 'image' in display:
                output["data"]["image/png"] = display['image']['data']
            
            cell["outputs"].append(output)
        
        for error in result.errors:
            cell["outputs"].append({
                "output_type": "error",
                "ename": error['ename'],
                "evalue": error['evalue'],
                "traceback": error['traceback']
            })
        
        # Append cell to notebook
        notebook["cells"].append(cell)
        
        # Save notebook
        with open(notebook_path, 'w') as f:
            json.dump(notebook, f, indent=2)
    
    async def restart_kernel(self, session_id: str) -> str:
        """Restart a kernel"""
        if session_id in self.kernels:
            await self.shutdown_kernel(session_id)
        
        return await self.create_kernel(session_id)
    
    async def shutdown_kernel(self, session_id: str):
        """Shutdown a kernel"""
        if session_id not in self.kernels:
            return
        
        kernel_info = self.kernels[session_id]
        kernel_info.status = KernelStatus.SHUTTING_DOWN
        
        try:
            # Stop kernel manager if it exists
            if kernel_info.kernel_manager:
                try:
                    kernel_info.kernel_manager.shutdown_kernel()
                except:
                    pass
            
            # Stop Docker container if it exists
            if kernel_info.container_id and self.docker_client:
                try:
                    container = self.docker_client.containers.get(kernel_info.container_id)
                    container.stop(timeout=5)
                    container.remove()
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error shutting down kernel: {str(e)}")
        
        finally:
            del self.kernels[session_id]
            logger.info(f"Kernel shut down for session {session_id}")
    
    async def _cleanup_idle_kernels(self):
        """Periodically clean up idle kernels"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                sessions_to_cleanup = []
                
                for session_id, kernel_info in self.kernels.items():
                    idle_time = (current_time - kernel_info.last_activity).total_seconds()
                    
                    if idle_time > self.kernel_timeout:
                        sessions_to_cleanup.append(session_id)
                
                for session_id in sessions_to_cleanup:
                    logger.info(f"Cleaning up idle kernel for session {session_id}")
                    await self.shutdown_kernel(session_id)
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
    
    async def get_kernel_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get kernel status"""
        if session_id not in self.kernels:
            return None
        
        kernel_info = self.kernels[session_id]
        
        return {
            "kernel_id": kernel_info.kernel_id,
            "session_id": kernel_info.session_id,
            "status": kernel_info.status.value,
            "created_at": kernel_info.created_at.isoformat(),
            "last_activity": kernel_info.last_activity.isoformat(),
            "execution_count": kernel_info.execution_count,
            "workspace_path": kernel_info.workspace_path,
            "has_docker": kernel_info.container_id is not None
        }
    
    async def list_kernels(self) -> List[Dict[str, Any]]:
        """List all active kernels"""
        return [
            await self.get_kernel_status(session_id)
            for session_id in self.kernels
        ]
    
    async def get_workspace_files(self, session_id: str) -> List[Dict[str, Any]]:
        """List files in a session's workspace"""
        if session_id not in self.kernels:
            return []
        
        kernel_info = self.kernels[session_id]
        workspace_path = kernel_info.workspace_path
        
        files = []
        if os.path.exists(workspace_path):
            for root, dirs, filenames in os.walk(workspace_path):
                for filename in filenames:
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, workspace_path)
                    
                    stat = os.stat(filepath)
                    files.append({
                        "name": filename,
                        "path": rel_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": self._get_file_type(filename)
                    })
        
        return files
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from extension"""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in ['.py']:
            return 'python'
        elif ext in ['.ipynb']:
            return 'notebook'
        elif ext in ['.csv', '.tsv']:
            return 'data'
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
            return 'image'
        elif ext in ['.json']:
            return 'json'
        elif ext in ['.txt', '.md']:
            return 'text'
        else:
            return 'file'
    
    async def cleanup(self):
        """Clean up all kernels on shutdown"""
        logger.info("Cleaning up all kernels...")
        
        sessions = list(self.kernels.keys())
        for session_id in sessions:
            await self.shutdown_kernel(session_id)
        
        if self.context:
            self.context.term()
        
        logger.info("Kernel manager cleanup complete")
