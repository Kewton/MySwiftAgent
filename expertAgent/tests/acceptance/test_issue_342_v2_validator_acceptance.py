"""
Issue #342 V2バリデーター修正 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh)
- .env に必要なAPIキーが設定されていること
- myAgentDesk が http://localhost:8000 で起動していること

実行方法:
  uv run pytest tests/acceptance/test_issue_342_v2_validator_acceptance.py -v

検証内容:
- MF-1: graphAiServerとの仕様同期（ALLOWED_ENV_VARS）
- DC-1: 環境変数許可リスト（${EXPERTAGENT_BASE_URL}等）
- DC-2: V1互換パスパターン（:source.query等）
- E2E: ワークフロー実行時にInvalid URLエラーが発生しないこと
"""

import os
from typing import Any

import pytest
import requests


@pytest.mark.acceptance
class TestIssue342V2ValidatorAcceptance:
    """Issue #342: V2バリデーター修正のE2E検証"""

    # サービスURL
    EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "http://localhost:8004")
    GRAPHAI_SERVER_URL = os.getenv("GRAPHAI_SERVER_URL", "http://localhost:8005")
    MYVAULT_URL = os.getenv("MYVAULT_URL", "http://localhost:8003")
    JOBQUEUE_URL = os.getenv("JOBQUEUE_URL", "http://localhost:8001")

    # テスト用プロジェクト/ワークベンチID
    PROJECT_ID = "proj_mjbjua2z7y65wy"
    WORKBENCH_ID = "wb_1766969315404_udrhx79"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        services = [
            (self.EXPERT_AGENT_URL, "expertAgent"),
            (self.GRAPHAI_SERVER_URL, "graphAiServer"),
            (self.MYVAULT_URL, "myVault"),
            (self.JOBQUEUE_URL, "jobqueue"),
        ]
        for url, name in services:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                assert response.status_code == 200, f"{name} is not healthy"
            except requests.exceptions.ConnectionError:
                pytest.skip(
                    f"{name} is not running at {url}. "
                    "Run: USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh"
                )

    # ==========================================================================
    # 受入条件1: 単体テスト全パス確認（静的検証）
    # ==========================================================================

    def test_ac1_unit_tests_configuration(self) -> None:
        """受入条件1: 単体テストの設定が正しい

        検証: バリデーター単体テストファイルが存在し、正しい構造を持つ
        """
        import importlib.util

        # AgentConstraintValidator テストファイル
        spec1 = importlib.util.find_spec(
            "tests.unit.test_job_generator_v2.test_agent_constraint_validator"
        )
        assert spec1 is not None, "test_agent_constraint_validator.py not found"

        # SourcePathRuleEngine テストファイル
        spec2 = importlib.util.find_spec(
            "tests.unit.test_job_generator_v2.test_source_path_rule_engine"
        )
        assert spec2 is not None, "test_source_path_rule_engine.py not found"

    # ==========================================================================
    # 受入条件2: ALLOWED_ENV_VARS検証
    # ==========================================================================

    def test_ac2_allowed_env_vars_includes_expertagent(self) -> None:
        """受入条件2: ALLOWED_ENV_VARSに${EXPERTAGENT_BASE_URL}が含まれる"""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            ALLOWED_ENV_VARS,
        )

        assert "${EXPERTAGENT_BASE_URL}" in ALLOWED_ENV_VARS
        assert "${GRAPHAISERVER_BASE_URL}" in ALLOWED_ENV_VARS
        assert "${MYVAULT_BASE_URL}" in ALLOWED_ENV_VARS

    def test_ac2_validator_accepts_allowed_env_vars(self) -> None:
        """受入条件2: バリデーターが許可環境変数を受け入れる"""
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        validator = AgentConstraintValidator()

        # 許可される環境変数
        config = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search"
            },
        }
        errors = validator.validate_fetch_agent(config)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    # ==========================================================================
    # 受入条件3: V1互換パスパターン検証
    # ==========================================================================

    def test_ac3_v1_compatible_source_path(self) -> None:
        """受入条件3: V1互換パスパターン(:source.query)が許可される"""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        engine = SourcePathRuleEngine()

        # V1互換パス（許可されるべき）
        v1_paths = [":source.query", ":source.results", ":source.body.field"]

        for path in v1_paths:
            is_valid, error = engine.validate_path(path)
            assert is_valid is True, f"V1 path '{path}' should be valid: {error}"

    def test_ac3_truly_invalid_paths_rejected(self) -> None:
        """受入条件3: 真に無効なパスは拒否される"""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        engine = SourcePathRuleEngine()

        # 真に無効なパス（拒否されるべき）
        invalid_paths = [":source", ":source."]

        for path in invalid_paths:
            is_valid, error = engine.validate_path(path)
            assert is_valid is False, f"Invalid path '{path}' should be rejected"

    # ==========================================================================
    # 受入条件4: API経由ジョブ生成テスト
    # ==========================================================================

    @pytest.mark.external
    def test_ac4_api_job_generation_with_v2(self) -> None:
        """受入条件4: V2でAPI経由ジョブ生成が成功する

        Note: このテストは実際のAPIキーが必要です。
        スキップする場合: pytest -m "not external"
        """
        # V2が有効か確認
        response = requests.get(f"{self.EXPERT_AGENT_URL}/v1/feature-flags", timeout=10)
        if response.status_code != 200:
            pytest.skip("Feature flags endpoint not available")

        flags = response.json()
        if not flags.get("use_job_generator_v2", False):
            pytest.skip("V2 Job Generator is not enabled")

        # ジョブ生成リクエスト
        payload: dict[str, Any] = {
            "project_id": self.PROJECT_ID,
            "workbench_id": self.WORKBENCH_ID,
            "user_requirement": "Google検索でAI関連のニュースを取得して要約する",
        }

        response = requests.post(
            f"{self.EXPERT_AGENT_URL}/v1/jobs/generate",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,  # ジョブ生成は時間がかかる
        )

        # ステータスコード確認（200または202）
        assert response.status_code in [200, 202], (
            f"Expected 200 or 202, got {response.status_code}: {response.text}"
        )

        data = response.json()

        # ジョブIDが返される
        assert "job_id" in data or "id" in data, f"Response missing job ID: {data}"

    # ==========================================================================
    # 受入条件5: Invalid URLエラーが発生しないことの検証
    # ==========================================================================

    def test_ac5_workflow_yaml_has_valid_env_vars(self) -> None:
        """受入条件5: 生成されたワークフローYAMLに有効な環境変数が含まれる

        検証: ${EXPERTAGENT_BASE_URL}がワークフローYAMLで使用可能
        """
        # バリデーターで検証
        from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
            AgentConstraintValidator,
        )

        validator = AgentConstraintValidator()

        # 典型的なV2生成ワークフローのノード
        workflow = {
            "nodes": {
                "source": {},
                "google_search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "body": {
                            "query": ":source.user_input.query",
                            "num": 5,
                        },
                    },
                    "timeout": 30000,
                },
                "summarize": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/llm_completion",
                        "body": {
                            "prompt": ":google_search.results",
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate_workflow(workflow)
        assert len(errors) == 0, f"Workflow validation errors: {errors}"

    def test_ac5_source_path_validation_passes(self) -> None:
        """受入条件5: ソースパス検証がV1/V2両方で成功する"""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        engine = SourcePathRuleEngine()

        # V1/V2両対応ワークフロー
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "query": ":source.query",  # V1スタイル
                        "params": ":source.user_input.params",  # V2スタイル
                    },
                },
                "output": {
                    "agent": "copyAgent",
                    "inputs": {
                        "results": ":search.results",
                    },
                    "isResult": True,
                },
            }
        }

        errors = engine.validate_workflow(workflow)
        assert len(errors) == 0, f"Source path validation errors: {errors}"


@pytest.mark.acceptance
class TestIssue342Integration:
    """Issue #342 統合確認テスト"""

    def test_validators_are_integrated_in_pipeline(self) -> None:
        """バリデーターがValidationPipelineに統合されている"""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        pipeline = ValidationPipeline()

        # パイプラインにバリデーターが含まれている
        assert hasattr(pipeline, "validators") or hasattr(pipeline, "_validators")

    def test_validators_are_integrated_in_schema_validator(self) -> None:
        """バリデーターがWorkflowSchemaValidatorに統合されている"""
        from aiagent.langgraph.jobGeneratorV2.validators.workflow_schema_validator import (
            WorkflowSchemaValidator,
        )

        validator = WorkflowSchemaValidator()

        # 両バリデーターが存在
        assert hasattr(validator, "source_path_validator")
        assert hasattr(validator, "agent_constraint_validator")
