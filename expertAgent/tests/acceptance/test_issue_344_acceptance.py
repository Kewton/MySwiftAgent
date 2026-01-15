"""
Issue #344 APIスキーマ検証 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_344_acceptance.py -v

検証内容:
- AC-1: APISchemaValidatorがValidationPipelineに統合されている
- AC-2: 正しいパラメータが検証に通過する
- AC-3: typo検出（query → queries）が動作する
- AC-4: 必須パラメータ欠落の検出が動作する
- AC-5: 型不一致の検出が動作する
"""

import os

import pytest
import requests


@pytest.mark.acceptance
class TestIssue344APISchemaValidatorAcceptance:
    """Issue #344: APISchemaValidator の E2E 検証"""

    # サービスURL
    EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "http://localhost:8004")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            assert response.status_code == 200, "expertAgent is not healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip(
                f"expertAgent is not running at {self.EXPERT_AGENT_URL}. "
                "Run: USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh"
            )

    # ==========================================================================
    # 受入条件1: APISchemaValidatorの統合確認
    # ==========================================================================

    def test_ac1_api_schema_validator_integrated_in_pipeline(self) -> None:
        """受入条件1: APISchemaValidatorがValidationPipelineに統合されている"""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        pipeline = ValidationPipeline()

        # パイプラインにAPISchemaValidatorが含まれている
        validators = pipeline.validators if hasattr(pipeline, "validators") else []
        api_schema_validator_found = any(
            isinstance(v, APISchemaValidator) for v in validators
        )
        assert api_schema_validator_found, (
            "APISchemaValidator not found in ValidationPipeline"
        )

    def test_ac1_validation_error_codes_exist(self) -> None:
        """受入条件1: 必要なValidationErrorCodeが存在する"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode

        # 全エラーコードが存在
        assert hasattr(ValidationErrorCode, "UNKNOWN_API_PARAMETER")
        assert hasattr(ValidationErrorCode, "MISSING_REQUIRED_PARAMETER")
        assert hasattr(ValidationErrorCode, "PARAMETER_TYPE_MISMATCH")
        assert hasattr(ValidationErrorCode, "PARAMETER_NAME_MISMATCH")

    # ==========================================================================
    # 受入条件2: 正しいパラメータの検証
    # ==========================================================================

    def test_ac2_valid_google_search_workflow(self) -> None:
        """受入条件2: 正しいGoogle Search workflowが検証に通過する"""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],  # 正しい: 配列
                            "num": 5,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) == 0, f"Valid workflow should pass: {errors}"

    def test_ac2_valid_fetch_web_content_workflow(self) -> None:
        """受入条件2: 正しいfetch_web_content workflowが検証に通過する"""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            "url": ":source.user_input.target_url",  # 必須パラメータ
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) == 0, f"Valid workflow should pass: {errors}"

    # ==========================================================================
    # 受入条件3: Typo検出（query → queries）
    # ==========================================================================

    def test_ac3_typo_detection_query_to_queries(self) -> None:
        """受入条件3: 'query' → 'queries' のtypoを検出する"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # typo: 正しくは queries
                            "num": 5,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) >= 1, "Typo should be detected"

        # PARAMETER_NAME_MISMATCH エラーコードが使用される
        typo_error = next(
            (
                e
                for e in errors
                if e.code == ValidationErrorCode.PARAMETER_NAME_MISMATCH
            ),
            None,
        )
        assert typo_error is not None, (
            f"Expected PARAMETER_NAME_MISMATCH, got: {[e.code for e in errors]}"
        )

        # 'queries' への修正が提案される
        assert "queries" in typo_error.suggestion.lower(), (
            f"Suggestion should include 'queries': {typo_error.suggestion}"
        )

    def test_ac3_typo_detection_num_results_to_num(self) -> None:
        """受入条件3: 'num_results' → 'num' のtypoを検出する"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],
                            "num_results": 5,  # typo: 正しくは num
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) >= 1, "Typo should be detected"

        # PARAMETER_NAME_MISMATCH エラーコードが使用される
        typo_error = next(
            (
                e
                for e in errors
                if e.code == ValidationErrorCode.PARAMETER_NAME_MISMATCH
            ),
            None,
        )
        assert typo_error is not None, (
            f"Expected PARAMETER_NAME_MISMATCH, got: {[e.code for e in errors]}"
        )

    # ==========================================================================
    # 受入条件4: 必須パラメータ欠落の検出
    # ==========================================================================

    def test_ac4_missing_required_queries(self) -> None:
        """受入条件4: 必須パラメータ 'queries' の欠落を検出する"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "num": 5,  # queries が欠落
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) >= 1, "Missing required parameter should be detected"

        # MISSING_REQUIRED_PARAMETER エラーコードが使用される
        missing_error = next(
            (
                e
                for e in errors
                if e.code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER
            ),
            None,
        )
        assert missing_error is not None, (
            f"Expected MISSING_REQUIRED_PARAMETER, got: {[e.code for e in errors]}"
        )
        assert "queries" in missing_error.message.lower()

    def test_ac4_missing_required_url(self) -> None:
        """受入条件4: 必須パラメータ 'url' の欠落を検出する（fetch_web_content）"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            "upload_to_drive": True,  # url が欠落
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) >= 1, "Missing required parameter should be detected"

        missing_error = next(
            (
                e
                for e in errors
                if e.code == ValidationErrorCode.MISSING_REQUIRED_PARAMETER
            ),
            None,
        )
        assert missing_error is not None

    # ==========================================================================
    # 受入条件5: 型不一致の検出
    # ==========================================================================

    def test_ac5_type_mismatch_queries_should_be_array(self) -> None:
        """受入条件5: 'queries' が配列でない場合に型不一致を検出する"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": "単一の文字列",  # 型不一致: 配列であるべき
                            "num": 5,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        assert len(errors) >= 1, "Type mismatch should be detected"

        type_error = next(
            (
                e
                for e in errors
                if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH
            ),
            None,
        )
        assert type_error is not None, (
            f"Expected PARAMETER_TYPE_MISMATCH, got: {[e.code for e in errors]}"
        )
        assert "array" in type_error.message.lower()

    def test_ac5_type_mismatch_skip_reference(self) -> None:
        """受入条件5: 参照（:で始まる）は型検証をスキップする"""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator = APISchemaValidator()

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": ":source.user_input.queries",  # 参照 - 型検証スキップ
                            "num": 5,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }

        errors = validator.validate(workflow)
        # 型エラーがないことを確認
        type_errors = [
            e for e in errors if e.code == ValidationErrorCode.PARAMETER_TYPE_MISMATCH
        ]
        assert len(type_errors) == 0, (
            f"Reference should skip type validation: {type_errors}"
        )


@pytest.mark.acceptance
class TestIssue344Integration:
    """Issue #344 統合確認テスト"""

    def test_api_schema_validator_in_validation_pipeline(self) -> None:
        """APISchemaValidatorがValidationPipelineに統合されている"""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        pipeline = ValidationPipeline()

        # APISchemaValidatorがパイプラインに含まれている
        validators = pipeline.validators if hasattr(pipeline, "validators") else []
        api_validator = next(
            (v for v in validators if isinstance(v, APISchemaValidator)), None
        )
        assert api_validator is not None, (
            "APISchemaValidator should be in ValidationPipeline"
        )

    def test_parameter_aliases_coverage(self) -> None:
        """PARAMETER_ALIASESが主要APIをカバーしている"""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        # 主要APIのカバレッジ確認
        assert "/utility/google_search" in PARAMETER_ALIASES
        assert "/utility/fetch_web_content" in PARAMETER_ALIASES

        # google_search のよくあるtypo
        google_search_aliases = PARAMETER_ALIASES["/utility/google_search"]
        assert "query" in google_search_aliases, "Should detect 'query' -> 'queries'"
        assert "num_results" in google_search_aliases, (
            "Should detect 'num_results' -> 'num'"
        )


@pytest.mark.acceptance
@pytest.mark.external
class TestIssue344E2E:
    """Issue #344 E2Eテスト（外部API呼び出しあり）"""

    EXPERT_AGENT_URL = os.getenv("EXPERT_AGENT_URL", "http://localhost:8004")

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """サービス起動確認"""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("expertAgent is not running")

    def test_e2e_validation_pipeline_via_api(self) -> None:
        """E2E: ValidationPipeline経由でAPIスキーマ検証が動作する

        Note: このテストはV2が有効でジョブ生成が可能な場合のみ動作します。
        """
        # V2が有効か確認
        try:
            response = requests.get(
                f"{self.EXPERT_AGENT_URL}/v1/feature-flags", timeout=10
            )
            if response.status_code != 200:
                pytest.skip("Feature flags endpoint not available")

            flags = response.json()
            if not flags.get("use_job_generator_v2", False):
                pytest.skip("V2 Job Generator is not enabled")
        except Exception as e:
            pytest.skip(f"Cannot check V2 status: {e}")

        # この時点でV2が有効 - 検証パイプラインがAPISchemaValidatorを含むことを確認済み
        # 実際のジョブ生成はAPIキーが必要なため、統合確認のみ
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        pipeline = ValidationPipeline()
        validators = pipeline.validators if hasattr(pipeline, "validators") else []

        api_validator = next(
            (v for v in validators if isinstance(v, APISchemaValidator)), None
        )
        assert api_validator is not None, (
            "APISchemaValidator should be in ValidationPipeline"
        )
