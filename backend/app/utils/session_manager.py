"""
Session Manager
Handles user sessions and state management
"""

import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
import json
import os
import asyncio
from pathlib import Path
import shutil
import logging

class SessionManager:
    """
    Enhanced session manager with persistence, conversation history, and isolation
    """
    
    def __init__(self, storage_path: str = "/tmp/aido_sessions"):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = 100
        self.session_timeout = 3600 * 24  # 24 hours in seconds
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Load existing sessions from disk on startup
        asyncio.create_task(self._load_sessions_from_disk())
    
    async def create_session(self, 
                            session_id: Optional[str] = None,
                            workspace_path: Optional[str] = None,
                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new session
        
        Args:
            session_id: Optional session ID (will generate if not provided)
            workspace_path: Path to session workspace
            user_id: User ID associated with session
        
        Returns:
            Session information
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Create isolated workspace directory
        if not workspace_path:
            workspace_path = str(self.storage_path / "workspaces" / session_id)
        
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        
        session = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "workspace_path": workspace_path,
            "user_id": user_id or "anonymous",
            "executions": [],
            "conversation_history": [],
            "current_branch": "main",
            "branch_code_cache": {},
            "uploaded_files": [],
            "sandbox_state": {
                "variables": {},
                "imports": [],
                "working_directory": workspace_path
            },
            "metadata": {},
            "active": True,
            "version_tree": {
                "main": {
                    "commits": [],
                    "current_head": None
                }
            }
        }
        
        self.sessions[session_id] = session
        
        # Persist session to disk
        await self._save_session_to_disk(session_id)
        
        # Clean up old sessions if we're at the limit
        if len(self.sessions) > self.max_sessions:
            await self._cleanup_old_sessions()
        
        self.logger.info(f"Created new session: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data or None if not found
        """
        session = self.sessions.get(session_id)
        
        if session:
            # Update last activity
            session["last_activity"] = datetime.utcnow().isoformat()
            # Persist updated activity to disk
            await self._save_session_to_disk(session_id)
        
        return session
    
    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            data: Data to update
        
        Returns:
            True if updated, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.update(data)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        # Persist changes to disk
        await self._save_session_to_disk(session_id)
        
        return True
    
    async def add_execution(self, session_id: str, execution: Dict[str, Any]) -> bool:
        """
        Add execution record to session
        
        Args:
            session_id: Session identifier
            execution: Execution data
        
        Returns:
            True if added, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session["executions"].append(execution)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        # Keep only last 100 executions in memory
        if len(session["executions"]) > 100:
            session["executions"] = session["executions"][-100:]
        
        # Persist execution to disk
        await self._save_session_to_disk(session_id)
        
        return True
    
    async def list_sessions(self, 
                           user_id: Optional[str] = None,
                           active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all sessions
        
        Args:
            user_id: Filter by user ID
            active_only: Only return active sessions
        
        Returns:
            List of sessions
        """
        sessions = list(self.sessions.values())
        
        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]
        
        if active_only:
            sessions = [s for s in sessions if s.get("active", True)]
        
        # Sort by last activity
        sessions.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        
        return sessions
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if deleted, False if not found
        """
        if session_id in self.sessions:
            # Clean up session workspace
            session = self.sessions[session_id]
            workspace_path = Path(session.get("workspace_path", ""))
            if workspace_path.exists():
                shutil.rmtree(workspace_path, ignore_errors=True)
            
            # Remove session file
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            del self.sessions[session_id]
            self.logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    async def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        current_time = datetime.utcnow()
        sessions_to_delete = []
        
        for session_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session.get("last_activity", session["created_at"]))
            time_diff = (current_time - last_activity).total_seconds()
            
            if time_diff > self.session_timeout:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            await self.delete_session(session_id)
        
        if sessions_to_delete:
            self.logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics
        
        Returns:
            Statistics about sessions
        """
        total_sessions = len(self.sessions)
        active_sessions = len([s for s in self.sessions.values() if s.get("active", True)])
        total_executions = sum(len(s.get("executions", [])) for s in self.sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_executions": total_executions,
            "max_sessions": self.max_sessions,
            "session_timeout_hours": self.session_timeout / 3600
        }
    
    def export_session(self, session_id: str, file_path: str) -> bool:
        """
        Export session to JSON file
        
        Args:
            session_id: Session identifier
            file_path: Path to save file
        
        Returns:
            True if exported, False otherwise
        """
        if session_id not in self.sessions:
            return False
        
        try:
            with open(file_path, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error exporting session: {e}")
            return False
    
    def import_session(self, file_path: str) -> Optional[str]:
        """
        Import session from JSON file
        
        Args:
            file_path: Path to JSON file
        
        Returns:
            Session ID if imported, None otherwise
        """
        try:
            with open(file_path, 'r') as f:
                session_data = json.load(f)
            
            session_id = session_data.get("session_id", str(uuid.uuid4()))
            self.sessions[session_id] = session_data
            
            return session_id
        except Exception as e:
            print(f"Error importing session: {e}")
            return None

    # New methods for enhanced session management
    
    async def add_conversation_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Add a conversation message to session history
        
        Args:
            session_id: Session identifier
            message: Message data with role, content, timestamp
        
        Returns:
            True if added, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        message["timestamp"] = datetime.utcnow().isoformat()
        session["conversation_history"].append(message)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        # Keep only last 200 messages in memory
        if len(session["conversation_history"]) > 200:
            session["conversation_history"] = session["conversation_history"][-200:]
        
        await self._save_session_to_disk(session_id)
        return True
    
    async def get_conversation_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of conversation messages
        """
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        history = session.get("conversation_history", [])
        if limit:
            history = history[-limit:]
        
        return history
    
    async def update_branch_state(self, session_id: str, branch: str, code: str) -> bool:
        """
        Update branch code cache
        
        Args:
            session_id: Session identifier
            branch: Branch name
            code: Current code for the branch
        
        Returns:
            True if updated, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session["branch_code_cache"][branch] = code
        session["current_branch"] = branch
        session["last_activity"] = datetime.utcnow().isoformat()
        
        await self._save_session_to_disk(session_id)
        return True
    
    async def add_uploaded_file(self, session_id: str, file_info: Dict[str, Any]) -> bool:
        """
        Track uploaded files for a session
        
        Args:
            session_id: Session identifier
            file_info: File information (name, path, size, etc.)
        
        Returns:
            True if added, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        file_info["uploaded_at"] = datetime.utcnow().isoformat()
        session["uploaded_files"].append(file_info)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        await self._save_session_to_disk(session_id)
        return True
    
    async def update_sandbox_state(self, session_id: str, variables: Dict[str, Any], imports: List[str]) -> bool:
        """
        Update sandbox execution state
        
        Args:
            session_id: Session identifier
            variables: Current variables in scope
            imports: List of imported modules
        
        Returns:
            True if updated, False if session not found
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session["sandbox_state"]["variables"] = variables
        session["sandbox_state"]["imports"] = imports
        session["last_activity"] = datetime.utcnow().isoformat()
        
        await self._save_session_to_disk(session_id)
        return True
    
    async def restore_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore session from disk if not in memory
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data if restored, None otherwise
        """
        if session_id in self.sessions:
            return self.sessions[session_id]
        
        session_file = self.storage_path / f"{session_id}.json"
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Verify workspace still exists
            workspace_path = Path(session_data.get("workspace_path", ""))
            if not workspace_path.exists():
                workspace_path.mkdir(parents=True, exist_ok=True)
            
            self.sessions[session_id] = session_data
            self.logger.info(f"Restored session from disk: {session_id}")
            return session_data
            
        except Exception as e:
            self.logger.error(f"Failed to restore session {session_id}: {e}")
            return None
    
    async def _save_session_to_disk(self, session_id: str):
        """Save session data to disk"""
        if session_id not in self.sessions:
            return
        
        session_file = self.storage_path / f"{session_id}.json"
        try:
            with open(session_file, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save session {session_id}: {e}")
    
    async def _load_sessions_from_disk(self):
        """Load existing sessions from disk on startup"""
        try:
            for session_file in self.storage_path.glob("*.json"):
                session_id = session_file.stem
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Check if session is still valid (not expired)
                    last_activity = datetime.fromisoformat(session_data.get("last_activity", session_data["created_at"]))
                    if (datetime.utcnow() - last_activity).total_seconds() < self.session_timeout:
                        self.sessions[session_id] = session_data
                        self.logger.info(f"Loaded session from disk: {session_id}")
                    else:
                        # Clean up expired session
                        session_file.unlink()
                        workspace_path = Path(session_data.get("workspace_path", ""))
                        if workspace_path.exists():
                            shutil.rmtree(workspace_path, ignore_errors=True)
                        
                except Exception as e:
                    self.logger.error(f"Failed to load session {session_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load sessions from disk: {e}")

