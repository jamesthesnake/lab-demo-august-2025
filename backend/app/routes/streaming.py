"""
Server-Sent Events (SSE) streaming for real-time chat experience
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from typing import AsyncGenerator, Dict, Any
import json
import asyncio
import logging
from datetime import datetime

from app.services.git_session_manager import GitSessionManager
from app.services.secure_kernel_manager import SecureKernelManager
from app.models.schemas import ChatRequest
from app.models.database import get_db, Session as DBSession, Conversation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["streaming"])

# Global managers
git_session_manager = GitSessionManager()
secure_kernel_manager = SecureKernelManager()

@router.post("/chat/{session_id}")
async def stream_chat(
    session_id: str,
    request: ChatRequest,
    db: DBSession = Depends(get_db)
):
    """Stream chat response with SSE"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Initialize session if needed
            session_info = git_session_manager.get_session_info(session_id)
            if not session_info:
                session_info = git_session_manager.create_session(session_id)
                yield f"data: {json.dumps({'type': 'session_created', 'payload': session_info})}\n\n"
            
            # Create execution branch
            branch_name = git_session_manager.create_execution_branch(session_id)
            yield f"data: {json.dumps({'type': 'branch_created', 'payload': {'branch': branch_name}})}\n\n"
            
            # Stream LLM response
            from app.main import llm_service
            if llm_service:
                yield f"data: {json.dumps({'type': 'thinking', 'payload': 'Analyzing your request...'})}\n\n"
                
                # Get LLM response with tool calling
                if llm_service.provider.value == "anthropic":
                    messages = [{"role": "user", "content": request.message}]
                    response = await llm_service.client.messages.create(
                        model=llm_service.model,
                        system="You are a data science assistant. Generate Python code to solve user requests. Use tool calling for code execution.",
                        messages=messages,
                        tools=[{
                            "name": "exec_python",
                            "description": "Execute Python code",
                            "input_schema": {
                                "type": "object",
                                "properties": {"code": {"type": "string"}},
                                "required": ["code"]
                            }
                        }],
                        tool_choice={"type": "tool", "name": "exec_python"},
                        temperature=0.7,
                        max_tokens=2000
                    )
                    
                    # Stream LLM text response
                    for content_block in response.content:
                        if hasattr(content_block, 'text') and content_block.text:
                            yield f"data: {json.dumps({'type': 'text', 'payload': content_block.text})}\n\n"
                        elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                            code = content_block.input.get('code', '')
                            yield f"data: {json.dumps({'type': 'code', 'payload': code})}\n\n"
                            
                            # Execute code
                            yield f"data: {json.dumps({'type': 'executing', 'payload': 'Running code...'})}\n\n"
                            
                            execution_result = await secure_kernel_manager.execute_code(session_id, code)
                            
                            # Stream execution result
                            result_data = {
                                "stdout": execution_result.stdout,
                                "stderr": execution_result.stderr,
                                "status": execution_result.status,
                                "execution_time": execution_result.execution_time
                            }
                            yield f"data: {json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                            
                            # Stream artifacts
                            for artifact in execution_result.artifacts:
                                artifact_url = f"/static/artifacts/{artifact.split('/')[-1]}"
                                yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'path': artifact}})}\n\n"
                            
                            # Commit to git
                            commit_sha = git_session_manager.commit_execution(
                                session_id, branch_name, code, result_data, execution_result.artifacts
                            )
                            yield f"data: {json.dumps({'type': 'commit', 'payload': {'sha': commit_sha, 'branch': branch_name}})}\n\n"
                            
                            # Save to database
                            conversation = Conversation(
                                session_id=session_id,
                                branch_name=branch_name,
                                prompt=request.message,
                                response=getattr(response, 'content', [{}])[0].get('text', ''),
                                code_executed=code,
                                execution_result=json.dumps(result_data),
                                artifacts=json.dumps(execution_result.artifacts)
                            )
                            db.add(conversation)
                            db.commit()
            
            yield f"data: {json.dumps({'type': 'complete', 'payload': 'Stream completed'})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_stream())

@router.get("/history/{session_id}")
async def stream_history(session_id: str):
    """Stream session history"""
    
    async def generate_history() -> AsyncGenerator[str, None]:
        try:
            # Get git history
            history = git_session_manager.get_commit_history(session_id)
            for commit in history:
                yield f"data: {json.dumps({'type': 'commit', 'payload': commit})}\n\n"
                await asyncio.sleep(0.1)  # Smooth streaming
            
            # Get branch tree
            tree = git_session_manager.get_branch_tree(session_id)
            yield f"data: {json.dumps({'type': 'tree', 'payload': tree})}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'payload': 'History loaded'})}\n\n"
            
        except Exception as e:
            logger.error(f"History stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_history())

@router.post("/fork/{session_id}")
async def fork_branch(
    session_id: str,
    from_commit: str,
    new_branch_name: str,
    db: DBSession = Depends(get_db)
):
    """Fork a new branch from any commit"""
    
    async def generate_fork() -> AsyncGenerator[str, None]:
        try:
            yield f"data: {json.dumps({'type': 'forking', 'payload': f'Creating branch {new_branch_name} from {from_commit}'})}\n\n"
            
            branch_name = git_session_manager.fork_branch(session_id, from_commit, new_branch_name)
            
            yield f"data: {json.dumps({'type': 'branch_created', 'payload': {'branch': branch_name, 'from_commit': from_commit}})}\n\n"
            
            # Update tree
            tree = git_session_manager.get_branch_tree(session_id)
            yield f"data: {json.dumps({'type': 'tree_updated', 'payload': tree})}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'payload': f'Branch {branch_name} created successfully'})}\n\n"
            
        except Exception as e:
            logger.error(f"Fork error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_fork())
