"""Diagnostic API schemas.

Issue #171: Diagnostic Information Retrieval API Implementation.
Defines request/response schemas for diagnostic endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MessageInfo(BaseModel):
    """Individual message information in a conversation turn."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(None, description="Message timestamp")
    tokens: Optional[int] = Field(None, description="Token count for this message")


class TokenUsage(BaseModel):
    """Token usage statistics for a conversation."""

    total_tokens: int = Field(0, description="Total tokens used", ge=0)
    input_tokens: int = Field(0, description="Input tokens (prompts)", ge=0)
    output_tokens: int = Field(0, description="Output tokens (completions)", ge=0)


class LangfuseLink(BaseModel):
    """Langfuse trace link information."""

    trace_id: Optional[str] = Field(None, description="Langfuse trace ID")
    trace_url: Optional[str] = Field(None, description="Full Langfuse trace URL")
    session_id: Optional[str] = Field(None, description="Langfuse session ID")


class DiagnosticInfo(BaseModel):
    """Diagnostic information for a single conversation.

    Contains all details needed for debugging and analysis of a conversation,
    including system prompts, messages, token usage, and Langfuse trace links.
    """

    conversation_id: str = Field(..., description="Unique conversation identifier")
    job_id: Optional[str] = Field(None, description="Associated job ID")
    user_id: Optional[str] = Field(None, description="User ID")
    project_id: Optional[str] = Field(None, description="Project ID")
    workflow_id: Optional[str] = Field(None, description="Workflow ID")
    system_prompt: Optional[str] = Field(
        None, description="Full system prompt used in the conversation"
    )
    messages: List[MessageInfo] = Field(
        default_factory=list, description="List of conversation messages"
    )
    token_usage: TokenUsage = Field(
        default_factory=lambda: TokenUsage(  # type: ignore[call-arg]
            total_tokens=0, input_tokens=0, output_tokens=0
        ),
        description="Token usage statistics",
    )
    langfuse_link: LangfuseLink = Field(
        default_factory=lambda: LangfuseLink(  # type: ignore[call-arg]
            trace_id=None, trace_url=None, session_id=None
        ),
        description="Langfuse trace link",
    )
    prompt_version: Optional[str] = Field(None, description="Prompt version used")
    created_at: Optional[datetime] = Field(
        None, description="Conversation creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Conversation last update timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class DiagnosticListQuery(BaseModel):
    """Query parameters for diagnostic list endpoint."""

    job_id: Optional[str] = Field(None, description="Filter by job ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    project_id: Optional[str] = Field(None, description="Filter by project ID")
    workflow_id: Optional[str] = Field(None, description="Filter by workflow ID")
    start_date: Optional[datetime] = Field(
        None, description="Filter conversations created after this date"
    )
    end_date: Optional[datetime] = Field(
        None, description="Filter conversations created before this date"
    )
    limit: int = Field(
        100,
        description="Maximum number of results to return",
        ge=1,
        le=1000,
    )
    offset: int = Field(
        0,
        description="Number of results to skip for pagination",
        ge=0,
    )


class DiagnosticListResponse(BaseModel):
    """Response for diagnostic list endpoint."""

    items: List[DiagnosticInfo] = Field(
        default_factory=list, description="List of diagnostic info items"
    )
    total: int = Field(0, description="Total number of matching items", ge=0)
    limit: int = Field(100, description="Limit used in the query", ge=1)
    offset: int = Field(0, description="Offset used in the query", ge=0)
    has_more: bool = Field(False, description="Whether there are more items available")


class DiagnosticSummary(BaseModel):
    """Summary statistics for diagnostic queries."""

    total_conversations: int = Field(0, description="Total number of conversations")
    total_tokens: int = Field(0, description="Total tokens used across conversations")
    average_tokens: float = Field(0.0, description="Average tokens per conversation")
    unique_users: int = Field(0, description="Number of unique users")
    unique_jobs: int = Field(0, description="Number of unique jobs")
    date_range_start: Optional[datetime] = Field(
        None, description="Earliest conversation date"
    )
    date_range_end: Optional[datetime] = Field(
        None, description="Latest conversation date"
    )
