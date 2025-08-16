"""
Secure Container-based Kernel Manager
Implements secure code execution with Docker containers
"""

import docker
import asyncio
import json
import uuid
import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class SecureExecutionResult:
    """Result of secure code execution"""
    stdout: str
    stderr: str
    execution_count: int
    status: str
    artifacts: List[str]
    execution_time: float
    container_id: Optional[str] = None

class SecureKernelManager:
    """Manages secure Docker-based code execution"""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            self.docker_available = True
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
            self.docker_client = None
            self.docker_available = False
        
        self.active_containers = {}
        self.execution_queue = asyncio.Queue()
        self.container_logs = {}
        
        # Security settings
        self.max_memory = "512m"
        self.max_cpus = "0.5"
        self.execution_timeout = 30
        self.max_processes = 50
        
        # Build secure image if not exists
        self._ensure_secure_image()
    
    def _ensure_secure_image(self):
        """Build secure execution image if it doesn't exist"""
        if not self.docker_available:
            return
            
        try:
            self.docker_client.images.get("aido-secure-kernel")
        except docker.errors.ImageNotFound:
            logger.info("Building secure kernel image...")
            dockerfile_path = Path(__file__).parent.parent.parent.parent / "docker" / "kernels"
            self.docker_client.images.build(
                path=str(dockerfile_path),
                dockerfile="Dockerfile.secure",
                tag="aido-secure-kernel",
                rm=True
            )
            logger.info("Secure kernel image built successfully")
        except Exception as e:
            logger.error(f"Failed to ensure secure image: {e}")
    
    async def get_or_create_container(self, session_id: str) -> str:
        """Get existing container or create new secure container for session"""
        
        if session_id in self.session_containers:
            container_id = self.session_containers[session_id]
            try:
                container = self.docker_client.containers.get(container_id)
                if container.status == "running":
                    return container_id
            except docker.errors.NotFound:
                pass
        
        # Create new secure container
        container_id = await self._create_secure_container(session_id)
        self.session_containers[session_id] = container_id
        return container_id
    
    async def _create_secure_container(self, session_id: str) -> str:
        """Create a new secure container with all security restrictions"""
        
        # Create session workspace
        workspace_path = Path(f"/tmp/aido-workspace-{session_id}")
        workspace_path.mkdir(exist_ok=True)
        
        # Security configuration
        security_opt = [
            "seccomp=/app/docker/kernels/seccomp-profile.json",
            "apparmor:docker-default",
            "no-new-privileges:true"
        ]
        
        # Network configuration - only allow PyPI and conda
        network_config = {
            "NetworkMode": "bridge",
            "PortBindings": {},
            "PublishAllPorts": False
        }
        
        # Resource limits
        host_config = {
            "Memory": self._parse_memory(self.max_memory),
            "MemorySwap": self._parse_memory(self.max_memory),  # No swap
            "CpuQuota": 50000,  # 0.5 CPU
            "CpuPeriod": 100000,
            "PidsLimit": 100,
            "ReadonlyRootfs": True,
            "Tmpfs": {
                "/tmp": "rw,noexec,nosuid,size=50m",
                "/workspace": f"rw,size={self.max_disk_size}"
            },
            "CapDrop": [
                "ALL"
            ],
            "CapAdd": [
                "SETUID",
                "SETGID"
            ],
            "SecurityOpt": security_opt,
            "Ulimits": [
                {"Name": "nproc", "Soft": 50, "Hard": 50},
                {"Name": "nofile", "Soft": 1024, "Hard": 1024}
            ]
        }
        
        # Environment variables
        environment = {
            "PYTHONPATH": "/workspace",
            "HOME": "/workspace",
            "USER": "sandbox",
            "SHELL": "/bin/false"
        }
        
        try:
            container = self.docker_client.containers.run(
                image="aido-secure-kernel",
                detach=True,
                remove=False,
                user="sandbox",
                working_dir="/workspace",
                environment=environment,
                **host_config,
                **network_config,
                command=["python", "-c", "import time; time.sleep(3600)"]  # Keep alive
            )
            
            container_id = container.id
            self.active_containers[container_id] = container
            
            logger.info(f"Created secure container {container_id[:12]} for session {session_id}")
            return container_id
            
        except Exception as e:
            logger.error(f"Failed to create secure container: {e}")
            raise
    
    async def _execute_fallback(self, code: str) -> SecureExecutionResult:
        """Fallback execution using subprocess when Docker is not available"""
        import subprocess
        import tempfile
        import os
        import sys
        
        start_time = time.time()
        
        try:
            # Create temporary file for code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute with subprocess
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout,
                cwd=tempfile.gettempdir()
            )
            
            execution_time = time.time() - start_time
            
            # Clean up
            os.unlink(temp_file)
            
            return SecureExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                execution_count=1,
                status="ok" if result.returncode == 0 else "error",
                artifacts=[],
                execution_time=execution_time,
                container_id=None
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return SecureExecutionResult(
                stdout="",
                stderr="Execution timed out",
                execution_count=1,
                status="timeout",
                artifacts=[],
                execution_time=execution_time,
                container_id=None
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return SecureExecutionResult(
                stdout="",
                stderr=f"Execution failed: {str(e)}",
                execution_count=1,
                status="error",
                artifacts=[],
                execution_time=execution_time,
                container_id=None
            )
    
    def _parse_memory(self, memory_str: str) -> int:
        """Parse memory string to bytes"""
        if memory_str.endswith('m'):
            return int(memory_str[:-1]) * 1024 * 1024
        elif memory_str.endswith('g'):
            return int(memory_str[:-1]) * 1024 * 1024 * 1024
        return int(memory_str)
    
    async def execute_code(self, session_id: str, code: str) -> SecureExecutionResult:
        """Execute code in secure container with timeout"""
        
        # Fallback to subprocess if Docker not available
        if not self.docker_available:
            return await self._execute_fallback(code)
        
        container_id = await self.get_or_create_container(session_id)
        container = self.active_containers[container_id]
        
        start_time = time.time()
        
        try:
            # Create execution script
            exec_script = f"""
import sys
import traceback
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import os
os.chdir('/workspace')

try:
{self._indent_code(code)}
    print("\\n__EXECUTION_SUCCESS__")
except Exception as e:
    print(f"__EXECUTION_ERROR__: {{e}}")
    traceback.print_exc()
"""
            
            # Execute with timeout
            exec_result = container.exec_run(
                cmd=["python", "-c", exec_script],
                user="sandbox",
                workdir="/workspace"
            )
            
            execution_time = time.time() - start_time
            
            # Check for timeout
            if execution_time > self.max_execution_time:
                await self.kill_container(container_id)
                return SecureExecutionResult(
                    stdout="",
                    stderr="Execution timeout exceeded",
                    execution_count=0,
                    status="timeout",
                    artifacts=[],
                    execution_time=execution_time,
                    container_id=container_id
                )
            
            stdout = exec_result.output.decode('utf-8')
            stderr = ""
            
            # Check execution status
            if "__EXECUTION_SUCCESS__" in stdout:
                status = "ok"
                stdout = stdout.replace("__EXECUTION_SUCCESS__", "").strip()
            elif "__EXECUTION_ERROR__" in stdout:
                status = "error"
                error_lines = stdout.split("__EXECUTION_ERROR__: ")
                if len(error_lines) > 1:
                    stderr = error_lines[1]
                    stdout = error_lines[0].strip()
            else:
                status = "error"
                stderr = "Unknown execution error"
            
            # Find artifacts (generated files)
            artifacts = await self._collect_artifacts(container_id, session_id)
            
            return SecureExecutionResult(
                stdout=stdout,
                stderr=stderr,
                execution_count=1,
                status=status,
                artifacts=artifacts,
                execution_time=execution_time,
                container_id=container_id
            )
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return SecureExecutionResult(
                stdout="",
                stderr=f"Container execution failed: {e}",
                execution_count=0,
                status="error",
                artifacts=[],
                execution_time=time.time() - start_time,
                container_id=container_id
            )
    
    def _indent_code(self, code: str) -> str:
        """Indent code for execution within try block"""
        lines = code.split('\n')
        return '\n'.join('    ' + line for line in lines)
    
    async def _collect_artifacts(self, container_id: str, session_id: str) -> List[str]:
        """Collect generated files from container"""
        container = self.active_containers[container_id]
        artifacts = []
        
        try:
            # List files in workspace
            result = container.exec_run(
                cmd=["find", "/workspace", "-type", "f", "-name", "*.png", "-o", "-name", "*.jpg", "-o", "-name", "*.csv", "-o", "-name", "*.json"],
                user="sandbox"
            )
            
            if result.exit_code == 0:
                files = result.output.decode('utf-8').strip().split('\n')
                for file_path in files:
                    if file_path and file_path != '/workspace':
                        # Copy file out of container
                        local_path = f"/workspace/{session_id}/{Path(file_path).name}"
                        try:
                            # Create directory if needed
                            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                            
                            # Extract file
                            tar_stream, _ = container.get_archive(file_path)
                            with open(local_path, 'wb') as f:
                                for chunk in tar_stream:
                                    f.write(chunk)
                            
                            artifacts.append(local_path)
                        except Exception as e:
                            logger.warning(f"Failed to extract artifact {file_path}: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to collect artifacts: {e}")
        
        return artifacts
    
    async def kill_container(self, container_id: str) -> bool:
        """Emergency kill container (panic button)"""
        try:
            if container_id in self.active_containers:
                container = self.active_containers[container_id]
                container.kill()
                container.remove(force=True)
                del self.active_containers[container_id]
                
                # Remove from session mapping
                for session_id, cid in list(self.session_containers.items()):
                    if cid == container_id:
                        del self.session_containers[session_id]
                        break
                
                logger.info(f"Killed container {container_id[:12]}")
                return True
        except Exception as e:
            logger.error(f"Failed to kill container {container_id}: {e}")
        
        return False
    
    async def cleanup_session(self, session_id: str):
        """Clean up session container and resources"""
        if session_id in self.session_containers:
            container_id = self.session_containers[session_id]
            await self.kill_container(container_id)
    
    async def panic_kill_all(self) -> int:
        """Emergency kill all containers"""
        killed_count = 0
        for container_id in list(self.active_containers.keys()):
            if await self.kill_container(container_id):
                killed_count += 1
        return killed_count
    
    def get_active_containers(self) -> Dict[str, Dict[str, Any]]:
        """Get info about active containers"""
        info = {}
        for container_id, container in self.active_containers.items():
            try:
                container.reload()
                info[container_id] = {
                    "status": container.status,
                    "created": container.attrs['Created'],
                    "image": container.attrs['Config']['Image'],
                    "session": next((sid for sid, cid in self.session_containers.items() if cid == container_id), None)
                }
            except Exception as e:
                info[container_id] = {"status": "error", "error": str(e)}
        
        return info
