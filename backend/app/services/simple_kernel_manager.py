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
            
            # Create temp file with enhanced code for artifact capture
            logger.info(f"About to enhance code for session {session_id}")
            enhanced_code = self._enhance_code_for_artifacts(code, session_id)
            logger.info(f"Enhanced code generated, length: {len(enhanced_code)}")
            logger.info(f"Enhanced code preview:\n{enhanced_code[:800]}")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(enhanced_code)
                temp_file = f.name
            logger.info(f"Enhanced code written to temp file: {temp_file}")
            
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
            logger.info(f"Looking for artifacts in: {workspace_path}")
            if workspace_path.exists():
                for file_path in workspace_path.glob("*"):
                    if file_path.is_file() and file_path.suffix in ['.png', '.jpg', '.jpeg', '.csv', '.json', '.txt']:
                        artifact_info = {
                            "filename": str(file_path.name),
                            "type": "plot" if file_path.suffix in ['.png', '.jpg', '.jpeg'] else 
                                   "table" if file_path.suffix in ['.csv', '.json'] else "file",
                            "size": file_path.stat().st_size
                        }
                        artifacts.append(artifact_info)
                        logger.info(f"Found artifact: {artifact_info}")
            
            logger.info(f"Total artifacts found: {len(artifacts)}")
            
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
    
    async def list_kernels(self):
        """List active kernels (returns empty list for simple manager)"""
        return []
    
    async def shutdown_kernel(self, session_id: str):
        """Shutdown kernel for a session"""
        logger.info(f"Kernel shutdown requested for session: {session_id}")
        return True
    
    async def restart_kernel(self, session_id: str):
        """Restart kernel for a session"""
        logger.info(f"Kernel restart requested for session: {session_id}")
        return True

    def _enhance_code_for_artifacts(self, code: str, session_id: str) -> str:
        """Enhance code to automatically capture plots and tables"""
        try:
            # Use string formatting to avoid f-string conflicts
            enhanced_code = '''
import sys
import os
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    _matplotlib_available = True
except ImportError:
    _matplotlib_available = False

try:
    import pandas as pd
    _pandas_available = True
except ImportError:
    _pandas_available = False

import json
from pathlib import Path

# Set up workspace
workspace_path = Path("/app/workspaces/{session_id}")
workspace_path.mkdir(parents=True, exist_ok=True)

# Global counters for auto-generated filenames
_plot_counter = 0
_table_counter = 0

# Override plt.show() and plt.savefig() to save plots automatically
if _matplotlib_available:
    original_show = plt.show
    original_savefig = plt.savefig
    
    def auto_save_show(*args, **kwargs):
        global _plot_counter
        if plt.get_fignums():  # If there are figures
            _plot_counter += 1
            filename = f"plot_{{_plot_counter}}.png"
            filepath = workspace_path / filename
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"📊 Plot saved: {{filename}}")
        original_show(*args, **kwargs)
    
    def auto_save_savefig(*args, **kwargs):
        global _plot_counter
        # Save to our workspace first
        if plt.get_fignums():
            _plot_counter += 1
            filename = f"plot_{{_plot_counter}}.png"
            filepath = workspace_path / filename
            original_savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"📊 Plot saved: {{filename}}")
        # Try original savefig (may fail but that's ok)
        try:
            original_savefig(*args, **kwargs)
        except Exception as e:
            pass  # Ignore errors from user's savefig path
    
    plt.show = auto_save_show
    plt.savefig = auto_save_savefig

# Override DataFrame display to save tables
if _pandas_available:
    original_repr = pd.DataFrame.__repr__
    def auto_save_repr(self):
        global _table_counter
        result = original_repr(self)
        
        # Save table if it's reasonably sized
        if len(self) <= 1000 and len(self.columns) <= 50:
            _table_counter += 1
            
            # Save as CSV
            csv_filename = f"table_{{_table_counter}}.csv"
            csv_filepath = workspace_path / csv_filename
            self.to_csv(csv_filepath, index=False)
            
            # Save as JSON for better frontend display
            json_filename = f"table_{{_table_counter}}.json"
            json_filepath = workspace_path / json_filename
            table_data = {{
                "columns": list(self.columns),
                "data": self.values.tolist(),
                "shape": self.shape
            }}
            with open(json_filepath, 'w') as f:
                json.dump(table_data, f, indent=2, default=str)
            
            print(f"📋 Table saved: {{csv_filename}} ({{len(self)}} rows, {{len(self.columns)}} cols)")
        
        return result
    
    pd.DataFrame.__repr__ = auto_save_repr

# User code starts here
{user_code}
'''.format(session_id=session_id, user_code=code)
            return enhanced_code
        except Exception as e:
            logger.error(f"Error enhancing code: {e}")
            return code  # Return original code if enhancement fails

    async def cleanup(self):
        """Cleanup method for application shutdown"""
        logger.info("SimpleKernelManager cleanup completed")
        pass
