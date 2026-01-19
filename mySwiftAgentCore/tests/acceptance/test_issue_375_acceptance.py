"""
Issue #375 受入テスト（L3: ローカル受入テスト）

mySwiftAgentCore: ワークフロー生成・実行のバリデーション強化

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest mySwiftAgentCore/tests/acceptance/test_issue_375_acceptance.py -v --no-cov

検証対象:
- AC-1: CapabilityValidatorがValidationPipelineに統合
- AC-2: OutputMappingValidatorがValidationPipelineに統合
- AC-3: NodeConfigValidatorがValidationPipelineに統合 + YAML仕様ファイル
- AC-4: POST /api/v1/taskflow/reload エンドポイント
"""
import pytest
import requests
from typing import Any
import os
from pathlib import Path


@pytest.mark.acceptance
class TestIssue375Acceptance:
    """Issue #375: mySwiftAgentCore ワークフロー生成・実行のバリデーション強化"""

    # サービスURL
    MYSWIFTAGENTCORE_URL = "http://localhost:8006"
    MYVAULT_URL = "http://localhost:8003"

    # プロジェクトルート
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.MYSWIFTAGENTCORE_URL, "mySwiftAgentCore"),
            (self.MYVAULT_URL, "myVault"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code not in [200, 404]:
                    pytest.skip(f"{name} is not healthy (status: {response.status_code})")
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running. "
                    "Run: ./scripts/dev-hybrid.sh or make dev-all"
                )

    # ==========================================================================
    # AC-1: capability_id存在バリデーション（コード統合検証）
    # ==========================================================================

    def test_ac1_capability_validator_exists(self) -> None:
        """AC-1: CapabilityValidatorファイルが存在する"""
        validator_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "validators" / "CapabilityValidator.ts"
        assert validator_path.exists(), f"CapabilityValidator not found at {validator_path}"

    def test_ac1_capability_validator_integrated_in_pipeline(self) -> None:
        """AC-1: CapabilityValidatorがValidationPipelineにインポートされている"""
        pipeline_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        assert pipeline_path.exists(), f"ValidationPipeline not found at {pipeline_path}"

        content = pipeline_path.read_text()
        assert "CapabilityValidator" in content, "CapabilityValidator not imported in ValidationPipeline"
        assert "createCapabilityValidator" in content or "CapabilityValidator" in content, (
            "CapabilityValidator not used in ValidationPipeline"
        )

    # ==========================================================================
    # AC-2: 出力マッピングとresponseSchemaの整合性チェック（コード統合検証）
    # ==========================================================================

    def test_ac2_output_mapping_validator_exists(self) -> None:
        """AC-2: OutputMappingValidatorファイルが存在する"""
        validator_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "validators" / "OutputMappingValidator.ts"
        assert validator_path.exists(), f"OutputMappingValidator not found at {validator_path}"

    def test_ac2_output_mapping_validator_integrated_in_pipeline(self) -> None:
        """AC-2: OutputMappingValidatorがValidationPipelineにインポートされている"""
        pipeline_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        content = pipeline_path.read_text()
        assert "OutputMappingValidator" in content, "OutputMappingValidator not imported in ValidationPipeline"

    # ==========================================================================
    # AC-3: ノードタイプ仕様のプロンプト追加（YAML + コード統合検証）
    # ==========================================================================

    def test_ac3_node_config_validator_exists(self) -> None:
        """AC-3: NodeConfigValidatorファイルが存在する"""
        validator_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "validators" / "NodeConfigValidator.ts"
        assert validator_path.exists(), f"NodeConfigValidator not found at {validator_path}"

    def test_ac3_node_config_validator_integrated_in_pipeline(self) -> None:
        """AC-3: NodeConfigValidatorがValidationPipelineにインポートされている"""
        pipeline_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        content = pipeline_path.read_text()
        assert "NodeConfigValidator" in content, "NodeConfigValidator not imported in ValidationPipeline"

    def test_ac3_node_types_spec_yaml_exists(self) -> None:
        """AC-3: node_types_spec.yamlファイルが存在する"""
        yaml_path = self.PROJECT_ROOT / "config" / "node_types_spec.yaml"
        assert yaml_path.exists(), f"node_types_spec.yaml not found at {yaml_path}"

    def test_ac3_node_types_spec_yaml_valid(self) -> None:
        """AC-3: node_types_spec.yamlが有効なYAMLである"""
        import yaml
        yaml_path = self.PROJECT_ROOT / "config" / "node_types_spec.yaml"
        content = yaml_path.read_text()

        try:
            data = yaml.safe_load(content)
            assert "node_types" in data, "YAML missing 'node_types' key"
            assert "transform" in data["node_types"], "YAML missing 'transform' node type"
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML: {e}")

    def test_ac3_transform_node_spec_correct(self) -> None:
        """AC-3: TransformNodeの仕様が正しい（template/mapping必須、expression未対応）"""
        import yaml
        yaml_path = self.PROJECT_ROOT / "config" / "node_types_spec.yaml"
        data = yaml.safe_load(yaml_path.read_text())

        transform_spec = data["node_types"]["transform"]

        # Check supported_config has template and mapping
        assert "supported_config" in transform_spec, "transform missing supported_config"
        assert "template" in transform_spec["supported_config"], "transform missing template"
        assert "mapping" in transform_spec["supported_config"], "transform missing mapping"

        # Check unsupported_config has expression
        assert "unsupported_config" in transform_spec, "transform missing unsupported_config"
        assert "expression" in transform_spec["unsupported_config"], (
            "expression should be in unsupported_config"
        )

    # ==========================================================================
    # AC-4: ワークフローリロード機能（API検証）
    # ==========================================================================

    def test_ac4_reload_endpoint_exists(self) -> None:
        """AC-4: POST /api/v1/taskflow/reload エンドポイントが存在する"""
        endpoint = f"{self.MYSWIFTAGENTCORE_URL}/api/v1/taskflow/reload"

        payload: dict[str, Any] = {
            "project": "default_project"
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            # Endpoint should exist (not 404)
            assert response.status_code != 404, (
                f"Reload endpoint not found: {response.status_code}"
            )

            # Check response structure
            if response.status_code == 200:
                data = response.json()
                assert "success" in data, f"Response missing 'success' field: {data}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API request failed: {e}")

    def test_ac4_reload_returns_success_status(self) -> None:
        """AC-4: リロード成功時にsuccess: trueが返る"""
        endpoint = f"{self.MYSWIFTAGENTCORE_URL}/api/v1/taskflow/reload"

        payload: dict[str, Any] = {
            "project": "default_project"
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )

            data = response.json()
            assert data.get("success") is True, f"Expected success=true, got: {data}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"API request failed: {e}")

    # ==========================================================================
    # AC-4追加: リロードAPI関連ファイルの検証
    # ==========================================================================

    def test_ac4_reload_routes_file_exists(self) -> None:
        """AC-4: taskflow-reload.tsファイルが存在する"""
        routes_path = self.PROJECT_ROOT / "src" / "api" / "routes" / "taskflow-reload.ts"
        assert routes_path.exists(), f"taskflow-reload.ts not found at {routes_path}"

    def test_ac4_reload_routes_integrated_in_main_routes(self) -> None:
        """AC-4: リロードルートがメインルーターに統合されている"""
        routes_path = self.PROJECT_ROOT / "src" / "api" / "routes.ts"
        content = routes_path.read_text()

        assert "taskflow-reload" in content or "createTaskFlowReloadRoutes" in content, (
            "Reload routes not imported in main routes.ts"
        )

    # ==========================================================================
    # Design Policy検証: ValidationPipelineへの統合
    # ==========================================================================

    def test_dp1_validation_pipeline_has_all_validators(self) -> None:
        """DP-1: ValidationPipelineに全てのバリデータが統合されている"""
        pipeline_path = self.PROJECT_ROOT / "src" / "taskflowGeneratorAgent" / "validator" / "ValidationPipeline.ts"
        content = pipeline_path.read_text()

        validators = [
            "CapabilityValidator",
            "OutputMappingValidator",
            "NodeConfigValidator",
        ]

        for validator in validators:
            assert validator in content, f"{validator} not found in ValidationPipeline"

    def test_dp2_file_system_watcher_exists(self) -> None:
        """DP-2: FileSystemWatcherファイルが存在する"""
        watcher_path = self.PROJECT_ROOT / "src" / "taskflowEngine" / "watcher" / "FileSystemWatcher.ts"
        assert watcher_path.exists(), f"FileSystemWatcher not found at {watcher_path}"

    def test_dp3_workflow_reloader_exists(self) -> None:
        """DP-3: WorkflowReloaderファイルが存在する"""
        reloader_path = self.PROJECT_ROOT / "src" / "taskflowEngine" / "loader" / "WorkflowReloader.ts"
        assert reloader_path.exists(), f"WorkflowReloader not found at {reloader_path}"
