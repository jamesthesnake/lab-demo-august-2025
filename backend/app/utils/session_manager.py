"""
Session Manager
Handles user sessions and state management
"""

import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime
import json
import os

class SessionManager:
    """
    Manages user sessions
    In production, this would use Redis or a database
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_sessions = 100
        self.session_timeout = 3600 * 24  # 24 hours in seconds
    
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
        
        session = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "workspace_path": workspace_path or f"/tmp/workspaces/{session_id}",
            "user_id": user_id or "anonymous",
            "executions": [],
            "metadata": {},
            "active": True
        }
        
        self.sessions[session_id] = session
        
        # Clean up old sessions if we're at the limit
        if len(self.sessions) > self.max_sessions:
            await self._cleanup_old_sessions()
        
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
            del self.sessions[session_id]
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
            del self.sessions[session_id]
        
        if sessions_to_delete:
            print(f"Cleaned up {len(sessions_to_delete)} old sessions")
    
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

