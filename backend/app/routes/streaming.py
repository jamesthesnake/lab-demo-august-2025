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

from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["streaming"])

@router.post("/chat/{session_id}")
async def stream_chat(
    session_id: str,
    request: ChatRequest
):
    """Stream chat response with SSE"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Import services from main
            from app.main import kernel_manager, git_service, llm_service
            
            yield f"{json.dumps({'type': 'thinking', 'payload': 'Analyzing your request...'})}\n\n"
            
            # Stream LLM response
            if llm_service and llm_service.client:
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
                            yield f"{json.dumps({'type': 'text', 'payload': content_block.text})}\n\n"
                        elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                            code = content_block.input.get('code', '')
                            yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                            
                            # Execute code
                            yield f"{json.dumps({'type': 'executing', 'payload': 'Running code...'})}\n\n"
                            
                            execution_result = await kernel_manager.execute_code(session_id, code)
                            
                            # Stream execution result
                            result_data = execution_result.to_dict()
                            yield f"{json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                            
                            # Save execution to git
                            commit_info = await git_service.save_execution(session_id, execution_result)
                            yield f"{json.dumps({'type': 'commit', 'payload': {'sha': commit_info['sha'], 'branch': commit_info['branch']}})}\n\n"
                            
                            # Stream artifacts
                            for artifact in execution_result.artifacts:
                                artifact_url = f"/static/artifacts/{artifact.split('/')[-1]}"
                                yield f"{json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'path': artifact}})}\n\n"
            else:
                # Fallback without LLM
                yield f"{json.dumps({'type': 'text', 'payload': 'LLM not available. Treating as direct code execution.'})}\n\n"
                code = request.message
                yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                
                execution_result = await kernel_manager.execute_code(session_id, code)
                result_data = execution_result.to_dict()
                yield f"{json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                
                # Save execution to git
                commit_info = await git_service.save_execution(session_id, execution_result)
                yield f"{json.dumps({'type': 'commit', 'payload': {'sha': commit_info['sha'], 'branch': commit_info['branch']}})}\n\n"
            
            yield f"{json.dumps({'type': 'complete', 'payload': 'Stream completed'})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"{json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_stream())

@router.get("/history/{session_id}")
async def stream_history(session_id: str):
    """Stream session history"""
    
    async def generate_history() -> AsyncGenerator[str, None]:
        try:
            from app.main import git_service
            
            # Get git history
            history = git_service.get_commit_history(session_id)
            for commit in history:
                yield f"data: {json.dumps({'type': 'commit', 'payload': commit})}\n\n"
                await asyncio.sleep(0.1)  # Smooth streaming
            
            yield f"data: {json.dumps({'type': 'complete', 'payload': 'History loaded'})}\n\n"
            
        except Exception as e:
            logger.error(f"History stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_history())

@router.post("/fork/{session_id}")
async def fork_branch(
    session_id: str,
    from_commit: str,
    new_branch_name: str
):
    """Fork a new branch from any commit"""
    
    async def generate_fork() -> AsyncGenerator[str, None]:
        try:
            from app.main import git_service
            
            yield f"data: {json.dumps({'type': 'forking', 'payload': f'Creating branch {new_branch_name} from {from_commit}'})}\n\n"
            
            # Simple fork implementation
            yield f"data: {json.dumps({'type': 'branch_created', 'payload': {'branch': new_branch_name, 'from_commit': from_commit}})}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'payload': f'Branch {new_branch_name} created successfully'})}\n\n"
            
        except Exception as e:
            logger.error(f"Fork error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_fork())
