"""Evaluation models for LLM Evaluator.

This module defines the data models for LLM evaluation results
and regenerated test data.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class LLMEvaluationResult(BaseModel):
    """LLM Evaluator evaluation result.

    Contains comprehensive evaluation scores and feedback for
    workflow quality assessment.
    """

    # Overall score (0-100)
    overall_score: int = Field(
        ..., ge=0, le=100, description="Overall evaluation score"
    )

    # Component scores
    structural_score: int = Field(
        ..., ge=0, le=100, description="Structural validity score"
    )
    requirement_score: int = Field(
        ..., ge=0, le=100, description="Requirement fulfillment score"
    )
    output_quality_score: int = Field(
        ..., ge=0, le=100, description="Output quality score"
    )
    error_handling_score: int = Field(
        ..., ge=0, le=100, description="Error handling score"
    )
    test_data_quality_score: int = Field(
        ..., ge=0, le=100, description="Test data quality score"
    )

    # Test data evaluation details
    test_data_issues: list[str] = Field(
        default_factory=list, description="Issues found with test data"
    )
    needs_test_data_regeneration: bool = Field(
        default=False, description="Whether test data needs regeneration"
    )
    suggested_test_data: dict[str, Any] | None = Field(
        default=None, description="Suggested test data for regeneration"
    )

    # Evaluation details
    strengths: list[str] = Field(
        default_factory=list, description="Positive aspects of the workflow"
    )
    weaknesses: list[str] = Field(
        default_factory=list, description="Areas needing improvement"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Specific improvement suggestions"
    )

    # Judgment
    is_acceptable: bool = Field(
        default=False, description="Whether workflow passes quality threshold"
    )
    failure_reason: Literal["none", "workflow_quality", "test_data_quality", "both"] = (
        Field(default="none", description="Category of failure if any")
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="LLM confidence level"
    )

    # Metadata
    evaluation_model: str = Field(
        default="unknown", description="Model used for evaluation"
    )
    evaluation_timestamp: str = Field(default="", description="Timestamp of evaluation")


class RegeneratedTestData(BaseModel):
    """Regenerated test data from LLM.

    Contains the new sample input along with rationale
    and expected behavior description.
    """

    sample_input: dict[str, Any] = Field(
        default_factory=dict, description="New sample input data"
    )
    generation_rationale: str = Field(
        default="", description="Explanation of why this data was generated"
    )
    expected_behavior: str = Field(
        default="", description="Expected workflow behavior with this data"
    )
