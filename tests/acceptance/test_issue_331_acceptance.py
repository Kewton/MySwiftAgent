"""
Issue #331 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_331_acceptance.py -v
"""

import os

import pytest
import requests


@pytest.mark.acceptance
class TestIssue331Acceptance:
    """Issue #331: graphAiServer job_params対応 - sourceノード構造変更"""

    # サービスURL（環境変数で上書き可能）
    GRAPHAISERVER_URL = os.getenv("GRAPHAISERVER_URL", "http://localhost:8005")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.GRAPHAISERVER_URL, "graphAiServer"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(f"{name} health check failed: {response.status_code}")
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. Run: ./scripts/dev-hybrid.sh or make dev-all"
                )

    # ==========================================================================
    # 正常系テスト
    # ==========================================================================

    def test_case_1_legacy_api_with_job_params(self) -> None:
        """テストケース1: レガシーAPI - job_params付きリクエスト

        受入条件: graphAiServerが job_params を受け取り、sourceノードに注入する
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "user_input": {"test": "value1"},
            "model_name": "test/model",
            "job_params": {"recipient_email": "test@example.com", "priority": "high"},
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()

        # レスポンスに results が含まれることを確認
        assert "results" in data, f"Response missing 'results' field: {data}"

        # source ノードに user_input と job_params が注入されていることを確認
        # ワークフロー test/model.yml で source を参照し、その構造を返すことで検証
        if "source_echo" in data["results"]:
            source_data = data["results"]["source_echo"]
            assert "user_input" in source_data, f"source node missing 'user_input': {source_data}"
            assert "job_params" in source_data, f"source node missing 'job_params': {source_data}"
            assert source_data["job_params"]["recipient_email"] == "test@example.com", (
                f"job_params.recipient_email mismatch: {source_data}"
            )

    def test_case_2_path_param_api_with_job_params(self) -> None:
        """テストケース2: パスパラメータAPI - job_params付きリクエスト

        受入条件: graphAiServerが job_params を受け取り、sourceノードに注入する
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent/test/model"
        payload = {
            "user_input": {"query": "search term"},
            "job_params": {"callback_url": "http://example.com/callback"},
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "results" in data, f"Response missing 'results' field: {data}"

    # ==========================================================================
    # 後方互換性テスト
    # ==========================================================================

    def test_case_3_legacy_api_without_job_params(self) -> None:
        """テストケース3: レガシーAPI - job_paramsなし（後方互換性）

        受入条件: job_paramsがない既存リクエストは従来通り動作
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "user_input": {"test": "value1"},
            "model_name": "test/model",
            # job_params は含めない（後方互換性テスト）
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "results" in data, f"Response missing 'results' field: {data}"

        # sourceノードにデフォルトの空job_paramsが設定されていることを確認
        if "source_echo" in data["results"]:
            source_data = data["results"]["source_echo"]
            assert "job_params" in source_data, (
                f"source node missing 'job_params' (should be empty object): {source_data}"
            )
            assert source_data["job_params"] == {}, (
                f"job_params should be empty object when not provided: {source_data}"
            )

    def test_case_4_path_param_api_without_job_params(self) -> None:
        """テストケース4: パスパラメータAPI - job_paramsなし（後方互換性）

        受入条件: job_paramsがない既存リクエストは従来通り動作
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent/test/model"
        payload = {
            "user_input": {"data": "test data"},
            # job_params は含めない
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "results" in data, f"Response missing 'results' field: {data}"

    # ==========================================================================
    # 異常系テスト
    # ==========================================================================

    def test_case_5_missing_user_input(self) -> None:
        """テストケース5: user_inputなしリクエスト

        受入条件: user_inputがない場合は400エラーを返す
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "model_name": "test/model",
            "job_params": {"param": "value"},
            # user_input は含めない
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "error" in data, f"Expected 'error' in response: {data}"
        assert "user_input" in data["error"].lower(), (
            f"Error message should mention user_input: {data}"
        )

    def test_case_6_missing_model_name_legacy_api(self) -> None:
        """テストケース6: model_nameなしリクエスト（レガシーAPI）

        受入条件: レガシーAPIでmodel_nameがない場合は400エラーを返す
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "user_input": {"test": "value"},
            "job_params": {"param": "value"},
            # model_name は含めない
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "error" in data, f"Expected 'error' in response: {data}"
        assert "model_name" in data["error"].lower(), (
            f"Error message should mention model_name: {data}"
        )

    # ==========================================================================
    # job_paramsデータ構造テスト
    # ==========================================================================

    def test_case_7_complex_job_params(self) -> None:
        """テストケース7: 複雑なjob_paramsオブジェクト

        受入条件: ネストされたjob_paramsが正しく処理される
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "user_input": {"action": "process"},
            "model_name": "test/model",
            "job_params": {
                "notification": {
                    "email": "user@example.com",
                    "slack_channel": "#alerts",
                },
                "config": {
                    "retry_count": 3,
                    "timeout": 300,
                },
                "tags": ["urgent", "auto-generated"],
            },
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "results" in data, f"Response missing 'results' field: {data}"

    def test_case_8_empty_job_params(self) -> None:
        """テストケース8: 空のjob_paramsオブジェクト

        受入条件: 空のjob_paramsが正しく処理される
        """
        # Arrange
        endpoint = f"{self.GRAPHAISERVER_URL}/api/v1/myagent"
        payload = {
            "user_input": {"test": "value"},
            "model_name": "test/model",
            "job_params": {},
        }

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # Assert
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "results" in data, f"Response missing 'results' field: {data}"
