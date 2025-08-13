"""
File Manager
Handles file operations in workspaces
"""

import os
import shutil
import json
import aiofiles
from typing import List, Dict, Optional, Any, BinaryIO
from datetime import datetime
from pathlib import Path
import mimetypes
import hashlib
import asyncio

class FileManager:
    """
    Manages files in session workspaces
    """
    
    def __init__(self, workspace_base: str = "/tmp/workspaces"):
        """
        Initialize File Manager
        
        Args:
            workspace_base: Base directory for all workspaces
        """
        self.workspace_base = workspace_base
        os.makedirs(workspace_base, exist_ok=True)
    
    def get_workspace_path(self, session_id: str) -> str:
        """
        Get workspace path for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Full workspace path
        """
        return os.path.join(self.workspace_base, session_id)
    
    async def create_workspace(self, session_id: str) -> str:
        """
        Create workspace directory for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Workspace path
        """
        workspace_path = self.get_workspace_path(session_id)
        os.makedirs(workspace_path, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(workspace_path, "data"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(workspace_path, "notebooks"), exist_ok=True)
        
        # Create README
        readme_path = os.path.join(workspace_path, "README.md")
        if not os.path.exists(readme_path):
            readme_content = f"""# Workspace for Session {session_id}

Created: {datetime.utcnow().isoformat()}

## Directory Structure
- `data/` - Input data files
- `outputs/` - Generated plots and results
- `notebooks/` - Jupyter notebooks

## Usage
This workspace contains all files for your data analysis session.
"""
            with open(readme_path, 'w') as f:
                f.write(readme_content)
        
        return workspace_path
    
    async def list_files(self, 
                        session_id: str, 
                        path: str = "",
                        recursive: bool = True) -> List[Dict[str, Any]]:
        """
        List files in workspace
        
        Args:
            session_id: Session identifier
            path: Subdirectory path (relative to workspace)
            recursive: Whether to list recursively
            
        Returns:
            List of file information
        """
        workspace_path = self.get_workspace_path(session_id)
        target_path = os.path.join(workspace_path, path) if path else workspace_path
        
        if not os.path.exists(target_path):
            return []
        
        files = []
        
        if recursive:
            for root, dirs, filenames in os.walk(target_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in filenames:
                    if filename.startswith('.'):
                        continue
                        
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, workspace_path)
                    
                    files.append(self._get_file_info(filepath, rel_path))
        else:
            for item in os.listdir(target_path):
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(target_path, item)
                rel_path = os.path.relpath(item_path, workspace_path)
                
                if os.path.isfile(item_path):
                    files.append(self._get_file_info(item_path, rel_path))
        
        return files
    
    def _get_file_info(self, filepath: str, rel_path: str) -> Dict[str, Any]:
        """
        Get file information
        
        Args:
            filepath: Absolute file path
            rel_path: Relative path from workspace
            
        Returns:
            File information dictionary
        """
        stat = os.stat(filepath)
        mime_type, _ = mimetypes.guess_type(filepath)
        
        return {
            "name": os.path.basename(filepath),
            "path": rel_path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "type": self._get_file_type(filepath),
            "mime_type": mime_type,
            "is_binary": self._is_binary_file(filepath)
        }
    
    def _get_file_type(self, filepath: str) -> str:
        """
        Determine file type from extension
        
        Args:
            filepath: File path
            
        Returns:
            File type string
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        type_map = {
            '.py': 'python',
            '.ipynb': 'notebook',
            '.csv': 'csv',
            '.tsv': 'tsv',
            '.json': 'json',
            '.txt': 'text',
            '.md': 'markdown',
            '.png': 'image',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.gif': 'image',
            '.svg': 'image',
            '.pdf': 'pdf',
            '.html': 'html',
            '.js': 'javascript',
            '.css': 'css',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.h5': 'hdf5',
            '.parquet': 'parquet',
            '.pkl': 'pickle',
            '.npy': 'numpy',
            '.npz': 'numpy'
        }
        
        return type_map.get(ext, 'file')
    
    def _is_binary_file(self, filepath: str) -> bool:
        """
        Check if file is binary
        
        Args:
            filepath: File path
            
        Returns:
            True if binary, False if text
        """
        text_extensions = {
            '.txt', '.md', '.py', '.json', '.csv', '.tsv', 
            '.html', '.css', '.js', '.xml', '.yaml', '.yml',
            '.ipynb', '.log', '.sh', '.bash', '.zsh'
        }
        
        ext = os.path.splitext(filepath)[1].lower()
        return ext not in text_extensions
    
    async def read_file(self, 
                       session_id: str, 
                       file_path: str,
                       encoding: str = 'utf-8') -> str:
        """
        Read file content
        
        Args:
            session_id: Session identifier
            file_path: File path relative to workspace
            encoding: File encoding
            
        Returns:
            File content
        """
        workspace_path = self.get_workspace_path(session_id)
        full_path = os.path.join(workspace_path, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if self._is_binary_file(full_path):
            # For binary files, return base64 encoded content
            import base64
            with open(full_path, 'rb') as f:
                content = f.read()
            return base64.b64encode(content).decode('utf-8')
        else:
            # For text files, return as string
            try:
                # Try using aiofiles if available
                import aiofiles
                async with aiofiles.open(full_path, 'r', encoding=encoding) as f:
                    return await f.read()
            except ImportError:
                # Fallback to synchronous read
                with open(full_path, 'r', encoding=encoding) as f:
                    return f.read()
    
    async def write_file(self,
                        session_id: str,
                        file_path: str,
                        content: str,
                        encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Write file content
        
        Args:
            session_id: Session identifier
            file_path: File path relative to workspace
            content: File content
            encoding: File encoding
            
        Returns:
            File information
        """
        workspace_path = self.get_workspace_path(session_id)
        full_path = os.path.join(workspace_path, file_path)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Write file
        try:
            # Try using aiofiles if available
            import aiofiles
            async with aiofiles.open(full_path, 'w', encoding=encoding) as f:
                await f.write(content)
        except ImportError:
            # Fallback to synchronous write
            with open(full_path, 'w', encoding=encoding) as f:
                f.write(content)
        
        return self._get_file_info(full_path, file_path)
    
    async def save_upload(self,
                         session_id: str,
                         file_data: BinaryIO,
                         filename: str,
                         path: str = "data") -> Dict[str, Any]:
        """
        Save uploaded file
        
        Args:
            session_id: Session identifier
            file_data: File data stream
            filename: Original filename
            path: Target directory in workspace
            
        Returns:
            File information
        """
        workspace_path = self.get_workspace_path(session_id)
        target_dir = os.path.join(workspace_path, path)
        os.makedirs(target_dir, exist_ok=True)
        
        # Sanitize filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.'))
        full_path = os.path.join(target_dir, safe_filename)
        
        # Handle duplicate filenames
        if os.path.exists(full_path):
            base, ext = os.path.splitext(safe_filename)
            counter = 1
            while os.path.exists(full_path):
                safe_filename = f"{base}_{counter}{ext}"
                full_path = os.path.join(target_dir, safe_filename)
                counter += 1
        
        # Save file
        with open(full_path, 'wb') as f:
            content = file_data.read()
            f.write(content)
        
        rel_path = os.path.relpath(full_path, workspace_path)
        return self._get_file_info(full_path, rel_path)
    
    async def delete_file(self, session_id: str, file_path: str) -> bool:
        """
        Delete file
        
        Args:
            session_id: Session identifier
            file_path: File path relative to workspace
            
        Returns:
            True if deleted, False if not found
        """
        workspace_path = self.get_workspace_path(session_id)
        full_path = os.path.join(workspace_path, file_path)
        
        if os.path.exists(full_path):
            if os.path.isfile(full_path):
                os.remove(full_path)
            else:
                shutil.rmtree(full_path)
            return True
        return False
    
    async def copy_file(self,
                       session_id: str,
                       source_path: str,
                       dest_path: str) -> Dict[str, Any]:
        """
        Copy file within workspace
        
        Args:
            session_id: Session identifier
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            Destination file information
        """
        workspace_path = self.get_workspace_path(session_id)
        source_full = os.path.join(workspace_path, source_path)
        dest_full = os.path.join(workspace_path, dest_path)
        
        if not os.path.exists(source_full):
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest_full), exist_ok=True)
        
        # Copy file
        if os.path.isfile(source_full):
            shutil.copy2(source_full, dest_full)
        else:
            shutil.copytree(source_full, dest_full)
        
        rel_path = os.path.relpath(dest_full, workspace_path)
        return self._get_file_info(dest_full, rel_path)
    
    async def move_file(self,
                       session_id: str,
                       source_path: str,
                       dest_path: str) -> Dict[str, Any]:
        """
        Move file within workspace
        
        Args:
            session_id: Session identifier
            source_path: Source file path
            dest_path: Destination file path
            
        Returns:
            Destination file information
        """
        workspace_path = self.get_workspace_path(session_id)
        source_full = os.path.join(workspace_path, source_path)
        dest_full = os.path.join(workspace_path, dest_path)
        
        if not os.path.exists(source_full):
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dest_full), exist_ok=True)
        
        # Move file
        shutil.move(source_full, dest_full)
        
        rel_path = os.path.relpath(dest_full, workspace_path)
        return self._get_file_info(dest_full, rel_path)
    
    async def get_workspace_size(self, session_id: str) -> Dict[str, Any]:
        """
        Get workspace size information
        
        Args:
            session_id: Session identifier
            
        Returns:
            Size information
        """
        workspace_path = self.get_workspace_path(session_id)
        
        if not os.path.exists(workspace_path):
            return {"total_size": 0, "file_count": 0}
        
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(workspace_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        return {
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count
        }
    
    async def cleanup_workspace(self, session_id: str) -> bool:
        """
        Clean up (delete) entire workspace
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        workspace_path = self.get_workspace_path(session_id)
        
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
            return True
        return False
    
    def get_file_hash(self, filepath: str) -> str:
        """
        Calculate file hash
        
        Args:
            filepath: File path
            
        Returns:
            SHA256 hash of file
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
