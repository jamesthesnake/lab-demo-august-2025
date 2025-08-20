"""
LLM Chat Orchestration for AIDO-Lab
Connects natural language to code execution
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ChatRequest(BaseModel):
    session_id: str
    message: str
    branch_from: Optional[str] = None

class ChatResponse(BaseModel):
    assistant_message: str
    code_executed: Optional[str] = None
    tool_results: Optional[Dict[str, Any]] = None
    commit_hash: Optional[str] = None
    artifacts: List[str] = []

SYSTEM_PROMPT = """You are AIDO Lab, a data analysis assistant. You MUST use the exec_python function for ANY request involving data analysis, computation, or visualization.

IMPORTANT: Always use exec_python to generate and execute code. Create sample data if none is provided.

When users ask for analysis, computation, or visualization:
1. ALWAYS use the exec_python function to write and execute code
2. Create realistic sample data if not provided by the user
3. Write clean Python code with proper imports
4. Create workspace directory if needed, then save plots with descriptive filenames
5. Handle errors gracefully

Available libraries: pandas, numpy, matplotlib, seaborn, scikit-learn, scipy

Example: If asked for a bar chart, immediately use exec_python with code that creates sample data and generates the chart."""

# OpenAI format tools
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "exec_python",
            "description": "Execute Python code for data analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    }
]

# Anthropic format tools
ANTHROPIC_TOOLS = [
    {
        "name": "exec_python",
        "description": "Execute Python code for data analysis",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    }
]

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with LLM orchestration"""
    
    # Import services from main
    from app.main import git_service, llm_service
    
    # Import kernel manager from main
    from app.main import kernel_manager
    
    if not llm_service:
        # Fallback: Execute code directly if it looks like Python
        if request.message.strip().startswith(('import ', 'from ', 'print(', 'def ', 'class ')):
            # Direct code execution
            result = await kernel_manager.execute_code(
                session_id=request.session_id,
                code=request.message
            )
            return ChatResponse(
                assistant_message="Code executed successfully.",
                code_executed=request.message,
                tool_results={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "execution_count": result.execution_count,
                    "status": result.status
                },
                artifacts=result.artifacts
            )
        else:
            return ChatResponse(
                assistant_message="LLM service not available. Please provide Python code directly.",
                code_executed=None,
                tool_results=None,
                artifacts=[]
            )
    
    try:
        # Call LLM with tools (supports both OpenAI and Anthropic)
        if llm_service.provider.value == "anthropic":
            # Anthropic API call - system prompt separate, no system role in messages
            messages = [{"role": "user", "content": request.message}]
            response = await llm_service.client.messages.create(
                model=llm_service.model,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=ANTHROPIC_TOOLS,
                tool_choice={"type": "tool", "name": "exec_python"},
                temperature=0.7,
                max_tokens=2000
            )
        else:
            # OpenAI API call - system prompt in messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.message}
            ]
            response = await llm_service.client.chat.completions.create(
                model=llm_service.model,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
                temperature=0.7
            )
        
        # Handle response format differences between providers
        if llm_service.provider.value == "anthropic":
            assistant_message = response
            # Extract tool calls from Anthropic response content
            tool_calls = []
            for content_block in response.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    tool_calls.append(content_block)
        else:
            assistant_message = response.choices[0].message
            tool_calls = getattr(assistant_message, 'tool_calls', None) or []
        
        # Check for tool calls
        code_executed = None
        tool_results = None
        artifacts = []
        
        if tool_calls:
            for tool_call in tool_calls:
                # Handle tool call format differences between providers
                if llm_service.provider.value == "anthropic":
                    tool_name = tool_call.name
                    tool_args = tool_call.input
                else:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name == "exec_python":
                    # Parse code from function call
                    code = tool_args["code"]
                    
                    # Execute code
                    execution_result = await kernel_manager.execute_code(
                        session_id=request.session_id,
                        code=code
                    )
                    
                    code_executed = code
                    tool_results = {
                        "stdout": execution_result.stdout,
                        "stderr": execution_result.stderr,
                        "execution_count": execution_result.execution_count,
                        "status": execution_result.status
                    }
                    
                    # Use artifacts from execution result
                    artifacts = execution_result.artifacts
                    
                    # Get final response from LLM
                    if llm_service.provider.value == "anthropic":
                        # For Anthropic, append tool result and get final response
                        messages.append({
                            "role": "assistant", 
                            "content": [{"type": "tool_use", "id": tool_call.id, "name": "exec_python", "input": tool_args}]
                        })
                        messages.append({
                            "role": "user",
                            "content": [{"type": "tool_result", "tool_use_id": tool_call.id, "content": json.dumps(tool_results)}]
                        })
                        
                        final_response = await llm_service.client.messages.create(
                            model=llm_service.model,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        final_message = final_response.content[0].text if final_response.content else "Code executed successfully."
                    else:
                        # For OpenAI
                        messages.append(assistant_message.model_dump())
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "exec_python",
                            "content": json.dumps(tool_results)
                        })
                        
                        final_response = await llm_service.client.chat.completions.create(
                            model=llm_service.model,
                            messages=messages,
                            temperature=0.7
                        )
                        
                        final_message = final_response.choices[0].message.content
                else:
                    if llm_service.provider.value == "anthropic":
                        final_message = assistant_message.content[0].text if assistant_message.content else "I can help you with that."
                    else:
                        final_message = assistant_message.content
        else:
            if llm_service.provider.value == "anthropic":
                final_message = assistant_message.content[0].text if assistant_message.content else "I can help you with that."
            else:
                final_message = assistant_message.content
        
        # Save to Git with artifacts
        commit_hash = None
        if git_service and code_executed:
            try:
                commit_info = await git_service.save_execution(
                    session_id=request.session_id,
                    code=code_executed,
                    results=tool_results or {},
                    metadata={"chat_message": request.message, "response": final_message, "artifacts": artifacts}
                )
                commit_hash = commit_info.sha if hasattr(commit_info, 'sha') else None
            except Exception as e:
                logger.error(f"Git commit failed: {e}")
        
        # Also save to file-based commit storage with artifacts
        if code_executed:
            try:
                from app.routes.git import save_session_commits, load_session_commits
                import time
                from datetime import datetime
                
                commit_data = {
                    "sha": f"chat_{int(time.time())}_{hash(code_executed) % 10000:04d}",
                    "message": f"Chat execution: {request.message[:50]}...",
                    "author": "AIDO Chat",
                    "timestamp": datetime.now().isoformat(),
                    "branch": "main",
                    "code": code_executed,
                    "artifacts": artifacts
                }
                
                commits = load_session_commits(request.session_id)
                commits.insert(0, commit_data)
                
                # Keep only last 50 commits
                if len(commits) > 50:
                    commits = commits[:50]
                
                save_session_commits(request.session_id, commits)
                logger.info(f"Chat execution committed with {len(artifacts)} artifacts")
            except Exception as e:
                logger.error(f"File-based commit failed: {e}")
        
        return ChatResponse(
            assistant_message=final_message or "I've executed the code.",
            code_executed=code_executed,
            tool_results=tool_results,
            commit_hash=commit_hash,
            artifacts=artifacts
        )
        
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return ChatResponse(
            assistant_message=f"Error: {str(e)}",
            code_executed=None,
            tool_results=None,
            artifacts=[]
        )

@router.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history with branching information"""
    from app.main import git_service
    
    if not git_service:
        return {"commits": [], "branches": [], "current_branch": "main"}
    
    try:
        commits = await git_service.get_history(session_id, limit=50)
        branches = await git_service.list_branches(session_id)
        
        return {
            "commits": [c.__dict__ for c in commits],
            "branches": [b.__dict__ for b in branches],
            "current_branch": "main"  # You'll need to implement this method
        }
    except Exception as e:
        return {"commits": [], "branches": [], "current_branch": "main", "error": str(e)}

@router.post("/api/chat/branch")
async def create_branch(session_id: str, from_commit: str, branch_name: str):
    """Create a new branch from a specific commit"""
    from app.main import git_service
    
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not available")
    
    try:
        await git_service.create_branch(
            session_id=session_id,
            branch_name=branch_name,
            from_commit=from_commit
        )
        return {"status": "success", "branch": branch_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))