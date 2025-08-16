"""
Git-based Session Manager
Each session is a bare git repository with branch-based execution history
"""

import os
import git
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GitSessionManager:
    """Manages sessions as git repositories with branch-based execution tracking"""
    
    def __init__(self, base_path: str = "/tmp/aido-sessions"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True, parents=True)
    
    def create_session(self, session_id: str, name: str = None) -> Dict[str, Any]:
        """Create a new session with bare git repository"""
        session_path = self.base_path / session_id
        
        if session_path.exists():
            return self.get_session_info(session_id)
        
        # Create bare git repository
        repo = git.Repo.init(session_path, bare=True)
        
        # Create initial commit on main branch
        work_tree = session_path / "workspace"
        work_tree.mkdir(exist_ok=True)
        
        # Initialize with empty commit
        with git.Repo.init(work_tree) as work_repo:
            work_repo.git.remote("add", "origin", str(session_path))
            
            # Create initial file
            readme_path = work_tree / "README.md"
            readme_path.write_text(f"# AIDO Lab Session: {name or session_id}\n\nCreated: {datetime.now().isoformat()}\n")
            
            work_repo.index.add([str(readme_path)])
            initial_commit = work_repo.index.commit("Initial session commit")
            
            # Push to bare repo
            work_repo.git.push("origin", "main")
        
        logger.info(f"Created git session {session_id} at {session_path}")
        
        return {
            "session_id": session_id,
            "name": name or session_id,
            "repo_path": str(session_path),
            "workspace_path": str(work_tree),
            "created_at": datetime.now().isoformat(),
            "initial_commit": str(initial_commit)
        }
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        session_path = self.base_path / session_id
        
        if not session_path.exists():
            return None
        
        try:
            repo = git.Repo(session_path)
            branches = [ref.name.split('/')[-1] for ref in repo.refs if ref.name.startswith('refs/heads/')]
            
            return {
                "session_id": session_id,
                "repo_path": str(session_path),
                "workspace_path": str(session_path / "workspace"),
                "branches": branches,
                "head_commit": str(repo.head.commit) if repo.head.is_valid() else None
            }
        except Exception as e:
            logger.error(f"Failed to get session info for {session_id}: {e}")
            return None
    
    def create_execution_branch(self, session_id: str, parent_commit: str = None, branch_name: str = None) -> str:
        """Create a new branch for code execution"""
        session_path = self.base_path / session_id
        work_tree = session_path / "workspace"
        
        if not branch_name:
            branch_name = f"exec-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with git.Repo(work_tree) as work_repo:
            # Create new branch from parent or current HEAD
            if parent_commit:
                work_repo.git.checkout("-b", branch_name, parent_commit)
            else:
                work_repo.git.checkout("-b", branch_name)
        
        logger.info(f"Created execution branch {branch_name} in session {session_id}")
        return branch_name
    
    def commit_execution(self, session_id: str, branch_name: str, code: str, 
                        result: Dict[str, Any], artifacts: List[str] = None) -> str:
        """Commit code execution results to branch"""
        session_path = self.base_path / session_id
        work_tree = session_path / "workspace"
        
        with git.Repo(work_tree) as work_repo:
            work_repo.git.checkout(branch_name)
            
            # Create execution metadata
            exec_metadata = {
                "timestamp": datetime.now().isoformat(),
                "code": code,
                "result": result,
                "artifacts": artifacts or []
            }
            
            # Save code to file
            code_file = work_tree / f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            code_file.write_text(code)
            
            # Save metadata
            metadata_file = work_tree / f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            metadata_file.write_text(json.dumps(exec_metadata, indent=2))
            
            # Add files to git
            work_repo.index.add([str(code_file), str(metadata_file)])
            
            # Add artifacts if any
            if artifacts:
                for artifact in artifacts:
                    artifact_path = Path(artifact)
                    if artifact_path.exists():
                        # Copy artifact to workspace
                        dest_path = work_tree / "artifacts" / artifact_path.name
                        dest_path.parent.mkdir(exist_ok=True)
                        dest_path.write_bytes(artifact_path.read_bytes())
                        work_repo.index.add([str(dest_path)])
            
            # Commit
            commit_msg = f"Execute code on {branch_name}\n\nStatus: {result.get('status', 'unknown')}"
            commit = work_repo.index.commit(commit_msg)
            
            # Push to bare repo
            work_repo.git.push("origin", branch_name)
            
            logger.info(f"Committed execution {commit} to branch {branch_name}")
            return str(commit)
    
    def get_commit_history(self, session_id: str, branch: str = None) -> List[Dict[str, Any]]:
        """Get commit history for session or branch"""
        session_path = self.base_path / session_id
        
        try:
            repo = git.Repo(session_path)
            
            if branch:
                commits = list(repo.iter_commits(branch, max_count=50))
            else:
                commits = list(repo.iter_commits('--all', max_count=50))
            
            history = []
            for commit in commits:
                history.append({
                    "sha": str(commit),
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "timestamp": commit.committed_datetime.isoformat(),
                    "branch": self._get_commit_branches(repo, commit)
                })
            
            return history
        except Exception as e:
            logger.error(f"Failed to get commit history for {session_id}: {e}")
            return []
    
    def _get_commit_branches(self, repo: git.Repo, commit: git.Commit) -> List[str]:
        """Get branches containing a commit"""
        try:
            branches = []
            for branch in repo.branches:
                if repo.is_ancestor(commit, branch.commit):
                    branches.append(branch.name)
            return branches
        except:
            return []
    
    def fork_branch(self, session_id: str, from_commit: str, new_branch_name: str) -> str:
        """Fork a new branch from any commit"""
        session_path = self.base_path / session_id
        work_tree = session_path / "workspace"
        
        with git.Repo(work_tree) as work_repo:
            work_repo.git.checkout("-b", new_branch_name, from_commit)
            work_repo.git.push("origin", new_branch_name)
        
        logger.info(f"Forked branch {new_branch_name} from {from_commit} in session {session_id}")
        return new_branch_name
    
    def get_branch_tree(self, session_id: str) -> Dict[str, Any]:
        """Get visual branch tree structure"""
        session_path = self.base_path / session_id
        
        try:
            repo = git.Repo(session_path)
            
            # Get all branches and their commits
            branches = {}
            for branch_ref in repo.branches:
                branch_name = branch_ref.name
                commits = list(repo.iter_commits(branch_name, max_count=20))
                
                branches[branch_name] = {
                    "commits": [
                        {
                            "sha": str(commit)[:8],
                            "message": commit.message.strip(),
                            "timestamp": commit.committed_datetime.isoformat()
                        }
                        for commit in commits
                    ],
                    "head": str(branch_ref.commit)[:8]
                }
            
            return {
                "session_id": session_id,
                "branches": branches,
                "graph": self._generate_git_graph(repo)
            }
        except Exception as e:
            logger.error(f"Failed to get branch tree for {session_id}: {e}")
            return {"session_id": session_id, "branches": {}, "graph": []}
    
    def _generate_git_graph(self, repo: git.Repo) -> List[Dict[str, Any]]:
        """Generate git log --graph equivalent data"""
        try:
            # Use git log --graph --all --oneline --format
            log_output = repo.git.log("--graph", "--all", "--oneline", "--format=%H|%s|%an|%ad", "--date=iso")
            
            graph_data = []
            for line in log_output.split('\n'):
                if '|' in line:
                    # Parse graph symbols and commit info
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        graph_part = parts[0]
                        commit_info = parts[1].split('|')
                        
                        if len(commit_info) >= 4:
                            graph_data.append({
                                "graph": graph_part,
                                "sha": commit_info[0][:8],
                                "message": commit_info[1],
                                "author": commit_info[2],
                                "date": commit_info[3]
                            })
            
            return graph_data
        except Exception as e:
            logger.warning(f"Failed to generate git graph: {e}")
            return []
    
    def cleanup_session(self, session_id: str):
        """Clean up session repository"""
        session_path = self.base_path / session_id
        
        if session_path.exists():
            import shutil
            shutil.rmtree(session_path)
            logger.info(f"Cleaned up session {session_id}")
    
    def get_artifact_hash(self, file_path: str) -> str:
        """Generate content hash for artifact storage"""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def store_large_artifact(self, session_id: str, file_path: str) -> str:
        """Store large artifact with content-addressed storage"""
        content_hash = self.get_artifact_hash(file_path)
        
        # Store in content-addressed location
        artifacts_dir = self.base_path / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        artifact_path = artifacts_dir / f"{content_hash[:2]}" / f"{content_hash[2:]}"
        artifact_path.parent.mkdir(exist_ok=True)
        
        if not artifact_path.exists():
            import shutil
            shutil.copy2(file_path, artifact_path)
        
        # Return pointer for git storage
        return f"artifacts/{content_hash[:2]}/{content_hash[2:]}"
