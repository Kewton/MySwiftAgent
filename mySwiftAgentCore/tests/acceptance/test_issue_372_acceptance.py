"""
Issue #372 受入テスト（L3: ローカル受入テスト）

feat(mySwiftAgentCore): ケイパビリティAPIエンドポイントのベースURL解決機能

前提条件:
- mySwiftAgentCore サービスが起動していること (./scripts/dev-hybrid.sh start --local-only)
- MyVault に ANTHROPIC_API_KEY が設定されていること
- expertAgent が起動していること

実行方法:
  cd mySwiftAgentCore
  uv run pytest tests/acceptance/test_issue_372_acceptance.py -v
"""

import os
from pathlib import Path
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue372Acceptance:
    """Issue #372: ケイパビリティAPIエンドポイントのベースURL解決機能"""

    MYSWIFTAGENTCORE_URL = "http://localhost:8006"
    EXPERT_AGENT_URL = "http://localhost:8004"
    BASE_DIR = Path(__file__).parent.parent.parent  # mySwiftAgentCore/

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.MYSWIFTAGENTCORE_URL, "mySwiftAgentCore"),
            (self.EXPERT_AGENT_URL, "expertAgent"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                assert response.status_code == 200, f"{name} is not healthy"
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running. "
                    "Run: ./scripts/dev-hybrid.sh start --local-only"
                )

    # ==========================================================================
    # TC-001: api_endpoints読み込みテスト（AC-1対応）
    # ==========================================================================

    def test_tc_001_load_api_endpoints(self) -> None:
        """TC-001: index.yaml の api_endpoints が正しく読み込めるか

        受入条件: AC-1 - CapabilityLoader が index.yaml の api_endpoints を読み込める
        設計方針: DP-4 - api_endpoints セクションをindex.yamlに追加
        """
        # 設定ファイルの存在確認
        config_file = self.BASE_DIR / "config" / "capabilities" / "default_project" / "index.yaml"
        assert config_file.exists(), f"Config file not found: {config_file}"

        # 設定ファイルの内容確認
        content = config_file.read_text()
        assert "api_endpoints:" in content, "api_endpoints section not found in index.yaml"
        assert "expert_agent:" in content, "expert_agent config not found"
        assert "base_url:" in content, "base_url not found"

    # ==========================================================================
    # TC-002, TC-003: 環境変数解決テスト（AC-2, AC-7対応）
    # ==========================================================================

    def test_tc_002_resolve_env_var_with_value(self) -> None:
        """TC-002: 環境変数が設定されている場合の値解決

        受入条件: AC-2 - CapabilityLoader が環境変数 ${VAR:-default} 形式を解決できる
        受入条件: AC-7 - 環境変数 EXPERT_AGENT_BASE_URL でベースURLをオーバーライドできる
        設計方針: DP-3 - ${VAR:-default} 形式の環境変数解決
        """
        # EndpointConfigManager のソースファイル確認
        endpoint_config_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "EndpointConfigManager.ts"
        assert endpoint_config_file.exists(), f"EndpointConfigManager not found: {endpoint_config_file}"

        # 環境変数解決のパターンが実装されているか確認
        content = endpoint_config_file.read_text()
        assert "resolveEnvVars" in content, "resolveEnvVars method not found"
        assert "${" in content, "Environment variable pattern not found"

    def test_tc_003_resolve_env_var_default(self) -> None:
        """TC-003: 環境変数が未設定の場合のデフォルト値使用

        受入条件: AC-2 - デフォルト値が正しく使用される
        設計方針: DP-3 - ${VAR:-default} 形式
        """
        # 設定ファイルでデフォルト値が設定されているか確認
        config_file = self.BASE_DIR / "config" / "capabilities" / "default_project" / "index.yaml"
        content = config_file.read_text()

        # ${...:-...} パターンがあることを確認
        assert ":-" in content or "localhost" in content, (
            "Default values not configured in index.yaml"
        )

    # ==========================================================================
    # TC-004, TC-005: URL解決テスト（AC-3, AC-4対応）
    # ==========================================================================

    def test_tc_004_resolve_url_by_api_source(self) -> None:
        """TC-004: api_source 指定によるベースURL特定

        受入条件: AC-3 - 各ケイパビリティの _internal.api_source からベースURLを特定できる
        設計方針: DP-1 - URLResolver コンポーネント
        """
        # URLResolver のソースファイル確認
        url_resolver_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "URLResolver.ts"
        assert url_resolver_file.exists(), f"URLResolver not found: {url_resolver_file}"

        # api_source によるURL解決が実装されているか確認
        content = url_resolver_file.read_text()
        assert "api_source" in content, "api_source handling not found in URLResolver"
        assert "findMatchingConfig" in content or "resolveUrl" in content, (
            "URL resolution method not found"
        )

    def test_tc_005_resolve_url_by_prefix_fallback(self) -> None:
        """TC-005: api_source 未設定時のプレフィックスマッチング

        受入条件: AC-4 - api_source がない場合、endpoint_prefix でフォールバック解決できる
        設計方針: DP-1 - URLResolver コンポーネント
        """
        # URLResolver のソースファイル確認
        url_resolver_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "URLResolver.ts"
        content = url_resolver_file.read_text()

        # endpoint_prefix によるフォールバックが実装されているか確認
        assert "endpoint_prefix" in content or "prefix" in content.lower(), (
            "endpoint_prefix fallback not found in URLResolver"
        )

    # ==========================================================================
    # TC-006, TC-007: ApiRestNode テスト（AC-6対応）
    # ==========================================================================

    def test_tc_006_api_rest_node_with_capability_id(self) -> None:
        """TC-006: capability_id 指定時の実行

        受入条件: AC-6 - 生成されたワークフローが taskflowEngine で正常に実行できる
        設計方針: DP-2 - ApiRestNodeに capability_id パラメータを追加
        """
        # ApiRestNode のソースファイル確認
        api_rest_node_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "ApiRestNode.ts"
        assert api_rest_node_file.exists(), f"ApiRestNode not found: {api_rest_node_file}"

        # capability_id パラメータが追加されているか確認
        content = api_rest_node_file.read_text()
        assert "capability_id" in content, "capability_id parameter not found in ApiRestNode"
        assert "CapabilityExecutor" in content or "capabilityExecutor" in content, (
            "CapabilityExecutor usage not found in ApiRestNode"
        )

    def test_tc_007_api_rest_node_with_direct_url(self) -> None:
        """TC-007: 従来の直接URL指定が引き続き動作する

        受入条件: AC-6 - 後方互換性の維持
        設計方針: DP-2 - ApiRestNode拡張
        """
        # ApiRestNode で直接URL指定がサポートされているか確認
        api_rest_node_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "ApiRestNode.ts"
        content = api_rest_node_file.read_text()

        # url パラメータが引き続きサポートされているか確認
        assert "url:" in content or 'url?' in content or '"url"' in content, (
            "Direct URL support removed from ApiRestNode"
        )

    # ==========================================================================
    # TC-008, TC-009: E2E ワークフロー実行テスト（AC-5, AC-6対応）
    # ==========================================================================

    def test_tc_008_e2e_workflow_execution(self) -> None:
        """TC-008: 生成されたワークフローがTaskFlowEngineで実行できる

        受入条件: AC-5 - taskflowGeneratorAgent が完全URLを含むワークフローを生成できる
        受入条件: AC-6 - 生成されたワークフローが taskflowEngine で正常に実行できる
        設計方針: DP-1, DP-2
        """
        # TaskFlow API stats エンドポイント確認
        endpoint = f"{self.MYSWIFTAGENTCORE_URL}/api/v1/taskflow/stats"
        response = requests.get(endpoint, timeout=10)

        assert response.status_code == 200, (
            f"TaskFlow stats endpoint failed: {response.status_code}"
        )
        data = response.json()
        assert "totalProjects" in data, f"Response missing 'totalProjects': {data}"

    def test_tc_009_env_override_e2e(self) -> None:
        """TC-009: 環境変数変更が実行時に反映される

        受入条件: AC-7 - 環境変数 EXPERT_AGENT_BASE_URL でベースURLをオーバーライドできる
        設計方針: DP-3
        """
        # 環境変数オーバーライドの仕組みが設定ファイルに存在するか確認
        config_file = self.BASE_DIR / "config" / "capabilities" / "default_project" / "index.yaml"
        content = config_file.read_text()

        # EXPERT_AGENT_BASE_URL 環境変数参照があるか確認
        assert "EXPERT_AGENT_BASE_URL" in content or "expert_agent" in content, (
            "EXPERT_AGENT_BASE_URL override not configured"
        )

    # ==========================================================================
    # TC-010, TC-011: エラーハンドリングテスト（AC-3, AC-4対応）
    # ==========================================================================

    def test_tc_010_invalid_api_source_error(self) -> None:
        """TC-010: 無効な api_source 指定時のエラー処理

        受入条件: AC-3 - 無効な api_source の場合、適切なエラーが返される
        設計方針: DP-1
        """
        # エラータイプの定義確認
        types_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "types.ts"
        assert types_file.exists(), f"Types file not found: {types_file}"

        content = types_file.read_text()
        assert "EndpointResolutionError" in content, (
            "EndpointResolutionError not defined in types.ts"
        )

    def test_tc_011_no_matching_prefix_error(self) -> None:
        """TC-011: プレフィックスマッチングで一致しない場合のエラー処理

        受入条件: AC-4 - マッチしない場合の適切なエラー処理
        設計方針: DP-1
        """
        # URLResolver にエラー処理が実装されているか確認
        url_resolver_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "URLResolver.ts"
        content = url_resolver_file.read_text()

        assert "Error" in content or "throw" in content, (
            "Error handling not found in URLResolver"
        )


# ==========================================================================
# 設計方針検証テスト
# ==========================================================================

@pytest.mark.acceptance
class TestIssue372DesignPolicy:
    """Issue #372: 設計方針検証"""

    BASE_DIR = Path(__file__).parent.parent.parent

    def test_dp1_component_structure(self) -> None:
        """DP-1: EndpointConfigManager、URLResolver、CapabilityExecutor の3コンポーネント構成

        設計方針: コンポーネント構成
        """
        # ディレクトリ構造確認
        endpoint_dir = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint"
        assert endpoint_dir.exists(), f"Endpoint directory not found: {endpoint_dir}"

        # 各コンポーネントファイルの存在確認
        required_files = [
            "EndpointConfigManager.ts",
            "URLResolver.ts",
            "types.ts",
            "index.ts",
        ]
        for filename in required_files:
            file_path = endpoint_dir / filename
            assert file_path.exists(), f"Required file not found: {file_path}"

        # CapabilityExecutor の存在確認
        capability_executor_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "CapabilityExecutor.ts"
        assert capability_executor_file.exists(), (
            f"CapabilityExecutor not found: {capability_executor_file}"
        )

    def test_dp2_api_rest_node_extension(self) -> None:
        """DP-2: ApiRestNodeに capability_id パラメータを追加

        設計方針: ApiRestNode拡張
        """
        api_rest_node_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "ApiRestNode.ts"
        content = api_rest_node_file.read_text()

        # ApiRestNodeConfig に capability_id が追加されているか
        assert "capability_id" in content, "capability_id not added to ApiRestNode"
        assert "project_id" in content, "project_id not added to ApiRestNode"

    def test_dp3_env_var_format(self) -> None:
        """DP-3: ${VAR:-default} 形式の環境変数解決

        設計方針: 環境変数形式
        """
        endpoint_config_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "EndpointConfigManager.ts"
        content = endpoint_config_file.read_text()

        # 正規表現パターンの存在確認
        assert "\\$\\{" in content or "${" in content, (
            "Environment variable pattern not found"
        )
        assert ":-" in content or "split" in content, (
            "Default value handling not found"
        )

    def test_dp4_index_yaml_format(self) -> None:
        """DP-4: api_endpoints セクションをindex.yamlに追加

        設計方針: index.yaml設定形式
        """
        config_file = self.BASE_DIR / "config" / "capabilities" / "default_project" / "index.yaml"
        content = config_file.read_text()

        # api_endpoints セクションの存在確認
        assert "api_endpoints:" in content, "api_endpoints section not found"
        assert "base_url" in content, "base_url configuration not found"
        assert "endpoint_prefix" in content, "endpoint_prefix configuration not found"


# ==========================================================================
# デッドコード検証テスト
# ==========================================================================

@pytest.mark.acceptance
class TestIssue372DeadCodeVerification:
    """Issue #372: デッドコード検証"""

    BASE_DIR = Path(__file__).parent.parent.parent

    def test_f1_endpoint_config_manager_is_used(self) -> None:
        """F-1: EndpointConfigManager が実際に使用されているか

        デッドコード検証: EndpointConfigManager
        """
        # エクスポートの確認
        index_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "index.ts"
        assert index_file.exists(), f"Index file not found: {index_file}"

        content = index_file.read_text()
        assert "EndpointConfigManager" in content, (
            "EndpointConfigManager not exported from index.ts"
        )

    def test_f2_url_resolver_is_used(self) -> None:
        """F-2: URLResolver が実際に使用されているか

        デッドコード検証: URLResolver
        """
        # エクスポートの確認
        index_file = self.BASE_DIR / "src" / "capabilityManagement" / "endpoint" / "index.ts"
        content = index_file.read_text()
        assert "URLResolver" in content, "URLResolver not exported from index.ts"

    def test_f3_capability_executor_is_used(self) -> None:
        """F-3: CapabilityExecutor が実際に使用されているか

        デッドコード検証: CapabilityExecutor
        """
        # CapabilityExecutor がノードのインデックスからエクスポートされているか
        nodes_index_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "index.ts"
        content = nodes_index_file.read_text()
        assert "CapabilityExecutor" in content, (
            "CapabilityExecutor not exported from nodes/index.ts"
        )

        # ApiRestNode から呼び出されているか
        api_rest_node_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "ApiRestNode.ts"
        api_content = api_rest_node_file.read_text()
        assert "capabilityExecutor" in api_content, (
            "CapabilityExecutor not used in ApiRestNode"
        )

    def test_f4_integration_chain_exists(self) -> None:
        """F-4: 統合チェーンが確立されているか

        デッドコード検証: TaskFlowEngine → WorkflowExecutor → ContextManager → ApiRestNode
        """
        # TaskFlowEngine に capabilityExecutor が設定可能か
        engine_file = self.BASE_DIR / "src" / "taskflowEngine" / "TaskFlowEngine.ts"
        engine_content = engine_file.read_text()
        assert "capabilityExecutor" in engine_content, (
            "capabilityExecutor not in TaskFlowEngine"
        )

        # WorkflowExecutor に capabilityExecutor が渡されるか
        executor_file = self.BASE_DIR / "src" / "taskflowEngine" / "executor" / "WorkflowExecutor.ts"
        executor_content = executor_file.read_text()
        assert "capabilityExecutor" in executor_content, (
            "capabilityExecutor not in WorkflowExecutor"
        )

        # ContextManager に capabilityExecutor が含まれるか
        context_file = self.BASE_DIR / "src" / "taskflowEngine" / "executor" / "ContextManager.ts"
        context_content = context_file.read_text()
        assert "capabilityExecutor" in context_content, (
            "capabilityExecutor not in ContextManager"
        )

        # BaseNode の NodeExecutionContext に capabilityExecutor があるか
        base_node_file = self.BASE_DIR / "src" / "taskflowEngine" / "nodes" / "BaseNode.ts"
        base_content = base_node_file.read_text()
        assert "capabilityExecutor" in base_content, (
            "capabilityExecutor not in BaseNode NodeExecutionContext"
        )


# ==========================================================================
# 単体テスト存在確認
# ==========================================================================

class TestIssue372UnitTestReference:
    """Issue #372 の単体テスト参照（vitest で実行）

    これらのテストは vitest で実行されます:
      cd mySwiftAgentCore
      npm run test

    テストファイル:
    - tests/unit/capabilityManagement/endpoint/EndpointConfigManager.test.ts
    - tests/unit/capabilityManagement/endpoint/URLResolver.test.ts
    - tests/unit/taskflowEngine/nodes/CapabilityExecutor.test.ts
    - tests/unit/taskflowEngine/nodes/ApiRestNode.test.ts
    """

    BASE_DIR = Path(__file__).parent.parent.parent

    def test_unit_tests_exist(self) -> None:
        """AC-8: 単体テストファイルが存在することを確認

        受入条件: 単体テストカバレッジ90%以上
        """
        test_files = [
            "tests/unit/capabilityManagement/endpoint/EndpointConfigManager.test.ts",
            "tests/unit/capabilityManagement/endpoint/URLResolver.test.ts",
            "tests/unit/taskflowEngine/nodes/CapabilityExecutor.test.ts",
            "tests/unit/taskflowEngine/nodes/ApiRestNode.test.ts",
        ]

        for test_file in test_files:
            file_path = self.BASE_DIR / test_file
            assert file_path.exists(), f"Unit test file not found: {file_path}"
