"""AB Test schemas for A/B testing infrastructure.

Issue #178: AB Test Infrastructure Implementation.
Provides schemas for A/B test configuration, variant assignment,
metrics collection, and statistical analysis.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ABTestStatus(str, Enum):
    """AB Test status enumeration."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class EffectSizeInterpretation(str, Enum):
    """Effect size interpretation based on Cohen's d."""

    NEGLIGIBLE = "negligible"  # |d| < 0.2
    SMALL = "small"  # 0.2 <= |d| < 0.5
    MEDIUM = "medium"  # 0.5 <= |d| < 0.8
    LARGE = "large"  # |d| >= 0.8


# ========================================
# Variant Definitions
# ========================================


class ABTestVariant(BaseModel):
    """AB test variant definition."""

    name: str = Field(..., description="Variant name (e.g., 'control', 'treatment')")
    prompt_version: str = Field(
        ..., description="Prompt version identifier (e.g., 'v1.0', 'v2.0-experimental')"
    )
    weight: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Variant weight for assignment (0.0-1.0)"
    )
    description: str | None = Field(None, description="Variant description")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional variant metadata"
    )


class ABTestVariantCreate(BaseModel):
    """Request schema for creating a variant."""

    name: str = Field(..., description="Variant name")
    prompt_version: str = Field(..., description="Prompt version identifier")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Variant weight")
    description: str | None = Field(None, description="Variant description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


# ========================================
# AB Test Configuration
# ========================================


class ABTestConfigBase(BaseModel):
    """Base schema for AB test configuration."""

    name: str = Field(..., min_length=1, max_length=255, description="Test name")
    description: str | None = Field(None, description="Test description")
    variants: list[ABTestVariant] = Field(
        ..., min_length=2, description="List of test variants (minimum 2)"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional test metadata"
    )


class ABTestConfigCreate(ABTestConfigBase):
    """Request schema for creating an AB test."""

    pass


class ABTestConfig(ABTestConfigBase):
    """AB test configuration with ID and status."""

    id: str = Field(..., description="Test ID")
    status: ABTestStatus = Field(
        default=ABTestStatus.DRAFT, description="Test status"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )


class ABTestConfigResponse(BaseModel):
    """Response schema for AB test configuration."""

    test: ABTestConfig = Field(..., description="AB test configuration")
    message: str = Field(default="Success", description="Response message")


class ABTestListResponse(BaseModel):
    """Response schema for listing AB tests."""

    tests: list[ABTestConfig] = Field(..., description="List of AB tests")
    total: int = Field(..., ge=0, description="Total number of tests")


# ========================================
# Variant Assignment
# ========================================


class ABTestAssignment(BaseModel):
    """Variant assignment for a session."""

    test_id: str = Field(..., description="AB test ID")
    session_id: str = Field(..., description="Session ID")
    variant_name: str = Field(..., description="Assigned variant name")
    prompt_version: str = Field(..., description="Assigned prompt version")
    assigned_at: datetime = Field(
        default_factory=datetime.now, description="Assignment timestamp"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Assignment metadata"
    )


class ABTestAssignmentRequest(BaseModel):
    """Request schema for getting/creating variant assignment."""

    session_id: str = Field(..., description="Session ID for assignment")


class ABTestAssignmentResponse(BaseModel):
    """Response schema for variant assignment."""

    assignment: ABTestAssignment = Field(..., description="Variant assignment")
    is_new: bool = Field(
        default=False, description="Whether this is a new assignment"
    )


# ========================================
# Metrics
# ========================================


class ABTestMetrics(BaseModel):
    """Metrics for a single variant."""

    variant_name: str = Field(..., description="Variant name")
    sample_size: int = Field(default=0, ge=0, description="Number of samples")
    mean: float = Field(default=0.0, description="Mean value")
    std: float = Field(default=0.0, ge=0.0, description="Standard deviation")
    min_value: float | None = Field(None, description="Minimum value")
    max_value: float | None = Field(None, description="Maximum value")
    confidence_interval_lower: float | None = Field(
        None, description="95% CI lower bound"
    )
    confidence_interval_upper: float | None = Field(
        None, description="95% CI upper bound"
    )


class MetricDataPoint(BaseModel):
    """Single metric data point for collection."""

    session_id: str = Field(..., description="Session ID")
    variant_name: str = Field(..., description="Variant name")
    metric_name: str = Field(default="quality_score", description="Metric name")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Data point timestamp"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")


# ========================================
# Statistical Analysis
# ========================================


class TTestResult(BaseModel):
    """T-test result for comparing two variants."""

    t_statistic: float = Field(..., description="T-statistic value")
    p_value: float = Field(..., ge=0.0, le=1.0, description="P-value (0.0-1.0)")
    degrees_of_freedom: float = Field(..., description="Degrees of freedom")
    is_significant: bool = Field(
        default=False, description="Whether result is statistically significant (p < 0.05)"
    )


class EffectSize(BaseModel):
    """Effect size calculation result."""

    cohens_d: float = Field(..., description="Cohen's d effect size")
    interpretation: EffectSizeInterpretation = Field(
        ..., description="Effect size interpretation"
    )


class ABTestReport(BaseModel):
    """Comprehensive AB test report."""

    test_id: str = Field(..., description="AB test ID")
    test_name: str = Field(..., description="AB test name")
    metrics: list[ABTestMetrics] = Field(
        ..., description="Metrics for each variant"
    )
    t_test_result: TTestResult | None = Field(
        None, description="T-test result (if applicable)"
    )
    effect_size: EffectSize | None = Field(
        None, description="Effect size (if applicable)"
    )
    winner: str | None = Field(
        None, description="Winning variant name (if significant)"
    )
    recommendation: str = Field(
        default="", description="Recommendation based on analysis"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, description="Report generation timestamp"
    )
    warning_messages: list[str] = Field(
        default_factory=list, description="Warning messages (e.g., low sample size)"
    )


class ABTestReportRequest(BaseModel):
    """Request schema for generating AB test report."""

    metric_name: str = Field(
        default="quality_score", description="Metric name to analyze"
    )
    significance_level: float = Field(
        default=0.05, ge=0.001, le=0.1, description="Significance level (alpha)"
    )
    minimum_sample_size: int = Field(
        default=30, ge=1, description="Minimum sample size per variant"
    )


# ========================================
# Status Update
# ========================================


class ABTestStatusUpdate(BaseModel):
    """Request schema for updating AB test status."""

    status: ABTestStatus = Field(..., description="New status")


class ABTestStatusResponse(BaseModel):
    """Response schema for status update."""

    test_id: str = Field(..., description="Test ID")
    old_status: ABTestStatus = Field(..., description="Previous status")
    new_status: ABTestStatus = Field(..., description="New status")
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Update timestamp"
    )
