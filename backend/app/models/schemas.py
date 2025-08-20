"""
Pydantic Models and Schemas
Data validation and serialization models
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class TaskType(str, Enum):
    """Types of analysis tasks"""
    DATA_ANALYSIS = "data_analysis"
    VISUALIZATION = "visualization"
    MACHINE_LEARNING = "machine_learning"
    DATA_CLEANING = "data_cleaning"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    CODE_IMPROVEMENT = "code_improvement"
    ERROR_FIXING = "error_fixing"

class ExecutionStatus(str, Enum):
    """Execution status"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"

class FileType(str, Enum):
    """File types"""
    PYTHON = "python"
    NOTEBOOK = "notebook"
    DATA = "data"
    IMAGE = "image"
    TEXT = "text"
    JSON = "json"
    OTHER = "other"

# ============================================================================
# Request Models
# ============================================================================

class ExecuteRequest(BaseModel):
    """Request to execute code or natural language query"""
    session_id: str = Field(..., description="Session identifier")
    query: str = Field(..., description="Code or natural language query")
    is_natural_language: bool = Field(True, description="Whether query is natural language")
    task_type: Optional[TaskType] = Field(None, description="Type of task for better code generation")
    timeout: Optional[int] = Field(30, description="Execution timeout in seconds", ge=1, le=300)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for execution")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "Load the sales data and create a bar chart",
                "is_natural_language": True,
                "task_type": "visualization",
                "timeout": 30
            }
        }

class BranchRequest(BaseModel):
    """Request to create or switch branches"""
    session_id: str = Field(..., description="Session identifier")
    branch_name: str = Field(..., description="Branch name", min_length=1, max_length=100)
    from_commit: Optional[str] = Field(None, description="Commit SHA to branch from")
    
    @validator('branch_name')
    def validate_branch_name(cls, v):
        # Sanitize branch name
        import re
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Branch name can only contain letters, numbers, hyphens, and underscores")
        return v

class CheckoutRequest(BaseModel):
    """Request to checkout a commit"""
    session_id: str = Field(..., description="Session identifier")
    commit_sha: str = Field(..., description="Commit SHA to checkout", min_length=7, max_length=40)
    create_branch: bool = Field(False, description="Create a new branch at this commit")
    branch_name: Optional[str] = Field(None, description="Name for new branch if creating")

class FileUploadRequest(BaseModel):
    """File upload metadata"""
    session_id: str = Field(..., description="Session identifier")
    filename: str = Field(..., description="File name")
    path: Optional[str] = Field(None, description="Target path in workspace")
    description: Optional[str] = Field(None, description="File description")

class ChatRequest(BaseModel):
    """Request for chat/streaming conversation"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v

class SuggestionRequest(BaseModel):
    """Request for AI suggestions"""
    session_id: str = Field(..., description="Session identifier")
    goal: Optional[str] = Field(None, description="Analysis goal")
    context_limit: int = Field(5, description="Number of previous executions to consider", ge=1, le=20)

# ============================================================================
# Response Models
# ============================================================================

class ExecutionResultData(BaseModel):
    """Execution result data"""
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    display_data: List[Dict[str, Any]] = Field([], description="Display data (plots, tables, etc.)")
    errors: List[Dict[str, Any]] = Field([], description="Execution errors")
    execution_count: int = Field(0, description="Execution count")
    status: ExecutionStatus = Field(ExecutionStatus.OK, description="Execution status")
    artifacts: List[Dict[str, Any]] = Field([], description="Generated artifacts (plots, tables, files)")

class CommitInfoResponse(BaseModel):
    """Git commit information"""
    sha: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    timestamp: datetime = Field(..., description="Commit timestamp")
    parent_sha: Optional[str] = Field(None, description="Parent commit SHA")
    branch: str = Field(..., description="Branch name")
    files_changed: List[str] = Field([], description="List of changed files")

class ExecuteResponse(BaseModel):
    """Response from code execution"""
    code: str = Field(..., description="Executed code")
    results: ExecutionResultData = Field(..., description="Execution results")
    commit: Optional[CommitInfoResponse] = Field(None, description="Git commit info")
    metadata: Dict[str, Any] = Field({}, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str = Field(..., description="Session identifier")
    created_at: datetime = Field(..., description="Session creation time")
    workspace_path: str = Field(..., description="Workspace directory path")
    executions: List[Dict[str, Any]] = Field([], description="Execution history")
    kernel_status: Optional[Dict[str, Any]] = Field(None, description="Kernel status")
    repository_stats: Optional[Dict[str, Any]] = Field(None, description="Git repository statistics")
    active: bool = Field(True, description="Whether session is active")

class BranchInfo(BaseModel):
    """Git branch information"""
    name: str = Field(..., description="Branch name")
    current: bool = Field(False, description="Whether this is the current branch")
    commits_ahead: int = Field(0, description="Commits ahead of main")
    commits_behind: int = Field(0, description="Commits behind main")
    last_commit: Optional[CommitInfoResponse] = Field(None, description="Last commit on branch")

class HistoryResponse(BaseModel):
    """Execution history response"""
    commits: List[Dict[str, Any]] = Field([], description="List of commits")
    tree: Dict[str, Any] = Field({}, description="History tree structure")
    current_branch: Optional[str] = Field(None, description="Current branch name")
    head: Optional[str] = Field(None, description="HEAD commit SHA")

class FileInfo(BaseModel):
    """File information"""
    name: str = Field(..., description="File name")
    path: str = Field(..., description="File path relative to workspace")
    size: int = Field(..., description="File size in bytes")
    modified: datetime = Field(..., description="Last modified time")
    type: FileType = Field(..., description="File type")

class FileListResponse(BaseModel):
    """File list response"""
    files: List[FileInfo] = Field([], description="List of files")
    workspace_path: str = Field(..., description="Workspace path")
    total_size: Optional[int] = Field(None, description="Total size of all files")

class SuggestionResponse(BaseModel):
    """AI suggestions response"""
    suggestions: List[str] = Field([], description="List of suggested next steps")
    context_summary: str = Field("", description="Summary of context used")
    confidence: float = Field(0.0, description="Confidence in suggestions", ge=0.0, le=1.0)

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field({}, description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")

class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    status_code: int = Field(500, description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

# ============================================================================
# Complex Request/Response Models
# ============================================================================

class CodeGenerationRequest(BaseModel):
    """Request for code generation"""
    query: str = Field(..., description="Natural language query")
    context: Optional[Dict[str, Any]] = Field(None, description="Context for generation")
    task_type: TaskType = Field(TaskType.DATA_ANALYSIS, description="Type of task")
    temperature: float = Field(0.7, description="Generation temperature", ge=0.0, le=1.0)
    max_tokens: int = Field(2000, description="Maximum tokens to generate", ge=100, le=4000)

class CodeGenerationResponse(BaseModel):
    """Response from code generation"""
    code: str = Field(..., description="Generated code")
    explanation: str = Field("", description="Code explanation")
    confidence: float = Field(0.0, description="Confidence in generation", ge=0.0, le=1.0)
    libraries_used: List[str] = Field([], description="Libraries used in code")
    warnings: List[str] = Field([], description="Warnings about the code")

class ExportRequest(BaseModel):
    """Request to export session"""
    session_id: str = Field(..., description="Session identifier")
    format: Literal["notebook", "python", "html", "markdown"] = Field("notebook", description="Export format")
    branch: Optional[str] = Field(None, description="Branch to export")
    include_outputs: bool = Field(True, description="Include execution outputs")

class ImportRequest(BaseModel):
    """Request to import notebook or code"""
    session_id: str = Field(..., description="Session identifier")
    format: Literal["notebook", "python"] = Field(..., description="Import format")
    content: str = Field(..., description="Content to import")
    execute_on_import: bool = Field(False, description="Execute code after import")

class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., description="Search query")
    session_id: Optional[str] = Field(None, description="Limit search to session")
    file_types: Optional[List[FileType]] = Field(None, description="Filter by file types")
    date_from: Optional[datetime] = Field(None, description="Search from date")
    date_to: Optional[datetime] = Field(None, description="Search to date")
    limit: int = Field(50, description="Maximum results", ge=1, le=200)

class SearchResult(BaseModel):
    """Search result item"""
    session_id: str = Field(..., description="Session ID")
    file_path: str = Field(..., description="File path")
    line_number: Optional[int] = Field(None, description="Line number in file")
    content: str = Field(..., description="Matched content")
    context: str = Field("", description="Surrounding context")
    score: float = Field(0.0, description="Relevance score")

class SearchResponse(BaseModel):
    """Search response"""
    results: List[SearchResult] = Field([], description="Search results")
    total_count: int = Field(0, description="Total number of results")
    query: str = Field(..., description="Original query")

# ============================================================================
# Utility Models
# ============================================================================

class HealthStatus(BaseModel):
    """Health check status"""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: Dict[str, bool] = Field({}, description="Service statuses")
    kernel_count: Optional[int] = Field(None, description="Active kernel count")
    version: str = Field("0.1.0", description="API version")

class SystemStats(BaseModel):
    """System statistics"""
    total_sessions: int = Field(0, description="Total sessions")
    active_kernels: int = Field(0, description="Active kernels")
    total_executions: int = Field(0, description="Total executions")
    disk_usage_mb: float = Field(0.0, description="Disk usage in MB")
    memory_usage_mb: float = Field(0.0, description="Memory usage in MB")
    uptime_seconds: float = Field(0.0, description="Uptime in seconds")

class UserPreferences(BaseModel):
    """User preferences"""
    theme: Literal["light", "dark", "auto"] = Field("auto", description="UI theme")
    font_size: int = Field(14, description="Editor font size", ge=10, le=24)
    tab_size: int = Field(4, description="Tab size", ge=2, le=8)
    auto_save: bool = Field(True, description="Auto-save enabled")
    show_line_numbers: bool = Field(True, description="Show line numbers")
    word_wrap: bool = Field(False, description="Word wrap enabled")
    
# ============================================================================
# Batch Operations
# ============================================================================

class BatchExecuteRequest(BaseModel):
    """Request to execute multiple code blocks"""
    session_id: str = Field(..., description="Session identifier")
    executions: List[ExecuteRequest] = Field(..., description="List of executions")
    stop_on_error: bool = Field(True, description="Stop execution on first error")
    parallel: bool = Field(False, description="Execute in parallel")

class BatchExecuteResponse(BaseModel):
    """Response from batch execution"""
    results: List[ExecuteResponse] = Field([], description="Execution results")
    success_count: int = Field(0, description="Number of successful executions")
    error_count: int = Field(0, description="Number of failed executions")
    total_time: float = Field(0.0, description="Total execution time in seconds")
