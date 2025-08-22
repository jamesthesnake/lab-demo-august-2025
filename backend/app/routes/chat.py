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

SYSTEM_PROMPT = """You are AIDO Lab, a friendly and helpful data analysis assistant. You provide conversational responses and execute code when needed.

IMPORTANT GUIDELINES:
1. ALWAYS provide a helpful conversational response, whether executing code or not
2. For data analysis, computation, or visualization requests: use exec_python function
3. For general questions, explanations, or guidance: provide helpful conversational responses without code
4. Create realistic sample data if none is provided by the user
5. Write clean Python code with proper imports when using exec_python
6. Handle errors gracefully and explain what went wrong
7. After code execution, explain the results in a friendly manner

RESPONSE STYLE:
- Always be conversational and helpful
- For coding tasks: explain what you're about to do, then execute code, then explain results
- For non-coding tasks: provide informative, friendly responses
- Offer suggestions for next steps when appropriate
- Ask clarifying questions if the request is unclear

Available libraries: pandas, numpy, matplotlib, seaborn, scikit-learn, scipy

Examples:
- Data request: "I'll create a bar chart for you using sample data. Let me generate that visualization..." then use exec_python
- General question: "That's a great question! Here's how you can approach data visualization..." (no code needed)"""

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
        if request.message.strip().startswith(('import ', 'from ', 'print(', 'def ', 'class ', 'pd.', 'np.', 'plt.', 'sns.')):
            # Direct code execution
            result = await kernel_manager.execute_code(
                session_id=request.session_id,
                code=request.message
            )
            
            # Create a helpful response message
            response_msg = "I've executed your Python code! "
            if result.stdout:
                response_msg += "Here are the results from the execution."
            if result.artifacts:
                response_msg += f" I also generated {len(result.artifacts)} visualization(s) for you."
            if result.stderr:
                response_msg += " Note: There were some warnings or errors during execution."
            
            return ChatResponse(
                assistant_message=response_msg,
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
                assistant_message="Hi! I'm AIDO Lab, your data analysis assistant. The LLM service isn't available right now, but I can still execute Python code directly. Try sending me some Python code for data analysis, visualization, or computation!",
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
                tool_choice="auto",  # Let the model decide whether to use tools
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
                    result = await kernel_manager.execute_code(
                        session_id=request.session_id,
                        code=code,
                        execution_count=1,
                        timeout=30,
                        user_message=request.message
                    )
                    
                    code_executed = code
                    tool_results = {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "execution_count": result.execution_count,
                        "status": result.status
                    }
                    
                    # Use artifacts from execution result
                    artifacts = result.artifacts
                    
                                # Get final response from LLM with execution results
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
                            system=SYSTEM_PROMPT + "\n\nNow provide a conversational response explaining what you did and the results.",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        final_message = final_response.content[0].text if final_response.content else "I've executed the code successfully!"
                    else:
                        # For OpenAI
                        messages.append(assistant_message.model_dump())
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": "exec_python",
                            "content": json.dumps(tool_results)
                        })
                        
                        # Add instruction for conversational response
                        messages.append({
                            "role": "system",
                            "content": "Now provide a conversational response explaining what you did and the results. Be friendly and helpful."
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
            # No tool calls - just conversational response
            if llm_service.provider.value == "anthropic":
                final_message = assistant_message.content[0].text if assistant_message.content else "I can help you with that."
            else:
                final_message = assistant_message.content or "I can help you with that."
        
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