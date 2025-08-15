"""
Main FastAPI Application
Central API server for AIDO-Lab
"""
from app.routes import chat, upload

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
import json
import uuid
import asyncio
import logging
from pathlib import Path
import base64
from io import BytesIO

# Import services
from app.services.kernel_manager import KernelManager, ExecutionResult, AnalysisContext
from app.services.git_service import GitService
from app.services.llm_service import LLMService, LLMProvider

# Import models
from app.models.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    SessionInfo,
    HistoryResponse,
    BranchRequest,
    CheckoutRequest,
    FileListResponse,
    SuggestionResponse,
    WebSocketMessage,
    CommitInfoResponse,
    SuggestionRequest,  # Add this
    ExecutionResultData
)
from app.models.schemas import (
    ExecuteRequest,
    ExecuteResponse,
    SessionInfo,
    HistoryResponse,
    BranchRequest,
    CheckoutRequest,
    FileListResponse,
    FileInfo,
    SuggestionRequest,  # Add this
    SuggestionResponse,
    WebSocketMessage,
    CommitInfoResponse,
    ExecutionResultData,
    ErrorResponse
)

# Import utilities
from app.utils.auth import get_current_user, create_access_token
from app.utils.session_manager import SessionManager
from app.utils.file_manager import FileManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed, using system environment variables")

# Global services
kernel_manager: Optional[KernelManager] = None
git_service: Optional[GitService] = None
llm_service: Optional[LLMService] = None
session_manager: Optional[SessionManager] = None
file_manager: Optional[FileManager] = None

# WebSocket connections
websocket_connections: Dict[str, WebSocket] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global kernel_manager, git_service, llm_service, session_manager, file_manager
    
    logger.info("Starting AIDO-Lab backend...")
    
    # Get workspace base from environment or use local directory
    workspace_base = os.getenv("WORKSPACE_BASE", "./workspaces")
    # Convert to absolute path
    workspace_base = os.path.abspath(workspace_base)
    
    # Create workspace directory if it doesn't exist
    os.makedirs(workspace_base, exist_ok=True)
    logger.info(f"Using workspace directory: {workspace_base}")
    
    # Initialize services
    kernel_manager = KernelManager(
        docker_image=os.getenv("KERNEL_IMAGE", "aido-kernel:latest"),
        workspace_base=workspace_base,
        max_kernels=int(os.getenv("MAX_KERNELS", "10")),
        kernel_timeout=int(os.getenv("KERNEL_TIMEOUT", "3600")),
        execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "30"))
    )
    
    git_service = GitService(workspace_base=workspace_base)
    
    # Initialize LLM service - try Anthropic first, then OpenAI
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if anthropic_key and anthropic_key != "your-anthropic-key-here" and anthropic_key != "":
        try:
            llm_service = LLMService(
                provider=LLMProvider.ANTHROPIC,
                api_key=anthropic_key,
                model="claude-3-5-sonnet-20241022",
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
            )
            
            # Check LLM API status
            api_status = await llm_service.check_api_status()
            if not api_status:
                logger.warning("Anthropic API is not available. Trying OpenAI...")
                raise Exception("Anthropic API check failed")
            else:
                logger.info("LLM service initialized with Anthropic Claude")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic LLM service: {e}")
            llm_service = None
    elif openai_key and openai_key != "your-openai-key-here" and openai_key != "":
        try:
            llm_service = LLMService(
                provider=LLMProvider.OPENAI,
                api_key=openai_key,
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
            )
            
            # Check LLM API status
            api_status = await llm_service.check_api_status()
            if not api_status:
                logger.warning("OpenAI API is not available. Natural language features will be limited.")
            else:
                logger.info("LLM service initialized with OpenAI")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI LLM service: {e}")
            llm_service = None
    else:
        logger.warning("No LLM API keys configured. Natural language features disabled.")
        llm_service = None
    
    session_manager = SessionManager()
    file_manager = FileManager(workspace_base=workspace_base)
    
    yield
    
    # Cleanup
    logger.info("Shutting down AIDO-Lab backend...")
    if kernel_manager:
        await kernel_manager.cleanup()

# Create FastAPI app
app = FastAPI(
    title="AIDO-Lab API",
    description="AI-Driven Data Science Platform API",
    version="0.1.0",
    lifespan=lifespan
)
app.include_router(chat.router)
app.include_router(upload.router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "AIDO-Lab API",
        "version": "0.1.0",
        "status": "running",
        "documentation": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "kernel_manager": kernel_manager is not None,
            "git_service": git_service is not None,
            "llm_service": llm_service is not None,
            "session_manager": session_manager is not None
        }
    }
    
    # Check LLM API
    if llm_service:
        health_status["services"]["llm_api"] = await llm_service.check_api_status()
    
    # Check kernel status
    if kernel_manager:
        active_kernels = await kernel_manager.list_kernels()
        health_status["kernel_count"] = len(active_kernels)
    
    return health_status

# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.post("/api/sessions/create")
async def create_session() -> SessionInfo:
    """Create a new analysis session"""
    session_id = str(uuid.uuid4())
    
    # Initialize repository
    repo_path = await git_service.init_session_repo(session_id)
    
    # Create session
    session_info = await session_manager.create_session(
        session_id=session_id,
        workspace_path=repo_path
    )
    
    logger.info(f"Created session: {session_id}")
    
    return SessionInfo(**session_info)

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionInfo:
    """Get session information"""
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Add kernel status
    kernel_status = await kernel_manager.get_kernel_status(session_id)
    session["kernel_status"] = kernel_status
    
    # Add repository stats
    try:
        repo_stats = await git_service.get_statistics(session_id)
        session["repository_stats"] = repo_stats
    except:
        session["repository_stats"] = {}
    
    return SessionInfo(**session)

@app.get("/api/sessions")
async def list_sessions() -> List[SessionInfo]:
    """List all active sessions"""
    sessions = await session_manager.list_sessions()
    return [SessionInfo(**s) for s in sessions]

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    # Shutdown kernel
    await kernel_manager.shutdown_kernel(session_id)
    
    # Clean up repository
    await git_service.cleanup_session(session_id)
    
    # Delete session
    await session_manager.delete_session(session_id)
    
    return {"status": "deleted", "session_id": session_id}

# ============================================================================
# Code Execution Endpoints
# ============================================================================

@app.post("/api/execute")
async def execute_code(request: ExecuteRequest) -> ExecuteResponse:
    """Execute code or natural language query"""
    session_id = request.session_id
    
    # Ensure session exists
    session = await session_manager.get_session(session_id)
    if not session:
        # Auto-create session
        session_info = await create_session()
        session_id = session_info.session_id
        session = await session_manager.get_session(session_id)
    
    # Get analysis context
    context = await _build_analysis_context(session_id)
    
    # Generate code if natural language
    code_metadata = {}
    if request.is_natural_language and llm_service:
        try:
            generation = await llm_service.generate_code(
                query=request.query,
                context=context,
                task_type=request.task_type or "data_analysis"
            )
            
            code = generation.code
            code_metadata = {
                "generated": True,
                "query": request.query,
                "confidence": generation.confidence,
                "warnings": generation.warnings,
                "libraries": generation.libraries_used
            }
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to simple code
            code = f"# Failed to generate code from: {request.query}\nprint('LLM service unavailable')"
            code_metadata = {"generated": False, "error": str(e)}
    else:
        code = request.query
        code_metadata = {"generated": False}
    
    # Execute code
    execution_result = await kernel_manager.execute_code(
        session_id=session_id,
        code=code,
        timeout=request.timeout
    )
    
    # Save to git
    try:
        commit_info = await git_service.save_execution(
            session_id=session_id,
            code=code,
            results=execution_result.to_dict(),
            metadata=code_metadata
        )
        commit_dict = {
            "sha": commit_info.sha,
            "message": commit_info.message,
            "author": commit_info.author,
            "timestamp": commit_info.timestamp,
            "parent_sha": commit_info.parent_sha,
            "branch": commit_info.branch,
            "files_changed": commit_info.files_changed
        }
    except Exception as e:
        logger.error(f"Failed to save to git: {e}")
        commit_dict = None
    
    # Update session
    await session_manager.add_execution(
        session_id=session_id,
        execution={
            "code": code,
            "results": execution_result.to_dict(),
            "commit": commit_dict["sha"] if commit_dict else None,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": code_metadata
        }
    )
    
    # Send WebSocket notification
    await _notify_websocket(session_id, {
        "type": "execution_complete",
        "data": {
            "execution_count": execution_result.execution_count,
            "status": execution_result.status
        }
    })
    
    # Create response
    results_data = ExecutionResultData(
        stdout=execution_result.to_dict()["stdout"],
        stderr=execution_result.to_dict()["stderr"],
        display_data=execution_result.display_data,
        errors=execution_result.errors,
        execution_count=execution_result.execution_count,
        status=execution_result.status
    )
    
    response = ExecuteResponse(
        code=code,
        results=results_data,
        commit=CommitInfoResponse(**commit_dict) if commit_dict else None,
        metadata=code_metadata,
        timestamp=datetime.utcnow()
    )
    
    return response

# ============================================================================
# Version Control Endpoints
# ============================================================================

@app.get("/api/history/{session_id}")
async def get_history(
    session_id: str,
    branch: Optional[str] = None,
    limit: int = 50
) -> HistoryResponse:
    """Get execution history"""
    try:
        commits = await git_service.get_history(session_id, branch, limit)
        tree = await git_service.get_history_tree(session_id)
        
        return HistoryResponse(
            commits=[{
                "sha": c.sha,
                "message": c.message,
                "author": c.author,
                "timestamp": c.timestamp.isoformat() if hasattr(c.timestamp, 'isoformat') else str(c.timestamp),
                "parent_sha": c.parent_sha,
                "branch": c.branch,
                "files_changed": c.files_changed
            } for c in commits],
            tree=tree,
            current_branch=tree.get("current_branch"),
            head=tree.get("head")
        )
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return HistoryResponse(commits=[], tree={}, current_branch=None, head=None)

@app.post("/api/branches/create")
async def create_branch(request: BranchRequest):
    """Create a new branch"""
    branch_info = await git_service.create_branch(
        session_id=request.session_id,
        branch_name=request.branch_name,
        from_commit=request.from_commit
    )
    
    return branch_info

@app.post("/api/branches/switch")
async def switch_branch(request: BranchRequest):
    """Switch to a different branch"""
    branch_info = await git_service.switch_branch(
        session_id=request.session_id,
        branch_name=request.branch_name
    )
    
    # Restart kernel with new workspace
    await kernel_manager.restart_kernel(request.session_id)
    
    return branch_info

@app.get("/api/branches/{session_id}")
async def list_branches(session_id: str):
    """List all branches"""
    branches = await git_service.list_branches(session_id)
    return {"branches": [b.__dict__ for b in branches]}

@app.post("/api/checkout")
async def checkout_commit(request: CheckoutRequest):
    """Checkout a specific commit"""
    result = await git_service.checkout_commit(
        session_id=request.session_id,
        commit_sha=request.commit_sha
    )
    
    # Restart kernel with new state
    await kernel_manager.restart_kernel(request.session_id)
    
    return result

# ============================================================================
# File Management Endpoints
# ============================================================================

@app.get("/api/files/{session_id}")
async def list_files(session_id: str) -> FileListResponse:
    """List files in workspace"""
    files = await file_manager.list_files(session_id)
    workspace_size = await file_manager.get_workspace_size(session_id)
    
    return FileListResponse(
        files=files,
        workspace_path=file_manager.get_workspace_path(session_id),
        total_size=workspace_size.get("total_size", 0)
    )

@app.get("/api/files/{session_id}/{file_path:path}")
async def get_file(session_id: str, file_path: str):
    """Get file content"""
    try:
        content = await file_manager.read_file(session_id, file_path)
        
        # Check if it's a binary file (base64 encoded)
        if file_path.endswith(('.png', '.jpg', '.jpeg', '.gif')):
            return StreamingResponse(
                BytesIO(base64.b64decode(content)),
                media_type=f"image/{file_path.split('.')[-1]}"
            )
        else:
            return {"content": content, "path": file_path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/files/{session_id}/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
    path: Optional[str] = None
):
    """Upload file to workspace"""
    file_info = await file_manager.save_upload(
        session_id=session_id,
        file_data=file.file,
        filename=file.filename,
        path=path or "data"
    )
    
    # Commit to git
    try:
        await git_service.save_execution(
            session_id=session_id,
            code=f"# Uploaded file: {file.filename}",
            results={"status": "file_uploaded"},
            metadata={"file_name": file.filename, "file_size": file_info["size"]}
        )
    except Exception as e:
        logger.error(f"Failed to commit file upload: {e}")
    
    return {
        "status": "uploaded",
        "file_info": file_info
    }

@app.delete("/api/files/{session_id}/{file_path:path}")
async def delete_file(session_id: str, file_path: str):
    """Delete file from workspace"""
    success = await file_manager.delete_file(session_id, file_path)
    
    if success:
        # Commit deletion
        try:
            await git_service.save_execution(
                session_id=session_id,
                code=f"# Deleted file: {file_path}",
                results={"status": "file_deleted"},
                metadata={"file_path": file_path}
            )
        except Exception as e:
            logger.error(f"Failed to commit file deletion: {e}")
        
        return {"status": "deleted", "path": file_path}
    else:
        raise HTTPException(status_code=404, detail="File not found")

# ============================================================================
# AI Assistant Endpoints
# ============================================================================

@app.post("/api/suggest")
async def get_suggestions(request: SuggestionRequest) -> SuggestionResponse:
    """Get AI suggestions for next steps"""
    if not llm_service:
        return SuggestionResponse(
            suggestions=["LLM service not available"],
            context_summary="No LLM configured",
            confidence=0.0
        )
    
    context = await _build_analysis_context(request.session_id)
    
    try:
        suggestions = await llm_service.suggest_next_steps(context, request.goal)
        
        return SuggestionResponse(
            suggestions=suggestions,
            context_summary=f"Based on {len(context.previous_code)} previous executions",
            confidence=0.8
        )
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        return SuggestionResponse(
            suggestions=["Failed to generate suggestions"],
            context_summary=str(e),
            confidence=0.0
        )

@app.post("/api/explain")
async def explain_code(code: str) -> Dict[str, str]:
    """Explain what code does"""
    if not llm_service:
        return {"explanation": "LLM service not available"}
    
    try:
        explanation = await llm_service.explain_code(code)
        return {"explanation": explanation}
    except Exception as e:
        logger.error(f"Failed to explain code: {e}")
        return {"explanation": f"Failed to explain: {str(e)}"}

# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket for real-time updates"""
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            # Handle different message types
            if data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data["type"] == "execute":
                # Execute code and stream results
                request = ExecuteRequest(
                    session_id=session_id,
                    query=data["query"],
                    is_natural_language=data.get("is_natural_language", True)
                )
                
                response = await execute_code(request)
                
                await websocket.send_json({
                    "type": "execution_result",
                    "data": response.dict()
                })
    
    except WebSocketDisconnect:
        del websocket_connections[session_id]
        logger.info(f"WebSocket disconnected for session {session_id}")

# ============================================================================
# Export Endpoints
# ============================================================================

@app.get("/api/export/{session_id}/notebook")
async def export_notebook(session_id: str, branch: Optional[str] = None):
    """Export session as Jupyter notebook"""
    try:
        notebook_path = await git_service.export_notebook(session_id, branch)
        
        return FileResponse(
            path=notebook_path,
            filename=f"aido_lab_session_{session_id}.ipynb",
            media_type="application/x-ipynb+json"
        )
    except Exception as e:
        logger.error(f"Failed to export notebook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Helper Functions
# ============================================================================

async def _build_analysis_context(session_id: str) -> AnalysisContext:
    """Build analysis context for LLM"""
    session = await session_manager.get_session(session_id)
    
    if not session:
        return AnalysisContext(
            session_id=session_id,
            previous_code=[],
            available_files=[],
            variables_in_scope={},
            installed_packages=["pandas", "numpy", "matplotlib", "seaborn", "scikit-learn"],
            execution_history=[]
        )
    
    # Get files
    try:
        files = await file_manager.list_files(session_id)
        file_paths = [f["path"] for f in files]
    except:
        file_paths = []
    
    # Get previous code
    previous_code = [exec.get("code", "") for exec in session.get("executions", [])[-5:]]
    
    return AnalysisContext(
        session_id=session_id,
        previous_code=previous_code,
        available_files=file_paths,
        variables_in_scope={},
        installed_packages=["pandas", "numpy", "matplotlib", "seaborn", "scikit-learn"],
        execution_history=session.get("executions", [])[-10:]
    )

async def _notify_websocket(session_id: str, message: Dict[str, Any]):
    """Send notification via WebSocket"""
    if session_id in websocket_connections:
        try:
            await websocket_connections[session_id].send_json(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
