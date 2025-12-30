"""
Issue #333 受入テスト（L3: ローカル受入テスト）

ワークフロー生成時のAPI型・フィールド名検証機能の受入テスト

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_333_acceptance.py -v

受入条件:
1. ワークフロー生成時に型ミスマッチが検出される
2. フィールド名不一致が検出される
3. 既存のワークフロー生成機能に影響なし
4. 単体テストカバレッジ90%以上（TDDフェーズで確認済み）
"""

import pytest
import requests


@pytest.mark.acceptance
class TestIssue333Acceptance:
    """Issue #333: ワークフロー生成時のAPI型・フィールド名検証機能"""

    # サービスURL
    EXPERT_AGENT_URL = "http://localhost:8004"
    MYVAULT_URL = "http://localhost:8003"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code != 200:
                    pytest.skip(
                        f"{name} is not healthy (status: {response.status_code})"
                    )
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: ./scripts/dev-start.sh or make dev-all"
                )

    # ==========================================================================
    # 受入条件1: ワークフロー生成時に型ミスマッチが検出される (E2E)
    # ==========================================================================

    def test_type_mismatch_detected_via_api(self) -> None:
        """型ミスマッチ検出: Object参照をString型フィールドに渡した場合エラーになる

        受入条件: ワークフロー生成時に型ミスマッチが検出される
        検証方法: スキーマ検証APIを呼び出し、型ミスマッチが検出されることを確認
        """
        # Arrange: 型ミスマッチを含むYAML（:fetch_data はObject参照）
        yaml_with_type_mismatch = """version: 0.5
nodes:
  source: {}

  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
    timeout: 30000

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :fetch_data
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""
        endpoint = (
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/workflow-generator/validate-schema"
        )
        payload = {"yaml_content": yaml_with_type_mismatch}

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        # 型ミスマッチが検出される
        assert data["is_valid"] is False, "Type mismatch should be detected"
        assert data["error_count"] >= 1, "At least one error expected"

        # 型ミスマッチのissueが存在する
        type_mismatch_issues = [
            i for i in data["issues"] if i["issue_type"] == "type_mismatch"
        ]
        assert len(type_mismatch_issues) >= 1, "type_mismatch issue not found"
        assert "Object" in type_mismatch_issues[0]["message"], (
            "Error message should mention Object type"
        )

    def test_valid_yaml_passes_validation_via_api(self) -> None:
        """正しいYAMLは検証に合格する

        受入条件: 型ミスマッチがないYAMLは検証に合格する
        検証方法: フィールドアクセスパターンを使用したYAMLが合格することを確認
        """
        # Arrange: 正しいYAML（:source.user_input.query はフィールドアクセス）
        valid_yaml = """version: 0.5
nodes:
  source: {}

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
        system_prompt: "You are a helpful assistant"
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""
        endpoint = (
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/workflow-generator/validate-schema"
        )
        payload = {"yaml_content": valid_yaml}

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        assert data["is_valid"] is True, (
            f"Valid YAML should pass validation. Issues: {data['issues']}"
        )
        assert data["error_count"] == 0, "No errors expected"

    # ==========================================================================
    # 受入条件2: フィールド名不一致が検出される (E2E)
    # ==========================================================================

    def test_deprecated_field_detected_via_api(self) -> None:
        """非推奨フィールド検出: system_imput は警告として検出される

        受入条件: フィールド名不一致が検出される
        検証方法: system_imput（タイポ）が警告として検出されることを確認
        """
        # Arrange: 非推奨フィールドを含むYAML
        yaml_with_deprecated_field = """version: 0.5
nodes:
  source: {}

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
        system_imput: "You are a helpful assistant"
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""
        endpoint = (
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/workflow-generator/validate-schema"
        )
        payload = {"yaml_content": yaml_with_deprecated_field}

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        # 非推奨フィールドは警告（warningだがエラーではない）
        deprecated_issues = [
            i for i in data["issues"] if i["issue_type"] == "deprecated_field"
        ]
        assert len(deprecated_issues) >= 1, "deprecated_field warning not found"
        assert "system_imput" in deprecated_issues[0]["message"], (
            "Warning should mention system_imput"
        )
        assert deprecated_issues[0]["severity"] == "warning", (
            "Deprecated field should be a warning, not error"
        )

    def test_deprecated_field_system_imput_accepted_with_warning(self) -> None:
        """非推奨フィールド system_imput が後方互換性を維持して動作する

        受入条件: フィールド名不一致が検出される（警告として）
        検証方法: system_imput を使用したリクエストが受け入れられることを確認
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/aiagent/utility/jsonoutput"
        payload = {
            "user_input": "What is the capital of Japan?",
            "system_imput": "You are a helpful assistant.",  # 非推奨フィールド
            "model_name": "gemini-2.0-flash-exp",
        }

        # Act
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
        except requests.exceptions.Timeout:
            pytest.skip("LLM API timed out")

        # Assert
        # system_imput は後方互換性のため受け入れられる（200または500/LLMエラー）
        # 422（バリデーションエラー）にはならないこと
        assert response.status_code != 422, (
            f"system_imput should be accepted for backward compatibility, "
            f"but got 422: {response.text}"
        )

    def test_new_field_system_prompt_accepted(self) -> None:
        """新フィールド system_prompt が正常に動作する

        受入条件: 正しいフィールド名 system_prompt が使用できる
        検証方法: system_prompt を使用したリクエストが受け入れられることを確認
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/aiagent/utility/jsonoutput"
        payload = {
            "user_input": "What is 2 + 2?",
            "system_prompt": "You are a helpful math assistant.",  # 正式フィールド
            "model_name": "gemini-2.0-flash-exp",
        }

        # Act
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
        except requests.exceptions.Timeout:
            pytest.skip("LLM API timed out")

        # Assert
        # system_prompt は正式フィールドとして受け入れられる
        assert response.status_code != 422, (
            f"system_prompt should be accepted, but got 422: {response.text}"
        )

    # ==========================================================================
    # 受入条件3: 既存のワークフロー生成機能に影響なし
    # ==========================================================================

    def test_workflow_generator_health_check(self) -> None:
        """ワークフロー生成APIがヘルスチェックに応答する

        受入条件: 既存のワークフロー生成機能に影響なし
        検証方法: ヘルスチェックエンドポイントが正常に応答することを確認
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/health"

        # Act
        response = requests.get(endpoint, timeout=10)

        # Assert
        assert response.status_code == 200, (
            f"Health check failed: {response.status_code} - {response.text}"
        )

    def test_schema_validation_endpoint_available(self) -> None:
        """スキーマ検証エンドポイントが利用可能

        受入条件: 新しいスキーマ検証エンドポイントが動作する
        検証方法: 空のYAMLを送信してエンドポイントが応答することを確認
        """
        # Arrange
        endpoint = (
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/workflow-generator/validate-schema"
        )
        payload = {"yaml_content": ""}

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, (
            f"Schema validation endpoint failed: {response.status_code}"
        )
        data = response.json()
        assert data["is_valid"] is True, "Empty YAML should be valid"

    def test_utility_api_basic_functionality(self) -> None:
        """ユーティリティAPIの基本機能が動作する

        受入条件: 既存のワークフロー生成機能に影響なし
        検証方法: 基本的なAPIエンドポイントが正常に動作することを確認
        """
        # Arrange
        endpoint = f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/aiagent/utility/jsonoutput"
        payload = {
            "user_input": "Say 'Hello, World!'",
            "model_name": "gemini-2.0-flash-exp",
        }

        # Act
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
        except requests.exceptions.Timeout:
            pytest.skip("LLM API timed out")

        # Assert
        # API が正常に動作すること（200）または LLM エラー（500）
        # 422（スキーマ検証エラー）にはならないこと
        assert response.status_code in [200, 500], (
            f"Expected 200 or 500, got {response.status_code}: {response.text}"
        )

    # ==========================================================================
    # E2E: 複合テスト（型ミスマッチ + フィールド名不一致の同時検出）
    # ==========================================================================

    def test_multiple_issues_detected_via_api(self) -> None:
        """複数の問題が同時に検出される

        受入条件: 型ミスマッチとフィールド名不一致が同時に検出される
        検証方法: 両方の問題を含むYAMLで両方が検出されることを確認
        """
        # Arrange: 型ミスマッチとフィールド名不一致を両方含むYAML
        yaml_with_multiple_issues = """version: 0.5
nodes:
  source: {}

  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
    timeout: 30000

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :fetch_data
        system_imput: "You are a helpful assistant"
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""
        endpoint = (
            f"{self.EXPERT_AGENT_URL}/aiagent-api/v1/workflow-generator/validate-schema"
        )
        payload = {"yaml_content": yaml_with_multiple_issues}

        # Act
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Assert
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()

        # 型ミスマッチが検出される
        type_mismatch_issues = [
            i for i in data["issues"] if i["issue_type"] == "type_mismatch"
        ]
        assert len(type_mismatch_issues) >= 1, "type_mismatch issue not found"

        # 非推奨フィールドも検出される
        deprecated_issues = [
            i for i in data["issues"] if i["issue_type"] == "deprecated_field"
        ]
        assert len(deprecated_issues) >= 1, "deprecated_field warning not found"

        # エラーがあるのでis_validはFalse
        assert data["is_valid"] is False, "Should be invalid due to type_mismatch error"

    # ==========================================================================
    # 型検証機能の統合確認（コード統合確認）
    # ==========================================================================

    def test_type_validation_rules_in_prompt(self) -> None:
        """TYPE_VALIDATION_RULES がプロンプトに統合されている

        受入条件: ワークフロー生成時に型ミスマッチが検出される
        検証方法: プロンプト生成関数を直接呼び出し、ルールが含まれることを確認
        """
        # Arrange & Act
        from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
            create_workflow_generation_prompt,
        )

        task_data = {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"schema": {"type": "object"}},
            "output_interface": {"schema": {"type": "object"}},
        }
        graphai_capabilities = {
            "agents": [
                {"name": "fetchAgent", "description": "HTTP fetch"},
            ]
        }
        expert_agent_capabilities = {
            "utility_apis": [],
            "ai_agent_apis": [],
        }

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # Assert
        # TYPE_VALIDATION_RULES がプロンプトに含まれていること
        assert "Important Type Validation Rules" in prompt, (
            "TYPE_VALIDATION_RULES is not integrated into the prompt"
        )
        assert "fetchAgent Output Type" in prompt, (
            "fetchAgent type guidance is missing from prompt"
        )

    def test_schema_validator_in_graph(self) -> None:
        """schema_validator ノードがグラフに組み込まれている

        受入条件: ワークフロー生成時に型ミスマッチが検出される
        検証方法: グラフ構造に schema_validator ノードが存在することを確認
        """
        # Arrange & Act
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            create_workflow_generator_graph,
        )

        graph = create_workflow_generator_graph()

        # Assert
        assert "schema_validator" in graph.nodes, (
            "schema_validator node is not in the workflow generator graph"
        )
        assert "generator" in graph.nodes, "generator node is missing from graph"
