"""Unit tests for ABTestService.

Tests for Issue #178: AB Test Infrastructure Implementation.
This module tests the AB test service with comprehensive coverage for:
- Test management (CRUD operations)
- Variant assignment
- Metrics collection
- Statistical analysis
"""

import math
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ab_test import (
    ABTestConfigCreate,
    ABTestMetrics,
    ABTestReportRequest,
    ABTestStatus,
    ABTestVariant,
    EffectSizeInterpretation,
)
from app.services.ab_test_service import (
    ABTestNotFoundError,
    ABTestService,
    ABTestServiceError,
    create_ab_test_service,
)


@pytest.fixture
def ab_service():
    """Create ABTestService instance without Valkey."""
    return ABTestService(use_valkey=False)


@pytest.fixture
def sample_config():
    """Sample AB test configuration."""
    return ABTestConfigCreate(
        name="Test Experiment",
        description="Testing prompt variations",
        variants=[
            ABTestVariant(name="control", prompt_version="v1.0", weight=0.5),
            ABTestVariant(name="treatment", prompt_version="v2.0", weight=0.5),
        ],
    )


@pytest.fixture
def three_variant_config():
    """Sample AB test configuration with three variants."""
    return ABTestConfigCreate(
        name="Three Way Test",
        variants=[
            ABTestVariant(name="control", prompt_version="v1.0", weight=0.33),
            ABTestVariant(name="treatment_a", prompt_version="v2.0", weight=0.33),
            ABTestVariant(name="treatment_b", prompt_version="v3.0", weight=0.34),
        ],
    )


class TestABTestServiceCreation:
    """Test ABTestService creation and initialization."""

    @pytest.mark.unit
    def test_create_service_default_params(self):
        """Test creating service with default parameters."""
        service = ABTestService()
        assert service._valkey_host == "localhost"
        assert service._valkey_port == 6379
        assert service._valkey_db == 0
        assert service._use_valkey is True

    @pytest.mark.unit
    def test_create_service_custom_params(self):
        """Test creating service with custom parameters."""
        service = ABTestService(
            valkey_host="redis.example.com",
            valkey_port=6380,
            valkey_db=1,
            use_valkey=False,
        )
        assert service._valkey_host == "redis.example.com"
        assert service._valkey_port == 6380
        assert service._valkey_db == 1
        assert service._use_valkey is False

    @pytest.mark.unit
    def test_create_service_factory(self):
        """Test factory function creates service correctly."""
        service = create_ab_test_service(
            valkey_host="test.host",
            valkey_port=6381,
            use_valkey=False,
        )
        assert isinstance(service, ABTestService)
        assert service._valkey_host == "test.host"


class TestTestManagement:
    """Test AB test CRUD operations."""

    @pytest.mark.unit
    async def test_create_test(self, ab_service: ABTestService, sample_config):
        """Test creating a new AB test."""
        result = await ab_service.create_test(sample_config)

        assert result.id is not None
        assert result.name == "Test Experiment"
        assert len(result.variants) == 2
        assert result.status == ABTestStatus.DRAFT
        assert result.created_at is not None

    @pytest.mark.unit
    async def test_create_test_normalizes_weights(self, ab_service: ABTestService):
        """Test that variant weights are normalized."""
        config = ABTestConfigCreate(
            name="Test",
            variants=[
                ABTestVariant(name="a", prompt_version="v1.0", weight=0.25),
                ABTestVariant(name="b", prompt_version="v2.0", weight=0.75),
            ],
        )
        result = await ab_service.create_test(config)

        # Weights should be normalized to sum to 1.0
        total_weight = sum(v.weight for v in result.variants)
        assert abs(total_weight - 1.0) < 0.001

        # Individual weights should be proportional
        assert result.variants[0].weight == pytest.approx(0.25, rel=0.01)
        assert result.variants[1].weight == pytest.approx(0.75, rel=0.01)

    @pytest.mark.unit
    async def test_create_test_zero_weights(self, ab_service: ABTestService):
        """Test handling zero weights (equal distribution)."""
        config = ABTestConfigCreate(
            name="Test",
            variants=[
                ABTestVariant(name="a", prompt_version="v1.0", weight=0.0),
                ABTestVariant(name="b", prompt_version="v2.0", weight=0.0),
            ],
        )
        result = await ab_service.create_test(config)

        # Should be equal distribution
        assert result.variants[0].weight == pytest.approx(0.5, rel=0.01)
        assert result.variants[1].weight == pytest.approx(0.5, rel=0.01)

    @pytest.mark.unit
    async def test_get_test(self, ab_service: ABTestService, sample_config):
        """Test getting a test by ID."""
        created = await ab_service.create_test(sample_config)
        retrieved = await ab_service.get_test(created.id)

        assert retrieved.id == created.id
        assert retrieved.name == created.name

    @pytest.mark.unit
    async def test_get_test_not_found(self, ab_service: ABTestService):
        """Test getting a non-existent test raises error."""
        with pytest.raises(ABTestNotFoundError, match="not found"):
            await ab_service.get_test("non-existent-id")

    @pytest.mark.unit
    async def test_list_tests(self, ab_service: ABTestService, sample_config):
        """Test listing tests."""
        # Create multiple tests
        await ab_service.create_test(sample_config)
        await ab_service.create_test(
            ABTestConfigCreate(
                name="Another Test",
                variants=[
                    ABTestVariant(name="a", prompt_version="v1.0"),
                    ABTestVariant(name="b", prompt_version="v2.0"),
                ],
            )
        )

        tests, total = await ab_service.list_tests()

        assert total == 2
        assert len(tests) == 2

    @pytest.mark.unit
    async def test_list_tests_with_status_filter(
        self, ab_service: ABTestService, sample_config
    ):
        """Test listing tests with status filter."""
        test1 = await ab_service.create_test(sample_config)
        await ab_service.update_test_status(test1.id, ABTestStatus.RUNNING)

        await ab_service.create_test(
            ABTestConfigCreate(
                name="Draft Test",
                variants=[
                    ABTestVariant(name="a", prompt_version="v1.0"),
                    ABTestVariant(name="b", prompt_version="v2.0"),
                ],
            )
        )

        running_tests, _ = await ab_service.list_tests(status=ABTestStatus.RUNNING)
        draft_tests, _ = await ab_service.list_tests(status=ABTestStatus.DRAFT)

        assert len(running_tests) == 1
        assert len(draft_tests) == 1

    @pytest.mark.unit
    async def test_list_tests_pagination(self, ab_service: ABTestService):
        """Test listing tests with pagination."""
        # Create 5 tests
        for i in range(5):
            await ab_service.create_test(
                ABTestConfigCreate(
                    name=f"Test {i}",
                    variants=[
                        ABTestVariant(name="a", prompt_version="v1.0"),
                        ABTestVariant(name="b", prompt_version="v2.0"),
                    ],
                )
            )

        page1, total = await ab_service.list_tests(limit=2, offset=0)
        page2, _ = await ab_service.list_tests(limit=2, offset=2)

        assert total == 5
        assert len(page1) == 2
        assert len(page2) == 2

    @pytest.mark.unit
    async def test_update_test_status(self, ab_service: ABTestService, sample_config):
        """Test updating test status."""
        test = await ab_service.create_test(sample_config)

        response = await ab_service.update_test_status(test.id, ABTestStatus.RUNNING)

        assert response.old_status == ABTestStatus.DRAFT
        assert response.new_status == ABTestStatus.RUNNING

        # Verify update persisted
        updated = await ab_service.get_test(test.id)
        assert updated.status == ABTestStatus.RUNNING

    @pytest.mark.unit
    async def test_update_status_not_found(self, ab_service: ABTestService):
        """Test updating status of non-existent test."""
        with pytest.raises(ABTestNotFoundError):
            await ab_service.update_test_status("non-existent", ABTestStatus.RUNNING)

    @pytest.mark.unit
    async def test_delete_test(self, ab_service: ABTestService, sample_config):
        """Test deleting a test."""
        test = await ab_service.create_test(sample_config)

        result = await ab_service.delete_test(test.id)
        assert result is True

        # Verify deleted
        with pytest.raises(ABTestNotFoundError):
            await ab_service.get_test(test.id)

    @pytest.mark.unit
    async def test_delete_test_not_found(self, ab_service: ABTestService):
        """Test deleting non-existent test."""
        with pytest.raises(ABTestNotFoundError):
            await ab_service.delete_test("non-existent")


class TestVariantAssignment:
    """Test variant assignment functionality."""

    @pytest.mark.unit
    async def test_assign_variant(self, ab_service: ABTestService, sample_config):
        """Test assigning variant to session."""
        test = await ab_service.create_test(sample_config)

        assignment, is_new = await ab_service.assign_variant(
            test.id, "session-123"
        )

        assert is_new is True
        assert assignment.test_id == test.id
        assert assignment.session_id == "session-123"
        assert assignment.variant_name in ["control", "treatment"]
        assert assignment.prompt_version in ["v1.0", "v2.0"]

    @pytest.mark.unit
    async def test_assign_variant_returns_existing(
        self, ab_service: ABTestService, sample_config
    ):
        """Test that existing assignment is returned."""
        test = await ab_service.create_test(sample_config)

        # First assignment
        first, is_new1 = await ab_service.assign_variant(test.id, "session-123")
        assert is_new1 is True

        # Second call should return existing
        second, is_new2 = await ab_service.assign_variant(test.id, "session-123")
        assert is_new2 is False
        assert second.variant_name == first.variant_name

    @pytest.mark.unit
    async def test_assign_variant_distribution(
        self, ab_service: ABTestService, sample_config
    ):
        """Test that variant distribution follows weights."""
        test = await ab_service.create_test(sample_config)

        # Assign many sessions
        counts = {"control": 0, "treatment": 0}
        num_assignments = 1000

        for i in range(num_assignments):
            assignment, _ = await ab_service.assign_variant(test.id, f"session-{i}")
            counts[assignment.variant_name] += 1

        # With 50/50 weights, should be roughly equal
        control_ratio = counts["control"] / num_assignments
        treatment_ratio = counts["treatment"] / num_assignments

        # Allow 10% deviation
        assert 0.4 < control_ratio < 0.6
        assert 0.4 < treatment_ratio < 0.6

    @pytest.mark.unit
    async def test_get_assignment(self, ab_service: ABTestService, sample_config):
        """Test getting existing assignment."""
        test = await ab_service.create_test(sample_config)
        await ab_service.assign_variant(test.id, "session-123")

        assignment = await ab_service.get_assignment(test.id, "session-123")

        assert assignment is not None
        assert assignment.session_id == "session-123"

    @pytest.mark.unit
    async def test_get_assignment_not_found(
        self, ab_service: ABTestService, sample_config
    ):
        """Test getting non-existent assignment returns None."""
        test = await ab_service.create_test(sample_config)

        assignment = await ab_service.get_assignment(test.id, "non-existent")

        assert assignment is None


class TestMetricsCollection:
    """Test metrics collection functionality."""

    @pytest.mark.unit
    async def test_collect_metric(self, ab_service: ABTestService, sample_config):
        """Test collecting a metric."""
        test = await ab_service.create_test(sample_config)
        await ab_service.assign_variant(test.id, "session-123")

        data_point = await ab_service.collect_metric(
            test.id, "session-123", value=0.85, metric_name="quality_score"
        )

        assert data_point.session_id == "session-123"
        assert data_point.value == 0.85
        assert data_point.metric_name == "quality_score"

    @pytest.mark.unit
    async def test_collect_metric_no_assignment(
        self, ab_service: ABTestService, sample_config
    ):
        """Test collecting metric without assignment raises error."""
        test = await ab_service.create_test(sample_config)

        with pytest.raises(ABTestServiceError, match="No assignment found"):
            await ab_service.collect_metric(
                test.id, "unassigned-session", value=0.85
            )

    @pytest.mark.unit
    async def test_get_variant_metrics(self, ab_service: ABTestService, sample_config):
        """Test getting aggregated metrics."""
        test = await ab_service.create_test(sample_config)

        # Assign and collect metrics for multiple sessions
        for i in range(10):
            assignment, _ = await ab_service.assign_variant(
                test.id, f"session-{i}"
            )
            # Control gets lower scores, treatment gets higher
            value = 0.7 if assignment.variant_name == "control" else 0.9
            await ab_service.collect_metric(test.id, f"session-{i}", value)

        metrics = await ab_service.get_variant_metrics(test.id)

        assert len(metrics) <= 2
        for m in metrics:
            assert m.sample_size > 0
            assert m.mean > 0

    @pytest.mark.unit
    async def test_get_variant_metrics_empty(
        self, ab_service: ABTestService, sample_config
    ):
        """Test getting metrics with no data."""
        test = await ab_service.create_test(sample_config)

        metrics = await ab_service.get_variant_metrics(test.id)

        assert len(metrics) == 0


class TestStatisticalAnalysis:
    """Test statistical analysis functionality."""

    @pytest.mark.unit
    def test_perform_t_test_significant(self, ab_service: ABTestService):
        """Test t-test with significant difference."""
        group_a = [70, 72, 71, 69, 73, 74, 70, 71, 72, 70]
        group_b = [85, 87, 86, 84, 88, 89, 85, 86, 87, 85]

        result = ab_service.perform_t_test(group_a, group_b)

        assert result.t_statistic < 0  # group_b > group_a
        assert result.p_value < 0.05
        assert result.is_significant is True
        assert result.degrees_of_freedom > 0

    @pytest.mark.unit
    def test_perform_t_test_not_significant(self, ab_service: ABTestService):
        """Test t-test with no significant difference."""
        group_a = [80, 82, 81, 79, 83, 84, 80, 81, 82, 80]
        group_b = [81, 83, 82, 80, 84, 85, 81, 82, 83, 81]

        result = ab_service.perform_t_test(group_a, group_b)

        assert result.p_value > 0.05
        assert result.is_significant is False

    @pytest.mark.unit
    def test_perform_t_test_custom_alpha(self, ab_service: ABTestService):
        """Test t-test with custom significance level."""
        group_a = [70, 72, 71, 69, 73]
        group_b = [75, 77, 76, 74, 78]

        result_05 = ab_service.perform_t_test(group_a, group_b, significance_level=0.05)
        result_01 = ab_service.perform_t_test(group_a, group_b, significance_level=0.01)

        # May be significant at 0.05 but not at 0.01
        assert result_05.p_value == result_01.p_value

    @pytest.mark.unit
    def test_perform_t_test_insufficient_samples(self, ab_service: ABTestService):
        """Test t-test with insufficient samples raises error."""
        with pytest.raises(ABTestServiceError, match="at least 2 samples"):
            ab_service.perform_t_test([1], [1, 2, 3])

        with pytest.raises(ABTestServiceError, match="at least 2 samples"):
            ab_service.perform_t_test([1, 2], [1])

    @pytest.mark.unit
    def test_calculate_cohens_d_large(self, ab_service: ABTestService):
        """Test Cohen's d calculation with large effect."""
        group_a = [50, 52, 51, 49, 53]
        group_b = [80, 82, 81, 79, 83]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        assert result.cohens_d > 0.8
        assert result.interpretation == EffectSizeInterpretation.LARGE

    @pytest.mark.unit
    def test_calculate_cohens_d_medium(self, ab_service: ABTestService):
        """Test Cohen's d calculation with medium effect."""
        # Use data designed to produce medium effect (0.5 <= |d| < 0.8)
        # For pooled std of 10, mean diff should be 5-8 for medium effect
        group_a = [50, 55, 45, 60, 40, 58, 52, 48, 56, 46]  # mean=51, std~6.3
        group_b = [54, 59, 49, 64, 44, 62, 56, 52, 60, 50]  # mean=55, diff=4

        result = ab_service.calculate_cohens_d(group_a, group_b)

        assert 0.5 <= abs(result.cohens_d) < 0.8
        assert result.interpretation == EffectSizeInterpretation.MEDIUM

    @pytest.mark.unit
    def test_calculate_cohens_d_small(self, ab_service: ABTestService):
        """Test Cohen's d calculation with small effect."""
        # Use data with higher variance relative to mean difference
        group_a = [70, 80, 75, 65, 85, 78, 72, 82, 68, 88]  # mean~76.3
        group_b = [72, 82, 77, 67, 87, 80, 74, 84, 70, 90]  # mean~78.3, diff=2

        result = ab_service.calculate_cohens_d(group_a, group_b)

        assert 0.2 <= abs(result.cohens_d) < 0.5
        assert result.interpretation == EffectSizeInterpretation.SMALL

    @pytest.mark.unit
    def test_calculate_cohens_d_negligible(self, ab_service: ABTestService):
        """Test Cohen's d calculation with negligible effect."""
        group_a = [80, 82, 81, 79, 83, 84, 80, 81, 82, 80]
        group_b = [80, 82, 81, 79, 83, 84, 80, 81, 82, 80]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        assert abs(result.cohens_d) < 0.2
        assert result.interpretation == EffectSizeInterpretation.NEGLIGIBLE

    @pytest.mark.unit
    def test_calculate_cohens_d_negative(self, ab_service: ABTestService):
        """Test Cohen's d can be negative (group_a > group_b)."""
        group_a = [85, 87, 86, 84, 88]
        group_b = [70, 72, 71, 69, 73]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        assert result.cohens_d < 0

    @pytest.mark.unit
    def test_interpret_effect_size(self, ab_service: ABTestService):
        """Test effect size interpretation."""
        assert ab_service.interpret_effect_size(0.1) == EffectSizeInterpretation.NEGLIGIBLE
        assert ab_service.interpret_effect_size(-0.1) == EffectSizeInterpretation.NEGLIGIBLE
        assert ab_service.interpret_effect_size(0.3) == EffectSizeInterpretation.SMALL
        assert ab_service.interpret_effect_size(0.6) == EffectSizeInterpretation.MEDIUM
        assert ab_service.interpret_effect_size(1.0) == EffectSizeInterpretation.LARGE
        assert ab_service.interpret_effect_size(-1.0) == EffectSizeInterpretation.LARGE


class TestReportGeneration:
    """Test report generation functionality."""

    @pytest.mark.unit
    async def test_generate_report_significant_result(
        self, ab_service: ABTestService, sample_config
    ):
        """Test report generation with significant result."""
        test = await ab_service.create_test(sample_config)

        # Create clear difference between variants
        for i in range(50):
            # Force specific variant assignments for testing
            ab_service._assignments[f"{test.id}:control-{i}"] = type(
                "Assignment",
                (),
                {"variant_name": "control", "prompt_version": "v1.0"},
            )()
            ab_service._assignments[f"{test.id}:treatment-{i}"] = type(
                "Assignment",
                (),
                {"variant_name": "treatment", "prompt_version": "v2.0"},
            )()

        # Add metrics directly
        from app.schemas.ab_test import MetricDataPoint

        for i in range(50):
            ab_service._metrics.setdefault(test.id, []).append(
                MetricDataPoint(
                    session_id=f"control-{i}",
                    variant_name="control",
                    value=0.70 + (i % 5) * 0.01,
                )
            )
            ab_service._metrics[test.id].append(
                MetricDataPoint(
                    session_id=f"treatment-{i}",
                    variant_name="treatment",
                    value=0.85 + (i % 5) * 0.01,
                )
            )

        request = ABTestReportRequest(minimum_sample_size=30)
        report = await ab_service.generate_report(test.id, request)

        assert report.test_id == test.id
        assert len(report.metrics) == 2
        assert report.t_test_result is not None
        assert report.t_test_result.is_significant is True
        assert report.effect_size is not None
        assert report.winner == "treatment"
        assert "significant" in report.recommendation.lower()

    @pytest.mark.unit
    async def test_generate_report_not_significant(
        self, ab_service: ABTestService, sample_config
    ):
        """Test report generation with no significant difference."""
        test = await ab_service.create_test(sample_config)

        # Add similar metrics for both variants
        from app.schemas.ab_test import MetricDataPoint

        for i in range(50):
            ab_service._metrics.setdefault(test.id, []).append(
                MetricDataPoint(
                    session_id=f"control-{i}",
                    variant_name="control",
                    value=0.80 + (i % 5) * 0.01,
                )
            )
            ab_service._metrics[test.id].append(
                MetricDataPoint(
                    session_id=f"treatment-{i}",
                    variant_name="treatment",
                    value=0.80 + (i % 5) * 0.01,
                )
            )

        report = await ab_service.generate_report(
            test.id, ABTestReportRequest(minimum_sample_size=30)
        )

        assert report.winner is None
        assert "no statistically significant" in report.recommendation.lower()

    @pytest.mark.unit
    async def test_generate_report_insufficient_samples(
        self, ab_service: ABTestService, sample_config
    ):
        """Test report with insufficient sample size warning."""
        test = await ab_service.create_test(sample_config)

        # Add only a few metrics
        from app.schemas.ab_test import MetricDataPoint

        for i in range(10):
            ab_service._metrics.setdefault(test.id, []).append(
                MetricDataPoint(
                    session_id=f"session-{i}",
                    variant_name="control" if i < 5 else "treatment",
                    value=0.80,
                )
            )

        report = await ab_service.generate_report(
            test.id, ABTestReportRequest(minimum_sample_size=30)
        )

        assert len(report.warning_messages) > 0
        assert any("below" in w.lower() for w in report.warning_messages)

    @pytest.mark.unit
    async def test_generate_report_three_variants(
        self, ab_service: ABTestService, three_variant_config
    ):
        """Test report with more than 2 variants."""
        test = await ab_service.create_test(three_variant_config)

        from app.schemas.ab_test import MetricDataPoint

        for i in range(30):
            ab_service._metrics.setdefault(test.id, []).append(
                MetricDataPoint(
                    session_id=f"session-{i}",
                    variant_name=["control", "treatment_a", "treatment_b"][i % 3],
                    value=0.80,
                )
            )

        report = await ab_service.generate_report(
            test.id, ABTestReportRequest(minimum_sample_size=10)
        )

        # Should have warning about only supporting 2 variants
        assert any("2 variants" in w for w in report.warning_messages)

    @pytest.mark.unit
    async def test_generate_report_no_data(
        self, ab_service: ABTestService, sample_config
    ):
        """Test report with no data."""
        test = await ab_service.create_test(sample_config)

        report = await ab_service.generate_report(
            test.id, ABTestReportRequest()
        )

        assert len(report.metrics) == 0
        assert report.t_test_result is None
        assert len(report.warning_messages) > 0


class TestHelperMethods:
    """Test private helper methods."""

    @pytest.mark.unit
    def test_mean(self, ab_service: ABTestService):
        """Test mean calculation."""
        assert ab_service._mean([1, 2, 3, 4, 5]) == 3.0
        assert ab_service._mean([10]) == 10.0
        assert ab_service._mean([]) == 0.0

    @pytest.mark.unit
    def test_std(self, ab_service: ABTestService):
        """Test standard deviation calculation."""
        # Known values
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        std = ab_service._std(values)
        assert std == pytest.approx(2.138, rel=0.01)

        # Edge cases
        assert ab_service._std([1]) == 0.0
        assert ab_service._std([]) == 0.0

    @pytest.mark.unit
    def test_variance(self, ab_service: ABTestService):
        """Test variance calculation."""
        values = [2, 4, 4, 4, 5, 5, 7, 9]
        var = ab_service._variance(values)
        std = ab_service._std(values)
        assert var == pytest.approx(std ** 2, rel=0.01)

    @pytest.mark.unit
    def test_calculate_variant_metrics(self, ab_service: ABTestService):
        """Test variant metrics calculation."""
        values = [0.80, 0.85, 0.90, 0.75, 0.82]
        metrics = ab_service._calculate_variant_metrics("test", values)

        assert metrics.variant_name == "test"
        assert metrics.sample_size == 5
        assert metrics.mean == pytest.approx(0.824, rel=0.01)
        assert metrics.std > 0
        assert metrics.min_value == 0.75
        assert metrics.max_value == 0.90
        assert metrics.confidence_interval_lower is not None
        assert metrics.confidence_interval_upper is not None

    @pytest.mark.unit
    def test_calculate_variant_metrics_empty(self, ab_service: ABTestService):
        """Test variant metrics with empty values."""
        metrics = ab_service._calculate_variant_metrics("test", [])

        assert metrics.sample_size == 0
        assert metrics.mean == 0.0
        assert metrics.std == 0.0

    @pytest.mark.unit
    def test_calculate_variant_metrics_single_value(self, ab_service: ABTestService):
        """Test variant metrics with single value."""
        metrics = ab_service._calculate_variant_metrics("test", [0.85])

        assert metrics.sample_size == 1
        assert metrics.mean == 0.85
        assert metrics.std == 0.0
        assert metrics.confidence_interval_lower is None


class TestValkeyIntegration:
    """Test Valkey integration."""

    @pytest.mark.unit
    async def test_valkey_disabled_returns_none(self, ab_service: ABTestService):
        """Test _get_valkey_client returns None when disabled."""
        ab_service._use_valkey = False
        result = await ab_service._get_valkey_client()
        assert result is None

    @pytest.mark.unit
    async def test_valkey_connection_error_handled(self):
        """Test Valkey connection error is handled gracefully."""
        from app.services.valkey_client import ValkeyConnectionError

        service = ABTestService(use_valkey=True)

        with patch(
            "app.services.ab_test_service.ValkeyClient"
        ) as MockValkeyClient:
            mock_client = MagicMock()
            mock_client.connect = AsyncMock(
                side_effect=ValkeyConnectionError("Connection failed")
            )
            MockValkeyClient.return_value = mock_client

            result = await service._get_valkey_client()

            assert result is None
            assert service._valkey_client is None

    @pytest.mark.unit
    async def test_valkey_fallback_to_memory(self, sample_config):
        """Test operations work with memory fallback when Valkey fails."""
        service = ABTestService(use_valkey=True)

        with patch.object(
            service, "_get_valkey_client", return_value=None
        ):
            # Create should still work with memory
            test = await service.create_test(sample_config)
            assert test.id is not None

            # Get should work
            retrieved = await service.get_test(test.id)
            assert retrieved.id == test.id

    @pytest.mark.unit
    async def test_get_test_valkey_path(self, sample_config):
        """Test get_test retrieves from Valkey when available."""
        service = ABTestService(use_valkey=True)

        # Create mock Valkey client with data (need at least 2 variants)
        mock_client = MagicMock()
        mock_client.get = AsyncMock(
            return_value={
                "id": "test-123",
                "name": "Test",
                "description": "desc",
                "variants": [
                    {"name": "control", "prompt_version": "v1", "weight": 0.5},
                    {"name": "treatment", "prompt_version": "v2", "weight": 0.5},
                ],
                "metadata": {},
                "status": "draft",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00",
            }
        )

        # Inject mock client
        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            result = await service.get_test("test-123")
            assert result.id == "test-123"
            assert result.name == "Test"
            mock_client.get.assert_called_once()

    @pytest.mark.unit
    async def test_get_test_valkey_exception_fallback(self, sample_config):
        """Test get_test falls back to memory when Valkey raises exception."""
        service = ABTestService(use_valkey=True)

        # Create test in memory first
        test = await service.create_test(sample_config)

        # Create mock Valkey client that raises exception
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Valkey error"))

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            # Should still return from memory
            result = await service.get_test(test.id)
            assert result.id == test.id

    @pytest.mark.unit
    async def test_get_assignment_valkey_path(self, sample_config):
        """Test get_assignment retrieves from Valkey when available."""
        service = ABTestService(use_valkey=True)

        # Create mock Valkey client
        mock_client = MagicMock()
        mock_client.get = AsyncMock(
            return_value={
                "test_id": "test-123",
                "session_id": "session-456",
                "variant_name": "control",
                "prompt_version": "v1.0",
                "assigned_at": "2025-01-01T00:00:00",
            }
        )

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            result = await service.get_assignment("test-123", "session-456")
            assert result is not None
            assert result.variant_name == "control"

    @pytest.mark.unit
    async def test_get_assignment_valkey_exception_fallback(self, sample_config):
        """Test get_assignment falls back to memory when Valkey raises exception."""
        service = ABTestService(use_valkey=True)

        # Create test and assignment in memory first
        test = await service.create_test(sample_config)
        assignment, _ = await service.assign_variant(test.id, "session-123")

        # Create mock Valkey client that raises exception
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Valkey error"))

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            # Should still return from memory
            result = await service.get_assignment(test.id, "session-123")
            assert result is not None
            assert result.variant_name == assignment.variant_name

    @pytest.mark.unit
    async def test_delete_test_valkey_path(self, sample_config):
        """Test delete_test deletes from Valkey when available."""
        service = ABTestService(use_valkey=True)

        # Create test
        test = await service.create_test(sample_config)

        # Create mock Valkey client
        mock_client = MagicMock()
        mock_client.delete = AsyncMock(return_value=True)

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            result = await service.delete_test(test.id)
            assert result is True
            mock_client.delete.assert_called_once()

    @pytest.mark.unit
    async def test_delete_test_valkey_exception_continues(self, sample_config):
        """Test delete_test continues even when Valkey raises exception."""
        service = ABTestService(use_valkey=True)

        # Create test
        test = await service.create_test(sample_config)

        # Create mock Valkey client that raises exception
        mock_client = MagicMock()
        mock_client.delete = AsyncMock(side_effect=Exception("Valkey error"))

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            # Should still succeed (removing from memory)
            result = await service.delete_test(test.id)
            assert result is True

    @pytest.mark.unit
    async def test_store_test_valkey_exception_continues(self, sample_config):
        """Test _store_test continues even when Valkey raises exception."""
        service = ABTestService(use_valkey=True)

        # Create mock Valkey client that raises exception on set
        mock_client = MagicMock()
        mock_client.set = AsyncMock(side_effect=Exception("Valkey error"))

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            # Should still create test (in memory)
            test = await service.create_test(sample_config)
            assert test.id is not None
            # Verify in memory
            assert test.id in service._tests

    @pytest.mark.unit
    async def test_store_assignment_valkey_exception_continues(self, sample_config):
        """Test _store_assignment continues even when Valkey raises exception."""
        service = ABTestService(use_valkey=True)

        # Create test first
        test = await service.create_test(sample_config)

        # Create mock Valkey client that raises exception on set
        mock_client = MagicMock()
        mock_client.set = AsyncMock(side_effect=Exception("Valkey error"))

        service._valkey_client = mock_client

        with patch.object(service, "_get_valkey_client", return_value=mock_client):
            # Should still assign variant (in memory)
            assignment, is_new = await service.assign_variant(test.id, "session-123")
            assert is_new is True
            assert assignment.variant_name in ["control", "treatment"]
            # Verify in memory
            assert f"{test.id}:session-123" in service._assignments


class TestEdgeCases:
    """Test edge cases and exception paths."""

    @pytest.mark.unit
    def test_calculate_cohens_d_insufficient_samples(self, ab_service: ABTestService):
        """Test Cohen's d raises error with insufficient samples."""
        with pytest.raises(ABTestServiceError, match="at least 2 samples"):
            ab_service.calculate_cohens_d([1], [1, 2, 3])

        with pytest.raises(ABTestServiceError, match="at least 2 samples"):
            ab_service.calculate_cohens_d([1, 2], [1])

    @pytest.mark.unit
    async def test_generate_report_exception_in_statistical_test(
        self, ab_service: ABTestService, sample_config
    ):
        """Test generate_report handles exception in statistical test."""
        test = await ab_service.create_test(sample_config)

        # Add metrics directly with only 1 sample per variant (causes exception)
        from app.schemas.ab_test import MetricDataPoint

        ab_service._metrics[test.id] = [
            MetricDataPoint(
                session_id="control-1",
                variant_name="control",
                value=0.80,
            ),
            MetricDataPoint(
                session_id="treatment-1",
                variant_name="treatment",
                value=0.85,
            ),
        ]

        request = ABTestReportRequest(minimum_sample_size=1)
        report = await ab_service.generate_report(test.id, request)

        # Should have warning about insufficient data
        assert any(
            "insufficient" in w.lower() or "2 samples" in w.lower()
            for w in report.warning_messages
        )
        assert report.t_test_result is None

    @pytest.mark.unit
    async def test_generate_report_t_test_exception_handled(
        self, ab_service: ABTestService, sample_config
    ):
        """Test generate_report catches ABTestServiceError from t-test."""
        test = await ab_service.create_test(sample_config)

        # Add enough metrics for statistical test
        from app.schemas.ab_test import MetricDataPoint

        for i in range(10):
            ab_service._metrics.setdefault(test.id, []).append(
                MetricDataPoint(
                    session_id=f"control-{i}",
                    variant_name="control",
                    value=0.80,
                )
            )
            ab_service._metrics[test.id].append(
                MetricDataPoint(
                    session_id=f"treatment-{i}",
                    variant_name="treatment",
                    value=0.85,
                )
            )

        # Mock perform_t_test to raise ABTestServiceError
        with patch.object(
            ab_service,
            "perform_t_test",
            side_effect=ABTestServiceError("Test error in t-test"),
        ):
            request = ABTestReportRequest(minimum_sample_size=1)
            report = await ab_service.generate_report(test.id, request)

            # Should have warning from the exception
            assert any("Test error in t-test" in w for w in report.warning_messages)
            assert report.t_test_result is None

    @pytest.mark.unit
    def test_parse_test_config_with_string_dates(self, ab_service: ABTestService):
        """Test _parse_test_config handles string dates correctly."""
        data = {
            "id": "test-123",
            "name": "Test",
            "description": "desc",
            "variants": [
                {"name": "control", "prompt_version": "v1", "weight": 0.5},
                {"name": "treatment", "prompt_version": "v2", "weight": 0.5},
            ],
            "metadata": {},
            "status": "draft",
            "created_at": "2025-01-15T10:30:00",
            "updated_at": "2025-01-15T11:00:00",
        }

        result = ab_service._parse_test_config(data)

        assert result.id == "test-123"
        assert result.created_at.year == 2025
        assert result.created_at.month == 1
        assert result.created_at.day == 15
        assert result.updated_at.hour == 11

    @pytest.mark.unit
    def test_parse_test_config_with_datetime_objects(self, ab_service: ABTestService):
        """Test _parse_test_config handles datetime objects correctly."""
        data = {
            "id": "test-456",
            "name": "Test 2",
            "description": "desc",
            "variants": [
                {"name": "control", "prompt_version": "v1", "weight": 0.5},
                {"name": "treatment", "prompt_version": "v2", "weight": 0.5},
            ],
            "metadata": {},
            "status": "running",
            "created_at": datetime(2025, 2, 20, 14, 30, 0),
            "updated_at": datetime(2025, 2, 20, 15, 0, 0),
        }

        result = ab_service._parse_test_config(data)

        assert result.id == "test-456"
        assert result.created_at.month == 2
        assert result.updated_at.hour == 15

    @pytest.mark.unit
    def test_variance_edge_cases(self, ab_service: ABTestService):
        """Test _variance with edge cases."""
        # Single value
        assert ab_service._variance([5]) == 0.0
        # Empty list
        assert ab_service._variance([]) == 0.0
        # Multiple identical values
        assert ab_service._variance([5, 5, 5, 5]) == 0.0


class TestStatisticalPrecision:
    """Test statistical calculation precision (Issue #178 requirement: 99.9%)."""

    @pytest.mark.unit
    def test_t_test_against_scipy(self, ab_service: ABTestService):
        """Verify t-test results match scipy directly."""
        from scipy import stats as scipy_stats

        group_a = [72.1, 75.3, 68.9, 71.5, 74.2, 69.8, 73.1, 70.6, 72.8, 71.0]
        group_b = [85.2, 88.4, 82.1, 84.7, 87.3, 83.5, 86.2, 84.9, 85.8, 86.0]

        # Our implementation
        result = ab_service.perform_t_test(group_a, group_b)

        # Direct scipy
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        # Should match to high precision
        assert result.t_statistic == pytest.approx(scipy_t, rel=0.001)
        assert result.p_value == pytest.approx(scipy_p, rel=0.001)

    @pytest.mark.unit
    def test_cohens_d_known_values(self, ab_service: ABTestService):
        """Verify Cohen's d with known values."""
        # Known case: groups with mean diff = 10, pooled std = 10 -> d = 1.0
        group_a = [45, 50, 55]  # mean = 50, var = 25
        group_b = [55, 60, 65]  # mean = 60, var = 25

        result = ab_service.calculate_cohens_d(group_a, group_b)

        # Cohen's d = (60 - 50) / 5 = 2.0
        assert result.cohens_d == pytest.approx(2.0, rel=0.01)

    @pytest.mark.unit
    def test_confidence_interval_coverage(self, ab_service: ABTestService):
        """Test 95% CI coverage is approximately correct."""
        import random as py_random

        py_random.seed(42)

        # Generate data from known distribution
        true_mean = 0.80
        true_std = 0.05
        sample_size = 50

        # Run multiple times to check CI coverage
        coverage_count = 0
        iterations = 100

        for _ in range(iterations):
            # Generate sample
            sample = [py_random.gauss(true_mean, true_std) for _ in range(sample_size)]
            metrics = ab_service._calculate_variant_metrics("test", sample)

            # Check if true mean is within CI
            if (
                metrics.confidence_interval_lower is not None
                and metrics.confidence_interval_upper is not None
            ):
                if (
                    metrics.confidence_interval_lower
                    <= true_mean
                    <= metrics.confidence_interval_upper
                ):
                    coverage_count += 1

        # 95% CI should contain true mean ~95% of the time
        coverage_rate = coverage_count / iterations
        assert 0.85 < coverage_rate < 1.0  # Allow some variance
