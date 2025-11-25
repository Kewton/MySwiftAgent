"""Pydantic schemas for Prompt Configuration in API requests.

This module provides schemas for controlling which prompt versions
to use during LangGraph agent execution via API requests.
"""

from typing import Literal

from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Configuration for selecting specific prompt versions.

    Attributes:
        agent_type: Type of agent ("jobTaskGeneratorAgents" or "workflowGeneratorAgents")
        prompt_name: Name of the prompt (e.g., "task_breakdown", "evaluation")
        version: Version identifier (default: "default")
    """

    agent_type: Literal["jobTaskGeneratorAgents", "workflowGeneratorAgents"] = Field(
        ...,
        description="Agent type for prompt selection",
        examples=["jobTaskGeneratorAgents"],
    )
    prompt_name: str = Field(
        ...,
        description="Prompt name (e.g., task_breakdown, evaluation, workflow_generation)",
        min_length=1,
        examples=["task_breakdown"],
    )
    version: str = Field(
        default="default",
        description="Prompt version identifier (default: 'default')",
        examples=["default", "v1.0", "v2.0"],
    )
