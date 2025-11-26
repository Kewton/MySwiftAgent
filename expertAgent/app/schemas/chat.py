"""Chat feature schemas for requirement clarification and job creation.

This module provides Pydantic models for the chat-based job creation flow:
1. RequirementChatRequest: User message with conversation context
2. RequirementState: Current state of requirement clarification
3. CreateJobRequest: Request to create job from clarified requirements
4. CreateJobResponse: Response after job creation
5. RequirementCandidate: Single requirement interpretation candidate
6. CandidateSelectionEvent: SSE event for candidate selection
7. CandidateSelectRequest: Request to select a candidate
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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


class ContextData(BaseModel):
    """Conversation context structure for requirement chat.

    Validates that all required context fields are present before
    SSE streaming begins, preventing runtime KeyError exceptions.
    """

    previous_messages: List[Dict[str, Any]] = Field(
        ...,
        description="Previous messages in the conversation",
        examples=[[{"role": "user", "content": "Hello"}]],
    )
    current_requirements: Dict[str, Any] = Field(
        ...,
        description="Current requirement state (must include all RequirementState fields)",
        examples=[
            {
                "data_source": None,
                "process_description": None,
                "output_format": None,
                "schedule": None,
                "completeness": 0.0,
            }
        ],
    )


class RequirementChatRequest(BaseModel):
    """Request for requirement clarification chat (SSE).

    Includes conversation context and current requirement state
    to enable contextual AI responses.
    """

    conversation_id: str = Field(..., description="Unique conversation session ID")
    user_message: str = Field(..., description="User's latest message")
    context: ContextData = Field(
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


# ============================================================================
# Multi-Candidate Suggestion Feature (Issue #173)
# ============================================================================


class RequirementCandidate(BaseModel):
    """Single requirement interpretation candidate.

    Represents one possible interpretation of user's requirement,
    containing all four aspects of job requirements plus metadata.

    Used in the multi-candidate suggestion feature to present
    alternative interpretations to the user.
    """

    candidate_id: Literal["A", "B"] = Field(
        ...,
        description="Candidate identifier ('A' or 'B')",
        examples=["A", "B"],
    )
    title: str = Field(
        ...,
        description="Short title summarizing this interpretation (max 20 chars)",
        examples=["簡易分析", "詳細レポート", "リアルタイム集計"],
    )
    data_source: str = Field(
        ...,
        description="Proposed data source",
        examples=["CSVファイル", "データベース", "API", "Google Sheets"],
    )
    process_description: str = Field(
        ...,
        description="Proposed processing description",
        examples=["売上データの月別集計", "顧客分析とトレンド予測"],
    )
    output_format: str = Field(
        ...,
        description="Proposed output format",
        examples=["Excelレポート", "PDFドキュメント", "Slackメッセージ"],
    )
    schedule: str = Field(
        ...,
        description="Proposed execution schedule",
        examples=["オンデマンド", "毎日実行", "毎週月曜日"],
    )
    confidence: float = Field(
        ...,
        description="Confidence score for this interpretation (0.0-1.0)",
        ge=0.0,
        le=1.0,
        examples=[0.85, 0.75],
    )

    @field_validator("candidate_id")
    @classmethod
    def validate_candidate_id(cls, v: str) -> str:
        """Validate that candidate_id is 'A' or 'B'."""
        if v not in ("A", "B"):
            raise ValueError("candidate_id must be 'A' or 'B'")
        return v


class CandidateSelectionEvent(BaseModel):
    """SSE event payload for candidate selection.

    Sent when the system presents multiple interpretation candidates
    for the user to choose from (typically on initial message).
    """

    candidates: List[RequirementCandidate] = Field(
        ...,
        description="List of requirement candidates (typically 2)",
        min_length=1,
    )
    prompt_for_selection: str = Field(
        ...,
        description="Message prompting user to select a candidate",
        examples=["どちらの解釈がお望みに近いですか？AまたはBを選んでください。"],
    )


class CandidateSelectRequest(BaseModel):
    """Request to select a candidate interpretation.

    Sent when user selects one of the presented candidates
    to continue the conversation with that interpretation.
    """

    conversation_id: str = Field(
        ...,
        description="Conversation session ID",
    )
    selected_candidate_id: Literal["A", "B"] = Field(
        ...,
        description="Selected candidate identifier ('A' or 'B')",
        examples=["A", "B"],
    )

    @field_validator("selected_candidate_id")
    @classmethod
    def validate_selected_candidate_id(cls, v: str) -> str:
        """Validate that selected_candidate_id is 'A' or 'B'."""
        if v not in ("A", "B"):
            raise ValueError("selected_candidate_id must be 'A' or 'B'")
        return v


class CandidateSelectResponse(BaseModel):
    """Response after candidate selection.

    Returns the updated requirement state based on the selected candidate.
    """

    conversation_id: str = Field(..., description="Conversation session ID")
    selected_candidate_id: str = Field(..., description="Selected candidate ID")
    requirements: RequirementState = Field(
        ..., description="Updated requirement state from selected candidate"
    )
    message: str = Field(
        ...,
        description="Confirmation message",
        examples=["候補Aを選択しました。追加の詳細を確認させてください。"],
    )
