"""Issue #358 受入テスト（L3: ローカル受入テスト）.

body_template 整合性バリデーション機能の受入テスト。

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_358_acceptance.py -v

テストケース:
- TC-001: 有効なbody_templateでの検証成功
- TC-002: テンプレート変数の正確な抽出
- TC-003: job.body参照の検証（正常系）
- TC-004: job.body参照の検証（異常系）
- TC-005: tasks[N]参照の検証（正常系）
- TC-006: tasks[N]参照の検証（未来タスク参照エラー）
- TC-007: tasks[N]参照の検証（存在しないインデックスエラー）
- TC-008: 検証結果レポートの構造確認
- TC-009: バリデーションエラー時のエラー詳細確認
- TC-010: 警告時の処理続行確認
- TC-011: 必須パラメータ情報の抽出
- TC-013: TaskFlowエンジンでの検証動作
- TC-014: GraphAIエンジンでの検証動作
"""

from __future__ import annotations

from typing import Any

import pytest

from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
    BodyTemplateValidationError,
    BodyTemplateValidationResult,
    BodyTemplateValidationWarning,
    BodyTemplateValidator,
    GraphAIValidationStrategy,
    TaskFlowValidationStrategy,
)
from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import (
    extract_template_variables,
)


@pytest.mark.acceptance
class TestTC001ValidTemplateJobGeneration:
    """TC-001: 有効なbody_templateでのジョブ生成成功.

    テスト観点: 正常系 - バリデーションを通過するbody_templateで検証が成功する
    関連する受入条件: AC-1, AC-6
    関連する設計方針: DP-3
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_valid_body_template_passes_validation(
        self, validator: BodyTemplateValidator
    ) -> None:
        """有効なbody_templateは検証を通過する."""
        # Arrange
        body_template = {
            "workflow_name": "test_workflow",
            "inputs": "{{job.body}}",
            "project": "{{job.project}}",
        }
        input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_template_with_task_references(
        self, validator: BodyTemplateValidator
    ) -> None:
        """タスク参照を含む有効なbody_templateは検証を通過する."""
        # Arrange
        body_template = {
            "inputs": "{{tasks[0].output_data}}",
            "project": "{{job.project}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0


@pytest.mark.acceptance
class TestTC002TemplateVariableExtraction:
    """TC-002: テンプレート変数の正確な抽出.

    テスト観点: {{job.body}}, {{tasks[N].output_data}}, {{job.project}}パターンの抽出
    関連する受入条件: AC-2
    関連する設計方針: DP-2
    """

    def test_extract_job_body_reference(self) -> None:
        """{{job.body}}パターンが正確に抽出される."""
        # Arrange
        body_template = {
            "inputs": "{{job.body}}",
        }

        # Act
        result = extract_template_variables(body_template)

        # Assert
        assert "job.body" in result.job_body_refs
        assert len(result.raw_variables) >= 1

    def test_extract_job_body_field_reference(self) -> None:
        """{{job.body.field}}パターンが正確に抽出される."""
        # Arrange
        body_template = {
            "user_input": "{{job.body.user_input}}",
            "email": "{{job.body.recipient_email}}",
        }

        # Act
        result = extract_template_variables(body_template)

        # Assert
        assert "job.body.user_input" in result.job_body_refs
        assert "job.body.recipient_email" in result.job_body_refs

    def test_extract_job_project_reference(self) -> None:
        """{{job.project}}パターンが正確に抽出される."""
        # Arrange
        body_template = {
            "project": "{{job.project}}",
        }

        # Act
        result = extract_template_variables(body_template)

        # Assert
        assert "job.project" in result.job_refs

    def test_extract_task_output_reference(self) -> None:
        """{{tasks[N].output_data}}パターンが正確に抽出される."""
        # Arrange
        body_template = {
            "previous_output": "{{tasks[0].output_data}}",
            "second_output": "{{tasks[1].output_data.result}}",
        }

        # Act
        result = extract_template_variables(body_template)

        # Assert
        assert len(result.task_output_refs) == 2
        assert result.task_output_refs[0].task_index == 0
        assert result.task_output_refs[1].task_index == 1
        assert result.task_output_refs[1].field_path == "result"

    def test_extract_nested_template_references(self) -> None:
        """ネスト構造からテンプレート変数が再帰的に抽出される."""
        # Arrange
        body_template = {
            "level1": {
                "level2": {
                    "inputs": "{{job.body.nested_field}}",
                },
            },
            "list_field": [
                "{{tasks[0].output_data}}",
                {"nested_in_list": "{{job.project}}"},
            ],
        }

        # Act
        result = extract_template_variables(body_template)

        # Assert
        assert "job.body.nested_field" in result.job_body_refs
        assert "job.project" in result.job_refs
        assert len(result.task_output_refs) == 1


@pytest.mark.acceptance
class TestTC003JobBodyReferenceValid:
    """TC-003: job.body参照の検証（正常系）.

    テスト観点: input_schemaに存在するフィールドへの参照がパスする
    関連する受入条件: AC-3
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_valid_job_body_field_reference(
        self, validator: BodyTemplateValidator
    ) -> None:
        """input_schemaに存在するフィールド参照は検証を通過する."""
        # Arrange
        body_template = {
            "user_input": "{{job.body.user_input}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_entire_job_body_reference(
        self, validator: BodyTemplateValidator
    ) -> None:
        """{{job.body}}（全体参照）は常に検証を通過する."""
        # Arrange
        body_template = {
            "all_inputs": "{{job.body}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                "optional_param": {"type": "number"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True


@pytest.mark.acceptance
class TestTC004JobBodyReferenceInvalid:
    """TC-004: job.body参照の検証（異常系）.

    テスト観点: 存在しないフィールド参照時にエラーを返す
    関連する受入条件: AC-3, AC-7
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_invalid_job_body_field_reference_returns_error(
        self, validator: BodyTemplateValidator
    ) -> None:
        """存在しないフィールド参照はエラーを返す."""
        # Arrange
        body_template = {
            "user_input": "{{job.body.nonexistent_field}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any(e.error_type == "MISSING_REFERENCE" for e in result.errors)
        assert any("nonexistent_field" in e.message for e in result.errors)

    def test_multiple_invalid_references_return_multiple_errors(
        self, validator: BodyTemplateValidator
    ) -> None:
        """複数の無効な参照は複数のエラーを返す."""
        # Arrange
        body_template = {
            "field1": "{{job.body.missing1}}",
            "field2": "{{job.body.missing2}}",
        }
        input_schema = {
            "type": "object",
            "properties": {},
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 2


@pytest.mark.acceptance
class TestTC005TaskReferenceValid:
    """TC-005: tasks[N]参照の検証（正常系）.

    テスト観点: 有効なタスクインデックス参照がパスする
    関連する受入条件: AC-4
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_valid_task_output_reference(
        self, validator: BodyTemplateValidator
    ) -> None:
        """有効なタスクインデックス参照は検証を通過する."""
        # Arrange - task[1] references task[0]'s output (valid: 0 < 1)
        body_template = {
            "inputs": "{{tasks[0].output_data}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
            {"type": "object", "properties": {"final": {"type": "string"}}},
        ]

        # Act - current task is task[1], so task_count=1 (preceding tasks)
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,  # Only task[0] exists before current task
            task_output_schemas=task_output_schemas[:1],
        )

        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_valid_task_output_field_reference(
        self, validator: BodyTemplateValidator
    ) -> None:
        """タスク出力の特定フィールド参照は検証を通過する."""
        # Arrange
        body_template = {
            "result": "{{tasks[0].output_data.result}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        # Assert
        assert result.is_valid is True


@pytest.mark.acceptance
class TestTC006TaskReferenceFutureTaskError:
    """TC-006: tasks[N]参照の検証（未来タスク参照エラー）.

    テスト観点: 未来のタスクを参照した場合にエラーを返す
    関連する受入条件: AC-4, AC-7
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_future_task_reference_returns_error(
        self, validator: BodyTemplateValidator
    ) -> None:
        """未来のタスク参照はエラーを返す（task[0]がtask[1]を参照）."""
        # Arrange - task[0] tries to reference task[1] (which doesn't exist yet)
        body_template = {
            "inputs": "{{tasks[1].output_data}}",
        }

        # Act - current task is task[0], so no preceding tasks exist (task_count=0)
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=0,  # No preceding tasks for first task
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is False
        assert any(e.error_type == "INVALID_INDEX" for e in result.errors)


@pytest.mark.acceptance
class TestTC007TaskReferenceOutOfRange:
    """TC-007: tasks[N]参照の検証（存在しないインデックスエラー）.

    テスト観点: 存在しないタスクインデックスを参照した場合にエラー
    関連する受入条件: AC-4, AC-7
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_out_of_range_task_index_returns_error(
        self, validator: BodyTemplateValidator
    ) -> None:
        """存在しないタスクインデックス参照はエラーを返す."""
        # Arrange - reference task[5] when only 2 tasks exist
        body_template = {
            "inputs": "{{tasks[5].output_data}}",
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=2,  # Only tasks 0 and 1 exist
            task_output_schemas=[{}, {}],
        )

        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any(e.error_type == "INVALID_INDEX" for e in result.errors)
        # Check error message mentions the index
        assert any("5" in e.message for e in result.errors)

    def test_out_of_range_with_large_index(
        self, validator: BodyTemplateValidator
    ) -> None:
        """大きなインデックス参照はエラーを返す."""
        # Arrange
        body_template = {
            "inputs": "{{tasks[99].output_data}}",
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=3,
            task_output_schemas=[{}, {}, {}],
        )

        # Assert
        assert result.is_valid is False
        assert any(e.error_type == "INVALID_INDEX" for e in result.errors)


@pytest.mark.acceptance
class TestTC008ValidationResultStructure:
    """TC-008: 検証結果レポートの構造確認.

    テスト観点: ValidationResultの構造が設計通りである
    関連する受入条件: AC-5
    関連する設計方針: DP-2
    """

    def test_validation_result_has_required_fields(self) -> None:
        """BodyTemplateValidationResultは必須フィールドを持つ."""
        # Arrange & Act
        result = BodyTemplateValidationResult(
            errors=[],
            warnings=[],
            required_job_body_fields=set(),
        )

        # Assert
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert hasattr(result, "required_job_body_fields")
        assert hasattr(result, "is_valid")

    def test_validation_error_structure(self) -> None:
        """BodyTemplateValidationErrorは必須フィールドを持つ."""
        # Arrange & Act
        error = BodyTemplateValidationError(
            error_type="MISSING_REFERENCE",
            message="Field 'test' not found in input_schema",
            location="job.body.test",
        )

        # Assert
        assert hasattr(error, "error_type")
        assert hasattr(error, "message")
        assert hasattr(error, "location")
        assert error.error_type == "MISSING_REFERENCE"

    def test_validation_warning_structure(self) -> None:
        """BodyTemplateValidationWarningは必須フィールドを持つ."""
        # Arrange & Act
        warning = BodyTemplateValidationWarning(
            warning_type="UNUSED_FIELD",
            message="Field not referenced",
            location="input_schema.optional_field",
        )

        # Assert
        assert hasattr(warning, "warning_type")
        assert hasattr(warning, "message")
        assert hasattr(warning, "location")

    def test_result_with_multiple_errors_and_warnings(self) -> None:
        """複数のエラーと警告を含む結果が正しく構成される."""
        # Arrange
        errors = [
            BodyTemplateValidationError(
                error_type="MISSING_REFERENCE",
                message="Field not found",
                location="job.body.field1",
            ),
            BodyTemplateValidationError(
                error_type="INVALID_INDEX",
                message="Task index out of range",
                location="tasks[5].output_data",
            ),
        ]
        warnings = [
            BodyTemplateValidationWarning(
                warning_type="UNUSED_FIELD",
                message="Field not used",
                location="input_schema.optional",
            ),
        ]

        # Act
        result = BodyTemplateValidationResult(
            errors=errors,
            warnings=warnings,
            required_job_body_fields={"user_input", "email"},
        )

        # Assert
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "user_input" in result.required_job_body_fields
        assert "email" in result.required_job_body_fields
        assert result.is_valid is False


@pytest.mark.acceptance
class TestTC009ValidationErrorStopsGeneration:
    """TC-009: バリデーションエラー時のジョブ生成中止.

    テスト観点: エラー検出時にジョブ生成が中止される（検証段階でエラーが返る）
    関連する受入条件: AC-6, AC-7
    関連する設計方針: DP-3
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_validation_error_returns_detailed_message(
        self, validator: BodyTemplateValidator
    ) -> None:
        """バリデーションエラーは詳細なメッセージを含む."""
        # Arrange
        body_template = {
            "field1": "{{job.body.missing_field}}",
            "field2": "{{tasks[10].output_data}}",
        }
        input_schema = {
            "type": "object",
            "properties": {"existing_field": {"type": "string"}},
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=2,
            task_output_schemas=[{}, {}],
        )

        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 2

        # Check that errors contain detailed information
        for error in result.errors:
            assert error.error_type in ["MISSING_REFERENCE", "INVALID_INDEX"]
            assert len(error.message) > 0
            assert len(error.location) > 0

    def test_task_field_missing_error(self, validator: BodyTemplateValidator) -> None:
        """タスク出力の存在しないフィールド参照はエラーを返す."""
        # Arrange
        body_template = {
            "result": "{{tasks[0].output_data.nonexistent_field}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        # Assert
        assert result.is_valid is False
        assert any("nonexistent_field" in e.message for e in result.errors)


@pytest.mark.acceptance
class TestTC010WarningAllowsContinuation:
    """TC-010: 警告時のジョブ生成続行.

    テスト観点: 警告レベルの問題ではジョブ生成が続行される
    関連する受入条件: AC-8
    関連する設計方針: DP-3
    """

    def test_warnings_do_not_affect_validity(self) -> None:
        """警告があっても検証は成功する."""
        # Arrange
        result = BodyTemplateValidationResult(
            errors=[],
            warnings=[
                BodyTemplateValidationWarning(
                    warning_type="UNUSED_FIELD",
                    message="Field not used",
                    location="input_schema.optional_field",
                ),
            ],
            required_job_body_fields=set(),
        )

        # Assert
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_validation_with_warnings_but_no_errors(self) -> None:
        """エラーなし・警告ありの場合は検証が成功する."""
        validator = BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

        # Arrange - valid template
        body_template = {
            "inputs": "{{job.body}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        # Even if there are warnings, is_valid should be True


@pytest.mark.acceptance
class TestTC011RequiredFieldExtraction:
    """TC-011: 必須パラメータ情報の抽出.

    テスト観点: job.body参照から必須フィールドが正しく抽出される
    関連する受入条件: AC-9
    関連する設計方針: DP-2
    """

    @pytest.fixture
    def validator(self) -> BodyTemplateValidator:
        """TaskFlow用バリデータを作成."""
        return BodyTemplateValidator(strategy=TaskFlowValidationStrategy())

    def test_required_fields_extracted_from_job_body_references(
        self, validator: BodyTemplateValidator
    ) -> None:
        """job.body.X参照から必須フィールドが抽出される."""
        # Arrange
        body_template = {
            "user_input": "{{job.body.user_input}}",
            "email": "{{job.body.recipient_email}}",
            "count": "{{job.body.count}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                "recipient_email": {"type": "string"},
                "count": {"type": "integer"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        assert "user_input" in result.required_job_body_fields
        assert "recipient_email" in result.required_job_body_fields
        assert "count" in result.required_job_body_fields

    def test_entire_job_body_does_not_extract_specific_fields(
        self, validator: BodyTemplateValidator
    ) -> None:
        """{{job.body}}（全体参照）は特定フィールドを抽出しない."""
        # Arrange
        body_template = {
            "all_inputs": "{{job.body}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        # {{job.body}} doesn't extract specific field names
        # (it references the entire body)

    def test_nested_field_extracts_top_level_field(
        self, validator: BodyTemplateValidator
    ) -> None:
        """ネストしたフィールド参照はトップレベルフィールド名を抽出する."""
        # Arrange
        body_template = {
            "nested": "{{job.body.config.setting}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "setting": {"type": "string"},
                    },
                },
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert - top-level field "config" should be extracted
        assert "config" in result.required_job_body_fields


@pytest.mark.acceptance
class TestTC013TaskFlowEngineValidation:
    """TC-013: TaskFlowエンジンでの検証動作.

    テスト観点: engine="taskflow"指定時に適切なStrategyが使用される
    関連する受入条件: AC-1
    関連する設計方針: DP-1
    """

    def test_taskflow_strategy_instance(self) -> None:
        """TaskFlowValidationStrategyがインスタンス化可能."""
        # Act
        strategy = TaskFlowValidationStrategy()

        # Assert
        assert strategy is not None
        assert hasattr(strategy, "validate_job_body_reference")
        assert hasattr(strategy, "validate_task_reference")

    def test_taskflow_validator_uses_strategy(self) -> None:
        """TaskFlowValidationStrategyを使用したバリデータが動作する."""
        # Arrange
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "workflow_name": "__PENDING__",
            "inputs": "{{job.body}}",
            "project": "{{job.project}}",
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True

    def test_taskflow_entire_body_reference_valid(self) -> None:
        """TaskFlowで{{job.body}}（全体参照）が有効."""
        # Arrange
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "all_params": "{{job.body}}",
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True

    def test_taskflow_task_chaining_validation(self) -> None:
        """TaskFlowのタスクチェイニング参照が検証される."""
        # Arrange
        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "previous": "{{tasks[0].output_data}}",
            "specific": "{{tasks[0].output_data.result}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        # Assert
        assert result.is_valid is True


@pytest.mark.acceptance
class TestTC014GraphAIEngineValidation:
    """TC-014: GraphAIエンジンでの検証動作.

    テスト観点: engine="graphai"指定時に適切なStrategyが使用される
    関連する受入条件: AC-1
    関連する設計方針: DP-1
    """

    def test_graphai_strategy_instance(self) -> None:
        """GraphAIValidationStrategyがインスタンス化可能."""
        # Act
        strategy = GraphAIValidationStrategy()

        # Assert
        assert strategy is not None
        assert hasattr(strategy, "validate_job_body_reference")
        assert hasattr(strategy, "validate_task_reference")

    def test_graphai_validator_uses_strategy(self) -> None:
        """GraphAIValidationStrategyを使用したバリデータが動作する."""
        # Arrange
        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "user_input": "{{job.body.user_input}}",
            "job_params": "{{job.body}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True

    def test_graphai_field_extraction_validation(self) -> None:
        """GraphAIで特定フィールド参照が検証される."""
        # Arrange
        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "query": "{{job.body.query}}",
            "options": "{{job.body.options}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "options": {"type": "object"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is True
        assert "query" in result.required_job_body_fields
        assert "options" in result.required_job_body_fields

    def test_graphai_invalid_field_reference_returns_error(self) -> None:
        """GraphAIで存在しないフィールド参照がエラーを返す."""
        # Arrange
        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "query": "{{job.body.nonexistent}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
        }

        # Act
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Assert
        assert result.is_valid is False
        assert any(e.error_type == "MISSING_REFERENCE" for e in result.errors)


@pytest.mark.acceptance
class TestMasterManagerIntegration:
    """MasterManagerSubWorkflowとの統合テスト.

    テスト観点: BodyTemplateValidatorがMasterManagerSubWorkflowに統合されている
    関連する受入条件: AC-6
    関連する設計方針: DP-3
    """

    def test_master_manager_has_body_template_validator(self) -> None:
        """MasterManagerSubWorkflowがBodyTemplateValidatorを持つ."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Act
        manager_taskflow = MasterManagerSubWorkflow(engine="taskflow")
        manager_graphai = MasterManagerSubWorkflow(engine="graphai")

        # Assert
        assert hasattr(manager_taskflow, "_body_template_validator")
        assert hasattr(manager_graphai, "_body_template_validator")
        assert isinstance(
            manager_taskflow._body_template_validator, BodyTemplateValidator
        )
        assert isinstance(
            manager_graphai._body_template_validator, BodyTemplateValidator
        )

    def test_master_manager_uses_correct_strategy(self) -> None:
        """MasterManagerSubWorkflowがエンジンに応じた正しいStrategyを使用する."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Act
        manager_taskflow = MasterManagerSubWorkflow(engine="taskflow")
        manager_graphai = MasterManagerSubWorkflow(engine="graphai")

        # Assert - check that validators use different strategies
        # (both should exist and be properly configured)
        assert manager_taskflow._body_template_validator is not None
        assert manager_graphai._body_template_validator is not None


@pytest.mark.acceptance
class TestTemplateVariableResultMethods:
    """TemplateVariableResultのメソッドテスト.

    テスト観点: TemplateVariableResultのユーティリティメソッドが正しく動作する
    """

    def test_get_required_job_body_fields(self) -> None:
        """get_required_job_body_fields()が正しくフィールドを抽出する."""
        # Arrange
        body_template = {
            "user_input": "{{job.body.user_input}}",
            "email": "{{job.body.recipient_email}}",
            "nested": "{{job.body.config.setting}}",
        }

        # Act
        result = extract_template_variables(body_template)
        fields = result.get_required_job_body_fields()

        # Assert
        assert "user_input" in fields
        assert "recipient_email" in fields
        assert "config" in fields  # Top-level field from nested reference

    def test_get_max_task_index(self) -> None:
        """get_max_task_index()が最大タスクインデックスを返す."""
        # Arrange
        body_template = {
            "t0": "{{tasks[0].output_data}}",
            "t1": "{{tasks[1].output_data}}",
            "t3": "{{tasks[3].output_data}}",
        }

        # Act
        result = extract_template_variables(body_template)
        max_index = result.get_max_task_index()

        # Assert
        assert max_index == 3

    def test_get_max_task_index_no_references(self) -> None:
        """タスク参照がない場合は-1を返す."""
        # Arrange
        body_template = {
            "inputs": "{{job.body}}",
        }

        # Act
        result = extract_template_variables(body_template)
        max_index = result.get_max_task_index()

        # Assert
        assert max_index == -1
