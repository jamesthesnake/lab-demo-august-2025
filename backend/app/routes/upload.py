"""
File Upload API for AIDO-Lab
Handles data file uploads for analysis
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from pathlib import Path
import uuid
from typing import Optional

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Configure upload directory
UPLOAD_BASE_DIR = Path("workspace")
ALLOWED_EXTENSIONS = {'.csv', '.json', '.xlsx', '.xls', '.txt', '.py', '.ipynb', '.parquet'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    """Upload a file for analysis in the specified session"""
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Create session directory
    session_dir = UPLOAD_BASE_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename to avoid conflicts
    original_name = Path(file.filename).stem
    file_extension = Path(file.filename).suffix
    unique_filename = f"{original_name}_{uuid.uuid4().hex[:8]}{file_extension}"
    file_path = session_dir / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "filename": unique_filename,
                "original_filename": file.filename,
                "file_path": f"/workspace/{session_id}/{unique_filename}",
                "size": file_size,
                "type": file_ext
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save file: {str(e)}"
        )

@router.get("/files/{session_id}")
async def list_session_files(session_id: str):
    """List all uploaded files for a session"""
    
    session_dir = UPLOAD_BASE_DIR / session_id
    if not session_dir.exists():
        return {"files": []}
    
    files = []
    for file_path in session_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "path": f"/workspace/{session_id}/{file_path.name}",
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "type": file_path.suffix.lower()
            })
    
    return {"files": files}

@router.delete("/files/{session_id}/{filename}")
async def delete_file(session_id: str, filename: str):
    """Delete an uploaded file"""
    
    file_path = UPLOAD_BASE_DIR / session_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        return {"message": f"File {filename} deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
