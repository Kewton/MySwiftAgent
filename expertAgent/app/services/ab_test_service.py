"""AB Test Service for A/B testing infrastructure.

Issue #178: AB Test Infrastructure Implementation.
Provides services for managing A/B tests, variant assignment,
metrics collection, and statistical analysis.
"""

import logging
import math
import random
import uuid
from datetime import datetime
from typing import Any

from scipy import stats  # type: ignore[import-untyped]

from app.schemas.ab_test import (
    ABTestAssignment,
    ABTestConfig,
    ABTestConfigCreate,
    ABTestMetrics,
    ABTestReport,
    ABTestReportRequest,
    ABTestStatus,
    ABTestStatusResponse,
    ABTestVariant,
    EffectSize,
    EffectSizeInterpretation,
    MetricDataPoint,
    TTestResult,
)
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError

from .base import BaseService
from .response_builder import ResponseBuilder

logger = logging.getLogger(__name__)

# Valkey key patterns
AB_TEST_KEY_PREFIX = "ab_test:"
AB_ASSIGNMENT_KEY_PREFIX = "ab_assignment:"
AB_METRICS_KEY_PREFIX = "ab_metrics:"

# Default TTL values (in seconds)
AB_TEST_TTL = 86400 * 365  # 1 year
AB_ASSIGNMENT_TTL = 86400 * 30  # 30 days
AB_METRICS_TTL = 86400 * 90  # 90 days


class ABTestServiceError(Exception):
    """Exception raised for AB test service errors."""

    pass


class ABTestNotFoundError(ABTestServiceError):
    """Exception raised when AB test is not found."""

    pass


class ABTestService(BaseService):
    """Service for managing A/B tests and statistical analysis.

    Provides functionality for:
    - Creating, updating, and deleting AB tests
    - Variant assignment using weighted random selection
    - Metrics collection and aggregation
    - Statistical analysis (t-test, effect size)
    """

    def __init__(
        self,
        valkey_host: str = "localhost",
        valkey_port: int = 6379,
        valkey_db: int = 0,
        use_valkey: bool = True,
    ) -> None:
        """Initialize ABTestService.

        Args:
            valkey_host: Valkey server host.
            valkey_port: Valkey server port.
            valkey_db: Valkey database number.
            use_valkey: Whether to use Valkey for persistence.
        """
        super().__init__(logger=logger, response_builder=ResponseBuilder())
        self._valkey_host = valkey_host
        self._valkey_port = valkey_port
        self._valkey_db = valkey_db
        self._use_valkey = use_valkey
        self._valkey_client: ValkeyClient | None = None

        # In-memory storage fallback
        self._tests: dict[str, ABTestConfig] = {}
        self._assignments: dict[str, ABTestAssignment] = {}
        self._metrics: dict[str, list[MetricDataPoint]] = {}

    # ========================================
    # Connection Management
    # ========================================

    async def _get_valkey_client(self) -> ValkeyClient | None:
        """Get or create Valkey client connection.

        Returns:
            ValkeyClient if available, None otherwise.
        """
        if not self._use_valkey:
            return None

        if self._valkey_client is None:
            try:
                self._valkey_client = ValkeyClient(
                    host=self._valkey_host,
                    port=self._valkey_port,
                    db=self._valkey_db,
                )
                await self._valkey_client.connect()
            except ValkeyConnectionError as e:
                self.logger.warning(f"Failed to connect to Valkey: {e}")
                self._valkey_client = None

        return self._valkey_client

    # ========================================
    # Test Management
    # ========================================

    async def create_test(self, config: ABTestConfigCreate) -> ABTestConfig:
        """Create a new AB test.

        Args:
            config: Test configuration.

        Returns:
            Created ABTestConfig with generated ID.
        """
        test_id = str(uuid.uuid4())
        now = datetime.now()

        # Normalize variant weights
        normalized_variants = self._normalize_variant_weights(config.variants)

        ab_test = ABTestConfig(
            id=test_id,
            name=config.name,
            description=config.description,
            variants=normalized_variants,
            metadata=config.metadata,
            status=ABTestStatus.DRAFT,
            created_at=now,
            updated_at=now,
        )

        # Store in Valkey or memory
        await self._store_test(ab_test)

        self.logger.info(f"Created AB test: {test_id} - {config.name}")
        return ab_test

    async def get_test(self, test_id: str) -> ABTestConfig:
        """Get an AB test by ID.

        Args:
            test_id: Test ID.

        Returns:
            ABTestConfig.

        Raises:
            ABTestNotFoundError: If test not found.
        """
        client = await self._get_valkey_client()

        if client:
            key = f"{AB_TEST_KEY_PREFIX}{test_id}"
            try:
                data = await client.get(key)
                if data:
                    return self._parse_test_config(data)
            except Exception as e:
                self.logger.warning(f"Valkey get failed: {e}")

        # Fallback to memory
        if test_id in self._tests:
            return self._tests[test_id]

        raise ABTestNotFoundError(f"AB test not found: {test_id}")

    async def list_tests(
        self, status: ABTestStatus | None = None, limit: int = 100, offset: int = 0
    ) -> tuple[list[ABTestConfig], int]:
        """List AB tests with optional filtering.

        Args:
            status: Optional status filter.
            limit: Maximum number of tests to return.
            offset: Offset for pagination.

        Returns:
            Tuple of (list of tests, total count).
        """
        # For now, use memory storage for listing
        # In production, would need Valkey SCAN or secondary index
        all_tests = list(self._tests.values())

        if status:
            all_tests = [t for t in all_tests if t.status == status]

        # Sort by created_at descending
        all_tests.sort(key=lambda t: t.created_at, reverse=True)

        total = len(all_tests)
        paginated = all_tests[offset : offset + limit]

        return paginated, total

    async def update_test_status(
        self, test_id: str, new_status: ABTestStatus
    ) -> ABTestStatusResponse:
        """Update AB test status.

        Args:
            test_id: Test ID.
            new_status: New status.

        Returns:
            ABTestStatusResponse.

        Raises:
            ABTestNotFoundError: If test not found.
        """
        test = await self.get_test(test_id)
        old_status = test.status

        test.status = new_status
        test.updated_at = datetime.now()

        await self._store_test(test)

        self.logger.info(
            f"Updated AB test {test_id} status: {old_status.value} -> {new_status.value}"
        )

        return ABTestStatusResponse(
            test_id=test_id,
            old_status=old_status,
            new_status=new_status,
            updated_at=test.updated_at,
        )

    async def delete_test(self, test_id: str) -> bool:
        """Delete an AB test.

        Args:
            test_id: Test ID.

        Returns:
            True if deleted successfully.

        Raises:
            ABTestNotFoundError: If test not found.
        """
        # Verify test exists
        await self.get_test(test_id)

        client = await self._get_valkey_client()

        if client:
            key = f"{AB_TEST_KEY_PREFIX}{test_id}"
            try:
                await client.delete(key)
            except Exception as e:
                self.logger.warning(f"Valkey delete failed: {e}")

        # Remove from memory
        if test_id in self._tests:
            del self._tests[test_id]

        self.logger.info(f"Deleted AB test: {test_id}")
        return True

    # ========================================
    # Variant Assignment
    # ========================================

    async def assign_variant(
        self, test_id: str, session_id: str
    ) -> tuple[ABTestAssignment, bool]:
        """Assign a variant to a session using weighted random selection.

        Args:
            test_id: Test ID.
            session_id: Session ID.

        Returns:
            Tuple of (ABTestAssignment, is_new).
        """
        # Check for existing assignment
        existing = await self.get_assignment(test_id, session_id)
        if existing:
            return existing, False

        # Get test configuration
        test = await self.get_test(test_id)

        # Weighted random selection
        variant = self._select_variant_weighted(test.variants)

        assignment = ABTestAssignment(
            test_id=test_id,
            session_id=session_id,
            variant_name=variant.name,
            prompt_version=variant.prompt_version,
            assigned_at=datetime.now(),
        )

        # Store assignment
        await self._store_assignment(test_id, session_id, assignment)

        self.logger.info(
            f"Assigned variant {variant.name} to session {session_id} for test {test_id}"
        )

        return assignment, True

    async def get_assignment(
        self, test_id: str, session_id: str
    ) -> ABTestAssignment | None:
        """Get existing assignment for a session.

        Args:
            test_id: Test ID.
            session_id: Session ID.

        Returns:
            ABTestAssignment if exists, None otherwise.
        """
        client = await self._get_valkey_client()

        if client:
            key = f"{AB_ASSIGNMENT_KEY_PREFIX}{test_id}:{session_id}"
            try:
                data = await client.get(key)
                if data:
                    return ABTestAssignment(**data)
            except Exception as e:
                self.logger.warning(f"Valkey get assignment failed: {e}")

        # Fallback to memory
        assignment_key = f"{test_id}:{session_id}"
        return self._assignments.get(assignment_key)

    # ========================================
    # Metrics Collection
    # ========================================

    async def collect_metric(
        self,
        test_id: str,
        session_id: str,
        value: float,
        metric_name: str = "quality_score",
    ) -> MetricDataPoint:
        """Collect a metric data point.

        Args:
            test_id: Test ID.
            session_id: Session ID.
            value: Metric value.
            metric_name: Metric name.

        Returns:
            Created MetricDataPoint.
        """
        # Get assignment to determine variant
        assignment = await self.get_assignment(test_id, session_id)
        if not assignment:
            raise ABTestServiceError(
                f"No assignment found for session {session_id} in test {test_id}"
            )

        data_point = MetricDataPoint(
            session_id=session_id,
            variant_name=assignment.variant_name,
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(),
        )

        # Store metric
        await self._store_metric(test_id, data_point)

        return data_point

    async def get_variant_metrics(
        self, test_id: str, metric_name: str = "quality_score"
    ) -> list[ABTestMetrics]:
        """Get aggregated metrics for each variant.

        Args:
            test_id: Test ID.
            metric_name: Metric name to aggregate.

        Returns:
            List of ABTestMetrics for each variant.
        """
        # Get all metrics for this test
        metrics_data = await self._get_metrics(test_id)

        # Filter by metric name and group by variant
        variant_values: dict[str, list[float]] = {}

        for data_point in metrics_data:
            if data_point.metric_name == metric_name:
                variant = data_point.variant_name
                if variant not in variant_values:
                    variant_values[variant] = []
                variant_values[variant].append(data_point.value)

        # Calculate statistics for each variant
        result = []
        for variant_name, values in variant_values.items():
            metrics = self._calculate_variant_metrics(variant_name, values)
            result.append(metrics)

        return result

    # ========================================
    # Statistical Analysis
    # ========================================

    def perform_t_test(
        self,
        group_a: list[float],
        group_b: list[float],
        significance_level: float = 0.05,
    ) -> TTestResult:
        """Perform independent two-sample t-test (Welch's t-test).

        Args:
            group_a: Values from group A.
            group_b: Values from group B.
            significance_level: Significance level (alpha).

        Returns:
            TTestResult with t-statistic, p-value, and degrees of freedom.
        """
        if len(group_a) < 2 or len(group_b) < 2:
            raise ABTestServiceError(
                "Both groups must have at least 2 samples for t-test"
            )

        # Welch's t-test (unequal variance)
        t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)

        # Handle NaN cases (identical data or zero variance)
        if math.isnan(t_stat):
            t_stat = 0.0
        if math.isnan(p_value):
            p_value = 1.0  # No significant difference if p-value is NaN

        # Calculate degrees of freedom for Welch's t-test
        n1, n2 = len(group_a), len(group_b)
        var1, var2 = self._variance(group_a), self._variance(group_b)

        dof: float
        if var1 == 0 and var2 == 0:
            # Both groups have zero variance
            dof = float(n1 + n2 - 2)
        else:
            numerator = (var1 / n1 + var2 / n2) ** 2
            denominator = ((var1 / n1) ** 2) / (n1 - 1) + ((var2 / n2) ** 2) / (n2 - 1)
            dof = numerator / denominator if denominator != 0 else float(n1 + n2 - 2)

        return TTestResult(
            t_statistic=float(t_stat),
            p_value=float(p_value),
            degrees_of_freedom=float(dof),
            is_significant=p_value < significance_level,
        )

    def calculate_cohens_d(
        self, group_a: list[float], group_b: list[float]
    ) -> EffectSize:
        """Calculate Cohen's d effect size.

        Args:
            group_a: Values from group A.
            group_b: Values from group B.

        Returns:
            EffectSize with Cohen's d and interpretation.
        """
        if len(group_a) < 2 or len(group_b) < 2:
            raise ABTestServiceError(
                "Both groups must have at least 2 samples for effect size calculation"
            )

        mean_a, mean_b = self._mean(group_a), self._mean(group_b)
        std_a, std_b = self._std(group_a), self._std(group_b)
        n_a, n_b = len(group_a), len(group_b)

        # Pooled standard deviation
        if std_a == 0 and std_b == 0:
            pooled_std = 0.0
        else:
            pooled_std = math.sqrt(
                ((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2)
            )

        # Cohen's d
        if pooled_std == 0:
            cohens_d = 0.0 if mean_a == mean_b else float("inf")
        else:
            cohens_d = (mean_b - mean_a) / pooled_std

        interpretation = self.interpret_effect_size(cohens_d)

        return EffectSize(cohens_d=cohens_d, interpretation=interpretation)

    def interpret_effect_size(self, cohens_d: float) -> EffectSizeInterpretation:
        """Interpret effect size based on Cohen's guidelines.

        Args:
            cohens_d: Cohen's d value.

        Returns:
            EffectSizeInterpretation.
        """
        abs_d = abs(cohens_d)

        if abs_d < 0.2:
            return EffectSizeInterpretation.NEGLIGIBLE
        elif abs_d < 0.5:
            return EffectSizeInterpretation.SMALL
        elif abs_d < 0.8:
            return EffectSizeInterpretation.MEDIUM
        else:
            return EffectSizeInterpretation.LARGE

    async def generate_report(
        self, test_id: str, request: ABTestReportRequest
    ) -> ABTestReport:
        """Generate a comprehensive AB test report.

        Args:
            test_id: Test ID.
            request: Report request parameters.

        Returns:
            ABTestReport with metrics and statistical analysis.
        """
        test = await self.get_test(test_id)
        metrics = await self.get_variant_metrics(test_id, request.metric_name)

        warnings: list[str] = []
        t_test_result = None
        effect_size = None
        winner = None
        recommendation = ""

        # Check sample sizes
        for m in metrics:
            if m.sample_size < request.minimum_sample_size:
                warnings.append(
                    f"Variant '{m.variant_name}' has {m.sample_size} samples, "
                    f"below recommended minimum of {request.minimum_sample_size}"
                )

        # Perform statistical analysis if we have 2 variants
        if len(metrics) == 2:
            # Get raw data for statistical tests
            variant_data = await self._get_variant_data(test_id, request.metric_name)

            if len(variant_data) == 2:
                variant_names = list(variant_data.keys())
                group_a = variant_data[variant_names[0]]
                group_b = variant_data[variant_names[1]]

                if len(group_a) >= 2 and len(group_b) >= 2:
                    try:
                        t_test_result = self.perform_t_test(
                            group_a, group_b, request.significance_level
                        )
                        effect_size = self.calculate_cohens_d(group_a, group_b)

                        # Determine winner
                        if t_test_result.is_significant:
                            mean_a = self._mean(group_a)
                            mean_b = self._mean(group_b)
                            winner = (
                                variant_names[1]
                                if mean_b > mean_a
                                else variant_names[0]
                            )
                            recommendation = (
                                f"Variant '{winner}' shows statistically significant "
                                f"improvement (p={t_test_result.p_value:.4f}, "
                                f"Cohen's d={effect_size.cohens_d:.2f} - {effect_size.interpretation.value})."
                            )
                        else:
                            recommendation = (
                                f"No statistically significant difference detected "
                                f"(p={t_test_result.p_value:.4f}). "
                                "Consider collecting more data."
                            )
                    except ABTestServiceError as e:
                        warnings.append(str(e))
                else:
                    warnings.append("Insufficient data for statistical analysis")
        elif len(metrics) > 2:
            warnings.append(
                "Statistical comparison currently supports only 2 variants. "
                "Report shows metrics only."
            )
        else:
            warnings.append("Not enough variants with data for comparison")

        return ABTestReport(
            test_id=test_id,
            test_name=test.name,
            metrics=metrics,
            t_test_result=t_test_result,
            effect_size=effect_size,
            winner=winner,
            recommendation=recommendation,
            generated_at=datetime.now(),
            warning_messages=warnings,
        )

    # ========================================
    # Private Helper Methods
    # ========================================

    def _normalize_variant_weights(
        self, variants: list[ABTestVariant]
    ) -> list[ABTestVariant]:
        """Normalize variant weights to sum to 1.0.

        Args:
            variants: List of variants.

        Returns:
            List of variants with normalized weights.
        """
        total_weight = sum(v.weight for v in variants)

        if total_weight == 0:
            # Equal weights if all are zero
            equal_weight = 1.0 / len(variants)
            return [
                ABTestVariant(
                    name=v.name,
                    prompt_version=v.prompt_version,
                    weight=equal_weight,
                    description=v.description,
                    metadata=v.metadata,
                )
                for v in variants
            ]

        return [
            ABTestVariant(
                name=v.name,
                prompt_version=v.prompt_version,
                weight=v.weight / total_weight,
                description=v.description,
                metadata=v.metadata,
            )
            for v in variants
        ]

    def _select_variant_weighted(self, variants: list[ABTestVariant]) -> ABTestVariant:
        """Select a variant using weighted random choice.

        Args:
            variants: List of variants with normalized weights.

        Returns:
            Selected variant.
        """
        weights = [v.weight for v in variants]
        selected = random.choices(variants, weights=weights, k=1)[0]  # noqa: S311
        return selected

    def _calculate_variant_metrics(
        self, variant_name: str, values: list[float]
    ) -> ABTestMetrics:
        """Calculate metrics for a variant.

        Args:
            variant_name: Variant name.
            values: List of metric values.

        Returns:
            ABTestMetrics.
        """
        n = len(values)

        if n == 0:
            return ABTestMetrics(
                variant_name=variant_name,
                sample_size=0,
                mean=0.0,
                std=0.0,
                min_value=None,
                max_value=None,
                confidence_interval_lower=None,
                confidence_interval_upper=None,
            )

        mean = self._mean(values)
        std = self._std(values) if n > 1 else 0.0

        # 95% confidence interval
        ci_lower = None
        ci_upper = None
        if n > 1 and std > 0:
            se = std / math.sqrt(n)
            t_critical = stats.t.ppf(0.975, n - 1)
            ci_lower = mean - t_critical * se
            ci_upper = mean + t_critical * se

        return ABTestMetrics(
            variant_name=variant_name,
            sample_size=n,
            mean=mean,
            std=std,
            min_value=min(values),
            max_value=max(values),
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
        )

    def _mean(self, values: list[float]) -> float:
        """Calculate mean."""
        return sum(values) / len(values) if values else 0.0

    def _std(self, values: list[float]) -> float:
        """Calculate sample standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = self._mean(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    def _variance(self, values: list[float]) -> float:
        """Calculate sample variance."""
        if len(values) < 2:
            return 0.0
        mean = self._mean(values)
        return sum((x - mean) ** 2 for x in values) / (len(values) - 1)

    async def _store_test(self, test: ABTestConfig) -> None:
        """Store AB test in Valkey and memory."""
        # Always store in memory for listing
        self._tests[test.id] = test

        client = await self._get_valkey_client()
        if client:
            key = f"{AB_TEST_KEY_PREFIX}{test.id}"
            data = test.model_dump(mode="json")
            try:
                await client.set(key, data, ttl=AB_TEST_TTL)
            except Exception as e:
                self.logger.warning(f"Valkey store test failed: {e}")

    def _parse_test_config(self, data: dict[str, Any]) -> ABTestConfig:
        """Parse test config from stored data."""
        # Convert string dates back to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return ABTestConfig(**data)

    async def _store_assignment(
        self, test_id: str, session_id: str, assignment: ABTestAssignment
    ) -> None:
        """Store assignment in Valkey and memory."""
        assignment_key = f"{test_id}:{session_id}"
        self._assignments[assignment_key] = assignment

        client = await self._get_valkey_client()
        if client:
            key = f"{AB_ASSIGNMENT_KEY_PREFIX}{assignment_key}"
            data = assignment.model_dump(mode="json")
            try:
                await client.set(key, data, ttl=AB_ASSIGNMENT_TTL)
            except Exception as e:
                self.logger.warning(f"Valkey store assignment failed: {e}")

    async def _store_metric(self, test_id: str, data_point: MetricDataPoint) -> None:
        """Store metric in memory (and optionally Valkey)."""
        if test_id not in self._metrics:
            self._metrics[test_id] = []
        self._metrics[test_id].append(data_point)

    async def _get_metrics(self, test_id: str) -> list[MetricDataPoint]:
        """Get all metrics for a test."""
        return self._metrics.get(test_id, [])

    async def _get_variant_data(
        self, test_id: str, metric_name: str
    ) -> dict[str, list[float]]:
        """Get raw data grouped by variant."""
        metrics_data = await self._get_metrics(test_id)
        variant_data: dict[str, list[float]] = {}

        for data_point in metrics_data:
            if data_point.metric_name == metric_name:
                if data_point.variant_name not in variant_data:
                    variant_data[data_point.variant_name] = []
                variant_data[data_point.variant_name].append(data_point.value)

        return variant_data


# Singleton instance factory
def create_ab_test_service(
    valkey_host: str = "localhost",
    valkey_port: int = 6379,
    valkey_db: int = 0,
    use_valkey: bool = True,
) -> ABTestService:
    """Create ABTestService instance.

    Args:
        valkey_host: Valkey server host.
        valkey_port: Valkey server port.
        valkey_db: Valkey database number.
        use_valkey: Whether to use Valkey for persistence.

    Returns:
        ABTestService instance.
    """
    return ABTestService(
        valkey_host=valkey_host,
        valkey_port=valkey_port,
        valkey_db=valkey_db,
        use_valkey=use_valkey,
    )
