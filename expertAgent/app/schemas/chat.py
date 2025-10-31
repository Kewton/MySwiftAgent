"""Chat feature schemas for requirement clarification and job creation.

This module provides Pydantic models for the chat-based job creation flow:
1. RequirementChatRequest: User message with conversation context
2. RequirementState: Current state of requirement clarification
3. CreateJobRequest: Request to create job from clarified requirements
4. CreateJobResponse: Response after job creation
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class RequirementState(BaseModel):
    """State of requirement clarification process.

    Tracks the completeness of job requirements through chat dialogue.
    Completeness is calculated based on filled fields:
    - data_source: +0.25
    - process_description: +0.35 (most important)
    - output_format: +0.25
    - schedule: +0.15
    Total ≥ 0.8 (80%) is required for job creation.
    """

    data_source: Optional[str] = Field(
        None,
        description="Data source (CSV, Excel, Database, API, etc.)",
        examples=["CSVファイル", "PostgreSQLデータベース", "Google Sheets"],
    )
    process_description: Optional[str] = Field(
        None,
        description="Description of processing to perform",
        examples=["売上データを月別に集計", "顧客データの分析", "レポート生成"],
    )
    output_format: Optional[str] = Field(
        None,
        description="Expected output format",
        examples=["Excelレポート", "PDFドキュメント", "JSON API"],
    )
    schedule: Optional[str] = Field(
        None,
        description="Execution schedule",
        examples=["毎日朝9時", "毎週月曜日", "オンデマンド"],
    )
    completeness: float = Field(
        0.0,
        description="Requirement clarification progress (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class Message(BaseModel):
    """Chat message model."""

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")


class RequirementChatRequest(BaseModel):
    """Request for requirement clarification chat (SSE).

    Includes conversation context and current requirement state
    to enable contextual AI responses.
    """

    conversation_id: str = Field(..., description="Unique conversation session ID")
    user_message: str = Field(..., description="User's latest message")
    context: Dict = Field(
        ...,
        description="Conversation context including previous messages and current requirements",
    )


class CreateJobRequest(BaseModel):
    """Request to create job from clarified requirements."""

    conversation_id: str = Field(..., description="Conversation session ID")
    requirements: RequirementState = Field(..., description="Clarified requirements")


class CreateJobResponse(BaseModel):
    """Response after job creation."""

    job_id: str = Field(..., description="Created job ID")
    job_master_id: str = Field(..., description="Job master ID")
    status: str = Field(..., description="Creation status (success, failed)")
    message: str = Field(..., description="Human-readable status message")
