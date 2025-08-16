"""
Git session management API routes
Handles version control operations for sessions
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
import logging

from app.services.git_session_manager import GitSessionManager
from app.models.database import get_db, Session as DBSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/git", tags=["git"])

# Global manager
git_session_manager = GitSessionManager()

@router.post("/sessions/{session_id}/init")
async def initialize_session(session_id: str):
    """Initialize a new git session"""
    try:
        session_info = git_session_manager.create_session(session_id)
        return {
            "status": "initialized",
            "session_id": session_id,
            "session_info": session_info
        }
    except Exception as e:
        logger.error(f"Failed to initialize session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Session initialization failed: {str(e)}")

@router.get("/sessions/{session_id}/info")
async def get_session_info(session_id: str):
    """Get session information"""
    try:
        session_info = git_session_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")

@router.post("/sessions/{session_id}/branches")
async def create_branch(session_id: str, branch_name: str, from_commit: Optional[str] = None):
    """Create a new branch"""
    try:
        if from_commit:
            branch = git_session_manager.fork_branch(session_id, from_commit, branch_name)
        else:
            branch = git_session_manager.create_execution_branch(session_id, branch_name)
        
        return {
            "status": "created",
            "branch_name": branch,
            "from_commit": from_commit
        }
    except Exception as e:
        logger.error(f"Failed to create branch {branch_name} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Branch creation failed: {str(e)}")

@router.get("/sessions/{session_id}/history")
async def get_commit_history(session_id: str, limit: int = 50):
    """Get commit history for session"""
    try:
        history = git_session_manager.get_commit_history(session_id, limit=limit)
        return {
            "session_id": session_id,
            "commits": history,
            "total": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to get history for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.get("/sessions/{session_id}/tree")
async def get_branch_tree(session_id: str):
    """Get branch tree for session"""
    try:
        tree = git_session_manager.get_branch_tree(session_id)
        return {
            "session_id": session_id,
            "tree": tree
        }
    except Exception as e:
        logger.error(f"Failed to get branch tree for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get branch tree: {str(e)}")

@router.post("/sessions/{session_id}/commit")
async def commit_execution(
    session_id: str,
    branch_name: str,
    code: str,
    result: Dict[str, Any],
    artifacts: List[str] = None
):
    """Commit code execution to git"""
    try:
        commit_sha = git_session_manager.commit_execution(
            session_id=session_id,
            branch_name=branch_name,
            code=code,
            result=result,
            artifacts=artifacts or []
        )
        
        return {
            "status": "committed",
            "commit_sha": commit_sha,
            "branch_name": branch_name
        }
    except Exception as e:
        logger.error(f"Failed to commit execution for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")

@router.get("/sessions/{session_id}/branches")
async def list_branches(session_id: str):
    """List all branches for session"""
    try:
        tree = git_session_manager.get_branch_tree(session_id)
        branches = tree.get("branches", {})
        
        return {
            "session_id": session_id,
            "branches": list(branches.keys()),
            "total": len(branches)
        }
    except Exception as e:
        logger.error(f"Failed to list branches for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list branches: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a git session"""
    try:
        # This would remove the session directory
        # Implementation depends on cleanup requirements
        return {
            "status": "deleted",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Session deletion failed: {str(e)}")
