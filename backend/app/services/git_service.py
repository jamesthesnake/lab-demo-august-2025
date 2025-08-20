"""
Git Version Control Service
Manages version control for code execution history
"""

import os
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import git
from git import Repo, InvalidGitRepositoryError
import aiofiles
import asyncio
import logging
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

@dataclass
class CommitInfo:
    """Information about a git commit"""
    sha: str
    message: str
    author: str
    timestamp: datetime
    parent_sha: Optional[str]
    branch: str
    files_changed: List[str]
    execution_info: Optional[Dict[str, Any]] = None

@dataclass
class BranchInfo:
    """Information about a git branch"""
    name: str
    current: bool
    commits_ahead: int
    commits_behind: int
    last_commit: Optional[CommitInfo]

class GitService:
    """
    Manages Git version control for session workspaces
    """
    
    def __init__(self, workspace_base: str = "/app/workspaces"):
        """
        Initialize Git Service
        
        Args:
            workspace_base: Base directory for session workspaces
        """
        self.workspace_base = workspace_base
        self.repos: Dict[str, Repo] = {}
        
        # Ensure workspace directory exists
        os.makedirs(workspace_base, exist_ok=True)
        
        logger.info(f"GitService initialized with workspace: {workspace_base}")
    
    async def init_session_repo(self, session_id: str) -> str:
        """
        Initialize a Git repository for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Repository path
        """
        repo_path = os.path.join(self.workspace_base, session_id)
        
        # Create directory if it doesn't exist
        os.makedirs(repo_path, exist_ok=True)
        
        # Check if repo already exists
        try:
            repo = Repo(repo_path)
            self.repos[session_id] = repo
            logger.info(f"Existing repository found for session {session_id}")
            return repo_path
        except InvalidGitRepositoryError:
            pass
        
        # Initialize new repository
        repo = Repo.init(repo_path)
        
        # Configure git user for the repo
        with repo.config_writer() as config:
            config.set_value("user", "name", "AIDO Lab")
            config.set_value("user", "email", "aidolab@localhost")
        
        # Create initial files
        readme_path = os.path.join(repo_path, "README.md")
        async with aiofiles.open(readme_path, 'w') as f:
            await f.write(f"""# AIDO Lab Session: {session_id}

Created: {datetime.utcnow().isoformat()}

This repository tracks the execution history of your data science analysis session.

## Files
- `README.md` - This file
- `session.ipynb` - Jupyter notebook with all executions
- `history.json` - Execution history metadata
- `outputs/` - Generated plots and data files

## Branches
Each exploration path creates a new branch, allowing you to experiment freely and return to any previous state.
""")
        
        # Create directories
        os.makedirs(os.path.join(repo_path, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(repo_path, "data"), exist_ok=True)
        
        # Create .gitignore
        gitignore_path = os.path.join(repo_path, ".gitignore")
        async with aiofiles.open(gitignore_path, 'w') as f:
            await f.write("""# Python
__pycache__/
*.pyc
.ipynb_checkpoints/

# Data files (can be large)
*.h5
*.hdf5
*.parquet

# Temporary files
*.tmp
*.bak
~*

# OS files
.DS_Store
Thumbs.db
""")
        
        # Create initial history file
        history_path = os.path.join(repo_path, "history.json")
        initial_history = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "executions": []
        }
        async with aiofiles.open(history_path, 'w') as f:
            await f.write(json.dumps(initial_history, indent=2))
        
        # Add files and create initial commit
        repo.index.add(["README.md", ".gitignore", "history.json"])
        repo.index.commit("Initial session setup")
        
        self.repos[session_id] = repo
        
        logger.info(f"Repository initialized for session {session_id}")
        return repo_path
    
    async def save_execution(self,
                            session_id: str,
                            code: str,
                            results: Dict[str, Any],
                            metadata: Optional[Dict[str, Any]] = None) -> CommitInfo:
        """
        Save code execution as a git commit
        
        Args:
            session_id: Session identifier
            code: Executed code
            results: Execution results
            metadata: Additional metadata
            
        Returns:
            CommitInfo for the created commit
        """
        if session_id not in self.repos:
            await self.init_session_repo(session_id)
        
        repo = self.repos[session_id]
        repo_path = repo.working_dir
        
        # Update history file
        history_path = os.path.join(repo_path, "history.json")
        async with aiofiles.open(history_path, 'r') as f:
            history = json.loads(await f.read())
        
        execution_entry = {
            "execution_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "code": code,
            "results": {
                "stdout": results.get("stdout", ""),
                "stderr": results.get("stderr", ""),
                "display_data_count": len(results.get("display_data", [])),
                "errors": results.get("errors", []),
                "status": results.get("status", "ok")
            },
            "artifacts": results.get("artifacts", []),
            "metadata": metadata or {}
        }
        
        history["executions"].append(execution_entry)
        
        async with aiofiles.open(history_path, 'w') as f:
            await f.write(json.dumps(history, indent=2))
        
        # Save code to a Python file for better diff viewing
        code_file = f"execution_{len(history['executions']):04d}.py"
        code_path = os.path.join(repo_path, "executions", code_file)
        os.makedirs(os.path.dirname(code_path), exist_ok=True)
        
        async with aiofiles.open(code_path, 'w') as f:
            await f.write(f"""# Execution {len(history['executions'])}
# Timestamp: {execution_entry['timestamp']}
# Status: {execution_entry['results']['status']}

{code}
""")
        
        # Track all files that might have been created/modified
        repo.index.add(["history.json", f"executions/{code_file}"])
        
        # Add any output files (plots, CSVs, etc.)
        outputs_dir = os.path.join(repo_path, "outputs")
        if os.path.exists(outputs_dir):
            for file in os.listdir(outputs_dir):
                repo.index.add([f"outputs/{file}"])
        
        # Add session notebook if it exists
        notebook_path = os.path.join(repo_path, "session.ipynb")
        if os.path.exists(notebook_path):
            repo.index.add(["session.ipynb"])
        
        # Create commit message
        code_preview = code[:50].replace('\n', ' ')
        if len(code) > 50:
            code_preview += "..."
        
        commit_message = f"Execute: {code_preview}"
        if results.get("status") == "error":
            commit_message = f"[ERROR] {commit_message}"
        
        # Commit changes
        commit = repo.index.commit(commit_message)
        
        # Create CommitInfo
        commit_info = CommitInfo(
            sha=commit.hexsha,
            message=commit_message,
            author="AIDO Lab",
            timestamp=datetime.fromtimestamp(commit.committed_date),
            parent_sha=commit.parents[0].hexsha if commit.parents else None,
            branch=repo.active_branch.name,
            files_changed=[item.a_path for item in commit.diff(commit.parents[0] if commit.parents else None)],
            execution_info=execution_entry
        )
        
        logger.info(f"Saved execution for session {session_id}: {commit.hexsha[:8]}")
        return commit_info
    
    async def create_branch(self, 
                           session_id: str, 
                           branch_name: str,
                           from_commit: Optional[str] = None) -> BranchInfo:
        """
        Create a new branch for exploration
        
        Args:
            session_id: Session identifier
            branch_name: Name for the new branch
            from_commit: Commit SHA to branch from (default: current HEAD)
            
        Returns:
            BranchInfo for the created branch
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Sanitize branch name
        branch_name = branch_name.replace(" ", "-").replace("/", "-")
        
        # Create branch
        if from_commit:
            commit = repo.commit(from_commit)
            new_branch = repo.create_head(branch_name, commit)
        else:
            new_branch = repo.create_head(branch_name)
        
        # Switch to new branch
        new_branch.checkout()
        
        logger.info(f"Created branch '{branch_name}' for session {session_id}")
        
        return await self.get_branch_info(session_id, branch_name)
    
    async def switch_branch(self, session_id: str, branch_name: str) -> BranchInfo:
        """
        Switch to a different branch
        
        Args:
            session_id: Session identifier
            branch_name: Branch to switch to
            
        Returns:
            BranchInfo for the target branch
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Check if branch exists
        if branch_name not in [b.name for b in repo.branches]:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        # Switch branch
        branch = repo.branches[branch_name]
        branch.checkout()
        
        logger.info(f"Switched to branch '{branch_name}' for session {session_id}")
        
        return await self.get_branch_info(session_id, branch_name)
    
    async def checkout_commit(self, session_id: str, commit_sha: str) -> Dict[str, Any]:
        """
        Checkout a specific commit (detached HEAD state)
        
        Args:
            session_id: Session identifier
            commit_sha: Commit SHA to checkout
            
        Returns:
            Commit information
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Checkout commit
        commit = repo.commit(commit_sha)
        repo.head.reference = commit
        repo.head.reset(index=True, working_tree=True)
        
        logger.info(f"Checked out commit {commit_sha[:8]} for session {session_id}")
        
        return {
            "sha": commit.hexsha,
            "message": commit.message,
            "author": commit.author.name,
            "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
            "detached": True
        }
    
    async def get_history(self, 
                         session_id: str,
                         branch: Optional[str] = None,
                         limit: int = 50) -> List[CommitInfo]:
        """
        Get commit history for a session
        
        Args:
            session_id: Session identifier
            branch: Specific branch (default: current branch)
            limit: Maximum number of commits to return
            
        Returns:
            List of CommitInfo objects
        """
        if session_id not in self.repos:
            return []
        
        repo = self.repos[session_id]
        
        # Get commits
        if branch:
            commits = list(repo.iter_commits(branch, max_count=limit))
        else:
            commits = list(repo.iter_commits(max_count=limit))
        
        # Load execution history for metadata
        history_path = os.path.join(repo.working_dir, "history.json")
        if os.path.exists(history_path):
            async with aiofiles.open(history_path, 'r') as f:
                history = json.loads(await f.read())
                executions = {e["timestamp"]: e for e in history.get("executions", [])}
        else:
            executions = {}
        
        # Convert to CommitInfo objects
        commit_infos = []
        for commit in commits:
            # Try to match execution info by timestamp
            commit_time = datetime.fromtimestamp(commit.committed_date)
            execution_info = None
            
            # Find closest execution by timestamp
            for exec_time, exec_data in executions.items():
                if abs((datetime.fromisoformat(exec_time) - commit_time).total_seconds()) < 5:
                    execution_info = exec_data
                    break
            
            commit_infos.append(CommitInfo(
                sha=commit.hexsha,
                message=commit.message,
                author=commit.author.name if commit.author else "Unknown",
                timestamp=commit_time,
                parent_sha=commit.parents[0].hexsha if commit.parents else None,
                branch=repo.active_branch.name if not repo.head.is_detached else "detached",
                files_changed=[item.a_path for item in commit.diff(commit.parents[0] if commit.parents else None)],
                execution_info=execution_info
            ))
        
        return commit_infos
    
    async def get_history_tree(self, session_id: str) -> Dict[str, Any]:
        """
        Get the complete history as a tree structure
        
        Args:
            session_id: Session identifier
            
        Returns:
            Tree structure with branches and commits
        """
        if session_id not in self.repos:
            return {"branches": [], "commits": []}
        
        repo = self.repos[session_id]
        
        # Get all branches
        branches = []
        for branch in repo.branches:
            branch_info = await self.get_branch_info(session_id, branch.name)
            branches.append(asdict(branch_info))
        
        # Get all commits with parent relationships
        all_commits = []
        seen_commits = set()
        
        for branch in repo.branches:
            for commit in repo.iter_commits(branch):
                if commit.hexsha not in seen_commits:
                    seen_commits.add(commit.hexsha)
                    
                    commit_info = {
                        "sha": commit.hexsha,
                        "message": commit.message,
                        "author": commit.author.name if commit.author else "Unknown",
                        "timestamp": datetime.fromtimestamp(commit.committed_date).isoformat(),
                        "parents": [p.hexsha for p in commit.parents],
                        "branch": branch.name
                    }
                    all_commits.append(commit_info)
        
        # Sort commits by timestamp
        all_commits.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "branches": branches,
            "commits": all_commits,
            "current_branch": repo.active_branch.name if not repo.head.is_detached else None,
            "head": repo.head.commit.hexsha
        }
    
    async def get_branch_info(self, session_id: str, branch_name: str) -> BranchInfo:
        """
        Get information about a specific branch
        
        Args:
            session_id: Session identifier
            branch_name: Branch name
            
        Returns:
            BranchInfo object
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        if branch_name not in [b.name for b in repo.branches]:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        branch = repo.branches[branch_name]
        
        # Get last commit on branch
        last_commit = None
        if branch.commit:
            last_commit = CommitInfo(
                sha=branch.commit.hexsha,
                message=branch.commit.message,
                author=branch.commit.author.name if branch.commit.author else "Unknown",
                timestamp=datetime.fromtimestamp(branch.commit.committed_date),
                parent_sha=branch.commit.parents[0].hexsha if branch.commit.parents else None,
                branch=branch_name,
                files_changed=[]
            )
        
        # Calculate commits ahead/behind main
        commits_ahead = 0
        commits_behind = 0
        
        if branch_name != "main" and "main" in [b.name for b in repo.branches]:
            main_branch = repo.branches["main"]
            
            # Commits ahead of main
            commits_ahead = len(list(repo.iter_commits(f"main..{branch_name}")))
            
            # Commits behind main
            commits_behind = len(list(repo.iter_commits(f"{branch_name}..main")))
        
        return BranchInfo(
            name=branch_name,
            current=repo.active_branch.name == branch_name if not repo.head.is_detached else False,
            commits_ahead=commits_ahead,
            commits_behind=commits_behind,
            last_commit=last_commit
        )
    
    async def list_branches(self, session_id: str) -> List[BranchInfo]:
        """
        List all branches for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of BranchInfo objects
        """
        if session_id not in self.repos:
            return []
        
        repo = self.repos[session_id]
        
        branches = []
        for branch in repo.branches:
            branch_info = await self.get_branch_info(session_id, branch.name)
            branches.append(branch_info)
        
        return branches
    
    async def merge_branches(self, 
                           session_id: str,
                           source_branch: str,
                           target_branch: str = "main") -> Dict[str, Any]:
        """
        Merge one branch into another
        
        Args:
            session_id: Session identifier
            source_branch: Branch to merge from
            target_branch: Branch to merge into
            
        Returns:
            Merge result information
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Switch to target branch
        target = repo.branches[target_branch]
        target.checkout()
        
        # Merge source branch
        source = repo.branches[source_branch]
        
        try:
            # Attempt merge
            merge_base = repo.merge_base(target, source)[0]
            repo.index.merge_tree(source)
            
            # Create merge commit
            commit_message = f"Merge branch '{source_branch}' into {target_branch}"
            merge_commit = repo.index.commit(
                commit_message,
                parent_commits=[target.commit, source.commit]
            )
            
            logger.info(f"Successfully merged '{source_branch}' into '{target_branch}' for session {session_id}")
            
            return {
                "status": "success",
                "merge_commit": merge_commit.hexsha,
                "message": commit_message,
                "conflicts": []
            }
            
        except git.GitCommandError as e:
            # Handle merge conflicts
            logger.warning(f"Merge conflict between '{source_branch}' and '{target_branch}': {str(e)}")
            
            # Get conflict files
            conflicts = [item.a_path for item in repo.index.entries if item.stage != 0]
            
            # Abort merge
            repo.git.merge("--abort")
            
            return {
                "status": "conflict",
                "message": f"Merge conflict between '{source_branch}' and '{target_branch}'",
                "conflicts": conflicts
            }
    
    async def create_worktree(self, 
                            session_id: str,
                            commit_sha: str,
                            worktree_name: Optional[str] = None) -> str:
        """
        Create a git worktree for parallel exploration
        
        Args:
            session_id: Session identifier
            commit_sha: Commit to create worktree from
            worktree_name: Optional name for worktree
            
        Returns:
            Path to the new worktree
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Generate worktree name if not provided
        if not worktree_name:
            worktree_name = f"exploration-{commit_sha[:8]}"
        
        # Create worktree path
        worktree_path = os.path.join(
            self.workspace_base,
            f"{session_id}-worktrees",
            worktree_name
        )
        
        # Create worktree
        repo.git.worktree("add", worktree_path, commit_sha)
        
        logger.info(f"Created worktree '{worktree_name}' at {worktree_path}")
        
        return worktree_path
    
    async def delete_worktree(self, session_id: str, worktree_path: str):
        """
        Delete a git worktree
        
        Args:
            session_id: Session identifier
            worktree_path: Path to the worktree
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Remove worktree
        repo.git.worktree("remove", worktree_path)
        
        logger.info(f"Deleted worktree at {worktree_path}")
    
    async def get_diff(self, 
                      session_id: str,
                      commit_sha1: str,
                      commit_sha2: Optional[str] = None) -> Dict[str, Any]:
        """
        Get diff between commits
        
        Args:
            session_id: Session identifier
            commit_sha1: First commit
            commit_sha2: Second commit (default: parent of first)
            
        Returns:
            Diff information
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        commit1 = repo.commit(commit_sha1)
        
        if commit_sha2:
            commit2 = repo.commit(commit_sha2)
        elif commit1.parents:
            commit2 = commit1.parents[0]
        else:
            # First commit, diff against empty tree
            return {
                "files_added": [item.a_path for item in commit1.diff(None)],
                "files_modified": [],
                "files_deleted": [],
                "stats": commit1.stats.files
            }
        
        # Get diff
        diff = commit2.diff(commit1)
        
        files_added = []
        files_modified = []
        files_deleted = []
        
        for item in diff:
            if item.new_file:
                files_added.append(item.a_path)
            elif item.deleted_file:
                files_deleted.append(item.a_path)
            else:
                files_modified.append(item.a_path)
        
        return {
            "files_added": files_added,
            "files_modified": files_modified,
            "files_deleted": files_deleted,
            "stats": commit1.stats.files
        }
    
    async def export_notebook(self, 
                            session_id: str,
                            branch: Optional[str] = None) -> str:
        """
        Export session as a Jupyter notebook
        
        Args:
            session_id: Session identifier
            branch: Specific branch to export
            
        Returns:
            Path to exported notebook
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Switch to specified branch if provided
        if branch and branch != repo.active_branch.name:
            await self.switch_branch(session_id, branch)
        
        # Get notebook path
        notebook_path = os.path.join(repo.working_dir, "session.ipynb")
        
        if not os.path.exists(notebook_path):
            # Create notebook from history
            await self._create_notebook_from_history(session_id)
        
        return notebook_path
    
    async def _create_notebook_from_history(self, session_id: str):
        """
        Create a Jupyter notebook from execution history
        
        Args:
            session_id: Session identifier
        """
        repo = self.repos[session_id]
        history_path = os.path.join(repo.working_dir, "history.json")
        
        if not os.path.exists(history_path):
            return
        
        async with aiofiles.open(history_path, 'r') as f:
            history = json.loads(await f.read())
        
        # Create notebook structure
        notebook = {
            "cells": [],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "name": "python",
                    "version": "3.11.0"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }
        
        # Add markdown header
        notebook["cells"].append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# AIDO Lab Session: {session_id}\n",
                f"\n",
                f"Created: {history.get('created_at', 'Unknown')}\n",
                f"\n",
                f"This notebook contains the complete execution history of your analysis session.\n"
            ]
        })
        
        # Add each execution as a cell
        for i, execution in enumerate(history.get("executions", [])):
            # Add code cell
            cell = {
                "cell_type": "code",
                "execution_count": i + 1,
                "metadata": {
                    "execution_time": execution.get("timestamp"),
                    "execution_id": execution.get("execution_id")
                },
                "source": execution.get("code", "").split("\n"),
                "outputs": []
            }
            
            # Add outputs
            results = execution.get("results", {})
            
            if results.get("stdout"):
                cell["outputs"].append({
                    "output_type": "stream",
                    "name": "stdout",
                    "text": results["stdout"].split("\n")
                })
            
            if results.get("stderr"):
                cell["outputs"].append({
                    "output_type": "stream",
                    "name": "stderr",
                    "text": results["stderr"].split("\n")
                })
            
            for error in results.get("errors", []):
                cell["outputs"].append({
                    "output_type": "error",
                    "ename": error.get("ename", "Error"),
                    "evalue": error.get("evalue", ""),
                    "traceback": error.get("traceback", [])
                })
            
            notebook["cells"].append(cell)
        
        # Save notebook
        notebook_path = os.path.join(repo.working_dir, "session.ipynb")
        async with aiofiles.open(notebook_path, 'w') as f:
            await f.write(json.dumps(notebook, indent=2))
        
        # Commit the notebook
        repo.index.add(["session.ipynb"])
        repo.index.commit("Generated notebook from history")
    
    async def cleanup_session(self, session_id: str):
        """
        Clean up a session's repository
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.repos:
            repo = self.repos[session_id]
            
            # Close repository
            repo.close()
            
            # Remove from cache
            del self.repos[session_id]
            
            logger.info(f"Cleaned up repository for session {session_id}")
    
    async def get_file_content(self, 
                              session_id: str,
                              file_path: str,
                              commit_sha: Optional[str] = None) -> str:
        """
        Get content of a file from the repository
        
        Args:
            session_id: Session identifier
            file_path: Path to file relative to repo root
            commit_sha: Specific commit to get file from
            
        Returns:
            File content as string
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        if commit_sha:
            # Get file from specific commit
            commit = repo.commit(commit_sha)
            try:
                file_content = commit.tree[file_path].data_stream.read()
                return file_content.decode('utf-8')
            except KeyError:
                raise FileNotFoundError(f"File '{file_path}' not found in commit {commit_sha[:8]}")
        else:
            # Get file from working directory
            full_path = os.path.join(repo.working_dir, file_path)
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"File '{file_path}' not found")
            
            async with aiofiles.open(full_path, 'r') as f:
                return await f.read()
    
    async def restore_file(self,
                          session_id: str,
                          file_path: str,
                          commit_sha: str):
        """
        Restore a file from a previous commit
        
        Args:
            session_id: Session identifier
            file_path: Path to file to restore
            commit_sha: Commit to restore from
        """
        if session_id not in self.repos:
            raise ValueError(f"No repository found for session {session_id}")
        
        repo = self.repos[session_id]
        
        # Checkout file from commit
        repo.git.checkout(commit_sha, "--", file_path)
        
        # Stage the change
        repo.index.add([file_path])
        
        # Commit the restoration
        repo.index.commit(f"Restored {file_path} from {commit_sha[:8]}")
        
        logger.info(f"Restored {file_path} from commit {commit_sha[:8]}")
    
    async def get_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get repository statistics
        
        Args:
            session_id: Session identifier
            
        Returns:
            Repository statistics
        """
        if session_id not in self.repos:
            return {}
        
        repo = self.repos[session_id]
        
        # Count commits
        total_commits = len(list(repo.iter_commits()))
        
        # Count branches
        total_branches = len(list(repo.branches))
        
        # Get repository size
        repo_size = 0
        for root, dirs, files in os.walk(repo.working_dir):
            # Skip .git directory
            dirs[:] = [d for d in dirs if d != '.git']
            for file in files:
                file_path = os.path.join(root, file)
                repo_size += os.path.getsize(file_path)
        
        # Get file counts by type
        file_types = {}
        for root, dirs, files in os.walk(repo.working_dir):
            dirs[:] = [d for d in dirs if d != '.git']
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    file_types[ext] = file_types.get(ext, 0) + 1
        
        # Get latest activity
        latest_commit = next(repo.iter_commits(), None)
        latest_activity = None
        if latest_commit:
            latest_activity = datetime.fromtimestamp(latest_commit.committed_date).isoformat()
        
        return {
            "total_commits": total_commits,
            "total_branches": total_branches,
            "repository_size_bytes": repo_size,
            "repository_size_mb": round(repo_size / (1024 * 1024), 2),
            "file_types": file_types,
            "latest_activity": latest_activity,
            "current_branch": repo.active_branch.name if not repo.head.is_detached else "detached",
            "is_dirty": repo.is_dirty()
        }
