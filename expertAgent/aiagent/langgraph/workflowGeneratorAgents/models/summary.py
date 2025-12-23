"""Summary models for Result Summary Generator.

This module defines the data models for validation summaries
and result reports.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class RuleBasedValidationSummary(BaseModel):
    """Summary of rule-based validation results."""

    yaml_syntax_valid: bool = Field(
        default=True, description="Whether YAML syntax is valid"
    )
    http_status_valid: bool = Field(
        default=True, description="Whether HTTP status is 200"
    )
    graphai_execution_valid: bool = Field(
        default=True, description="Whether GraphAI execution succeeded"
    )
    output_schema_valid: bool = Field(
        default=True, description="Whether output matches schema"
    )
    issues: list[str] = Field(
        default_factory=list, description="List of validation issues"
    )


class LLMEvaluationSummary(BaseModel):
    """Summary of LLM evaluation results."""

    overall_score: int = Field(..., ge=0, le=100, description="Overall score")
    structural_score: int = Field(..., ge=0, le=100, description="Structural score")
    requirement_score: int = Field(..., ge=0, le=100, description="Requirement score")
    output_quality_score: int = Field(
        ..., ge=0, le=100, description="Output quality score"
    )
    error_handling_score: int = Field(
        ..., ge=0, le=100, description="Error handling score"
    )
    test_data_quality_score: int = Field(
        ..., ge=0, le=100, description="Test data quality score"
    )
    strengths: list[str] = Field(default_factory=list, description="Strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Weaknesses")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions")


class TestDataEvaluationSummary(BaseModel):
    """Summary of test data evaluation."""

    quality_score: int = Field(..., ge=0, le=100, description="Quality score")
    source: Literal["auto_generated", "llm_regenerated"] = Field(
        default="auto_generated", description="Source of test data"
    )
    issues: list[str] = Field(default_factory=list, description="Test data issues")
    regeneration_history: list[dict[str, Any]] = Field(
        default_factory=list, description="History of regeneration attempts"
    )


class ValidationSummary(BaseModel):
    """Complete validation summary combining all evaluations."""

    # Basic info
    task_master_id: str = Field(..., description="TaskMaster ID")
    task_name: str = Field(..., description="Task name")
    workflow_name: str = Field(..., description="Workflow name")
    generated_at: str = Field(..., description="Generation timestamp")

    # Status
    overall_status: Literal["success", "partial", "failed"] = Field(
        ..., description="Overall validation status"
    )

    # Validation results
    rule_based_validation: RuleBasedValidationSummary = Field(
        ..., description="Rule-based validation summary"
    )
    llm_evaluation: LLMEvaluationSummary = Field(
        ..., description="LLM evaluation summary"
    )
    test_data_evaluation: TestDataEvaluationSummary = Field(
        ..., description="Test data evaluation summary"
    )

    # Scores
    final_score: int = Field(..., ge=0, le=100, description="Final combined score")

    # Recommendations
    recommended_actions: list[str] = Field(
        default_factory=list, description="Recommended improvement actions"
    )

    # Retry info
    retry_count: int = Field(default=0, ge=0, description="Workflow retry count")
    max_retry: int = Field(default=3, ge=0, description="Max retry limit")
    test_data_regeneration_count: int = Field(
        default=0, ge=0, description="Test data regeneration count"
    )
    max_test_data_regeneration: int = Field(
        default=2, ge=0, description="Max test data regeneration limit"
    )
