"""Metrics aggregation service for requirement definition quality visualization.

Issue #175: Quality visualization API implementation.
Provides aggregated metrics for requirement definition conversations including:
- Average quality scores
- Dialogue turn counts
- Completion rates
- Model usage statistics
"""

import hashlib
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.schemas.observability import (
    ModelUsage,
    RequirementDefinitionMetrics,
    RequirementDefinitionMetricsRequest,
    RequirementDefinitionMetricsResponse,
)
from app.services.trace_service import trace_service
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError
from core.config import settings

from .base import BaseService
from .response_builder import ResponseBuilder

logger = logging.getLogger(__name__)

# Cache TTL: 5 minutes
CACHE_TTL_SECONDS = 300


class MetricsAggregationService(BaseService):
    """Service for aggregating requirement definition metrics."""

    def __init__(self) -> None:
        """Initialize MetricsAggregationService."""
        super().__init__(logger=logger, response_builder=ResponseBuilder())
        self._use_valkey = settings.VALKEY_ENABLED
        self._valkey_client: ValkeyClient | None = None

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
                    host=settings.VALKEY_HOST,
                    port=settings.VALKEY_PORT,
                    db=settings.VALKEY_DB,
                )
                await self._valkey_client.connect()
            except ValkeyConnectionError as e:
                self.logger.warning(f"Failed to connect to Valkey: {e}")
                self._valkey_client = None

        return self._valkey_client

    async def get_requirement_definition_metrics(
        self, request: RequirementDefinitionMetricsRequest
    ) -> RequirementDefinitionMetricsResponse:
        """Get aggregated metrics for requirement definition conversations.

        Args:
            request: Request with date range parameters.

        Returns:
            RequirementDefinitionMetricsResponse: Aggregated metrics.
        """
        # Try to get from cache first
        try:
            cached_response = await self._get_from_cache(request)
            if cached_response is not None:
                return cached_response
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {e}")

        # Fetch data and calculate metrics
        try:
            sessions = await self._fetch_sessions(
                from_date=request.from_date, to_date=request.to_date
            )
        except ValueError:
            # Langfuse not enabled - return empty metrics
            sessions = []

        metrics = self._calculate_metrics(sessions)

        response = RequirementDefinitionMetricsResponse(
            metrics=metrics,
            from_date=request.from_date,
            to_date=request.to_date,
            cache_hit=False,
            generated_at=datetime.now(),
        )

        # Store in cache (fire and forget)
        try:
            await self._store_in_cache(request, response)
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {e}")

        return response

    def _generate_cache_key(self, request: RequirementDefinitionMetricsRequest) -> str:
        """Generate cache key from request parameters.

        Args:
            request: Request parameters.

        Returns:
            Cache key string.
        """
        key_data = f"requirement_definition_metrics:{request.from_date.strftime('%Y-%m-%d')}:{request.to_date.strftime('%Y-%m-%d')}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    async def _get_from_cache(
        self, request: RequirementDefinitionMetricsRequest
    ) -> RequirementDefinitionMetricsResponse | None:
        """Get metrics from Valkey cache.

        Args:
            request: Request parameters.

        Returns:
            Cached response or None if not found.
        """
        client = await self._get_valkey_client()
        if client is None:
            return None

        cache_key = self._generate_cache_key(request)
        try:
            cached_data = await client.get(cache_key)
            if cached_data is None:
                return None

            # Parse cached data
            return RequirementDefinitionMetricsResponse(
                metrics=RequirementDefinitionMetrics(**cached_data["metrics"]),
                from_date=datetime.fromisoformat(cached_data["from_date"]),
                to_date=datetime.fromisoformat(cached_data["to_date"]),
                cache_hit=True,
                generated_at=datetime.fromisoformat(cached_data["generated_at"]),
            )
        except Exception as e:
            self.logger.warning(f"Failed to parse cached data: {e}")
            return None

    async def _store_in_cache(
        self,
        request: RequirementDefinitionMetricsRequest,
        response: RequirementDefinitionMetricsResponse,
    ) -> None:
        """Store metrics in Valkey cache.

        Args:
            request: Request parameters (used for key generation).
            response: Response to cache.
        """
        client = await self._get_valkey_client()
        if client is None:
            return

        cache_key = self._generate_cache_key(request)
        cache_data = {
            "metrics": response.metrics.model_dump(),
            "from_date": response.from_date.isoformat(),
            "to_date": response.to_date.isoformat(),
            "generated_at": response.generated_at.isoformat(),
        }

        try:
            await client.set(cache_key, cache_data, ttl=CACHE_TTL_SECONDS)
        except Exception as e:
            self.logger.warning(f"Failed to store in cache: {e}")

    async def _fetch_sessions(
        self, from_date: datetime, to_date: datetime
    ) -> list[dict[str, Any]]:
        """Fetch session data from Langfuse.

        Args:
            from_date: Start date for filtering.
            to_date: End date for filtering.

        Returns:
            List of session data with traces.

        Raises:
            ValueError: If Langfuse is not enabled.
        """
        if not trace_service._is_enabled():
            raise ValueError("Langfuse is not enabled")

        # Fetch traces from Langfuse
        raw_traces = trace_service.get_traces(
            limit=10000,  # Large limit for metrics aggregation
            from_timestamp=from_date.isoformat(),
            to_timestamp=to_date.isoformat(),
            tags=["requirement_definition"],
        )

        if raw_traces is None:
            return []

        # Group traces by session
        sessions_map: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"session_id": "", "traces": []}
        )

        for raw_trace in raw_traces:
            session_id = raw_trace.get("sessionId", raw_trace.get("id", "unknown"))
            if not sessions_map[session_id]["session_id"]:
                sessions_map[session_id]["session_id"] = session_id

            # Fetch scores and observations for each trace
            trace_id = raw_trace.get("id", "")
            scores = trace_service.get_scores_by_trace(trace_id) or []
            observations = trace_service.get_observations_by_trace(trace_id) or []

            trace_data = {
                "id": trace_id,
                "name": raw_trace.get("name", ""),
                "timestamp": raw_trace.get("timestamp", ""),
                "metadata": raw_trace.get("metadata", {}),
                "scores": scores,
                "observations": observations,
            }
            sessions_map[session_id]["traces"].append(trace_data)

        return list(sessions_map.values())

    def _calculate_metrics(
        self, sessions: list[dict[str, Any]]
    ) -> RequirementDefinitionMetrics:
        """Calculate aggregated metrics from session data.

        Args:
            sessions: List of session data with traces.

        Returns:
            RequirementDefinitionMetrics: Calculated metrics.
        """
        if not sessions:
            return RequirementDefinitionMetrics(
                average_score=0.0,
                total_turns=0,
                completion_rate=0.0,
                total_sessions=0,
                model_usage=[],
            )

        # Collect all scores
        all_scores: list[float] = []
        total_turns = 0
        completed_sessions = 0
        model_counts: dict[str, int] = defaultdict(int)

        for session in sessions:
            traces = session.get("traces", [])
            total_turns += len(traces)

            # Check if session is completed (last trace has completed status)
            session_completed = False
            for trace in traces:
                # Collect scores
                scores = trace.get("scores", [])
                for score in scores:
                    if score.get("name") == "quality_score":
                        all_scores.append(score.get("value", 0.0))

                # Check completion status
                metadata = trace.get("metadata", {})
                if metadata.get("status") == "completed":
                    session_completed = True

                # Count model usage
                observations = trace.get("observations", [])
                for obs in observations:
                    if obs.get("type") == "generation":
                        model_name = obs.get("model", "unknown")
                        if model_name:
                            model_counts[model_name] += 1

            if session_completed:
                completed_sessions += 1

        # Calculate average score
        average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0

        # Calculate completion rate
        total_sessions = len(sessions)
        completion_rate = (
            (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
        )

        # Calculate model usage percentages
        total_model_usage = sum(model_counts.values())
        model_usage = []
        for model_name, count in model_counts.items():
            percentage = (
                (count / total_model_usage * 100) if total_model_usage > 0 else 0.0
            )
            model_usage.append(
                ModelUsage(
                    model_name=model_name,
                    usage_percentage=percentage,
                    usage_count=count,
                )
            )

        # Sort by usage percentage descending
        model_usage.sort(key=lambda x: x.usage_percentage, reverse=True)

        return RequirementDefinitionMetrics(
            average_score=average_score,
            total_turns=total_turns,
            completion_rate=completion_rate,
            total_sessions=total_sessions,
            model_usage=model_usage,
        )


# Singleton instance
metrics_aggregation_service = MetricsAggregationService()
