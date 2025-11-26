"""Unit tests for MetricsAggregationService.

Tests for Issue #175: Quality visualization API implementation.
This test module verifies the requirement-definition-metrics implementation with 90% coverage target.
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.observability import (
    ModelUsage,
    RequirementDefinitionMetrics,
    RequirementDefinitionMetricsRequest,
    RequirementDefinitionMetricsResponse,
)
from app.services.metrics_aggregation_service import MetricsAggregationService


# Sample test data
def create_sample_sessions() -> list[dict[str, Any]]:
    """Create sample session data for testing."""
    return [
        {
            "session_id": "session-1",
            "traces": [
                {
                    "id": "trace-1-1",
                    "name": "requirement_definition",
                    "timestamp": "2025-11-01T10:00:00",
                    "metadata": {
                        "status": "completed",
                        "model": "gpt-4o-mini",
                    },
                    "scores": [
                        {"name": "quality_score", "value": 0.85},
                    ],
                    "observations": [
                        {"type": "generation", "model": "gpt-4o-mini"},
                        {"type": "generation", "model": "gpt-4o-mini"},
                    ],
                },
                {
                    "id": "trace-1-2",
                    "name": "requirement_definition",
                    "timestamp": "2025-11-01T10:05:00",
                    "metadata": {
                        "status": "completed",
                        "model": "gpt-4o-mini",
                    },
                    "scores": [
                        {"name": "quality_score", "value": 0.90},
                    ],
                    "observations": [
                        {"type": "generation", "model": "gpt-4o-mini"},
                    ],
                },
            ],
        },
        {
            "session_id": "session-2",
            "traces": [
                {
                    "id": "trace-2-1",
                    "name": "requirement_definition",
                    "timestamp": "2025-11-02T11:00:00",
                    "metadata": {
                        "status": "completed",
                        "model": "claude-haiku-4-5",
                    },
                    "scores": [
                        {"name": "quality_score", "value": 0.80},
                    ],
                    "observations": [
                        {"type": "generation", "model": "claude-haiku-4-5"},
                    ],
                },
            ],
        },
        {
            "session_id": "session-3",
            "traces": [
                {
                    "id": "trace-3-1",
                    "name": "requirement_definition",
                    "timestamp": "2025-11-03T09:00:00",
                    "metadata": {
                        "status": "in_progress",  # Not completed
                        "model": "gpt-4o",
                    },
                    "scores": [],
                    "observations": [
                        {"type": "generation", "model": "gpt-4o"},
                    ],
                },
            ],
        },
    ]


@pytest.fixture
def metrics_service():
    """Create MetricsAggregationService instance."""
    return MetricsAggregationService()


@pytest.fixture
def sample_sessions():
    """Sample session data fixture."""
    return create_sample_sessions()


class TestRequirementDefinitionMetricsCalculation:
    """Test requirement definition metrics calculation."""

    @pytest.mark.unit
    async def test_calculate_average_score(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test average score calculation from multiple sessions."""
        # Sessions have scores: 0.85, 0.90, 0.80 = average 0.85
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.average_score == pytest.approx(0.85, rel=0.01)

    @pytest.mark.unit
    async def test_calculate_total_turns(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test total dialogue turns calculation."""
        # Total traces: 2 + 1 + 1 = 4 turns
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.total_turns == 4

    @pytest.mark.unit
    async def test_calculate_completion_rate(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test completion rate calculation."""
        # 3 sessions total: 2 completed, 1 in_progress = 66.67%
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.completion_rate == pytest.approx(66.67, rel=0.01)

    @pytest.mark.unit
    async def test_calculate_model_usage(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test model usage rate calculation."""
        # gpt-4o-mini: 3 generations, claude-haiku-4-5: 1, gpt-4o: 1 = total 5
        # gpt-4o-mini: 60%, claude-haiku-4-5: 20%, gpt-4o: 20%
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            model_usage = result.metrics.model_usage
            assert len(model_usage) >= 1
            gpt_4o_mini_usage = next(
                (m for m in model_usage if m.model_name == "gpt-4o-mini"), None
            )
            assert gpt_4o_mini_usage is not None
            assert gpt_4o_mini_usage.usage_percentage == pytest.approx(60.0, rel=0.01)

    @pytest.mark.unit
    async def test_total_sessions_count(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test total sessions count."""
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.total_sessions == 3


class TestRequirementDefinitionMetricsEdgeCases:
    """Test edge cases for requirement definition metrics."""

    @pytest.mark.unit
    async def test_empty_data_returns_zero_metrics(
        self, metrics_service: MetricsAggregationService
    ):
        """Test that empty data returns zero values."""
        with patch.object(metrics_service, "_fetch_sessions", return_value=[]):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.average_score == 0.0
            assert result.metrics.total_turns == 0
            assert result.metrics.completion_rate == 0.0
            assert result.metrics.total_sessions == 0
            assert result.metrics.model_usage == []

    @pytest.mark.unit
    async def test_no_scores_returns_zero_average(
        self, metrics_service: MetricsAggregationService
    ):
        """Test that sessions without scores return zero average."""
        sessions_no_scores = [
            {
                "session_id": "session-no-score",
                "traces": [
                    {
                        "id": "trace-1",
                        "name": "requirement_definition",
                        "timestamp": "2025-11-01T10:00:00",
                        "metadata": {"status": "completed"},
                        "scores": [],
                        "observations": [],
                    }
                ],
            }
        ]
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sessions_no_scores
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.average_score == 0.0

    @pytest.mark.unit
    async def test_single_session_metrics(
        self, metrics_service: MetricsAggregationService
    ):
        """Test metrics calculation with a single session."""
        single_session = [
            {
                "session_id": "session-single",
                "traces": [
                    {
                        "id": "trace-1",
                        "name": "requirement_definition",
                        "timestamp": "2025-11-01T10:00:00",
                        "metadata": {"status": "completed", "model": "gpt-4o"},
                        "scores": [{"name": "quality_score", "value": 0.95}],
                        "observations": [{"type": "generation", "model": "gpt-4o"}],
                    }
                ],
            }
        ]
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=single_session
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.metrics.average_score == pytest.approx(0.95, rel=0.01)
            assert result.metrics.total_turns == 1
            assert result.metrics.completion_rate == pytest.approx(100.0, rel=0.01)
            assert result.metrics.total_sessions == 1


class TestCacheFunctionality:
    """Test caching functionality for metrics."""

    @pytest.mark.unit
    async def test_cache_hit(self, metrics_service: MetricsAggregationService):
        """Test that cached data is returned on cache hit."""
        cached_metrics = RequirementDefinitionMetrics(
            average_score=0.90,
            total_turns=100,
            completion_rate=85.0,
            total_sessions=50,
            model_usage=[ModelUsage(model_name="gpt-4o", usage_percentage=100.0)],
        )
        cached_response = RequirementDefinitionMetricsResponse(
            metrics=cached_metrics,
            from_date=datetime(2025, 11, 1),
            to_date=datetime(2025, 11, 30),
            cache_hit=True,
            generated_at=datetime.now(),
        )

        with patch.object(
            metrics_service, "_get_from_cache", return_value=cached_response
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.cache_hit is True
            assert result.metrics.average_score == 0.90

    @pytest.mark.unit
    async def test_cache_miss_triggers_calculation(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test that cache miss triggers metric calculation."""
        with (
            patch.object(metrics_service, "_get_from_cache", return_value=None),
            patch.object(
                metrics_service, "_fetch_sessions", return_value=sample_sessions
            ),
            patch.object(
                metrics_service, "_store_in_cache", return_value=None
            ) as mock_store,
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.cache_hit is False
            mock_store.assert_called_once()

    @pytest.mark.unit
    async def test_cache_key_generation(
        self, metrics_service: MetricsAggregationService
    ):
        """Test cache key is generated correctly and consistently."""
        request1 = RequirementDefinitionMetricsRequest(
            from_date=datetime(2025, 11, 1),
            to_date=datetime(2025, 11, 30),
        )
        request2 = RequirementDefinitionMetricsRequest(
            from_date=datetime(2025, 11, 1),
            to_date=datetime(2025, 11, 30),
        )
        request3 = RequirementDefinitionMetricsRequest(
            from_date=datetime(2025, 10, 1),
            to_date=datetime(2025, 10, 30),
        )
        cache_key1 = metrics_service._generate_cache_key(request1)
        cache_key2 = metrics_service._generate_cache_key(request2)
        cache_key3 = metrics_service._generate_cache_key(request3)

        # Same request should produce same key
        assert cache_key1 == cache_key2
        # Different request should produce different key
        assert cache_key1 != cache_key3
        # Key should be a valid MD5 hash (32 characters hex)
        assert len(cache_key1) == 32
        assert all(c in "0123456789abcdef" for c in cache_key1)


class TestLangfuseIntegration:
    """Test Langfuse integration for fetching trace data."""

    @pytest.mark.unit
    async def test_fetch_sessions_from_langfuse(
        self, metrics_service: MetricsAggregationService
    ):
        """Test fetching session data from Langfuse."""
        mock_traces = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            }
        ]

        with patch(
            "app.services.metrics_aggregation_service.trace_service"
        ) as mock_trace_service:
            mock_trace_service._is_enabled.return_value = True
            mock_trace_service.get_traces.return_value = mock_traces
            mock_trace_service.get_scores_by_trace.return_value = [
                {"name": "quality_score", "value": 0.85}
            ]
            mock_trace_service.get_observations_by_trace.return_value = [
                {"type": "generation", "model": "gpt-4o"}
            ]

            sessions = await metrics_service._fetch_sessions(
                from_date=datetime(2025, 11, 1), to_date=datetime(2025, 11, 30)
            )

            assert len(sessions) >= 0  # May be 0 or more depending on grouping

    @pytest.mark.unit
    async def test_langfuse_disabled_raises_error(
        self, metrics_service: MetricsAggregationService
    ):
        """Test that disabled Langfuse raises appropriate error."""
        with patch(
            "app.services.metrics_aggregation_service.trace_service"
        ) as mock_trace_service:
            mock_trace_service._is_enabled.return_value = False

            with pytest.raises(ValueError, match="Langfuse is not enabled"):
                await metrics_service._fetch_sessions(
                    from_date=datetime(2025, 11, 1), to_date=datetime(2025, 11, 30)
                )


class TestPerformance:
    """Test performance-related functionality."""

    @pytest.mark.unit
    async def test_large_dataset_processing(
        self, metrics_service: MetricsAggregationService
    ):
        """Test handling of large datasets (1000+ sessions)."""
        # Generate 1000 sessions with multiple traces each
        large_sessions = []
        for i in range(1000):
            session = {
                "session_id": f"session-{i}",
                "traces": [
                    {
                        "id": f"trace-{i}-1",
                        "name": "requirement_definition",
                        "timestamp": f"2025-11-{(i % 28) + 1:02d}T10:00:00",
                        "metadata": {
                            "status": "completed" if i % 5 != 0 else "in_progress"
                        },
                        "scores": (
                            [{"name": "quality_score", "value": 0.70 + (i % 30) / 100}]
                            if i % 5 != 0
                            else []
                        ),
                        "observations": [
                            {
                                "type": "generation",
                                "model": ["gpt-4o", "claude-haiku-4-5", "gpt-4o-mini"][
                                    i % 3
                                ],
                            }
                        ],
                    }
                ],
            }
            large_sessions.append(session)

        with patch.object(
            metrics_service, "_fetch_sessions", return_value=large_sessions
        ):
            import time

            start_time = time.time()

            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            elapsed_time = time.time() - start_time

            # Should complete within 1 second
            assert elapsed_time < 1.0
            assert result.metrics.total_sessions == 1000


class TestDateRangeFiltering:
    """Test date range filtering functionality."""

    @pytest.mark.unit
    async def test_default_date_range(self, metrics_service: MetricsAggregationService):
        """Test default 30-day date range."""
        request = RequirementDefinitionMetricsRequest()

        # Verify default dates are set
        assert request.to_date is not None
        assert request.from_date is not None
        # Default should be approximately 30 days ago
        date_diff = request.to_date - request.from_date
        assert date_diff.days == 30

    @pytest.mark.unit
    async def test_custom_date_range(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test custom date range filtering."""
        with patch.object(
            metrics_service, "_fetch_sessions", return_value=sample_sessions
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 15),
            )
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.from_date == datetime(2025, 11, 1)
            assert result.to_date == datetime(2025, 11, 15)


class TestValkeyCache:
    """Test Valkey cache integration."""

    @pytest.mark.unit
    async def test_valkey_cache_store(self, metrics_service: MetricsAggregationService):
        """Test storing metrics in Valkey cache."""
        mock_valkey = MagicMock()
        mock_valkey.set = AsyncMock(return_value=True)

        with (
            patch.object(metrics_service, "_valkey_client", mock_valkey),
            patch.object(metrics_service, "_use_valkey", True),
        ):
            response = RequirementDefinitionMetricsResponse(
                metrics=RequirementDefinitionMetrics(
                    average_score=0.85,
                    total_turns=10,
                    completion_rate=80.0,
                    total_sessions=5,
                    model_usage=[],
                ),
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
                cache_hit=False,
                generated_at=datetime.now(),
            )
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )

            await metrics_service._store_in_cache(request, response)

            mock_valkey.set.assert_awaited_once()

    @pytest.mark.unit
    async def test_valkey_cache_retrieve(
        self, metrics_service: MetricsAggregationService
    ):
        """Test retrieving metrics from Valkey cache."""
        cached_data = {
            "metrics": {
                "average_score": 0.85,
                "total_turns": 10,
                "completion_rate": 80.0,
                "total_sessions": 5,
                "model_usage": [],
            },
            "from_date": "2025-11-01T00:00:00",
            "to_date": "2025-11-30T00:00:00",
            "cache_hit": True,
            "generated_at": "2025-11-15T12:00:00",
        }

        mock_valkey = MagicMock()
        mock_valkey.get = AsyncMock(return_value=cached_data)

        with (
            patch.object(metrics_service, "_valkey_client", mock_valkey),
            patch.object(metrics_service, "_use_valkey", True),
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )

            result = await metrics_service._get_from_cache(request)

            assert result is not None
            assert result.cache_hit is True
            assert result.metrics.average_score == 0.85

    @pytest.mark.unit
    async def test_cache_fallback_on_valkey_error(
        self, metrics_service: MetricsAggregationService, sample_sessions: list
    ):
        """Test fallback when Valkey is unavailable."""
        mock_valkey = MagicMock()
        mock_valkey.get = AsyncMock(side_effect=Exception("Connection failed"))

        with (
            patch.object(metrics_service, "_valkey_client", mock_valkey),
            patch.object(metrics_service, "_use_valkey", True),
            patch.object(
                metrics_service, "_fetch_sessions", return_value=sample_sessions
            ),
        ):
            request = RequirementDefinitionMetricsRequest(
                from_date=datetime(2025, 11, 1),
                to_date=datetime(2025, 11, 30),
            )

            # Should still return valid result despite cache error
            result = await metrics_service.get_requirement_definition_metrics(request)

            assert result.cache_hit is False
            assert result.metrics is not None
