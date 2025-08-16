"""
Artifact storage service for large files
Supports both S3 and Git-LFS backends for efficient storage of plots, datasets, models
"""

import os
import hashlib
import json
import boto3
import subprocess
from typing import Dict, List, Optional, Union, BinaryIO
from pathlib import Path
from datetime import datetime
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ArtifactMetadata:
    hash: str
    filename: str
    size: int
    content_type: str
    created_at: datetime
    storage_backend: str
    storage_path: str

class ArtifactStorage:
    """Manages storage of large artifacts using S3 or Git-LFS"""
    
    def __init__(self, storage_backend: str = "local"):
        self.storage_backend = storage_backend
        self.base_path = Path(os.getenv("ARTIFACT_STORAGE_PATH", "./artifacts"))
        self.base_path.mkdir(exist_ok=True)
        
        # Initialize S3 client if using S3
        if storage_backend == "s3":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            self.s3_bucket = os.getenv("S3_ARTIFACT_BUCKET", "aido-lab-artifacts")
        
        # Git-LFS configuration
        self.git_lfs_enabled = os.getenv("GIT_LFS_ENABLED", "false").lower() == "true"
        
    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _get_content_type(self, filename: str) -> str:
        """Determine content type from filename"""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.pkl': 'application/octet-stream',
            '.joblib': 'application/octet-stream',
            '.h5': 'application/octet-stream',
            '.parquet': 'application/octet-stream'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def store_artifact(self, content: bytes, filename: str, session_id: str) -> ArtifactMetadata:
        """Store artifact and return metadata"""
        content_hash = self._calculate_hash(content)
        content_type = self._get_content_type(filename)
        
        # Create metadata
        metadata = ArtifactMetadata(
            hash=content_hash,
            filename=filename,
            size=len(content),
            content_type=content_type,
            created_at=datetime.utcnow(),
            storage_backend=self.storage_backend,
            storage_path=""
        )
        
        if self.storage_backend == "s3":
            storage_path = self._store_s3(content, content_hash, filename, session_id, metadata)
        elif self.storage_backend == "git-lfs":
            storage_path = self._store_git_lfs(content, content_hash, filename, session_id)
        else:
            storage_path = self._store_local(content, content_hash, filename, session_id)
        
        metadata.storage_path = storage_path
        
        # Save metadata
        self._save_metadata(content_hash, metadata)
        
        return metadata
    
    def _store_local(self, content: bytes, content_hash: str, filename: str, session_id: str) -> str:
        """Store artifact locally"""
        # Use content-addressed storage: first 2 chars of hash as directory
        storage_dir = self.base_path / content_hash[:2]
        storage_dir.mkdir(exist_ok=True)
        
        storage_path = storage_dir / f"{content_hash}_{filename}"
        
        # Only write if file doesn't exist (deduplication)
        if not storage_path.exists():
            with open(storage_path, 'wb') as f:
                f.write(content)
        
        return str(storage_path)
    
    def _store_s3(self, content: bytes, content_hash: str, filename: str, session_id: str, metadata: ArtifactMetadata) -> str:
        """Store artifact in S3"""
        s3_key = f"artifacts/{content_hash[:2]}/{content_hash}_{filename}"
        
        try:
            # Check if object already exists (deduplication)
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                logger.info(f"Artifact {content_hash} already exists in S3")
                return f"s3://{self.s3_bucket}/{s3_key}"
            except self.s3_client.exceptions.NoSuchKey:
                pass
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType=metadata.content_type,
                Metadata={
                    'session_id': session_id,
                    'original_filename': filename,
                    'content_hash': content_hash,
                    'created_at': metadata.created_at.isoformat()
                }
            )
            
            logger.info(f"Stored artifact {content_hash} in S3: {s3_key}")
            return f"s3://{self.s3_bucket}/{s3_key}"
            
        except Exception as e:
            logger.error(f"Failed to store artifact in S3: {e}")
            # Fallback to local storage
            return self._store_local(content, content_hash, filename, session_id)
    
    def _store_git_lfs(self, content: bytes, content_hash: str, filename: str, session_id: str) -> str:
        """Store artifact using Git-LFS"""
        if not self.git_lfs_enabled:
            return self._store_local(content, content_hash, filename, session_id)
        
        try:
            # Store locally first
            local_path = self._store_local(content, content_hash, filename, session_id)
            
            # Add to Git-LFS
            lfs_dir = self.base_path / "lfs"
            lfs_dir.mkdir(exist_ok=True)
            
            lfs_path = lfs_dir / f"{content_hash}_{filename}"
            
            # Copy to LFS directory
            with open(local_path, 'rb') as src, open(lfs_path, 'wb') as dst:
                dst.write(src.read())
            
            # Initialize Git-LFS if not already done
            subprocess.run(['git', 'lfs', 'install'], cwd=lfs_dir, check=False)
            
            # Track the file type with Git-LFS
            file_ext = Path(filename).suffix
            subprocess.run(['git', 'lfs', 'track', f'*{file_ext}'], cwd=lfs_dir, check=False)
            
            # Add to git
            subprocess.run(['git', 'add', str(lfs_path.name)], cwd=lfs_dir, check=False)
            subprocess.run(['git', 'add', '.gitattributes'], cwd=lfs_dir, check=False)
            
            logger.info(f"Added artifact {content_hash} to Git-LFS")
            return str(lfs_path)
            
        except Exception as e:
            logger.error(f"Failed to store artifact in Git-LFS: {e}")
            # Fallback to local storage
            return self._store_local(content, content_hash, filename, session_id)
    
    def retrieve_artifact(self, content_hash: str) -> Optional[bytes]:
        """Retrieve artifact by hash"""
        metadata = self._load_metadata(content_hash)
        if not metadata:
            return None
        
        if metadata.storage_backend == "s3":
            return self._retrieve_s3(metadata.storage_path)
        elif metadata.storage_backend == "git-lfs":
            return self._retrieve_git_lfs(metadata.storage_path)
        else:
            return self._retrieve_local(metadata.storage_path)
    
    def _retrieve_local(self, storage_path: str) -> Optional[bytes]:
        """Retrieve artifact from local storage"""
        try:
            with open(storage_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Artifact not found at {storage_path}")
            return None
    
    def _retrieve_s3(self, s3_path: str) -> Optional[bytes]:
        """Retrieve artifact from S3"""
        try:
            # Parse S3 path
            if s3_path.startswith('s3://'):
                bucket, key = s3_path[5:].split('/', 1)
            else:
                bucket, key = self.s3_bucket, s3_path
            
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
            
        except Exception as e:
            logger.error(f"Failed to retrieve artifact from S3: {e}")
            return None
    
    def _retrieve_git_lfs(self, lfs_path: str) -> Optional[bytes]:
        """Retrieve artifact from Git-LFS"""
        try:
            # Git-LFS should handle this transparently
            with open(lfs_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Git-LFS artifact not found at {lfs_path}")
            return None
    
    def _save_metadata(self, content_hash: str, metadata: ArtifactMetadata):
        """Save artifact metadata"""
        metadata_dir = self.base_path / "metadata"
        metadata_dir.mkdir(exist_ok=True)
        
        metadata_file = metadata_dir / f"{content_hash}.json"
        
        with open(metadata_file, 'w') as f:
            json.dump({
                'hash': metadata.hash,
                'filename': metadata.filename,
                'size': metadata.size,
                'content_type': metadata.content_type,
                'created_at': metadata.created_at.isoformat(),
                'storage_backend': metadata.storage_backend,
                'storage_path': metadata.storage_path
            }, f, indent=2)
    
    def _load_metadata(self, content_hash: str) -> Optional[ArtifactMetadata]:
        """Load artifact metadata"""
        metadata_file = self.base_path / "metadata" / f"{content_hash}.json"
        
        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                return ArtifactMetadata(
                    hash=data['hash'],
                    filename=data['filename'],
                    size=data['size'],
                    content_type=data['content_type'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    storage_backend=data['storage_backend'],
                    storage_path=data['storage_path']
                )
        except FileNotFoundError:
            return None
    
    def get_artifact_url(self, content_hash: str) -> Optional[str]:
        """Get public URL for artifact"""
        metadata = self._load_metadata(content_hash)
        if not metadata:
            return None
        
        if metadata.storage_backend == "s3":
            # Generate presigned URL for S3
            try:
                bucket, key = metadata.storage_path[5:].split('/', 1)
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=3600  # 1 hour
                )
                return url
            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {e}")
                return None
        else:
            # Return local file path (will be served by static file handler)
            return f"/static/artifacts/{content_hash}_{metadata.filename}"
    
    def list_artifacts(self, session_id: Optional[str] = None) -> List[ArtifactMetadata]:
        """List all artifacts, optionally filtered by session"""
        artifacts = []
        metadata_dir = self.base_path / "metadata"
        
        if not metadata_dir.exists():
            return artifacts
        
        for metadata_file in metadata_dir.glob("*.json"):
            metadata = self._load_metadata(metadata_file.stem)
            if metadata:
                artifacts.append(metadata)
        
        return sorted(artifacts, key=lambda x: x.created_at, reverse=True)
    
    def cleanup_old_artifacts(self, days: int = 30):
        """Clean up artifacts older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cleaned_count = 0
        
        for artifact in self.list_artifacts():
            if artifact.created_at < cutoff_date:
                try:
                    # Remove metadata
                    metadata_file = self.base_path / "metadata" / f"{artifact.hash}.json"
                    if metadata_file.exists():
                        metadata_file.unlink()
                    
                    # Remove artifact file
                    if artifact.storage_backend == "local":
                        artifact_file = Path(artifact.storage_path)
                        if artifact_file.exists():
                            artifact_file.unlink()
                    elif artifact.storage_backend == "s3":
                        bucket, key = artifact.storage_path[5:].split('/', 1)
                        self.s3_client.delete_object(Bucket=bucket, Key=key)
                    
                    cleaned_count += 1
                    logger.info(f"Cleaned up artifact {artifact.hash}")
                    
                except Exception as e:
                    logger.error(f"Failed to clean up artifact {artifact.hash}: {e}")
        
        return cleaned_count

# Global storage instance
artifact_storage = ArtifactStorage(
    storage_backend=os.getenv("ARTIFACT_STORAGE_BACKEND", "local")
)
