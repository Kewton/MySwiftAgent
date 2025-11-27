"""Unit tests for AB Test Statistical Calculation Precision.

Tests for Issue #178: AB Test Infrastructure Implementation.
This module verifies statistical calculation precision at 99.9% accuracy.
"""

import math
import random

import pytest
from scipy import stats as scipy_stats

from app.services.ab_test_service import ABTestService


@pytest.fixture
def ab_service():
    """Create ABTestService instance without Valkey."""
    return ABTestService(use_valkey=False)


class TestTTestPrecision:
    """Test t-test calculation precision against scipy."""

    @pytest.mark.unit
    def test_t_test_precision_normal_data(self, ab_service: ABTestService):
        """Test t-test precision with normally distributed data."""
        random.seed(42)

        # Generate normally distributed samples
        group_a = [random.gauss(50, 10) for _ in range(100)]
        group_b = [random.gauss(55, 10) for _ in range(100)]

        # Our implementation
        result = ab_service.perform_t_test(group_a, group_b)

        # Direct scipy reference
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        # 99.9% precision = relative error < 0.001
        assert abs(result.t_statistic - scipy_t) / abs(scipy_t) < 0.001
        assert abs(result.p_value - scipy_p) / scipy_p < 0.001

    @pytest.mark.unit
    def test_t_test_precision_small_samples(self, ab_service: ABTestService):
        """Test t-test precision with small sample sizes."""
        group_a = [23.5, 27.1, 19.8, 24.3, 21.6]
        group_b = [31.2, 28.9, 33.5, 30.1, 29.7]

        result = ab_service.perform_t_test(group_a, group_b)
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        assert result.t_statistic == pytest.approx(scipy_t, rel=0.001)
        assert result.p_value == pytest.approx(scipy_p, rel=0.001)

    @pytest.mark.unit
    def test_t_test_precision_large_difference(self, ab_service: ABTestService):
        """Test t-test precision with large mean difference."""
        group_a = [10, 12, 11, 9, 13, 10, 11, 12, 10, 11]
        group_b = [90, 92, 91, 89, 93, 90, 91, 92, 90, 91]

        result = ab_service.perform_t_test(group_a, group_b)
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        assert result.t_statistic == pytest.approx(scipy_t, rel=0.001)
        # p-value will be very small, use absolute precision
        assert result.p_value == pytest.approx(scipy_p, abs=1e-10)

    @pytest.mark.unit
    def test_t_test_precision_unequal_variances(self, ab_service: ABTestService):
        """Test t-test precision with unequal variances (Welch's)."""
        random.seed(123)

        # Different variances
        group_a = [random.gauss(50, 5) for _ in range(50)]  # Low variance
        group_b = [random.gauss(55, 15) for _ in range(50)]  # High variance

        result = ab_service.perform_t_test(group_a, group_b)
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        assert result.t_statistic == pytest.approx(scipy_t, rel=0.001)
        assert result.p_value == pytest.approx(scipy_p, rel=0.001)

    @pytest.mark.unit
    def test_t_test_precision_unequal_sample_sizes(self, ab_service: ABTestService):
        """Test t-test precision with unequal sample sizes."""
        random.seed(456)

        group_a = [random.gauss(50, 10) for _ in range(30)]
        group_b = [random.gauss(52, 10) for _ in range(100)]

        result = ab_service.perform_t_test(group_a, group_b)
        scipy_t, scipy_p = scipy_stats.ttest_ind(group_a, group_b, equal_var=False)

        assert result.t_statistic == pytest.approx(scipy_t, rel=0.001)
        assert result.p_value == pytest.approx(scipy_p, rel=0.001)

    @pytest.mark.unit
    def test_t_test_identical_groups(self, ab_service: ABTestService):
        """Test t-test with identical groups."""
        group_a = [50, 51, 52, 49, 50]
        group_b = [50, 51, 52, 49, 50]

        result = ab_service.perform_t_test(group_a, group_b)

        # Should have t=0 and p=1
        assert result.t_statistic == pytest.approx(0.0, abs=0.001)
        assert result.p_value == pytest.approx(1.0, rel=0.001)
        assert result.is_significant is False


class TestCohensDBPrecision:
    """Test Cohen's d calculation precision."""

    @pytest.mark.unit
    def test_cohens_d_known_formula(self, ab_service: ABTestService):
        """Test Cohen's d against known formula calculation."""
        group_a = [10, 12, 11, 13, 14]
        group_b = [15, 17, 16, 18, 19]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        # Manual calculation
        mean_a = sum(group_a) / len(group_a)  # 12
        mean_b = sum(group_b) / len(group_b)  # 17
        n_a, n_b = len(group_a), len(group_b)

        var_a = sum((x - mean_a) ** 2 for x in group_a) / (n_a - 1)
        var_b = sum((x - mean_b) ** 2 for x in group_b) / (n_b - 1)

        pooled_std = math.sqrt(
            ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
        )
        expected_d = (mean_b - mean_a) / pooled_std

        assert result.cohens_d == pytest.approx(expected_d, rel=0.001)

    @pytest.mark.unit
    def test_cohens_d_precision_large_sample(self, ab_service: ABTestService):
        """Test Cohen's d precision with large samples."""
        random.seed(789)

        group_a = [random.gauss(100, 15) for _ in range(500)]
        group_b = [random.gauss(110, 15) for _ in range(500)]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        # Expected d ~ (110-100) / 15 = 0.667
        # Allow for sampling variability
        assert 0.5 < result.cohens_d < 0.9

    @pytest.mark.unit
    def test_cohens_d_edge_case_zero_effect(self, ab_service: ABTestService):
        """Test Cohen's d with zero effect (identical distributions)."""
        random.seed(111)

        group_a = [random.gauss(50, 10) for _ in range(100)]
        group_b = [random.gauss(50, 10) for _ in range(100)]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        # Should be close to 0
        assert abs(result.cohens_d) < 0.3


class TestDegreesOfFreedomPrecision:
    """Test degrees of freedom calculation (Welch-Satterthwaite)."""

    @pytest.mark.unit
    def test_dof_welch_satterthwaite(self, ab_service: ABTestService):
        """Test Welch-Satterthwaite degrees of freedom calculation."""
        group_a = [23, 25, 27, 29, 31]  # var = 10
        group_b = [45, 55, 65, 75, 85]  # var = 250

        result = ab_service.perform_t_test(group_a, group_b)

        # Manual Welch-Satterthwaite formula
        n1, n2 = 5, 5
        s1_sq = 10  # variance of group_a
        s2_sq = 250  # variance of group_b

        numerator = (s1_sq / n1 + s2_sq / n2) ** 2
        denominator = ((s1_sq / n1) ** 2) / (n1 - 1) + ((s2_sq / n2) ** 2) / (n2 - 1)
        expected_dof = numerator / denominator

        assert result.degrees_of_freedom == pytest.approx(expected_dof, rel=0.01)

    @pytest.mark.unit
    def test_dof_equal_variances(self, ab_service: ABTestService):
        """Test DoF with equal variances approaches n1+n2-2."""
        group_a = [50, 51, 52, 53, 54, 55, 56, 57, 58, 59]
        group_b = [60, 61, 62, 63, 64, 65, 66, 67, 68, 69]

        result = ab_service.perform_t_test(group_a, group_b)

        # With equal variances, DoF should be close to n1+n2-2 = 18
        assert 17 < result.degrees_of_freedom < 19


class TestConfidenceIntervalPrecision:
    """Test confidence interval calculation precision."""

    @pytest.mark.unit
    def test_95_ci_known_values(self, ab_service: ABTestService):
        """Test 95% CI calculation with known values."""
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]

        metrics = ab_service._calculate_variant_metrics("test", values)

        # Mean = 19, std = 6.055, n = 10
        # SE = 6.055 / sqrt(10) = 1.914
        # t_critical(0.975, 9) = 2.262
        # CI = 19 +/- 2.262 * 1.914 = 19 +/- 4.33
        assert metrics.mean == pytest.approx(19.0, rel=0.001)
        assert metrics.confidence_interval_lower is not None
        assert metrics.confidence_interval_upper is not None

        # CI should contain the mean
        assert (
            metrics.confidence_interval_lower
            < metrics.mean
            < metrics.confidence_interval_upper
        )

        # CI width should be approximately correct
        ci_width = metrics.confidence_interval_upper - metrics.confidence_interval_lower
        expected_width = 2 * scipy_stats.t.ppf(0.975, 9) * metrics.std / math.sqrt(10)
        assert ci_width == pytest.approx(expected_width, rel=0.01)

    @pytest.mark.unit
    def test_ci_coverage_simulation(self, ab_service: ABTestService):
        """Test that 95% CI achieves approximately 95% coverage."""
        random.seed(42)

        true_mean = 100
        true_std = 10
        n_simulations = 500
        sample_size = 50

        coverage_count = 0

        for _ in range(n_simulations):
            sample = [random.gauss(true_mean, true_std) for _ in range(sample_size)]
            metrics = ab_service._calculate_variant_metrics("test", sample)

            if (
                metrics.confidence_interval_lower is not None
                and metrics.confidence_interval_upper is not None
                and metrics.confidence_interval_lower
                <= true_mean
                <= metrics.confidence_interval_upper
            ):
                coverage_count += 1

        coverage_rate = coverage_count / n_simulations

        # 95% CI should have coverage rate approximately 0.95
        # Allow for sampling variability (90% to 99%)
        assert 0.90 < coverage_rate < 0.99


class TestStatisticalEdgeCases:
    """Test edge cases in statistical calculations."""

    @pytest.mark.unit
    def test_t_test_constant_group(self, ab_service: ABTestService):
        """Test t-test when one group has constant values."""
        group_a = [50, 50, 50, 50, 50]
        group_b = [60, 62, 58, 61, 59]

        result = ab_service.perform_t_test(group_a, group_b)

        # Should still produce valid result
        assert not math.isnan(result.t_statistic)
        assert not math.isnan(result.p_value)
        assert 0 <= result.p_value <= 1

    @pytest.mark.unit
    def test_cohens_d_zero_pooled_std(self, ab_service: ABTestService):
        """Test Cohen's d when pooled std is zero (identical values)."""
        group_a = [50, 50, 50]
        group_b = [50, 50, 50]

        result = ab_service.calculate_cohens_d(group_a, group_b)

        # With identical values, d should be 0
        assert result.cohens_d == 0.0

    @pytest.mark.unit
    def test_extreme_p_values(self, ab_service: ABTestService):
        """Test handling of extreme p-values."""
        # Groups with very large difference
        group_a = [1, 2, 3, 4, 5] * 20  # 100 samples, mean=3
        group_b = [96, 97, 98, 99, 100] * 20  # 100 samples, mean=98

        result = ab_service.perform_t_test(group_a, group_b)

        # p-value should be extremely small
        assert result.p_value < 1e-50
        assert result.is_significant is True

    @pytest.mark.unit
    def test_minimum_sample_size(self, ab_service: ABTestService):
        """Test with minimum sample size (n=2)."""
        group_a = [10, 20]
        group_b = [30, 40]

        result = ab_service.perform_t_test(group_a, group_b)

        # Should produce valid results
        assert not math.isnan(result.t_statistic)
        assert 0 <= result.p_value <= 1


class TestNumericalStability:
    """Test numerical stability of calculations."""

    @pytest.mark.unit
    def test_large_values(self, ab_service: ABTestService):
        """Test stability with large values."""
        group_a = [1e10 + i for i in range(10)]
        group_b = [1e10 + 100 + i for i in range(10)]

        result = ab_service.perform_t_test(group_a, group_b)

        assert not math.isnan(result.t_statistic)
        assert not math.isnan(result.p_value)
        assert result.is_significant is True  # Difference should be significant

    @pytest.mark.unit
    def test_small_values(self, ab_service: ABTestService):
        """Test stability with small values."""
        group_a = [1e-10 * i for i in range(1, 11)]
        group_b = [1e-10 * (i + 10) for i in range(1, 11)]

        result = ab_service.perform_t_test(group_a, group_b)

        assert not math.isnan(result.t_statistic)
        assert not math.isnan(result.p_value)

    @pytest.mark.unit
    def test_mixed_signs(self, ab_service: ABTestService):
        """Test with mixed positive and negative values."""
        group_a = [-5, -3, -1, 1, 3, 5]
        group_b = [0, 2, 4, 6, 8, 10]

        result = ab_service.perform_t_test(group_a, group_b)
        cohens = ab_service.calculate_cohens_d(group_a, group_b)

        assert not math.isnan(result.t_statistic)
        assert not math.isnan(cohens.cohens_d)
        assert cohens.cohens_d > 0  # group_b > group_a


class TestStatisticalConsistency:
    """Test consistency between different statistical measures."""

    @pytest.mark.unit
    def test_t_stat_and_cohens_d_sign_consistency(self, ab_service: ABTestService):
        """Test that t-statistic and Cohen's d have consistent signs."""
        # Group B larger than A
        group_a = [10, 12, 11, 13, 14]
        group_b = [20, 22, 21, 23, 24]

        t_result = ab_service.perform_t_test(group_a, group_b)
        d_result = ab_service.calculate_cohens_d(group_a, group_b)

        # Both should indicate group_b > group_a (same direction)
        assert (t_result.t_statistic < 0) == (d_result.cohens_d > 0)

    @pytest.mark.unit
    def test_significance_consistency(self, ab_service: ABTestService):
        """Test that significant t-test implies non-negligible effect size."""
        random.seed(999)

        # Generate data with moderate difference
        group_a = [random.gauss(50, 5) for _ in range(50)]
        group_b = [random.gauss(54, 5) for _ in range(50)]  # 4 unit difference

        t_result = ab_service.perform_t_test(group_a, group_b)
        d_result = ab_service.calculate_cohens_d(group_a, group_b)

        # If t-test is significant, effect size should not be negligible
        if t_result.is_significant:
            assert abs(d_result.cohens_d) >= 0.1
