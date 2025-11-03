"""Trace retrieval service for Langfuse observability.

このモジュールはLangfuse APIからトレース情報を取得するサービスを提供します。
トレース一覧取得、詳細取得、UI URL生成などの機能を実装します。

Issue #113: Langfuse Self-hosted構築 + expertAgentトレーシング統合
"""

import logging
from typing import Any

import httpx

from core.config import settings
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)


class TraceService:
    """Langfuse APIからトレース情報を取得するサービス.

    Self-hosted Langfuse環境のREST APIを使用してトレース情報を取得します。
    フィードバック収集、ダッシュボード連携をサポートします。

    Attributes:
        _base_url: Langfuse Self-hosted URL
        _public_key: Langfuse Public Key (myVault or env)
        _secret_key: Langfuse Secret Key (myVault or env)
    """

    def __init__(self) -> None:
        """TraceService初期化（myVault対応）."""
        self._base_url = settings.LANGFUSE_HOST
        self._public_key: str | None = None
        self._secret_key: str | None = None
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        """APIキーをmyVault優先で初期化."""
        try:
            # myVault優先でAPIキーを取得
            self._public_key = secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
            self._secret_key = secrets_manager.get_secret("LANGFUSE_SECRET_KEY")
            logger.info(
                f"Langfuse API keys retrieved successfully (myVault: {secrets_manager.myvault_enabled})"
            )
        except ValueError:
            # myVaultでも環境変数でもAPIキーが見つからない
            logger.warning("Langfuse API keys not found in myVault or environment")
            self._public_key = None
            self._secret_key = None

    def _is_enabled(self) -> bool:
        """Langfuse統合が有効かチェック.

        Returns:
            APIキーが設定されている場合True（myVault or 環境変数）
        """
        return bool(self._public_key and self._secret_key and self._base_url)

    def get_trace_url(self, trace_id: str) -> str | None:
        """トレースIDからLangfuse UI URLを生成.

        Args:
            trace_id: トレースID

        Returns:
            Langfuse UI URL or None（Langfuse無効時）

        Example:
            >>> url = trace_service.get_trace_url("trace-abc123")
            >>> print(url)
            http://localhost:3001/project/expertAgent-traces/traces/trace-abc123
        """
        if not self._is_enabled():
            logger.warning("Langfuse is not enabled, cannot generate trace URL")
            return None

        # Langfuse v3 UI URL format
        # {base_url}/project/{project_name}/traces/{trace_id}
        project_name = "expertAgent-traces"  # 設定ファイルから取得することも可能
        return f"{self._base_url}/project/{project_name}/traces/{trace_id}"

    def get_traces(
        self,
        limit: int = 50,
        user_id: str | None = None,
        tags: list[str] | None = None,
        from_timestamp: str | None = None,
        to_timestamp: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """トレース一覧を取得.

        Args:
            limit: 取得件数上限（デフォルト: 50）
            user_id: ユーザーIDでフィルタ
            tags: タグリストでフィルタ
            from_timestamp: 開始日時（ISO 8601形式）
            to_timestamp: 終了日時（ISO 8601形式）

        Returns:
            トレース一覧 or None（Langfuse無効時またはエラー時）

        Example:
            >>> traces = trace_service.get_traces(
            ...     limit=10,
            ...     user_id="user123",
            ...     tags=["production", "chat"]
            ... )
            >>> for trace in traces:
            ...     print(trace["id"], trace["name"])
        """
        if not self._is_enabled():
            logger.warning("Langfuse is not enabled, cannot get traces")
            return None

        try:
            # Langfuse API endpoint: GET /api/public/traces
            url = f"{self._base_url}/api/public/traces"
            params: dict[str, Any] = {"limit": limit}

            if user_id:
                params["userId"] = user_id
            if tags:
                params["tags"] = ",".join(tags)
            if from_timestamp:
                params["fromTimestamp"] = from_timestamp
            if to_timestamp:
                params["toTimestamp"] = to_timestamp

            with httpx.Client() as client:
                response = client.get(
                    url,
                    params=params,
                    auth=(
                        self._public_key or "",
                        self._secret_key or "",
                    ),  # type: ignore[arg-type]
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                result: list[dict[str, Any]] = data.get("data", [])
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting traces: {e.response.status_code} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting traces: {e}")
            return None

    def get_trace_by_id(self, trace_id: str) -> dict[str, Any] | None:
        """トレースIDから詳細情報を取得.

        Args:
            trace_id: トレースID

        Returns:
            トレース詳細 or None（Langfuse無効時またはエラー時）

        Example:
            >>> trace = trace_service.get_trace_by_id("trace-abc123")
            >>> if trace:
            ...     print(trace["name"], trace["input"], trace["output"])
        """
        if not self._is_enabled():
            logger.warning("Langfuse is not enabled, cannot get trace")
            return None

        try:
            # Langfuse API endpoint: GET /api/public/traces/{traceId}
            url = f"{self._base_url}/api/public/traces/{trace_id}"

            with httpx.Client() as client:
                response = client.get(
                    url,
                    auth=(
                        self._public_key or "",
                        self._secret_key or "",
                    ),  # type: ignore[arg-type]
                    timeout=30.0,
                )
                response.raise_for_status()
                result: dict[str, Any] = response.json()
                return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Trace not found: {trace_id}")
            else:
                logger.error(
                    f"HTTP error getting trace: {e.response.status_code} - {e}"
                )
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting trace {trace_id}: {e}")
            return None

    def get_observations_by_trace(self, trace_id: str) -> list[dict[str, Any]] | None:
        """トレースIDから関連するObservation（span, generation等）を取得.

        Args:
            trace_id: トレースID

        Returns:
            Observation一覧 or None（Langfuse無効時またはエラー時）

        Example:
            >>> observations = trace_service.get_observations_by_trace("trace-abc123")
            >>> for obs in observations:
            ...     print(obs["type"], obs["name"], obs["startTime"])
        """
        if not self._is_enabled():
            logger.warning("Langfuse is not enabled, cannot get observations")
            return None

        try:
            # Langfuse API endpoint: GET /api/public/observations
            url = f"{self._base_url}/api/public/observations"
            params = {"traceId": trace_id}

            with httpx.Client() as client:
                response = client.get(
                    url,
                    params=params,
                    auth=(
                        self._public_key or "",
                        self._secret_key or "",
                    ),  # type: ignore[arg-type]
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                result: list[dict[str, Any]] = data.get("data", [])
                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error getting observations: {e.response.status_code} - {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error getting observations for trace {trace_id}: {e}"
            )
            return None

    def get_scores_by_trace(self, trace_id: str) -> list[dict[str, Any]] | None:
        """トレースIDから関連するスコア（フィードバック）を取得.

        Args:
            trace_id: トレースID

        Returns:
            スコア一覧 or None（Langfuse無効時またはエラー時）

        Example:
            >>> scores = trace_service.get_scores_by_trace("trace-abc123")
            >>> for score in scores:
            ...     print(score["name"], score["value"], score["comment"])
        """
        if not self._is_enabled():
            logger.warning("Langfuse is not enabled, cannot get scores")
            return None

        try:
            # Langfuse API endpoint: GET /api/public/scores
            url = f"{self._base_url}/api/public/scores"
            params = {"traceId": trace_id}

            with httpx.Client() as client:
                response = client.get(
                    url,
                    params=params,
                    auth=(
                        self._public_key or "",
                        self._secret_key or "",
                    ),  # type: ignore[arg-type]
                    timeout=30.0,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                result: list[dict[str, Any]] = data.get("data", [])
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting scores: {e.response.status_code} - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting scores for trace {trace_id}: {e}")
            return None


# シングルトンインスタンス
trace_service = TraceService()
