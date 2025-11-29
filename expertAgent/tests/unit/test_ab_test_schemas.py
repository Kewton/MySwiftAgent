"""Unit tests for AB Test schemas.

Tests for Issue #178: AB Test Infrastructure Implementation.
This module tests all AB test schema definitions with comprehensive coverage.
"""

import pytest
from pydantic import ValidationError

from app.schemas.ab_test import (
    ABTestAssignment,
    ABTestAssignmentRequest,
    ABTestAssignmentResponse,
    ABTestConfig,
    ABTestConfigBase,
    ABTestConfigCreate,
    ABTestConfigResponse,
    ABTestListResponse,
    ABTestMetrics,
    ABTestReport,
    ABTestReportRequest,
    ABTestStatus,
    ABTestStatusResponse,
    ABTestStatusUpdate,
    ABTestVariant,
    ABTestVariantCreate,
    EffectSize,
    EffectSizeInterpretation,
    MetricDataPoint,
    TTestResult,
)


class TestABTestStatus:
    """Test ABTestStatus enumeration."""

    @pytest.mark.unit
    def test_status_values(self):
        """Test all status values are correctly defined."""
        assert ABTestStatus.DRAFT.value == "draft"
        assert ABTestStatus.RUNNING.value == "running"
        assert ABTestStatus.PAUSED.value == "paused"
        assert ABTestStatus.COMPLETED.value == "completed"

    @pytest.mark.unit
    def test_status_from_string(self):
        """Test status can be created from string."""
        assert ABTestStatus("draft") == ABTestStatus.DRAFT
        assert ABTestStatus("running") == ABTestStatus.RUNNING


class TestEffectSizeInterpretation:
    """Test EffectSizeInterpretation enumeration."""

    @pytest.mark.unit
    def test_interpretation_values(self):
        """Test all effect size interpretation values."""
        assert EffectSizeInterpretation.NEGLIGIBLE.value == "negligible"
        assert EffectSizeInterpretation.SMALL.value == "small"
        assert EffectSizeInterpretation.MEDIUM.value == "medium"
        assert EffectSizeInterpretation.LARGE.value == "large"


class TestABTestVariant:
    """Test ABTestVariant schema."""

    @pytest.mark.unit
    def test_valid_variant_creation(self):
        """Test creating a valid variant."""
        variant = ABTestVariant(
            name="control",
            prompt_version="v1.0",
            weight=0.5,
            description="Control group variant",
        )
        assert variant.name == "control"
        assert variant.prompt_version == "v1.0"
        assert variant.weight == 0.5
        assert variant.description == "Control group variant"
        assert variant.metadata == {}

    @pytest.mark.unit
    def test_variant_with_metadata(self):
        """Test variant with metadata."""
        variant = ABTestVariant(
            name="treatment",
            prompt_version="v2.0",
            metadata={"model": "gpt-4o", "temperature": 0.7},
        )
        assert variant.metadata["model"] == "gpt-4o"
        assert variant.metadata["temperature"] == 0.7

    @pytest.mark.unit
    def test_variant_default_weight(self):
        """Test variant default weight is 1.0."""
        variant = ABTestVariant(name="test", prompt_version="v1.0")
        assert variant.weight == 1.0

    @pytest.mark.unit
    def test_variant_weight_validation_lower_bound(self):
        """Test variant weight lower bound validation."""
        with pytest.raises(ValidationError):
            ABTestVariant(name="test", prompt_version="v1.0", weight=-0.1)

    @pytest.mark.unit
    def test_variant_weight_validation_upper_bound(self):
        """Test variant weight upper bound validation."""
        with pytest.raises(ValidationError):
            ABTestVariant(name="test", prompt_version="v1.0", weight=1.1)

    @pytest.mark.unit
    def test_variant_weight_boundary_values(self):
        """Test variant weight at boundary values."""
        variant_zero = ABTestVariant(name="test", prompt_version="v1.0", weight=0.0)
        variant_one = ABTestVariant(name="test", prompt_version="v1.0", weight=1.0)
        assert variant_zero.weight == 0.0
        assert variant_one.weight == 1.0


class TestABTestVariantCreate:
    """Test ABTestVariantCreate schema."""

    @pytest.mark.unit
    def test_create_variant_request(self):
        """Test creating a variant create request."""
        create_req = ABTestVariantCreate(
            name="treatment_a",
            prompt_version="v2.0-experimental",
            weight=0.6,
            description="Experimental variant",
        )
        assert create_req.name == "treatment_a"
        assert create_req.prompt_version == "v2.0-experimental"


class TestABTestConfigBase:
    """Test ABTestConfigBase schema."""

    @pytest.mark.unit
    def test_valid_config_base(self):
        """Test creating a valid config base."""
        config = ABTestConfigBase(
            name="Test AB Experiment",
            description="Testing prompt variations",
            variants=[
                ABTestVariant(name="control", prompt_version="v1.0", weight=0.5),
                ABTestVariant(name="treatment", prompt_version="v2.0", weight=0.5),
            ],
        )
        assert config.name == "Test AB Experiment"
        assert len(config.variants) == 2

    @pytest.mark.unit
    def test_config_minimum_two_variants(self):
        """Test that config requires minimum 2 variants."""
        with pytest.raises(ValidationError):
            ABTestConfigBase(
                name="Test",
                variants=[ABTestVariant(name="only_one", prompt_version="v1.0")],
            )

    @pytest.mark.unit
    def test_config_name_min_length(self):
        """Test config name minimum length validation."""
        with pytest.raises(ValidationError):
            ABTestConfigBase(
                name="",
                variants=[
                    ABTestVariant(name="a", prompt_version="v1.0"),
                    ABTestVariant(name="b", prompt_version="v2.0"),
                ],
            )

    @pytest.mark.unit
    def test_config_name_max_length(self):
        """Test config name maximum length validation."""
        with pytest.raises(ValidationError):
            ABTestConfigBase(
                name="x" * 256,
                variants=[
                    ABTestVariant(name="a", prompt_version="v1.0"),
                    ABTestVariant(name="b", prompt_version="v2.0"),
                ],
            )


class TestABTestConfig:
    """Test ABTestConfig schema."""

    @pytest.mark.unit
    def test_config_with_id_and_status(self):
        """Test config with ID and status."""
        config = ABTestConfig(
            id="test-123",
            name="Experiment 1",
            variants=[
                ABTestVariant(name="control", prompt_version="v1.0"),
                ABTestVariant(name="treatment", prompt_version="v2.0"),
            ],
            status=ABTestStatus.RUNNING,
        )
        assert config.id == "test-123"
        assert config.status == ABTestStatus.RUNNING
        assert config.created_at is not None
        assert config.updated_at is not None

    @pytest.mark.unit
    def test_config_default_status(self):
        """Test config default status is DRAFT."""
        config = ABTestConfig(
            id="test-123",
            name="Test",
            variants=[
                ABTestVariant(name="a", prompt_version="v1.0"),
                ABTestVariant(name="b", prompt_version="v2.0"),
            ],
        )
        assert config.status == ABTestStatus.DRAFT


class TestABTestConfigCreate:
    """Test ABTestConfigCreate schema."""

    @pytest.mark.unit
    def test_create_config_request(self):
        """Test creating a config create request."""
        create_req = ABTestConfigCreate(
            name="New Experiment",
            description="Testing new prompts",
            variants=[
                ABTestVariant(name="control", prompt_version="v1.0"),
                ABTestVariant(name="treatment", prompt_version="v2.0"),
            ],
        )
        assert create_req.name == "New Experiment"
        assert len(create_req.variants) == 2


class TestABTestConfigResponse:
    """Test ABTestConfigResponse schema."""

    @pytest.mark.unit
    def test_config_response(self):
        """Test config response schema."""
        config = ABTestConfig(
            id="test-123",
            name="Test",
            variants=[
                ABTestVariant(name="a", prompt_version="v1.0"),
                ABTestVariant(name="b", prompt_version="v2.0"),
            ],
        )
        response = ABTestConfigResponse(test=config)
        assert response.test.id == "test-123"
        assert response.message == "Success"


class TestABTestListResponse:
    """Test ABTestListResponse schema."""

    @pytest.mark.unit
    def test_list_response(self):
        """Test list response schema."""
        tests = [
            ABTestConfig(
                id=f"test-{i}",
                name=f"Test {i}",
                variants=[
                    ABTestVariant(name="a", prompt_version="v1.0"),
                    ABTestVariant(name="b", prompt_version="v2.0"),
                ],
            )
            for i in range(3)
        ]
        response = ABTestListResponse(tests=tests, total=3)
        assert len(response.tests) == 3
        assert response.total == 3

    @pytest.mark.unit
    def test_list_response_empty(self):
        """Test empty list response."""
        response = ABTestListResponse(tests=[], total=0)
        assert len(response.tests) == 0
        assert response.total == 0


class TestABTestAssignment:
    """Test ABTestAssignment schema."""

    @pytest.mark.unit
    def test_valid_assignment(self):
        """Test creating a valid assignment."""
        assignment = ABTestAssignment(
            test_id="test-123",
            session_id="session-456",
            variant_name="control",
            prompt_version="v1.0",
        )
        assert assignment.test_id == "test-123"
        assert assignment.session_id == "session-456"
        assert assignment.variant_name == "control"
        assert assignment.prompt_version == "v1.0"
        assert assignment.assigned_at is not None

    @pytest.mark.unit
    def test_assignment_with_metadata(self):
        """Test assignment with metadata."""
        assignment = ABTestAssignment(
            test_id="test-123",
            session_id="session-456",
            variant_name="treatment",
            prompt_version="v2.0",
            metadata={"user_id": "user-789"},
        )
        assert assignment.metadata["user_id"] == "user-789"


class TestABTestAssignmentRequest:
    """Test ABTestAssignmentRequest schema."""

    @pytest.mark.unit
    def test_assignment_request(self):
        """Test assignment request schema."""
        request = ABTestAssignmentRequest(session_id="session-123")
        assert request.session_id == "session-123"


class TestABTestAssignmentResponse:
    """Test ABTestAssignmentResponse schema."""

    @pytest.mark.unit
    def test_assignment_response(self):
        """Test assignment response schema."""
        assignment = ABTestAssignment(
            test_id="test-123",
            session_id="session-456",
            variant_name="control",
            prompt_version="v1.0",
        )
        response = ABTestAssignmentResponse(assignment=assignment, is_new=True)
        assert response.is_new is True
        assert response.assignment.variant_name == "control"


class TestABTestMetrics:
    """Test ABTestMetrics schema."""

    @pytest.mark.unit
    def test_valid_metrics(self):
        """Test creating valid metrics."""
        metrics = ABTestMetrics(
            variant_name="control",
            sample_size=100,
            mean=0.85,
            std=0.12,
            min_value=0.5,
            max_value=1.0,
            confidence_interval_lower=0.82,
            confidence_interval_upper=0.88,
        )
        assert metrics.variant_name == "control"
        assert metrics.sample_size == 100
        assert metrics.mean == 0.85
        assert metrics.std == 0.12

    @pytest.mark.unit
    def test_metrics_defaults(self):
        """Test metrics default values."""
        metrics = ABTestMetrics(variant_name="test")
        assert metrics.sample_size == 0
        assert metrics.mean == 0.0
        assert metrics.std == 0.0

    @pytest.mark.unit
    def test_metrics_sample_size_non_negative(self):
        """Test metrics sample size must be non-negative."""
        with pytest.raises(ValidationError):
            ABTestMetrics(variant_name="test", sample_size=-1)

    @pytest.mark.unit
    def test_metrics_std_non_negative(self):
        """Test metrics std must be non-negative."""
        with pytest.raises(ValidationError):
            ABTestMetrics(variant_name="test", std=-0.1)


class TestMetricDataPoint:
    """Test MetricDataPoint schema."""

    @pytest.mark.unit
    def test_valid_data_point(self):
        """Test creating a valid data point."""
        data_point = MetricDataPoint(
            session_id="session-123",
            variant_name="control",
            metric_name="quality_score",
            value=0.85,
        )
        assert data_point.session_id == "session-123"
        assert data_point.value == 0.85

    @pytest.mark.unit
    def test_data_point_default_metric_name(self):
        """Test data point default metric name."""
        data_point = MetricDataPoint(
            session_id="session-123",
            variant_name="control",
            value=0.9,
        )
        assert data_point.metric_name == "quality_score"


class TestTTestResult:
    """Test TTestResult schema."""

    @pytest.mark.unit
    def test_valid_t_test_result(self):
        """Test creating a valid t-test result."""
        result = TTestResult(
            t_statistic=2.45,
            p_value=0.015,
            degrees_of_freedom=98.5,
            is_significant=True,
        )
        assert result.t_statistic == 2.45
        assert result.p_value == 0.015
        assert result.degrees_of_freedom == 98.5
        assert result.is_significant is True

    @pytest.mark.unit
    def test_t_test_p_value_bounds(self):
        """Test p-value must be between 0 and 1."""
        with pytest.raises(ValidationError):
            TTestResult(t_statistic=2.0, p_value=1.5, degrees_of_freedom=50)
        with pytest.raises(ValidationError):
            TTestResult(t_statistic=2.0, p_value=-0.1, degrees_of_freedom=50)

    @pytest.mark.unit
    def test_t_test_p_value_boundary(self):
        """Test p-value at boundaries."""
        result_zero = TTestResult(t_statistic=100.0, p_value=0.0, degrees_of_freedom=50)
        result_one = TTestResult(t_statistic=0.0, p_value=1.0, degrees_of_freedom=50)
        assert result_zero.p_value == 0.0
        assert result_one.p_value == 1.0


class TestEffectSize:
    """Test EffectSize schema."""

    @pytest.mark.unit
    def test_valid_effect_size(self):
        """Test creating a valid effect size."""
        effect_size = EffectSize(
            cohens_d=0.65,
            interpretation=EffectSizeInterpretation.MEDIUM,
        )
        assert effect_size.cohens_d == 0.65
        assert effect_size.interpretation == EffectSizeInterpretation.MEDIUM

    @pytest.mark.unit
    def test_negative_cohens_d(self):
        """Test negative Cohen's d is valid."""
        effect_size = EffectSize(
            cohens_d=-0.8,
            interpretation=EffectSizeInterpretation.LARGE,
        )
        assert effect_size.cohens_d == -0.8


class TestABTestReport:
    """Test ABTestReport schema."""

    @pytest.mark.unit
    def test_valid_report(self):
        """Test creating a valid report."""
        metrics = [
            ABTestMetrics(variant_name="control", sample_size=50, mean=0.8, std=0.1),
            ABTestMetrics(variant_name="treatment", sample_size=50, mean=0.85, std=0.12),
        ]
        t_test = TTestResult(
            t_statistic=2.5, p_value=0.014, degrees_of_freedom=98, is_significant=True
        )
        effect_size = EffectSize(
            cohens_d=0.5, interpretation=EffectSizeInterpretation.MEDIUM
        )
        report = ABTestReport(
            test_id="test-123",
            test_name="Experiment 1",
            metrics=metrics,
            t_test_result=t_test,
            effect_size=effect_size,
            winner="treatment",
            recommendation="Treatment variant shows significant improvement.",
        )
        assert report.test_id == "test-123"
        assert len(report.metrics) == 2
        assert report.winner == "treatment"

    @pytest.mark.unit
    def test_report_with_warnings(self):
        """Test report with warning messages."""
        report = ABTestReport(
            test_id="test-123",
            test_name="Test",
            metrics=[ABTestMetrics(variant_name="control", sample_size=10)],
            warning_messages=["Sample size below recommended minimum (30)"],
        )
        assert len(report.warning_messages) == 1
        assert "Sample size" in report.warning_messages[0]

    @pytest.mark.unit
    def test_report_no_significant_result(self):
        """Test report without significant result."""
        report = ABTestReport(
            test_id="test-123",
            test_name="Test",
            metrics=[ABTestMetrics(variant_name="control")],
            winner=None,
            recommendation="No statistically significant difference detected.",
        )
        assert report.winner is None


class TestABTestReportRequest:
    """Test ABTestReportRequest schema."""

    @pytest.mark.unit
    def test_default_values(self):
        """Test default values for report request."""
        request = ABTestReportRequest()
        assert request.metric_name == "quality_score"
        assert request.significance_level == 0.05
        assert request.minimum_sample_size == 30

    @pytest.mark.unit
    def test_custom_values(self):
        """Test custom values for report request."""
        request = ABTestReportRequest(
            metric_name="latency",
            significance_level=0.01,
            minimum_sample_size=50,
        )
        assert request.metric_name == "latency"
        assert request.significance_level == 0.01
        assert request.minimum_sample_size == 50

    @pytest.mark.unit
    def test_significance_level_bounds(self):
        """Test significance level bounds."""
        with pytest.raises(ValidationError):
            ABTestReportRequest(significance_level=0.0001)  # Below 0.001
        with pytest.raises(ValidationError):
            ABTestReportRequest(significance_level=0.2)  # Above 0.1

    @pytest.mark.unit
    def test_minimum_sample_size_validation(self):
        """Test minimum sample size must be positive."""
        with pytest.raises(ValidationError):
            ABTestReportRequest(minimum_sample_size=0)


class TestABTestStatusUpdate:
    """Test ABTestStatusUpdate schema."""

    @pytest.mark.unit
    def test_status_update(self):
        """Test status update schema."""
        update = ABTestStatusUpdate(status=ABTestStatus.RUNNING)
        assert update.status == ABTestStatus.RUNNING


class TestABTestStatusResponse:
    """Test ABTestStatusResponse schema."""

    @pytest.mark.unit
    def test_status_response(self):
        """Test status response schema."""
        response = ABTestStatusResponse(
            test_id="test-123",
            old_status=ABTestStatus.DRAFT,
            new_status=ABTestStatus.RUNNING,
        )
        assert response.test_id == "test-123"
        assert response.old_status == ABTestStatus.DRAFT
        assert response.new_status == ABTestStatus.RUNNING
        assert response.updated_at is not None


class TestSchemasSerialization:
    """Test schema serialization and deserialization."""

    @pytest.mark.unit
    def test_variant_to_dict(self):
        """Test variant serialization."""
        variant = ABTestVariant(
            name="control",
            prompt_version="v1.0",
            weight=0.5,
        )
        data = variant.model_dump()
        assert data["name"] == "control"
        assert data["prompt_version"] == "v1.0"
        assert data["weight"] == 0.5

    @pytest.mark.unit
    def test_config_to_dict(self):
        """Test config serialization."""
        config = ABTestConfig(
            id="test-123",
            name="Test",
            variants=[
                ABTestVariant(name="a", prompt_version="v1.0"),
                ABTestVariant(name="b", prompt_version="v2.0"),
            ],
            status=ABTestStatus.RUNNING,
        )
        data = config.model_dump()
        assert data["id"] == "test-123"
        assert data["status"] == "running"
        assert len(data["variants"]) == 2

    @pytest.mark.unit
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = ABTestMetrics(
            variant_name="control",
            sample_size=100,
            mean=0.85,
            std=0.1,
        )
        data = metrics.model_dump()
        assert data["variant_name"] == "control"
        assert data["sample_size"] == 100

    @pytest.mark.unit
    def test_report_to_json(self):
        """Test report JSON serialization."""
        report = ABTestReport(
            test_id="test-123",
            test_name="Test",
            metrics=[
                ABTestMetrics(variant_name="control"),
                ABTestMetrics(variant_name="treatment"),
            ],
        )
        json_str = report.model_dump_json()
        assert "test-123" in json_str
        assert "control" in json_str
        assert "treatment" in json_str
