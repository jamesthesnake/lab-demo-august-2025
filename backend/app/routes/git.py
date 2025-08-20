"""
Git session management API routes
Handles version control operations for sessions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import os
import json
from pathlib import Path

from ..services.git_service import GitService
from app.models.database import get_db, Session as DBSession
from pydantic import BaseModel

# File-based commit storage
COMMITS_DIR = Path("/tmp/aido-commits")
COMMITS_DIR.mkdir(exist_ok=True)

def get_commits_file(session_id: str) -> Path:
    return COMMITS_DIR / f"{session_id}.json"

def load_session_commits(session_id: str) -> List[Dict[str, Any]]:
    commits_file = get_commits_file(session_id)
    if commits_file.exists():
        try:
            with open(commits_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load commits for {session_id}: {e}")
    return []

def save_session_commits(session_id: str, commits: List[Dict[str, Any]]):
    commits_file = get_commits_file(session_id)
    try:
        with open(commits_file, 'w') as f:
            json.dump(commits, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save commits for {session_id}: {e}")

def get_commits_by_branch(session_id: str, branch: str) -> List[Dict[str, Any]]:
    """Get commits filtered by branch"""
    all_commits = load_session_commits(session_id)
    return [commit for commit in all_commits if commit.get('branch') == branch]

class CommitRequest(BaseModel):
    message: str
    code: str
    branch: Optional[str] = "main"

class BranchCreateRequest(BaseModel):
    name: str
    from_branch: Optional[str] = None

class BranchSwitchRequest(BaseModel):
    branch: str

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
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@router.post("/commit/{session_id}")
async def manual_commit(session_id: str, request: CommitRequest):
    """Manually commit code to git for a session"""
    try:
        # Get current branch from request or default to main
        current_branch = request.branch
        
        # Create commit entry in memory
        commit_data = {
            "sha": f"commit_{int(time.time())}_{hash(request.code) % 10000:04d}",
            "message": request.message,
            "author": "AIDO User",
            "timestamp": datetime.now().isoformat(),
            "branch": current_branch,
            "code": request.code
        }
        
        # Load existing commits and add new one
        commits = load_session_commits(session_id)
        commits.insert(0, commit_data)  # Insert at beginning for latest first
        
        # Keep only last 50 commits
        if len(commits) > 50:
            commits = commits[:50]
        
        # Save commits to file
        save_session_commits(session_id, commits)
        
        logger.info(f"Manual commit created for session {session_id}: {commit_data['sha']} - Total commits: {len(commits)}")
        
        return {
            "status": "committed",
            "sha": commit_data["sha"],
            "message": commit_data["message"],
            "branch": commit_data["branch"],
            "timestamp": commit_data["timestamp"]
        }
    except Exception as e:
        logger.error(f"Manual commit failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")

@router.get("/sessions/{session_id}/branches")
async def get_branches(session_id: str):
    """Get all branches for a session"""
    try:
        from app.main import git_service
        
        # Initialize session if needed
        if session_id not in git_service.repos:
            await git_service.init_session_repo(session_id)
        
        repo = git_service.repos[session_id]
        branches = []
        current_branch = repo.active_branch.name
        
        for branch in repo.branches:
            branches.append({
                "name": branch.name,
                "current": branch.name == current_branch,
                "lastCommit": str(branch.commit.hexsha[:8]) if branch.commit else None
            })
        
        return {
            "branches": branches,
            "current_branch": current_branch
        }
    except Exception as e:
        logger.error(f"Failed to get branches for session {session_id}: {e}")
        # Return default if git fails
        return {
            "branches": [{"name": "main", "current": True}],
            "current_branch": "main"
        }

@router.post("/sessions/{session_id}/branches")
async def create_branch(session_id: str, request: BranchCreateRequest):
    """Create a new branch"""
    try:
        from app.main import git_service
        
        if session_id not in git_service.repos:
            await git_service.init_session_repo(session_id)
        
        repo = git_service.repos[session_id]
        
        # Create new branch from current or specified branch
        if request.from_branch:
            source_branch = repo.branches[request.from_branch]
            new_branch = repo.create_head(request.name, source_branch.commit)
        else:
            new_branch = repo.create_head(request.name)
        
        return {
            "status": "created",
            "branch_name": request.name,
            "from_branch": request.from_branch or repo.active_branch.name
        }
    except Exception as e:
        logger.error(f"Failed to create branch for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create branch: {str(e)}")

@router.post("/sessions/{session_id}/switch")
async def switch_branch(session_id: str, request: BranchSwitchRequest):
    """Switch to a different branch"""
    try:
        from app.main import git_service
        
        if session_id not in git_service.repos:
            await git_service.init_session_repo(session_id)
        
        repo = git_service.repos[session_id]
        
        # Switch to the specified branch
        if request.branch in [b.name for b in repo.branches]:
            repo.heads[request.branch].checkout()
        else:
            raise HTTPException(status_code=404, detail=f"Branch '{request.branch}' not found")
        
        return {
            "status": "switched",
            "branch": request.branch,
            "commit": str(repo.active_branch.commit.hexsha[:8])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch branch for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch branch: {str(e)}")

@router.get("/sessions/{session_id}/history")
async def get_commit_history(session_id: str, limit: int = 50, branch: Optional[str] = None):
    """Get commit history for session, optionally filtered by branch"""
    try:
        if branch:
            # Get commits filtered by branch
            commits = get_commits_by_branch(session_id, branch)
            logger.info(f"Getting history for session {session_id} branch {branch}: {len(commits)} commits found")
        else:
            # Get all commits
            commits = load_session_commits(session_id)
            logger.info(f"Getting history for session {session_id}: {len(commits)} commits found")
        
        # Apply limit
        if limit and len(commits) > limit:
            commits = commits[:limit]
        
        return {
            "session_id": session_id,
            "commits": commits,
            "total": len(commits),
            "branch": branch
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


@router.post("/sessions/{session_id}/checkout/{commit_sha}")
async def checkout_commit(session_id: str, commit_sha: str, restore_state: bool = True):
    """Checkout a specific commit and optionally restore execution state"""
    try:
        from app.main import git_service, kernel_manager
        
        if not git_service:
            raise HTTPException(status_code=503, detail="Git service not available")
        
        # Checkout the commit in git
        commit_info = await git_service.checkout_commit(session_id, commit_sha)
        
        # Restore execution state if requested
        state_restored = False
        if restore_state and kernel_manager:
            state_restored = await kernel_manager.restore_session_state(session_id, commit_sha)
        
        return {
            "status": "checked_out",
            "commit": commit_info,
            "state_restored": state_restored,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Failed to checkout commit {commit_sha} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")

@router.post("/sessions/{session_id}/restore/{commit_sha}")
async def restore_to_commit(session_id: str, commit_sha: str, create_branch: bool = False, branch_name: str = None):
    """Restore session to a previous commit state"""
    try:
        from app.main import git_service, kernel_manager
        
        if not git_service:
            raise HTTPException(status_code=503, detail="Git service not available")
        
        # Create new branch if requested
        if create_branch:
            if not branch_name:
                branch_name = f"restore-{commit_sha[:8]}-{int(time.time())}"
            
            branch_info = await git_service.create_branch(session_id, branch_name, commit_sha)
            await git_service.switch_branch(session_id, branch_name)
        else:
            # Just checkout the commit
            await git_service.checkout_commit(session_id, commit_sha)
        
        # Restore execution state
        state_restored = False
        if kernel_manager:
            state_restored = await kernel_manager.restore_session_state(session_id, commit_sha)
        
        return {
            "status": "restored",
            "commit_sha": commit_sha,
            "branch_created": create_branch,
            "branch_name": branch_name if create_branch else None,
            "state_restored": state_restored
        }
    except Exception as e:
        logger.error(f"Failed to restore to commit {commit_sha} for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@router.get("/sessions/{session_id}/diff/{commit_sha1}/{commit_sha2}")
async def get_commit_diff(session_id: str, commit_sha1: str, commit_sha2: str):
    """Get diff between two commits"""
    try:
        from app.main import git_service
        
        if not git_service:
            raise HTTPException(status_code=503, detail="Git service not available")
        
        diff_info = await git_service.get_diff(session_id, commit_sha1, commit_sha2)
        
        return {
            "session_id": session_id,
            "commit_sha1": commit_sha1,
            "commit_sha2": commit_sha2,
            "diff": diff_info
        }
    except Exception as e:
        logger.error(f"Failed to get diff for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Diff failed: {str(e)}")

@router.post("/sessions/{session_id}/merge")
async def merge_branches(session_id: str, source_branch: str, target_branch: str = "main"):
    """Merge one branch into another"""
    try:
        from app.main import git_service
        
        if not git_service:
            raise HTTPException(status_code=503, detail="Git service not available")
        
        merge_result = await git_service.merge_branches(session_id, source_branch, target_branch)
        
        return {
            "session_id": session_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "result": merge_result
        }
    except Exception as e:
        logger.error(f"Failed to merge branches for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Merge failed: {str(e)}")

@router.post("/sessions/{session_id}/checkpoint")
async def create_checkpoint(session_id: str):
    """Create a checkpoint of current session state"""
    try:
        from app.main import kernel_manager
        
        if not kernel_manager:
            raise HTTPException(status_code=503, detail="Kernel manager not available")
        
        checkpoint_id = await kernel_manager.checkpoint_session(session_id)
        
        if checkpoint_id:
            return {
                "status": "checkpoint_created",
                "checkpoint_id": checkpoint_id,
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create checkpoint")
            
    except Exception as e:
        logger.error(f"Failed to create checkpoint for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Checkpoint failed: {str(e)}")

@router.get("/sessions/{session_id}/file/{commit_sha}/{file_path:path}")
async def get_file_content(session_id: str, commit_sha: str, file_path: str):
    """Get file content from a specific commit"""
    try:
        from app.main import git_service
        
        if not git_service:
            raise HTTPException(status_code=503, detail="Git service not available")
        
        content = await git_service.get_file_content(session_id, file_path, commit_sha)
        
        return {
            "session_id": session_id,
            "commit_sha": commit_sha,
            "file_path": file_path,
            "content": content
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Failed to get file content for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get file content: {str(e)}")

@router.get("/api/git/sessions/{session_id}/commits/{commit_sha}/code")
async def get_commit_code(session_id: str, commit_sha: str):
    """Get the code from a specific commit"""
    try:
        git_service = GitService()
        
        # Get commit details
        commits = await git_service.get_commits_by_branch(session_id, "main")
        
        # Find the specific commit
        target_commit = None
        for commit in commits:
            if commit.sha.startswith(commit_sha):
                target_commit = commit
                break
        
        if not target_commit:
            raise HTTPException(status_code=404, detail="Commit not found")
        
        # Extract code from execution_info instead of metadata
        code = ""
        if hasattr(target_commit, 'execution_info') and target_commit.execution_info:
            if isinstance(target_commit.execution_info, dict):
                code = target_commit.execution_info.get('code', '')
            elif hasattr(target_commit.execution_info, 'get'):
                code = target_commit.execution_info.get('code', '')
        
        # If no code found in execution_info, try to read from the committed file
        if not code:
            try:
                # Try to find the execution file in the commit
                workspace_path = f"/app/workspaces/{session_id}"
                executions_dir = os.path.join(workspace_path, "executions")
                if os.path.exists(executions_dir):
                    # Find the most recent execution file
                    execution_files = [f for f in os.listdir(executions_dir) if f.endswith('.py')]
                    if execution_files:
                        execution_files.sort(reverse=True)
                        latest_file = os.path.join(executions_dir, execution_files[0])
                        with open(latest_file, 'r') as f:
                            content = f.read()
                            # Extract just the code part (skip the header comments)
                            lines = content.split('\n')
                            code_lines = []
                            skip_header = True
                            for line in lines:
                                if skip_header and (line.startswith('#') or line.strip() == ''):
                                    continue
                                skip_header = False
                                code_lines.append(line)
                            code = '\n'.join(code_lines)
            except Exception as e:
                logger.warning(f"Could not read execution file: {e}")
        
        return {
            "commit_sha": target_commit.sha,
            "code": code,
            "message": target_commit.message,
            "timestamp": target_commit.timestamp
        }
        
    except Exception as e:
        logger.error(f"Error retrieving commit code: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve commit code")

@router.get("/api/git/sessions/{session_id}/artifacts")
async def get_session_artifacts(session_id: str, branch: str = "main"):
    """Get artifacts filtered by branch"""
    try:
        # Get commits for the specified branch
        commits = get_commits_by_branch(session_id, branch)
        
        # Collect all artifacts from commits on this branch
        branch_artifacts = []
        for commit in commits:
            if 'artifacts' in commit:
                for artifact in commit['artifacts']:
                    # Add commit info to artifact for context
                    artifact_with_context = {
                        **artifact,
                        'commit_sha': commit.get('sha'),
                        'commit_message': commit.get('message'),
                        'timestamp': commit.get('timestamp'),
                        'branch': branch
                    }
                    branch_artifacts.append(artifact_with_context)
        
        return {
            "session_id": session_id,
            "branch": branch,
            "artifacts": branch_artifacts,
            "total": len(branch_artifacts)
        }
    except Exception as e:
        logger.error(f"Failed to get artifacts for session {session_id}, branch {branch}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get artifacts: {str(e)}")

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
