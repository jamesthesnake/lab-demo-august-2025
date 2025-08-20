"""
Session management API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
from ..utils.session_manager import SessionManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Global session manager instance
session_manager = SessionManager()

class ConversationMessage(BaseModel):
    role: str
    content: str

class BranchUpdate(BaseModel):
    branch: str
    code: str

class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    type: str

class SandboxState(BaseModel):
    variables: Dict[str, Any]
    imports: List[str]

@router.post("/create")
async def create_session(user_id: Optional[str] = None):
    """Create a new session"""
    try:
        session = await session_manager.create_session(user_id=user_id)
        return session
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session by ID, restore from disk if needed"""
    try:
        # Try to get from memory first
        session = await session_manager.get_session(session_id)
        
        # If not in memory, try to restore from disk
        if not session:
            session = await session_manager.restore_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        success = await session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "deleted", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.put("/{session_id}/activity")
async def update_activity(session_id: str):
    """Update session last activity timestamp"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "updated", "last_activity": session["last_activity"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update activity for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update activity: {str(e)}")

@router.post("/{session_id}/conversation")
async def add_conversation_message(session_id: str, message: ConversationMessage):
    """Add a conversation message to session history"""
    try:
        success = await session_manager.add_conversation_message(
            session_id, 
            message.dict()
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "added", "message": message.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add conversation message to session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add message: {str(e)}")

@router.get("/{session_id}/conversation")
async def get_conversation_history(session_id: str, limit: Optional[int] = None):
    """Get conversation history for a session"""
    try:
        history = await session_manager.get_conversation_history(session_id, limit)
        return {"conversation_history": history}
    except Exception as e:
        logger.error(f"Failed to get conversation history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")

@router.put("/{session_id}/branch")
async def update_branch_state(session_id: str, branch_update: BranchUpdate):
    """Update branch code cache"""
    try:
        success = await session_manager.update_branch_state(
            session_id,
            branch_update.branch,
            branch_update.code
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "updated", "branch": branch_update.branch}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update branch state for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update branch state: {str(e)}")

@router.post("/{session_id}/files")
async def track_uploaded_file(session_id: str, file_info: FileInfo):
    """Track uploaded files for a session"""
    try:
        success = await session_manager.add_uploaded_file(
            session_id,
            file_info.dict()
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "tracked", "file": file_info.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track uploaded file for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to track file: {str(e)}")

@router.get("/{session_id}/files")
async def get_uploaded_files(session_id: str):
    """Get list of uploaded files for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"uploaded_files": session.get("uploaded_files", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get uploaded files for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get uploaded files: {str(e)}")

@router.put("/{session_id}/sandbox")
async def update_sandbox_state(session_id: str, sandbox_state: SandboxState):
    """Update sandbox execution state"""
    try:
        success = await session_manager.update_sandbox_state(
            session_id,
            sandbox_state.variables,
            sandbox_state.imports
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "updated", "sandbox_state": sandbox_state.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update sandbox state for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update sandbox state: {str(e)}")

@router.get("/{session_id}/sandbox")
async def get_sandbox_state(session_id: str):
    """Get current sandbox state for a session"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"sandbox_state": session.get("sandbox_state", {})}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sandbox state for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sandbox state: {str(e)}")

@router.get("/")
async def list_sessions(user_id: Optional[str] = None, active_only: bool = True):
    """List all sessions"""
    try:
        sessions = await session_manager.list_sessions(user_id=user_id, active_only=active_only)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.get("/stats")
async def get_session_stats():
    """Get session statistics"""
    try:
        stats = await session_manager.get_session_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session stats: {str(e)}")
