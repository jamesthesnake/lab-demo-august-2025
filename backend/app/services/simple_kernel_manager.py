"""
Simple Subprocess-based Code Execution Manager
Direct Python execution without Docker containers
"""

import asyncio
import json
import uuid
import time
import logging
import tempfile
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Result of code execution"""
    stdout: str
    stderr: str
    execution_count: int
    status: str
    artifacts: List[str]
    execution_time: float
    display_data: List[Dict[str, Any]] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.display_data is None:
            self.display_data = []
        if self.errors is None:
            self.errors = []
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_count": self.execution_count,
            "status": self.status,
            "artifacts": self.artifacts,
            "execution_time": self.execution_time,
            "display_data": self.display_data,
            "errors": self.errors
        }

class SimpleKernelManager:
    """Manages direct Python code execution via subprocess"""
    
    def __init__(self):
        self.session_states = {}  # Store session execution states
        self.execution_timeout = 30
        self.max_execution_time = 30
        
        logger.info("SimpleKernelManager initialized - using direct Python execution")
    
    async def execute_code(self, session_id: str, code: str, execution_count: int = 1, timeout: int = None) -> ExecutionResult:
        """Execute Python code directly via subprocess"""
        start_time = time.time()
        
        try:
            # Ensure workspace directory exists
            workspace_path = Path(f"/app/workspaces/{session_id}")
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Create temporary file for code execution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Execute Python code
            process = await asyncio.create_subprocess_exec(
                "/usr/local/bin/python3", temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(workspace_path),
                env={**os.environ, "PYTHONPATH": "/app"}
            )
            
            try:
                # Use provided timeout or default
                exec_timeout = timeout if timeout is not None else self.execution_timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=exec_timeout
                )
                
                stdout_str = stdout.decode('utf-8') if stdout else ""
                stderr_str = stderr.decode('utf-8') if stderr else ""
                
                status = "ok" if process.returncode == 0 else "error"
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout_str = ""
                stderr_str = "Execution timed out"
                status = "timeout"
            
            # Clean up temp file
            os.unlink(temp_file)
            
            execution_time = time.time() - start_time
            
            # Look for artifacts (saved files)
            workspace_path = Path(f"/app/workspaces/{session_id}")
            artifacts = []
            if workspace_path.exists():
                for file_path in workspace_path.glob("*"):
                    if file_path.is_file() and file_path.suffix in ['.png', '.jpg', '.csv', '.json', '.txt']:
                        artifacts.append(str(file_path.name))
            
            return ExecutionResult(
                stdout=stdout_str,
                stderr=stderr_str,
                execution_count=execution_count,
                status=status,
                artifacts=artifacts,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ExecutionResult(
                stdout="",
                stderr=f"Execution failed: {str(e)}",
                execution_count=execution_count,
                status="error",
                artifacts=[],
                execution_time=time.time() - start_time
            )
    
    def get_active_containers(self) -> List[Dict[str, Any]]:
        """Return empty list since we don't use containers"""
        return []
    
    async def panic_kill_all(self) -> int:
        """No containers to kill"""
        return 0
    
    async def kill_container(self, container_id: str) -> bool:
        """No containers to kill"""
        return False
    
    async def cleanup_session(self, session_id: str):
        """Clean up session workspace"""
        workspace_path = Path(f"/app/workspaces/{session_id}")
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)
        
        if session_id in self.session_states:
            del self.session_states[session_id]
    
    def create_session_workspace(self, session_id: str):
        """Create workspace directory for session"""
        workspace_path = Path(f"/app/workspaces/{session_id}")
        workspace_path.mkdir(parents=True, exist_ok=True)
        return str(workspace_path)
    
    async def list_kernels(self):
        """List active kernels (returns empty list for simple manager)"""
        return []
    
    async def get_kernel_status(self, session_id: str):
        """Get kernel status for a session"""
        return {"status": "ready", "session_id": session_id}
    
    async def shutdown_kernel(self, session_id: str):
        """Shutdown kernel for a session"""
        logger.info(f"Kernel shutdown requested for session: {session_id}")
        return True
    
    async def restart_kernel(self, session_id: str):
        """Restart kernel for a session"""
        logger.info(f"Kernel restart requested for session: {session_id}")
        return True


    async def cleanup(self):
        """Cleanup method for application shutdown"""
        logger.info("SimpleKernelManager cleanup completed")
        pass
