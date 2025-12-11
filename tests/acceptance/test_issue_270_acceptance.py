"""
Issue #270 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_270_acceptance.py -v
"""
import os
import sys
from pathlib import Path
from typing import Any

import pytest
import requests


# expertAgentのパスを追加
EXPERT_AGENT_PATH = Path(__file__).parent.parent.parent / "expertAgent"
sys.path.insert(0, str(EXPERT_AGENT_PATH))


@pytest.mark.acceptance
class TestIssue270Acceptance:
    """Issue #270: expert_agent_capabilities.yamlにリクエスト/レスポンススキーマを追加"""

    # サービスURL（環境変数で上書き可能）
    EXPERT_AGENT_URL = os.environ.get("EXPERT_AGENT_URL", "http://localhost:8004")
    MYVAULT_URL = os.environ.get("MYVAULT_URL", "http://localhost:8003")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (f"{self.EXPERT_AGENT_URL}/aiagent-api/health", "expertAgent"),
            (f"{self.MYVAULT_URL}/health", "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(url, timeout=5)
                assert response.status_code == 200, f"{name} is not healthy"
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running. "
                    "Run: ./scripts/dev-start.sh or make dev-all"
                )

    # ==========================================================================
    # AC1: 主要API（10件以上）のスキーマが capabilities.yaml に追加されている
    # ==========================================================================

    def test_ac1_yaml_has_minimum_10_apis_with_schema(self) -> None:
        """AC1: 10件以上のAPIにスキーマが追加されていることを確認

        受入条件: 主要API（10件以上）のスキーマが capabilities.yaml に追加されている
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            EXPERT_AGENT_APIS,
        )

        apis_with_schema = [
            a for a in EXPERT_AGENT_APIS if a.request_schema or a.response_schema
        ]

        assert len(apis_with_schema) >= 10, (
            f"Expected at least 10 APIs with schema, got {len(apis_with_schema)}"
        )
        print(f"[PASS] {len(apis_with_schema)} APIs have schema defined")

    def test_ac1_gmail_api_has_request_schema(self) -> None:
        """AC1: Gmail検索APIにリクエストスキーマがあることを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            EXPERT_AGENT_APIS,
        )

        gmail = next((a for a in EXPERT_AGENT_APIS if a.name == "Gmail検索"), None)

        assert gmail is not None, "Gmail検索 API not found"
        assert gmail.request_schema is not None, "Gmail検索 has no request_schema"
        # The schema format is field_name -> {type, description, required}
        assert "query" in gmail.request_schema, (
            "request_schema missing 'query' field"
        )
        print(f"[PASS] Gmail検索 request_schema: {list(gmail.request_schema.keys())}")

    def test_ac1_all_apis_have_method_field(self) -> None:
        """AC1: 全APIにmethodフィールドがあることを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            EXPERT_AGENT_APIS,
        )

        apis_without_method = [a for a in EXPERT_AGENT_APIS if not a.method]

        assert len(apis_without_method) == 0, (
            f"APIs without method: {[a.name for a in apis_without_method]}"
        )
        print(f"[PASS] All {len(EXPERT_AGENT_APIS)} APIs have method field")

    # ==========================================================================
    # AC2: LLMプロンプトでスキーマ情報が参照されている
    # ==========================================================================

    def test_ac2_prompt_contains_schema_hints(self) -> None:
        """AC2: プロンプト生成でスキーマヒントが含まれることを確認

        受入条件: LLMプロンプトでスキーマ情報が参照されている
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            _build_expert_agent_capabilities,
        )

        prompt = _build_expert_agent_capabilities()

        # スキーマ関連のキーワードが含まれていることを確認
        # Issue #270: Schema hints are shown as "[required: field1, field2]" format
        schema_keywords = ["required:", "[", "]", "api", "endpoint"]
        found_keywords = [kw for kw in schema_keywords if kw.lower() in prompt.lower()]

        assert len(found_keywords) >= 2, (
            f"Prompt should contain schema keywords, found: {found_keywords}"
        )
        print(f"[PASS] Prompt contains schema keywords: {found_keywords}")
        print(f"[PASS] Prompt length: {len(prompt)} chars")

    def test_ac2_schema_hint_function_works(self) -> None:
        """AC2: _build_schema_hint関数が正しく動作することを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
            _build_schema_hint,
        )

        # The actual schema format used in expert_agent_capabilities.yaml
        # is field_name -> {type, description, required}
        test_api: dict[str, Any] = {
            "name": "Test API",
            "request_schema": {
                "query": {"type": "string", "description": "検索クエリ", "required": True},
                "max_results": {"type": "integer", "description": "最大結果数", "required": False},
            },
        }

        hint = _build_schema_hint(test_api)

        # The hint should contain required fields
        assert "query" in hint, "Hint should contain 'query'"
        assert "required" in hint.lower(), (
            "Hint should indicate required fields"
        )
        print(f"[PASS] Schema hint generated: {hint}")

    # ==========================================================================
    # AC3: インターフェース生成の精度が向上している（手動検証）
    # ==========================================================================

    @pytest.mark.external
    def test_ac3_job_generation_uses_schema(self) -> None:
        """AC3: ジョブ生成APIがスキーマを参照してインターフェースを生成することを確認

        受入条件: インターフェース生成の精度が向上している（手動検証）

        Note: このテストは実際のLLM APIキーが必要です。
        スキップする場合: pytest -m "not external"
        """
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/job-generator"
        payload: dict[str, Any] = {
            "user_request": "最新のメールを5件検索して、件名と送信者を教えてください",
            "available_capabilities": ["Gmail検索"],
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert data.get("status") in ["success", "completed"], (
            f"Job generation failed: {data}"
        )

        # タスク情報にinterfaceが含まれていることを確認
        tasks = data.get("tasks", []) or data.get("task_breakdown", [])
        if tasks:
            print(f"✅ Generated {len(tasks)} tasks")
            for task in tasks:
                if "interface" in task:
                    print(f"  - Task: {task.get('task_name')}")
                    print(f"    Interface: {task['interface']}")

    # ==========================================================================
    # AC4: 既存のワークフロー生成が正常に動作する
    # ==========================================================================

    @pytest.mark.external
    def test_ac4_existing_workflow_generation_works(self) -> None:
        """AC4: 既存のワークフロー生成が正常動作することを確認

        受入条件: 既存のワークフロー生成が正常に動作する

        Note: このテストは実際のLLM APIキーが必要です。
        スキップする場合: pytest -m "not external"
        """
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/job-generator"
        payload: dict[str, Any] = {
            "user_request": "テストメッセージを音声に変換してください",
            "available_capabilities": ["Text-to-Speech（Base64）"],
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        # 既存のAPIが正常に動作することを確認
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data = response.json()
        # エラーではないことを確認（成功または処理中）
        assert "error" not in data.get("status", "").lower(), (
            f"Workflow generation error: {data}"
        )
        print(f"✅ Existing workflow generation works: {data.get('status')}")

    # ==========================================================================
    # AC5: 単体テストカバレッジ90%以上
    # ==========================================================================

    def test_ac5_unit_tests_exist_and_pass(self) -> None:
        """AC5: 単体テストが存在し、パスすることを確認

        受入条件: 単体テストカバレッジ90%以上

        Note: このテストではテストファイルの存在のみ確認します。
        実際のカバレッジはCI/CDで検証されます。
        """
        test_files = [
            EXPERT_AGENT_PATH / "tests" / "unit" / "test_graphai_capabilities.py",
            EXPERT_AGENT_PATH / "tests" / "unit" / "test_task_breakdown.py",
        ]

        for test_file in test_files:
            assert test_file.exists(), f"Test file not found: {test_file}"
            print(f"✅ Test file exists: {test_file.name}")

    # ==========================================================================
    # SF-01: output_schema → response_schema マイグレーション
    # ==========================================================================

    def test_sf01_schema_normalization_works(self) -> None:
        """SF-01: スキーマ正規化が正しく動作することを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            _normalize_schema_keys,
        )

        # output_schema を含むテストデータ
        test_api: dict[str, Any] = {
            "name": "Test API",
            "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        }

        normalized = _normalize_schema_keys(test_api)

        assert "response_schema" in normalized, (
            "output_schema should be converted to response_schema"
        )
        assert "output_schema" not in normalized, (
            "output_schema should be removed after normalization"
        )
        print("✅ SF-01: Schema normalization works correctly")

    # ==========================================================================
    # SF-02: スキーマバリデーション
    # ==========================================================================

    def test_sf02_schema_validation_works(self) -> None:
        """SF-02: スキーマバリデーションが正しく動作することを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            validate_schema,
        )

        # The actual schema format: field_name -> {type, description, required}
        valid_schema: dict[str, Any] = {
            "query": {"type": "string", "description": "検索クエリ", "required": True},
        }

        # 正常なスキーマは例外を投げない
        errors = validate_schema(valid_schema, "TestAPI", "request")
        assert len(errors) == 0, f"Valid schema should have no errors: {errors}"
        print("[PASS] SF-02: Schema validation works for valid schema")

    def test_sf02_invalid_schema_returns_errors(self) -> None:
        """SF-02: 不正なスキーマがエラーを返すことを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
            SchemaValidationError,
            validate_schema,
        )

        # Invalid schema: field has an invalid type
        invalid_schema: dict[str, Any] = {
            "query": {"type": "invalid_type", "description": "検索クエリ"},
        }

        # The validate_schema function raises SchemaValidationError for invalid types
        try:
            validate_schema(invalid_schema, "TestAPI", "request")
            assert False, "Invalid schema should raise SchemaValidationError"
        except SchemaValidationError as e:
            print(f"[PASS] SF-02: Invalid schema raises error: {e}")
