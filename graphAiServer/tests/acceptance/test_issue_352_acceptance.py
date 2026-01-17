"""
Issue #352 受入テスト（L3: ローカル受入テスト）

TaskFlow V2: URL変数参照バリデーション不整合修正

前提条件:
- GraphAiServerが起動していること (http://localhost:8005)
- Admin tokenが設定されていること

実行方法:
  cd graphAiServer
  uv run pytest tests/acceptance/test_issue_352_acceptance.py -v
"""

import os
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue352Acceptance:
    """Issue #352: TaskFlow V2 URL変数参照バリデーション不整合修正"""

    GRAPHAI_SERVER_URL = os.environ.get("GRAPHAI_SERVER_URL", "http://localhost:8005")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "duxwHg0N-MrYHZD__T5zLUc50ATvlpXKmHN0xtkdxuY")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.GRAPHAI_SERVER_URL}/health", timeout=5)
            assert response.status_code == 200, "GraphAiServer is not healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("GraphAiServer is not running. Run: ./scripts/dev-hybrid.sh start")

    @pytest.fixture
    def headers(self) -> dict[str, str]:
        """API headers with admin token"""
        return {
            "Content-Type": "application/json",
            "X-Admin-Token": self.ADMIN_TOKEN,
        }

    def _register_workflow(
        self, headers: dict[str, str], workflow_name: str, definition: dict[str, Any]
    ) -> requests.Response:
        """ワークフロー登録ヘルパー"""
        return requests.post(
            f"{self.GRAPHAI_SERVER_URL}/api/v2/workflows/register",
            headers=headers,
            json={
                "workflow_name": workflow_name,
                "definition": definition,
                "overwrite": True,
            },
            timeout=30,
        )

    def _delete_workflow(self, headers: dict[str, str], workflow_name: str) -> None:
        """ワークフロー削除ヘルパー"""
        requests.delete(
            f"{self.GRAPHAI_SERVER_URL}/api/v2/workflows/{workflow_name}",
            headers=headers,
            timeout=10,
        )

    # ==========================================================================
    # 正常系テスト: ${inputs.*} 変数参照
    # ==========================================================================

    def test_inputs_variable_in_url(self, headers: dict[str, str]) -> None:
        """シナリオ1: ${inputs.*} 変数参照を含むURLが登録できる

        受入条件: ${inputs.field} 形式の変数参照がURLとして許可される
        """
        workflow_name = "test_352_inputs_var"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "description": "Test ${inputs.*} variable in URL",
            "input_schema": {"base_url": "string", "user_id": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "fetch_user",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${inputs.base_url}/users/${inputs.user_id}",
                    },
                }
            ],
            "output": {"result": "${fetch_user.output}"},
        }

        try:
            response = self._register_workflow(headers, workflow_name, definition)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data.get("status") == "success", f"Unexpected response: {data}"
            assert data.get("workflow_name") == workflow_name
        finally:
            self._delete_workflow(headers, workflow_name)

    # ==========================================================================
    # 正常系テスト: ${step.output} 変数参照
    # ==========================================================================

    def test_step_output_variable_in_url(self, headers: dict[str, str]) -> None:
        """シナリオ2: ${step_id.output} 変数参照を含むURLが登録できる

        受入条件: ${step_id.output.field} 形式の変数参照がURLとして許可される
        """
        workflow_name = "test_352_step_output_var"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "description": "Test step output variable in URL",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "transform",
                    "config": {
                        "step_type": "transform",
                        "mode": "template",
                        "template": "https://api.example.com/search",
                    },
                },
                {
                    "id": "step_002",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${step_001.output}",
                    },
                },
            ],
            "output": {"result": "${step_002.output}"},
        }

        try:
            response = self._register_workflow(headers, workflow_name, definition)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data.get("status") == "success", f"Unexpected response: {data}"
        finally:
            self._delete_workflow(headers, workflow_name)

    # ==========================================================================
    # 正常系テスト: 後続パス付き変数参照
    # ==========================================================================

    def test_variable_with_trailing_path(self, headers: dict[str, str]) -> None:
        """シナリオ3: 変数参照に後続パス/クエリが付いたURLが登録できる

        受入条件: ${inputs.base_url}/api/v1/endpoint?query=1 形式が許可される
        """
        workflow_name = "test_352_trailing_path"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "description": "Test variable with trailing path",
            "input_schema": {"base_url": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "api_call",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${inputs.base_url}/api/v1/users?limit=10",
                    },
                }
            ],
            "output": {"result": "${api_call.output}"},
        }

        try:
            response = self._register_workflow(headers, workflow_name, definition)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data.get("status") == "success", f"Unexpected response: {data}"
        finally:
            self._delete_workflow(headers, workflow_name)

    # ==========================================================================
    # 異常系テスト: 不正な変数参照の拒否
    # ==========================================================================

    def test_invalid_variable_rejected(self, headers: dict[str, str]) -> None:
        """シナリオ4: 不正な変数参照は拒否される

        受入条件: ${123invalid} のような不正な変数参照は400エラーになる
        """
        workflow_name = "test_352_invalid_var"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${123invalid}/path",
                    },
                }
            ],
            "output": {"result": "${step_001.output}"},
        }

        response = self._register_workflow(headers, workflow_name, definition)
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "error" in data, f"Expected error response: {data}"

    # ==========================================================================
    # 異常系テスト: 改善されたエラーメッセージ確認
    # ==========================================================================

    def test_improved_error_message(self, headers: dict[str, str]) -> None:
        """シナリオ5: エラーメッセージに ${inputs.*}, ${step_id.output.*} が含まれる

        受入条件: SF-2で改善されたエラーメッセージが表示される
        """
        workflow_name = "test_352_error_msg"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "invalid-url",
                    },
                }
            ],
            "output": {"result": "${step_001.output}"},
        }

        response = self._register_workflow(headers, workflow_name, definition)
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}: {response.text}"
        )
        data = response.json()

        # エラーメッセージを検証
        error_msg = str(data.get("error", {}))
        assert "${inputs.*}" in error_msg or "inputs" in error_msg, (
            f"Error message should mention ${{inputs.*}}: {error_msg}"
        )
        assert "${step_id.output.*}" in error_msg or "step" in error_msg, (
            f"Error message should mention ${{step_id.output.*}}: {error_msg}"
        )

    # ==========================================================================
    # 正常系テスト: ${env.*} と ${secrets.*} は引き続き許可
    # ==========================================================================

    def test_env_variable_still_allowed(self, headers: dict[str, str]) -> None:
        """シナリオ6: ${env.*} 変数参照は引き続き許可される

        受入条件: 既存の ${env.VAR} 形式は影響を受けない
        """
        workflow_name = "test_352_env_var"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "description": "Test ${env.*} variable still works",
            "input_schema": {},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "api_call",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${env.API_BASE_URL}/health",
                    },
                }
            ],
            "output": {"result": "${api_call.output}"},
        }

        try:
            response = self._register_workflow(headers, workflow_name, definition)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data.get("status") == "success", f"Unexpected response: {data}"
        finally:
            self._delete_workflow(headers, workflow_name)

    def test_secrets_variable_still_allowed(self, headers: dict[str, str]) -> None:
        """シナリオ7: ${secrets.*} 変数参照は引き続き許可される

        受入条件: 既存の ${secrets.KEY} 形式は影響を受けない
        """
        workflow_name = "test_352_secrets_var"
        definition: dict[str, Any] = {
            "workflow_name": workflow_name,
            "description": "Test ${secrets.*} variable still works",
            "input_schema": {},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "api_call",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "${secrets.PRIVATE_API_URL}/data",
                    },
                }
            ],
            "output": {"result": "${api_call.output}"},
        }

        try:
            response = self._register_workflow(headers, workflow_name, definition)
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data.get("status") == "success", f"Unexpected response: {data}"
        finally:
            self._delete_workflow(headers, workflow_name)
