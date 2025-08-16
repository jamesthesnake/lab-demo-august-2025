"""
Artifact management API routes
Handles upload, retrieval, and management of large artifacts
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import os
import io
from pathlib import Path
import logging

from app.services.artifact_storage import artifact_storage, ArtifactMetadata

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])

@router.post("/upload")
async def upload_artifact(
    session_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """Upload an artifact file"""
    try:
        # Read file content
        content = await file.read()
        
        # Store artifact
        metadata = artifact_storage.store_artifact(
            content=content,
            filename=file.filename,
            session_id=session_id
        )
        
        # Get public URL
        public_url = artifact_storage.get_artifact_url(metadata.hash)
        
        return {
            "hash": metadata.hash,
            "filename": metadata.filename,
            "size": metadata.size,
            "content_type": metadata.content_type,
            "url": public_url,
            "storage_backend": metadata.storage_backend
        }
        
    except Exception as e:
        logger.error(f"Failed to upload artifact: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/{artifact_hash}")
async def get_artifact(artifact_hash: str):
    """Retrieve artifact by hash"""
    try:
        content = artifact_storage.retrieve_artifact(artifact_hash)
        if not content:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        metadata = artifact_storage._load_metadata(artifact_hash)
        if not metadata:
            raise HTTPException(status_code=404, detail="Artifact metadata not found")
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=metadata.content_type,
            headers={"Content-Disposition": f"inline; filename={metadata.filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve artifact {artifact_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@router.get("/{artifact_hash}/info")
async def get_artifact_info(artifact_hash: str):
    """Get artifact metadata"""
    metadata = artifact_storage._load_metadata(artifact_hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    return {
        "hash": metadata.hash,
        "filename": metadata.filename,
        "size": metadata.size,
        "content_type": metadata.content_type,
        "created_at": metadata.created_at.isoformat(),
        "storage_backend": metadata.storage_backend,
        "url": artifact_storage.get_artifact_url(artifact_hash)
    }

@router.get("/")
async def list_artifacts(session_id: Optional[str] = None, limit: int = 100):
    """List artifacts, optionally filtered by session"""
    try:
        artifacts = artifact_storage.list_artifacts(session_id)[:limit]
        
        return {
            "artifacts": [
                {
                    "hash": a.hash,
                    "filename": a.filename,
                    "size": a.size,
                    "content_type": a.content_type,
                    "created_at": a.created_at.isoformat(),
                    "storage_backend": a.storage_backend,
                    "url": artifact_storage.get_artifact_url(a.hash)
                }
                for a in artifacts
            ],
            "total": len(artifacts)
        }
        
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}")
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")

@router.delete("/{artifact_hash}")
async def delete_artifact(artifact_hash: str):
    """Delete an artifact"""
    try:
        metadata = artifact_storage._load_metadata(artifact_hash)
        if not metadata:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        # Remove metadata file
        metadata_file = artifact_storage.base_path / "metadata" / f"{artifact_hash}.json"
        if metadata_file.exists():
            metadata_file.unlink()
        
        # Remove artifact file
        if metadata.storage_backend == "local":
            artifact_file = Path(metadata.storage_path)
            if artifact_file.exists():
                artifact_file.unlink()
        elif metadata.storage_backend == "s3":
            bucket, key = metadata.storage_path[5:].split('/', 1)
            artifact_storage.s3_client.delete_object(Bucket=bucket, Key=key)
        
        return {"status": "deleted", "hash": artifact_hash}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete artifact {artifact_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/cleanup")
async def cleanup_old_artifacts(days: int = 30, background_tasks: BackgroundTasks = None):
    """Clean up artifacts older than specified days"""
    try:
        if background_tasks:
            background_tasks.add_task(artifact_storage.cleanup_old_artifacts, days)
            return {"status": "cleanup_scheduled", "days": days}
        else:
            cleaned_count = artifact_storage.cleanup_old_artifacts(days)
            return {"status": "cleanup_completed", "cleaned_count": cleaned_count, "days": days}
            
    except Exception as e:
        logger.error(f"Failed to cleanup artifacts: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/stats/storage")
async def get_storage_stats():
    """Get storage statistics"""
    try:
        artifacts = artifact_storage.list_artifacts()
        
        total_size = sum(a.size for a in artifacts)
        by_backend = {}
        by_type = {}
        
        for artifact in artifacts:
            # Count by backend
            backend = artifact.storage_backend
            if backend not in by_backend:
                by_backend[backend] = {"count": 0, "size": 0}
            by_backend[backend]["count"] += 1
            by_backend[backend]["size"] += artifact.size
            
            # Count by content type
            content_type = artifact.content_type.split('/')[0]  # Get main type
            if content_type not in by_type:
                by_type[content_type] = {"count": 0, "size": 0}
            by_type[content_type]["count"] += 1
            by_type[content_type]["size"] += artifact.size
        
        return {
            "total_artifacts": len(artifacts),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_backend": by_backend,
            "by_content_type": by_type,
            "storage_backend": artifact_storage.storage_backend
        }
        
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")
