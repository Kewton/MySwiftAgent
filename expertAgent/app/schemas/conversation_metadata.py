"""Conversation metadata schemas for diagnostic API.

Issue #171: Diagnostic Information Retrieval API Implementation.
Extends Valkey metadata schema with job_id, user_id, project_id, workflow_id.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConversationMetadata(BaseModel):
    """Extended metadata for conversation tracking.

    Supports filtering and indexing by job_id, user_id, project_id, workflow_id.
    All metadata is stored in Valkey alongside the conversation data.

    Attributes:
        trace_id: Langfuse trace ID for observability
        prompt_version: Version of the prompt used
        job_id: Associated job ID for batch operations
        user_id: User ID for user-level filtering
        project_id: Project ID for project-level grouping
        workflow_id: Workflow ID for workflow-level grouping
        created_at: Timestamp when the conversation was created
        updated_at: Timestamp when the conversation was last updated
        system_prompt: Full system prompt used in the conversation
        total_tokens: Total tokens used in the conversation
        input_tokens: Input tokens used
        output_tokens: Output tokens generated
    """

    trace_id: Optional[str] = Field(
        None,
        description="Langfuse trace ID for observability",
        examples=["trace-abc123"],
    )
    prompt_version: Optional[str] = Field(
        None,
        description="Version of the prompt used",
        examples=["v1.0.0", "v2.1.0"],
    )
    job_id: Optional[str] = Field(
        None,
        description="Associated job ID for batch operations",
        examples=["job-12345"],
    )
    user_id: Optional[str] = Field(
        None,
        description="User ID for user-level filtering",
        examples=["user-789"],
    )
    project_id: Optional[str] = Field(
        None,
        description="Project ID for project-level grouping",
        examples=["project-456"],
    )
    workflow_id: Optional[str] = Field(
        None,
        description="Workflow ID for workflow-level grouping",
        examples=["workflow-321"],
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the conversation was created",
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the conversation was last updated",
    )
    system_prompt: Optional[str] = Field(
        None,
        description="Full system prompt used in the conversation",
    )
    total_tokens: int = Field(
        0,
        description="Total tokens used in the conversation",
        ge=0,
    )
    input_tokens: int = Field(
        0,
        description="Input tokens used",
        ge=0,
    )
    output_tokens: int = Field(
        0,
        description="Output tokens generated",
        ge=0,
    )

    def to_index_keys(self) -> Dict[str, str]:
        """Generate secondary index keys for this metadata.

        Returns:
            Dictionary mapping index type to index key.
            Example: {"job_index": "job-12345", "user_index": "user-789"}
        """
        keys: Dict[str, str] = {}
        if self.job_id:
            keys["job_index"] = self.job_id
        if self.user_id:
            keys["user_index"] = self.user_id
        if self.project_id:
            keys["project_index"] = self.project_id
        if self.workflow_id:
            keys["workflow_index"] = self.workflow_id
        return keys

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for Valkey storage.

        Returns:
            Dictionary representation of the metadata.
        """
        data = self.model_dump(mode="json", exclude_none=True)
        # Ensure datetime fields are ISO formatted strings
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMetadata":
        """Create metadata from dictionary.

        Args:
            data: Dictionary representation of the metadata.

        Returns:
            ConversationMetadata instance.
        """
        return cls.model_validate(data)
