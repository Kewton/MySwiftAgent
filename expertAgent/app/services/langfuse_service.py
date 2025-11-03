"""Langfuse統合サービス - LLM Observabilityの中核.

このモジュールはLangfuse Self-hosted環境との統合を提供します。
トレーシング、フィードバック収集、CallbackHandler生成を統合管理します。

Issue #113: Langfuse Self-hosted構築 + expertAgentトレーシング統合
"""

import logging
from typing import Any

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from core.config import settings
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)


class LangfuseService:
    """Langfuse統合を管理するシングルトンサービス.

    Self-hosted Langfuse環境へのトレーシング送信、フィードバック管理を提供します。
    シングルトンパターンでアプリケーション全体で1つのクライアントを共有します。

    Attributes:
        _instance: シングルトンインスタンス
        _client: Langfuseクライアント
    """

    _instance: "LangfuseService | None" = None
    _client: Langfuse | None = None

    def __new__(cls) -> "LangfuseService":
        """シングルトンインスタンス取得."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Langfuseクライアント初期化."""
        if self._client is None and self._is_enabled():
            self._initialize_client()

    def _is_enabled(self) -> bool:
        """Langfuse統合が有効かチェック.

        Returns:
            APIキーが設定されている場合True（myVault or 環境変数）
        """
        try:
            # myVault優先でAPIキーを取得
            public_key = secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
            secret_key = secrets_manager.get_secret("LANGFUSE_SECRET_KEY")
            return bool(public_key and secret_key)
        except ValueError:
            # myVaultでも環境変数でもAPIキーが見つからない
            return False

    def _initialize_client(self) -> None:
        """Langfuse クライアント初期化（Self-hosted対応）.

        myVault優先でAPIキーを取得し、環境変数にフォールバックします。
        """
        try:
            # myVault優先でAPIキーを取得
            public_key = secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
            secret_key = secrets_manager.get_secret("LANGFUSE_SECRET_KEY")

            self._client = Langfuse(
                secret_key=secret_key,
                public_key=public_key,
                host=settings.LANGFUSE_HOST,  # Self-hosted URL
            )
            logger.info(
                f"Langfuse client initialized successfully (host: {settings.LANGFUSE_HOST})"
            )
        except ValueError as e:
            logger.error(f"Failed to get Langfuse API keys: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse: {e}")
            self._client = None

    def get_callback_handler(
        self,
        trace_name: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CallbackHandler | None:
        """LangChain/LangGraph用のCallbackHandlerを取得.

        Note:
            Langfuse v3では、CallbackHandlerは引数なしで作成します。
            trace_name, user_id, session_id等のパラメータは将来の拡張用に保持していますが、
            現在は使用されません。トレースIDは handler.last_trace_id から取得できます。

        Args:
            trace_name: トレース名（将来の拡張用、現在は未使用）
            user_id: ユーザーID（将来の拡張用、現在は未使用）
            session_id: セッションID（将来の拡張用、現在は未使用）
            tags: タグリスト（将来の拡張用、現在は未使用）
            metadata: メタデータ（将来の拡張用、現在は未使用）

        Returns:
            CallbackHandler or None（Langfuse無効時）

        Example:
            >>> handler = langfuse_service.get_callback_handler()
            >>> agent.invoke({"input": "Hello"}, config={"callbacks": [handler]})
            >>> trace_id = handler.last_trace_id if hasattr(handler, 'last_trace_id') else None
        """
        if not self._is_enabled() or self._client is None:
            return None

        try:
            # Langfuse v3: CallbackHandler は引数なしで作成
            handler = CallbackHandler()
            logger.debug("CallbackHandler created successfully")
            return handler
        except Exception as e:
            logger.error(f"Failed to create CallbackHandler: {e}")
            return None

    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> bool:
        """トレースにスコアを追加（フィードバック）.

        Args:
            trace_id: トレースID
            name: スコア名（例: "user_rating", "accuracy", "helpfulness"）
            value: スコア値（0.0 - 1.0）
            comment: コメント（任意）

        Returns:
            成功したかどうか

        Example:
            >>> langfuse_service.score_trace(
            ...     trace_id="trace-abc123",
            ...     name="user_rating",
            ...     value=0.9,
            ...     comment="Very helpful response"
            ... )
            True
        """
        if not self._is_enabled() or self._client is None:
            logger.warning("Langfuse is not enabled, skipping score")
            return False

        try:
            # Langfuse v3 API: score() メソッドを使用
            # Note: Langfuse SDKのバージョンにより署名が異なる可能性あり
            self._client.score(  # type: ignore[attr-defined]
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
            logger.info(f"Score added to trace {trace_id}: {name}={value}")
            return True
        except Exception as e:
            logger.error(f"Failed to add score to trace {trace_id}: {e}")
            return False

    def flush(self) -> None:
        """保留中のトレースをLangfuseに送信.

        非同期トレーシングのため、内部バッファに保留されているトレースを
        強制的にLangfuseサーバーに送信します。

        Note:
            通常は自動的にフラッシュされますが、アプリケーション終了時や
            テスト終了時に明示的に呼び出すことを推奨します。
        """
        if self._client:
            try:
                self._client.flush()
                logger.debug("Langfuse traces flushed successfully")
            except Exception as e:
                logger.error(f"Failed to flush Langfuse traces: {e}")

    def shutdown(self) -> None:
        """Langfuseクライアントのシャットダウン.

        保留中のトレースをすべて送信し、クライアントを終了します。
        アプリケーション終了時に呼び出してください。
        """
        if self._client:
            try:
                self.flush()
                logger.info("Langfuse client shutdown successfully")
            except Exception as e:
                logger.error(f"Error during Langfuse shutdown: {e}")


# シングルトンインスタンス
langfuse_service = LangfuseService()
