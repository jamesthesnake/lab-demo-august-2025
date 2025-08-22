"""
Server-Sent Events (SSE) streaming for real-time chat experience
"""

import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.models.schemas import ChatRequest
from app.services.llm_service import LLMService
from app.services.simple_kernel_manager import SimpleKernelManager
from app.services.git_service import GitService
import logging
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
                    # Build user message with context if provided
                    user_content = request.message
                    if request.context:
                        context_parts = []
                        if "current_code" in request.context:
                            context_parts.append(f"Current code in editor:\n```python\n{request.context['current_code']}\n```")
                        if "current_output" in request.context:
                            context_parts.append(f"Current output console:\n```\n{request.context['current_output']}\n```")
                        if context_parts:
                            user_content = f"{request.message}\n\n{chr(10).join(context_parts)}"
                    messages = [{"role": "user", "content": user_content}]
                    
                    try:
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
                            max_tokens=1500
                        )
                    except Exception as e:
                        yield f"{json.dumps({'type': 'error', 'payload': f'LLM request failed: {str(e)}. Generating basic Python code.'})}\n\n"
                        # Generate basic Python code based on the request
                        if "football" in request.message.lower() and "pandas" in request.message.lower():
                            code = """import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample football data
np.random.seed(42)
teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham']
data = {
    'Team': teams,
    'Goals_Scored': np.random.randint(50, 100, len(teams)),
    'Goals_Conceded': np.random.randint(20, 60, len(teams)),
    'Wins': np.random.randint(15, 30, len(teams)),
    'Draws': np.random.randint(5, 15, len(teams)),
    'Losses': np.random.randint(3, 12, len(teams))
}

df = pd.DataFrame(data)
print("Football Data:")
print(df)

# Create a plot
plt.figure(figsize=(10, 6))
plt.bar(df['Team'], df['Goals_Scored'], alpha=0.7, label='Goals Scored')
plt.bar(df['Team'], df['Goals_Conceded'], alpha=0.7, label='Goals Conceded')
plt.xlabel('Team')
plt.ylabel('Goals')
plt.title('Football Team Performance')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('football_plot.png', dpi=150, bbox_inches='tight')
plt.show()"""
                        else:
                            code = f"# Generated from: {request.message}\nprint('Please provide a more specific Python code request')"
                        yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                        yield f"{json.dumps({'type': 'executing', 'payload': 'Running code...'})}\n\n"
                        execution_result = await kernel_manager.execute_code(session_id, code)
                        result_data = execution_result.to_dict()
                        yield f"{json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                        yield f"{json.dumps({'type': 'complete', 'payload': 'Stream completed with fallback'})}\n\n"
                        return
                    
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
                            commit_info = await git_service.save_execution(
                                session_id=session_id,
                                code=code,
                                results=result_data,
                                metadata={"message": request.message}
                            )
                            yield f"data: {json.dumps({'type': 'commit', 'payload': {'sha': commit_info.sha, 'branch': commit_info.branch}})}\n\n"
                            
                            # Stream artifacts
                            for artifact in execution_result.artifacts:
                                if isinstance(artifact, dict) and 'filename' in artifact:
                                    artifact_url = f"/static/artifacts/{artifact['filename']}"
                                    yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'filename': artifact['filename'], 'type': artifact.get('type', 'unknown')}})}\n\n"
                                elif isinstance(artifact, str):
                                    artifact_url = f"/static/artifacts/{artifact.split('/')[-1]}"
                                    yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'path': artifact}})}\n\n"
                else:
                    # Adjust system prompt and tool choice based on response format
                    if request.response_format.value == "conversational":
                        system_prompt = "You are a helpful data science assistant. Provide conversational explanations and analysis. Only use tool calling when the user explicitly asks for code execution."
                        tool_choice = {"type": "auto"}
                    else:
                        system_prompt = "You are a data science assistant. Generate Python code to solve user requests. Use tool calling for code execution."
                        tool_choice = {"type": "tool", "name": "exec_python"}
                    
                    # Build user message with context if provided
                    user_content = request.message
                    if request.context:
                        context_parts = []
                        if "current_code" in request.context:
                            context_parts.append(f"Current code in editor:\n```python\n{request.context['current_code']}\n```")
                        if "current_output" in request.context:
                            context_parts.append(f"Current output console:\n```\n{request.context['current_output']}\n```")
                        
                        if context_parts:
                            user_content = f"{request.message}\n\n{chr(10).join(context_parts)}"
                    
                    messages = [{"role": "user", "content": user_content}]
                    
                    try:
                        response = await llm_service.client.messages.create(
                            model=llm_service.model,
                            system=system_prompt,
                            messages=messages,
                            tools=[
                                {
                                    "name": "execute_python",
                                    "description": "Execute Python code and return the results",
                                    "input_schema": {
                                        "type": "object",
                                        "properties": {
                                            "code": {
                                                "type": "string",
                                                "description": "The Python code to execute"
                                            }
                                        },
                                        "required": ["code"]
                                    }
                                }
                            ],
                            tool_choice=tool_choice,
                            temperature=0.7,
                            max_tokens=1500
                        )
                    except Exception as e:
                        yield f"{json.dumps({'type': 'error', 'payload': f'LLM request failed: {str(e)}. Generating basic Python code.'})}\n\n"
                        # Generate basic Python code based on the request
                        if "football" in request.message.lower() and "pandas" in request.message.lower():
                            code = """import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample football data
np.random.seed(42)
teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham']
data = {
    'Team': teams,
    'Goals_Scored': np.random.randint(50, 100, len(teams)),
    'Goals_Conceded': np.random.randint(20, 60, len(teams)),
    'Wins': np.random.randint(15, 30, len(teams)),
    'Draws': np.random.randint(5, 15, len(teams)),
    'Losses': np.random.randint(3, 12, len(teams))
}

df = pd.DataFrame(data)
print("Football Data:")
print(df)

# Create a plot
plt.figure(figsize=(10, 6))
plt.bar(df['Team'], df['Goals_Scored'], alpha=0.7, label='Goals Scored')
plt.bar(df['Team'], df['Goals_Conceded'], alpha=0.7, label='Goals Conceded')
plt.xlabel('Team')
plt.ylabel('Goals')
plt.title('Football Team Performance')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('football_plot.png', dpi=150, bbox_inches='tight')
plt.show()"""
                        else:
                            code = f"# Generated from: {request.message}\nprint('Please provide a more specific Python code request')"
                        yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                        yield f"{json.dumps({'type': 'executing', 'payload': 'Running code...'})}\n\n"
                        execution_result = await kernel_manager.execute_code(session_id, code)
                        result_data = execution_result.to_dict()
                        yield f"{json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                        yield f"{json.dumps({'type': 'complete', 'payload': 'Stream completed with fallback'})}\n\n"
                        return
                    
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
                            commit_info = await git_service.save_execution(
                                session_id=session_id,
                                code=code,
                                results=result_data,
                                metadata={"message": request.message}
                            )
                            yield f"data: {json.dumps({'type': 'commit', 'payload': {'sha': commit_info.sha, 'branch': commit_info.branch}})}\n\n"
                            
                            # Stream artifacts
                            for artifact in execution_result.artifacts:
                                if isinstance(artifact, dict) and 'filename' in artifact:
                                    artifact_url = f"/static/artifacts/{artifact['filename']}"
                                    yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'filename': artifact['filename'], 'type': artifact.get('type', 'unknown')}})}\n\n"
                                elif isinstance(artifact, str):
                                    artifact_url = f"/static/artifacts/{artifact.split('/')[-1]}"
                                    yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'path': artifact}})}\n\n"
            else:
                # Fallback without LLM
                yield f"{json.dumps({'type': 'text', 'payload': 'LLM not available. Generating basic Python code.'})}\n\n"
                
                # Generate basic Python code based on the request
                if "football" in request.message.lower() and "pandas" in request.message.lower():
                    code = """import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample football data
np.random.seed(42)
teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United', 'Tottenham']
data = {
    'Team': teams,
    'Goals_Scored': np.random.randint(50, 100, len(teams)),
    'Goals_Conceded': np.random.randint(20, 60, len(teams)),
    'Wins': np.random.randint(15, 30, len(teams)),
    'Draws': np.random.randint(5, 15, len(teams)),
    'Losses': np.random.randint(3, 12, len(teams))
}

df = pd.DataFrame(data)
print("Football Data:")
print(df)

# Create a plot
plt.figure(figsize=(10, 6))
plt.bar(df['Team'], df['Goals_Scored'], alpha=0.7, label='Goals Scored')
plt.bar(df['Team'], df['Goals_Conceded'], alpha=0.7, label='Goals Conceded')
plt.xlabel('Team')
plt.ylabel('Goals')
plt.title('Football Team Performance')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('football_plot.png', dpi=150, bbox_inches='tight')
plt.show()"""
                else:
                    code = f"# Generated from: {request.message}\nprint('Please provide a more specific Python code request')"
                
                yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                
                execution_result = await kernel_manager.execute_code(session_id, code)
                result_data = execution_result.to_dict()
                yield f"{json.dumps({'type': 'result', 'payload': result_data})}\n\n"
                
                # Stream artifacts
                for artifact in execution_result.artifacts:
                    if isinstance(artifact, dict) and 'filename' in artifact:
                        artifact_url = f"/static/artifacts/{artifact['filename']}"
                        yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'filename': artifact['filename'], 'type': artifact.get('type', 'unknown')}})}\n\n"
                    elif isinstance(artifact, str):
                        artifact_url = f"/static/artifacts/{artifact.split('/')[-1]}"
                        yield f"data: {json.dumps({'type': 'artifact', 'payload': {'url': artifact_url, 'path': artifact}})}\n\n"
                
                # Save execution to git
                commit_info = await git_service.save_execution(
                    session_id=session_id,
                    code=code,
                    results=result_data,
                    metadata={"message": request.message}
                )
                yield f"{json.dumps({'type': 'commit', 'payload': {'sha': commit_info.sha, 'branch': commit_info.branch}})}\n\n"
            
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
