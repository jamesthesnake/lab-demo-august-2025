"""
LLM Chat Orchestration Endpoint
Handles natural language → code generation → execution → results
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import httpx
import asyncio
from datetime import datetime

# Import your existing services
from app.services.kernel_manager import KernelManager
from app.services.git_service import GitService

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    message: str
    branch_from: Optional[str] = None  # For branching history

class ChatResponse(BaseModel):
    assistant_message: Dict[str, Any]
    tool_results: Optional[Dict[str, Any]] = None
    commit_hash: str
    artifacts: List[str] = []

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# System prompt for the data analysis assistant
SYSTEM_PROMPT = """You are AIDO Lab, an expert data analysis assistant.

Your capabilities:
- Execute Python code for data analysis, visualization, and computation
- Create plots, tables, and statistical analyses
- Work with various data formats (CSV, JSON, etc.)
- Perform machine learning and statistical modeling

Guidelines:
- When code execution is needed, use the exec_python tool
- Write clean, efficient, and well-commented code
- Prefer pandas for data manipulation and matplotlib/seaborn for visualization
- Always handle potential errors gracefully
- Keep outputs concise and informative
- Save visualizations as files for display

You have access to common data science libraries: numpy, pandas, matplotlib, seaborn, scikit-learn, scipy, etc.
"""

# Tool schema for function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "exec_python",
            "description": "Execute Python code in a sandboxed Jupyter kernel",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename to save the code",
                        "nullable": True
                    }
                },
                "required": ["code"]
            }
        }
    }
]

async def call_llm(messages: List[Dict], tools: Optional[List] = None, tool_choice: str = "auto"):
    """Call OpenAI API with messages and optional tools"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))

async def execute_python_code(session_id: str, code: str, filename: Optional[str] = None):
    """Execute Python code using the kernel manager"""
    kernel_manager = KernelManager(session_id=session_id)
    
    # Ensure kernel is ready
    await kernel_manager.ensure_kernel()
    
    # Execute the code
    result = await kernel_manager.execute_code(code)
    
    # Collect artifacts (images, CSVs, etc.)
    artifacts = []
    workspace_path = f"/app/workspaces/{session_id}"
    
    # Check for generated files
    if os.path.exists(workspace_path):
        for file in os.listdir(workspace_path):
            if file.endswith(('.png', '.jpg', '.svg', '.csv', '.json')):
                artifacts.append(f"/workspace/{session_id}/{file}")
    
    return {
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "status": result.get("status", "ok"),
        "artifacts": artifacts
    }

async def load_conversation_history(session_id: str, branch: Optional[str] = None):
    """Load conversation history from Git"""
    git_service = GitService(session_id)
    
    if branch:
        git_service.checkout_branch(branch)
    
    # Load messages from Git history or database
    # For now, return empty history
    return []

@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint that orchestrates LLM and code execution"""
    
    session_id = request.session_id
    user_message = request.message
    
    # Initialize Git service for this session
    git_service = GitService(session_id)
    
    # Handle branching if requested
    if request.branch_from:
        git_service.create_branch(f"analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    
    # Load conversation history
    history = await load_conversation_history(session_id, request.branch_from)
    
    # Construct messages for LLM
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_message}
    ]
    
    # Call LLM with tools
    llm_response = await call_llm(messages, TOOLS)
    assistant_message = llm_response["choices"][0]["message"]
    messages.append(assistant_message)
    
    tool_results = None
    artifacts = []
    
    # Handle tool calls if present
    if "tool_calls" in assistant_message:
        for tool_call in assistant_message["tool_calls"]:
            if tool_call["function"]["name"] == "exec_python":
                # Parse arguments
                args = json.loads(tool_call["function"]["arguments"])
                code = args["code"]
                filename = args.get("filename")
                
                # Execute the code
                execution_result = await execute_python_code(session_id, code, filename)
                tool_results = execution_result
                artifacts = execution_result["artifacts"]
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": "exec_python",
                    "content": json.dumps(execution_result)
                })
        
        # Get final response from LLM after tool execution
        final_response = await call_llm(messages)
        assistant_message = final_response["choices"][0]["message"]
    
    # Commit to Git
    commit_data = {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "tool_results": tool_results,
        "timestamp": datetime.now().isoformat()
    }
    
    commit_hash = git_service.commit_snapshot(
        message=f"Chat: {user_message[:50]}...",
        data=commit_data
    )
    
    return ChatResponse(
        assistant_message=assistant_message,
        tool_results=tool_results,
        commit_hash=commit_hash,
        artifacts=artifacts
    )

@router.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history with branching information"""
    git_service = GitService(session_id)
    commits = git_service.get_commits()
    branches = git_service.get_branches()
    
    return {
        "commits": commits,
        "branches": branches,
        "current_branch": git_service.current_branch()
    }

@router.post("/api/chat/branch")
async def create_branch(session_id: str, from_commit: str, branch_name: str):
    """Create a new branch from a specific commit"""
    git_service = GitService(session_id)
    git_service.create_branch_from_commit(branch_name, from_commit)
    return {"status": "success", "branch": branch_name}
