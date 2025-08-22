"""
Server-Sent Events (SSE) streaming for real-time chat experience - Code Generation Only
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
    """Stream chat response with SSE - Code generation only, no auto-execution"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Import services from main
            from app.main import kernel_manager, git_service, llm_service
            
            yield f"{json.dumps({'type': 'thinking', 'payload': 'Analyzing your request...'})}\n\n"
            
            # Stream LLM response
            if llm_service and llm_service.client:
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
                
                # Adjust system prompt based on response format
                if request.response_format.value == "conversational":
                    system_prompt = "You are a helpful data science assistant. Provide conversational explanations and generate Python code when requested. Do not execute code automatically."
                    tool_choice = {"type": "auto"}
                else:
                    system_prompt = "You are a data science assistant. Generate Python code to solve user requests. Only generate code, do not execute it automatically."
                    tool_choice = {"type": "tool", "name": "generate_python"}
                
                try:
                    response = await llm_service.client.messages.create(
                        model=llm_service.model,
                        system=system_prompt,
                        messages=messages,
                        tools=[
                            {
                                "name": "generate_python",
                                "description": "Generate Python code for data science tasks",
                                "input_schema": {
                                    "type": "object",
                                    "properties": {
                                        "code": {
                                            "type": "string",
                                            "description": "The Python code to generate"
                                        },
                                        "explanation": {
                                            "type": "string", 
                                            "description": "Brief explanation of what the code does"
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
                    if "basketball" in request.message.lower() or "sports" in request.message.lower():
                        code = """import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample basketball data
np.random.seed(42)
teams = ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Nets', 'Bucks']
data = {
    'Team': teams,
    'Points_Per_Game': np.random.randint(105, 125, len(teams)),
    'Rebounds_Per_Game': np.random.randint(40, 50, len(teams)),
    'Assists_Per_Game': np.random.randint(20, 30, len(teams)),
    'Wins': np.random.randint(35, 60, len(teams)),
    'Losses': np.random.randint(22, 47, len(teams))
}

df = pd.DataFrame(data)
print("Basketball Team Statistics:")
print(df)

# Create a visualization
plt.figure(figsize=(12, 8))
plt.subplot(2, 2, 1)
plt.bar(df['Team'], df['Points_Per_Game'], color='orange', alpha=0.7)
plt.title('Points Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 2)
plt.bar(df['Team'], df['Rebounds_Per_Game'], color='blue', alpha=0.7)
plt.title('Rebounds Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 3)
plt.bar(df['Team'], df['Assists_Per_Game'], color='green', alpha=0.7)
plt.title('Assists Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 4)
plt.scatter(df['Wins'], df['Points_Per_Game'], s=100, alpha=0.7)
plt.xlabel('Wins')
plt.ylabel('Points Per Game')
plt.title('Wins vs Points Per Game')

plt.tight_layout()
plt.savefig('basketball_analysis.png', dpi=150, bbox_inches='tight')
plt.show()"""
                    else:
                        code = f"# Generated from: {request.message}\nprint('Please provide a more specific Python code request')"
                    
                    yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
                    yield f"{json.dumps({'type': 'complete', 'payload': 'Code generated - click Insert or Run to use it'})}\n\n"
                    return
                
                # Stream LLM text response
                for content_block in response.content:
                    if hasattr(content_block, 'text') and content_block.text:
                        yield f"{json.dumps({'type': 'text', 'payload': content_block.text})}\n\n"
                    elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                        code = content_block.input.get('code', '')
                        explanation = content_block.input.get('explanation', '')
                        
                        if explanation:
                            yield f"{json.dumps({'type': 'text', 'payload': explanation})}\n\n"
                        
                        yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
            else:
                # Fallback without LLM
                yield f"{json.dumps({'type': 'text', 'payload': 'LLM not available. Generating basic Python code.'})}\n\n"
                
                # Generate basic Python code based on the request
                if "basketball" in request.message.lower() or "sports" in request.message.lower():
                    code = """import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create sample basketball data
np.random.seed(42)
teams = ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Nets', 'Bucks']
data = {
    'Team': teams,
    'Points_Per_Game': np.random.randint(105, 125, len(teams)),
    'Rebounds_Per_Game': np.random.randint(40, 50, len(teams)),
    'Assists_Per_Game': np.random.randint(20, 30, len(teams)),
    'Wins': np.random.randint(35, 60, len(teams)),
    'Losses': np.random.randint(22, 47, len(teams))
}

df = pd.DataFrame(data)
print("Basketball Team Statistics:")
print(df)

# Create a visualization  
plt.figure(figsize=(12, 8))
plt.subplot(2, 2, 1)
plt.bar(df['Team'], df['Points_Per_Game'], color='orange', alpha=0.7)
plt.title('Points Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 2)
plt.bar(df['Team'], df['Rebounds_Per_Game'], color='blue', alpha=0.7)
plt.title('Rebounds Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 3)
plt.bar(df['Team'], df['Assists_Per_Game'], color='green', alpha=0.7)
plt.title('Assists Per Game')
plt.xticks(rotation=45)

plt.subplot(2, 2, 4)
plt.scatter(df['Wins'], df['Points_Per_Game'], s=100, alpha=0.7)
plt.xlabel('Wins')
plt.ylabel('Points Per Game')
plt.title('Wins vs Points Per Game')

plt.tight_layout()
plt.savefig('basketball_analysis.png', dpi=150, bbox_inches='tight')
plt.show()"""
                else:
                    code = f"# Generated from: {request.message}\nprint('Please provide a more specific Python code request')"
                
                yield f"{json.dumps({'type': 'code', 'payload': code})}\n\n"
            
            yield f"{json.dumps({'type': 'complete', 'payload': 'Code generated - use Insert or Run buttons to proceed'})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"{json.dumps({'type': 'error', 'payload': str(e)})}\n\n"
    
    return EventSourceResponse(generate_stream())