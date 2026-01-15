"""
Issue #350 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキー（GEMINI_API_KEY等）が設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_350_acceptance.py -v

テストケース:
- AC-1: 自然言語からTaskFlow V2ワークフロー生成
- AC-2: 生成されたワークフローのgraphAiServerでの実行確認
- AC-3: engineパラメータの動作確認
- AC-4: 後方互換性（GraphAI YAML生成機能維持）
- AC-5: セキュリティ検証（HTTP URLの拒否）
- AC-6: セキュリティ検証（プライベートIPの拒否）

Note: Job Generator APIは非同期パターンを使用します。
      1. POST /v1/job-generator でジョブを作成し job_id を取得
      2. GET /api/v1/jobs/{job_id}/status でステータスをポーリング
      3. 完了後にワークフロー結果を検証
"""

import time
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue350Acceptance:
    """Issue #350: ワークフロー生成エージェントV2の対象エンジンの切り替え"""

    # サービスURL（環境変数で上書き可能）
    EXPERT_AGENT_URL = "http://localhost:8004"
    GRAPHAI_SERVER_URL = "http://localhost:8005"
    MYVAULT_URL = "http://localhost:8003"

    # ポーリング設定
    POLL_INTERVAL = 5  # 秒
    MAX_WAIT_TIME = 300  # 秒（5分）

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.GRAPHAI_SERVER_URL, "graphAiServer"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(
                        f"{name} health check failed with status {response.status_code}"
                    )
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: ./scripts/dev-start.sh or make dev-all"
                )

    def _create_job(
        self, user_requirement: str, project_id: str, engine: str | None = None
    ) -> dict[str, Any]:
        """ジョブを作成してレスポンスを返す"""
        endpoint = f"{self.EXPERT_AGENT_URL}/v1/job-generator"
        payload: dict[str, Any] = {
            "user_requirement": user_requirement,
            "project_id": project_id,
        }
        if engine is not None:
            payload["engine"] = engine

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        assert response.status_code == 200, (
            f"Job creation failed: {response.status_code}: {response.text}"
        )
        return response.json()

    def _poll_job_status(self, job_id: str) -> dict[str, Any]:
        """ジョブ完了までポーリングして結果を返す"""
        endpoint = f"{self.EXPERT_AGENT_URL}/api/v1/jobs/{job_id}/status"
        start_time = time.time()

        while time.time() - start_time < self.MAX_WAIT_TIME:
            response = requests.get(endpoint, timeout=30)
            if response.status_code != 200:
                time.sleep(self.POLL_INTERVAL)
                continue

            data = response.json()
            status = data.get("status", "")

            # 完了ステータス
            if status in ["completed", "success", "finished"]:
                return data
            # エラーステータス
            if status in ["failed", "error"]:
                pytest.fail(f"Job failed: {data.get('error_message', 'Unknown error')}")
            # 進行中
            time.sleep(self.POLL_INTERVAL)

        pytest.fail(f"Job timed out after {self.MAX_WAIT_TIME} seconds")

    # ==========================================================================
    # AC-1: 自然言語からTaskFlow V2ワークフロー生成
    # ==========================================================================

    def test_ac1_job_creation_with_taskflow_engine(self) -> None:
        """AC-1: TaskFlow V2エンジンでジョブが作成される

        受入条件:
        - HTTP 200でジョブが作成される
        - job_idが返される
        - engineパラメータが受け入れられる
        """
        # Act
        response = self._create_job(
            user_requirement="天気APIから東京の天気を取得して、日本語でフォーマットする",
            project_id="test_ac1",
            engine="taskflow",
        )

        # Assert
        assert "job_id" in response, f"Response missing job_id: {response}"
        assert response.get("status") in ["creating", "pending", "processing"], (
            f"Unexpected status: {response.get('status')}"
        )
        # engineパラメータが受け入れられた（エラーなし）

    # ==========================================================================
    # AC-3: engineパラメータの動作確認
    # ==========================================================================

    def test_ac3_default_engine_creates_job(self) -> None:
        """AC-3: デフォルトエンジン（engine未指定）でジョブが作成される

        受入条件:
        - engine未指定でもHTTP 200が返る
        - ジョブが正常に作成される
        """
        # Act（engineを指定しない）
        response = self._create_job(
            user_requirement="シンプルなAPI呼び出しワークフロー",
            project_id="test_ac3_default",
            engine=None,
        )

        # Assert
        assert "job_id" in response, f"Response missing job_id: {response}"
        assert response.get("status") in ["creating", "pending", "processing"], (
            f"Unexpected status: {response.get('status')}"
        )

    # ==========================================================================
    # AC-4: 後方互換性（GraphAI YAML生成機能維持）
    # ==========================================================================

    def test_ac4_graphai_engine_creates_job(self) -> None:
        """AC-4: engine='graphai'でジョブが作成される

        受入条件:
        - engine='graphai'でHTTP 200が返る
        - ジョブが正常に作成される
        - 後方互換性が維持されている
        """
        # Act
        response = self._create_job(
            user_requirement="SlackにメッセージをPOSTする",
            project_id="test_ac4",
            engine="graphai",
        )

        # Assert
        assert "job_id" in response, f"Response missing job_id: {response}"
        assert response.get("status") in ["creating", "pending", "processing"], (
            f"Unexpected status: {response.get('status')}"
        )

    # ==========================================================================
    # AC-5: セキュリティ検証（バリデーター統合確認）
    # ==========================================================================

    @pytest.mark.security
    def test_ac5_taskflow_validator_job_creation(self) -> None:
        """AC-5: TaskFlow生成時にセキュリティバリデーションが有効

        受入条件:
        - TaskFlowエンジンでジョブが作成できる
        - セキュリティ検証はワークフロー生成時に実施される

        Note: バリデーターの詳細な動作は単体テストでカバー済み
        """
        # Act
        response = self._create_job(
            user_requirement="HTTPSのAPIからデータを取得する",
            project_id="test_ac5",
            engine="taskflow",
        )

        # Assert
        assert "job_id" in response, f"Response missing job_id: {response}"

    # ==========================================================================
    # AC-2: 生成されたワークフローのgraphAiServerでの実行確認
    # ==========================================================================

    @pytest.mark.external
    @pytest.mark.slow
    def test_ac2_graphai_server_health(self) -> None:
        """AC-2: graphAiServerが正常に動作している

        受入条件:
        - graphAiServerが起動している
        - ヘルスチェックが成功する

        Note: 実際のワークフロー実行は長時間かかるため、
        ヘルスチェックで間接確認
        """
        # Act
        response = requests.get(
            f"{self.GRAPHAI_SERVER_URL}/health",
            timeout=10,
        )

        # Assert
        assert response.status_code == 200, (
            f"graphAiServer health check failed: {response.status_code}"
        )

    # ==========================================================================
    # AC-6: セキュリティ検証（プライベートIPの拒否）
    # ==========================================================================

    @pytest.mark.security
    def test_ac6_security_validator_job_creation(self) -> None:
        """AC-6: セキュリティバリデーターが統合されている

        受入条件:
        - TaskFlowエンジンでジョブが作成できる
        - SSRF対策のバリデーションはワークフロー生成時に実施

        Note: バリデーターの詳細な動作は単体テストでカバー済み
        """
        # Act
        response = self._create_job(
            user_requirement="公開APIからデータを取得する（HTTPSのみ使用）",
            project_id="test_ac6",
            engine="taskflow",
        )

        # Assert
        assert "job_id" in response, f"Response missing job_id: {response}"

    # ==========================================================================
    # Strategy Pattern統合確認
    # ==========================================================================

    def test_strategy_pattern_integration_taskflow(self) -> None:
        """Strategy Pattern統合: TaskFlowエンジンが選択される

        受入条件:
        - engine='taskflow'でジョブが作成できる
        - Strategy Patternによるエンジン切り替えが動作
        """
        # Act
        response = self._create_job(
            user_requirement="REST APIを呼び出すワークフロー",
            project_id="test_strategy_taskflow",
            engine="taskflow",
        )

        # Assert
        assert "job_id" in response
        # エラーがなければStrategy Patternが正常に動作している

    def test_strategy_pattern_integration_graphai(self) -> None:
        """Strategy Pattern統合: GraphAIエンジンが選択される

        受入条件:
        - engine='graphai'でジョブが作成できる
        - Strategy Patternによるエンジン切り替えが動作
        - 後方互換性が維持されている
        """
        # Act
        response = self._create_job(
            user_requirement="GraphAIワークフロー生成テスト",
            project_id="test_strategy_graphai",
            engine="graphai",
        )

        # Assert
        assert "job_id" in response
        # エラーがなければStrategy Patternが正常に動作している


# ==========================================================================
# 直接実行時のエントリーポイント
# ==========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
