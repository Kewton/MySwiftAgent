"""
Issue #407 受入テスト（L3: ローカル受入テスト）

Issue: SYSTEM_INJECTED_FIELDSの前方一致チェック対応
前提条件:
- expertAgentが起動していること
- Issue #403で追加された`_build_multi_dependency_template`のフォールバックロジックが
  `{{job.body.user_input.{field}}}`形式を生成する
- この形式がバリデーションエラーにならないことを確認

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_407_acceptance.py -v
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
    SYSTEM_INJECTED_FIELDS,
    GraphAIValidationStrategy,
    TaskFlowValidationStrategy,
    _is_system_injected_field,
)


class TestIssue407Acceptance:
    """Issue #407: SYSTEM_INJECTED_FIELDSの前方一致チェック対応

    受入条件:
    - AC-1: user_input.{field}形式の参照がバリデーションエラーにならない
    - AC-2: project.{field}形式の参照がバリデーションエラーにならない
    - AC-3: 既存のuser_input完全一致のスキップ動作が維持される
    - AC-4: 既存のproject完全一致のスキップ動作が維持される
    - AC-5: 無関係なフィールド（例: query）のバリデーションが引き続き実行される
    - AC-7: GraphAIエンジン使用時もuser_input.{field}形式がエラーにならない
    - AC-8: モジュールレベルのプライベートヘルパー関数_is_system_injected_fieldが追加
    """

    # ==========================================================================
    # AC-8: ヘルパー関数の存在確認
    # ==========================================================================

    def test_tc001_helper_function_exists(self) -> None:
        """TC-001: ヘルパー関数_is_system_injected_fieldが存在する

        受入条件: AC-8
        """
        # Assert
        assert callable(_is_system_injected_field), (
            "_is_system_injected_field should be a callable function"
        )

    def test_tc002_system_injected_fields_constant_exists(self) -> None:
        """TC-002: SYSTEM_INJECTED_FIELDS定数が存在する

        受入条件: AC-8
        """
        # Assert
        assert SYSTEM_INJECTED_FIELDS is not None
        assert "user_input" in SYSTEM_INJECTED_FIELDS
        assert "project" in SYSTEM_INJECTED_FIELDS

    # ==========================================================================
    # AC-1: user_input.{field}形式のスキップ
    # ==========================================================================

    @pytest.mark.parametrize(
        "field_path",
        [
            "user_input.query",
            "user_input.max_results",
            "user_input.nested.deep.field",
        ],
    )
    def test_tc003_user_input_nested_field_is_skipped(self, field_path: str) -> None:
        """TC-003: user_input.{field}形式がスキップされる

        受入条件: AC-1
        """
        # Act
        result = _is_system_injected_field(field_path)

        # Assert
        assert result is True, (
            f"'{field_path}' should be recognized as a system-injected field"
        )

    # ==========================================================================
    # AC-2: project.{field}形式のスキップ
    # ==========================================================================

    @pytest.mark.parametrize(
        "field_path",
        [
            "project.name",
            "project.secrets.api_key",
            "project.config.setting",
        ],
    )
    def test_tc004_project_nested_field_is_skipped(self, field_path: str) -> None:
        """TC-004: project.{field}形式がスキップされる

        受入条件: AC-2
        """
        # Act
        result = _is_system_injected_field(field_path)

        # Assert
        assert result is True, (
            f"'{field_path}' should be recognized as a system-injected field"
        )

    # ==========================================================================
    # AC-3, AC-4: 既存の完全一致動作維持
    # ==========================================================================

    def test_tc005_exact_match_user_input_is_skipped(self) -> None:
        """TC-005: user_input完全一致がスキップされる

        受入条件: AC-3
        """
        # Act
        result = _is_system_injected_field("user_input")

        # Assert
        assert result is True, (
            "'user_input' exact match should be recognized as a system-injected field"
        )

    def test_tc006_exact_match_project_is_skipped(self) -> None:
        """TC-006: project完全一致がスキップされる

        受入条件: AC-4
        """
        # Act
        result = _is_system_injected_field("project")

        # Assert
        assert result is True, (
            "'project' exact match should be recognized as a system-injected field"
        )

    # ==========================================================================
    # AC-5: 無関係フィールドのバリデーション継続
    # ==========================================================================

    @pytest.mark.parametrize(
        "field_path",
        [
            "query",
            "user_input_extra",
            "user_inputquery",
            "project_extra",
            "projectname",
            "some_other_field",
        ],
    )
    def test_tc007_unrelated_field_is_not_skipped(self, field_path: str) -> None:
        """TC-007: 無関係なフィールドはスキップされない

        受入条件: AC-5
        """
        # Act
        result = _is_system_injected_field(field_path)

        # Assert
        assert result is False, (
            f"'{field_path}' should NOT be recognized as a system-injected field"
        )

    # ==========================================================================
    # AC-1, AC-7: TaskFlow/GraphAI Strategy統合テスト
    # ==========================================================================

    def test_tc008_taskflow_strategy_skips_user_input_nested(self) -> None:
        """TC-008: TaskFlowValidationStrategyがuser_input.{field}をスキップする

        受入条件: AC-1
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        input_schema: dict[str, str] = {}  # user_input.queryはinput_schemaにない

        # Act
        errors = strategy.validate_job_body_reference(
            reference="job.body.user_input.query",
            input_schema=input_schema,
        )

        # Assert
        assert len(errors) == 0, (
            f"TaskFlowValidationStrategy should skip 'user_input.query', "
            f"but got errors: {errors}"
        )

    def test_tc009_graphai_strategy_skips_user_input_nested(self) -> None:
        """TC-009: GraphAIValidationStrategyがuser_input.{field}をスキップする

        受入条件: AC-7
        """
        # Arrange
        strategy = GraphAIValidationStrategy()
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(
            reference="job.body.user_input.max_results",
            input_schema=input_schema,
        )

        # Assert
        assert len(errors) == 0, (
            f"GraphAIValidationStrategy should skip 'user_input.max_results', "
            f"but got errors: {errors}"
        )

    def test_tc010_taskflow_strategy_validates_unrelated_field(self) -> None:
        """TC-010: TaskFlowValidationStrategyが無関係なフィールドをバリデートする

        受入条件: AC-5
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        input_schema: dict[str, str] = {}  # unknown_fieldはinput_schemaにない

        # Act
        errors = strategy.validate_job_body_reference(
            reference="job.body.unknown_field",
            input_schema=input_schema,
        )

        # Assert
        assert len(errors) > 0, (
            "TaskFlowValidationStrategy should report error for 'unknown_field'"
        )
        assert any("unknown_field" in str(e) for e in errors), (
            f"Error should mention 'unknown_field', but got: {errors}"
        )

    # ==========================================================================
    # AC-1, AC-2: Strategy統合テスト（直接validate_job_body_reference呼び出し）
    # ==========================================================================

    def test_tc011_strategy_validates_user_input_nested(self) -> None:
        """TC-011: Strategyがuser_input.{field}参照を許可する

        受入条件: AC-1
        Note: BodyTemplateValidator経由ではなく、Strategyを直接テスト
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        # job.body.user_input.queryの形式でreference
        reference = "job.body.user_input.query"
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(reference, input_schema)

        # Assert
        assert len(errors) == 0, (
            f"Strategy should accept 'user_input.query', but got errors: {errors}"
        )

    def test_tc012_strategy_validates_project_nested(self) -> None:
        """TC-012: Strategyがproject.{field}参照を許可する

        受入条件: AC-2
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        reference = "job.body.project.name"
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(reference, input_schema)

        # Assert
        assert len(errors) == 0, (
            f"Strategy should accept 'project.name', but got errors: {errors}"
        )

    def test_tc013_strategy_rejects_invalid_field(self) -> None:
        """TC-013: Strategyが無効なフィールドを拒否する

        受入条件: AC-5
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        reference = "job.body.invalid_field"
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(reference, input_schema)

        # Assert
        assert len(errors) > 0, "Strategy should reject 'invalid_field'"


class TestIssue407EdgeCases:
    """Issue #407 エッジケーステスト"""

    @pytest.mark.parametrize(
        "field_path,expected",
        [
            ("", False),  # 空文字列
            (".", False),  # ドットのみ
            # Note: "user_input." is True because startswith("user_input.") matches
            # This is acceptable behavior as it will be caught by later validation
            ("user_input.", True),  # 末尾ドット（前方一致でマッチ）
            (".user_input", False),  # 先頭ドット
            ("USER_INPUT", False),  # 大文字（大文字小文字区別）
            ("PROJECT", False),  # 大文字
        ],
    )
    def test_edge_cases(self, field_path: str, expected: bool) -> None:
        """エッジケーステスト"""
        # Act
        result = _is_system_injected_field(field_path)

        # Assert
        assert result is expected, (
            f"_is_system_injected_field('{field_path}') should return {expected}"
        )

    def test_deeply_nested_user_input_field(self) -> None:
        """深くネストされたuser_inputフィールドのテスト"""
        # Arrange
        field_path = "user_input.level1.level2.level3.level4"

        # Act
        result = _is_system_injected_field(field_path)

        # Assert
        assert result is True, f"Deeply nested field '{field_path}' should be skipped"

    def test_mixed_valid_and_invalid_fields(self) -> None:
        """有効・無効フィールドが混在するケースのテスト"""
        # Arrange
        strategy = TaskFlowValidationStrategy()
        input_schema: dict[str, str] = {}

        # Act - user_input.queryは有効
        errors_valid = strategy.validate_job_body_reference(
            "job.body.user_input.query", input_schema
        )
        # Act - unknown_fieldは無効
        errors_invalid = strategy.validate_job_body_reference(
            "job.body.unknown_field", input_schema
        )

        # Assert
        assert len(errors_valid) == 0, (
            f"'user_input.query' should be valid, but got errors: {errors_valid}"
        )
        assert len(errors_invalid) > 0, "'unknown_field' should be invalid"
        # unknown_fieldに対してエラーが発生
        error_messages = [str(e) for e in errors_invalid]
        assert any("unknown_field" in msg for msg in error_messages), (
            f"Error should mention 'unknown_field', got: {error_messages}"
        )


class TestIssue407RegressionPrevention:
    """Issue #407 リグレッション防止テスト

    Issue #403で追加されたフォールバックロジックとの互換性を確認
    """

    def test_issue_403_fallback_format_is_valid(self) -> None:
        """Issue #403のフォールバック形式がバリデーションを通過する

        Issue #403で_build_multi_dependency_templateが生成する
        {{job.body.user_input.missing_field}}形式がエラーにならないことを確認
        """
        # Arrange
        strategy = TaskFlowValidationStrategy()
        # Issue #403のフォールバックで生成される形式
        reference = "job.body.user_input.missing_field"
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(reference, input_schema)

        # Assert
        assert len(errors) == 0, (
            f"Issue #403 fallback format should be valid, but got errors: {errors}"
        )

    def test_graphai_engine_also_accepts_user_input_nested(self) -> None:
        """GraphAIエンジンでもuser_input.{field}形式が有効

        受入条件: AC-7
        """
        # Arrange
        strategy = GraphAIValidationStrategy()
        reference = "job.body.user_input.param"
        input_schema: dict[str, str] = {}

        # Act
        errors = strategy.validate_job_body_reference(reference, input_schema)

        # Assert
        assert len(errors) == 0, (
            f"GraphAI engine should accept 'user_input.param', but got errors: {errors}"
        )
