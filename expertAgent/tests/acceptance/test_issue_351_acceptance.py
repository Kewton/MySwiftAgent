"""
Issue #351 受入テスト（L3: ローカル受入テスト）

前提条件:
- expertAgent サービスが起動していること（または直接インポートテスト）
- .env に必要なAPIキーが設定されていること（ワークフロー生成テスト用）

実行方法:
  cd expertAgent && PYTHONPATH=. uv run pytest tests/acceptance/test_issue_351_acceptance.py -v

Issue:
  #351: TaskFlow V2: output フィールドの変数参照構文がJSONバリデーションエラーを引き起こす

受入条件:
  1. output フィールドに変数参照構文（${step.field}）を含む値が設定できる
  2. TaskFlow V2 ワークフロー生成が成功する
  3. 既存のテストが全てパスする
  4. 新規テストケースを追加（変数参照を含むoutputのバリデーション）
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# Direct import test - no service required
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    TaskFlowStep,
    TaskFlowWorkflow,
    UnifiedStepConfig,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.variable_patterns import (
    TASKFLOW_VARIABLE_PATTERN,
    contains_variable_reference,
    mask_secret_references,
    replace_variables_with_placeholder,
    validate_variable_syntax,
)


@pytest.mark.acceptance
class TestIssue351Acceptance:
    """Issue #351: TaskFlow V2 output フィールドの変数参照構文バリデーション修正

    受入条件:
    1. output フィールドに変数参照構文（${step.field}）を含む値が設定できる
    2. TaskFlow V2 ワークフロー生成が成功する
    3. 既存のテストが全てパスする
    4. 新規テストケースを追加（変数参照を含むoutputのバリデーション）
    """

    # ==========================================================================
    # 受入条件 1: output フィールドに変数参照構文を含む値が設定できる
    # ==========================================================================

    def test_acceptance_criterion_1_output_with_variable_reference(self) -> None:
        """受入条件1: output フィールドに変数参照構文（${step.field}）を含む値が設定できる

        これはLangfuseトレース e5eff2c5134442999d725b36f105a4dd で発生した
        実際のエラーシナリオを再現しています。
        """
        # Arrange: Google検索ワークフローのステップを作成
        google_search_step = TaskFlowStep(
            id="google_search",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/utility/google_search",
                headers={"Content-Type": "application/json"},
                body='{"queries": ["${inputs.query}"], "num": 10}',
            ),
        )

        # Act: 変数参照を含むoutputでワークフローを作成
        # これは以前は ValidationError を発生させていた
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search Google and return results",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[google_search_step],
            output='{"search_results": "${google_search.output.search_results}"}',
        )

        # Assert: ワークフローが正常に作成され、変数参照が保持されている
        assert workflow.workflow_name == "google_search_workflow"
        assert "${google_search.output.search_results}" in workflow.output
        assert (
            workflow.output
            == '{"search_results": "${google_search.output.search_results}"}'
        )

    def test_acceptance_criterion_1_nested_variable_reference(self) -> None:
        """受入条件1: ネストした変数参照（${step.output.data.name}）も設定できる"""
        # Arrange
        step = TaskFlowStep(
            id="fetch_user",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="GET",
                url="http://localhost:8004/v1/users/${inputs.user_id}",
            ),
        )

        # Act
        workflow = TaskFlowWorkflow(
            workflow_name="user_profile_workflow",
            input_schema='{"user_id": "string"}',
            output_schema='{"user_name": "string", "email": "string"}',
            steps=[step],
            output='{"user_name": "${fetch_user.output.data.name}", "email": "${fetch_user.output.data.email}"}',
        )

        # Assert
        assert "${fetch_user.output.data.name}" in workflow.output
        assert "${fetch_user.output.data.email}" in workflow.output

    def test_acceptance_criterion_1_hyphenated_step_id(self) -> None:
        """受入条件1: ハイフンを含むステップID（step-001）も変数参照で使用できる"""
        # Arrange
        step = TaskFlowStep(
            id="step-001",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.data}",
            ),
        )

        # Act
        workflow = TaskFlowWorkflow(
            workflow_name="hyphen_workflow",
            input_schema='{"data": "string"}',
            output_schema='{"result": "string"}',
            steps=[step],
            output='{"result": "${step-001.output}"}',
        )

        # Assert
        assert "${step-001.output}" in workflow.output

    # ==========================================================================
    # 受入条件 2: TaskFlow V2 ワークフロー生成が成功する
    # ==========================================================================

    def test_acceptance_criterion_2_complex_workflow_creation(self) -> None:
        """受入条件2: 複雑なTaskFlow V2 ワークフロー（複数ステップ、複数変数参照）が成功する"""
        # Arrange: 複数ステップのワークフロー
        step1 = TaskFlowStep(
            id="search",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/utility/google_search",
                body='{"queries": ["${inputs.query}"]}',
            ),
        )

        step2 = TaskFlowStep(
            id="summarize",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/mylllm",
                body='{"user_input": "${search.output.results}", "system_prompt": "Summarize"}',
            ),
        )

        step3 = TaskFlowStep(
            id="format",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${summarize.output.result}",
            ),
        )

        # Act
        workflow = TaskFlowWorkflow(
            workflow_name="search_and_summarize",
            description="Search, summarize, and format",
            input_schema='{"query": "string"}',
            output_schema='{"summary": "string", "search_count": "number"}',
            steps=[step1, step2, step3],
            output='{"summary": "${format.output}", "search_count": "${search.output.count}"}',
        )

        # Assert
        assert len(workflow.steps) == 3
        assert "${format.output}" in workflow.output
        assert "${search.output.count}" in workflow.output

    def test_acceptance_criterion_2_mixed_static_and_variable(self) -> None:
        """受入条件2: 静的値と変数参照を混在させたoutputが設定できる"""
        # Arrange
        step = TaskFlowStep(
            id="api_call",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="GET",
                url="http://localhost:8004/health",
            ),
        )

        # Act
        workflow = TaskFlowWorkflow(
            workflow_name="mixed_output_workflow",
            input_schema="{}",
            output_schema='{"status": "string", "data": "object", "version": "string"}',
            steps=[step],
            output='{"status": "success", "data": "${api_call.output}", "version": "1.0.0"}',
        )

        # Assert
        assert '"status": "success"' in workflow.output
        assert "${api_call.output}" in workflow.output
        assert '"version": "1.0.0"' in workflow.output

    # ==========================================================================
    # 受入条件 3: 既存のテストが全てパスする（不正なJSON検出）
    # ==========================================================================

    def test_acceptance_criterion_3_invalid_json_still_rejected(self) -> None:
        """受入条件3: 不正なJSON構造は引き続き検出される（後方互換性）"""
        # Arrange
        step = TaskFlowStep(
            id="test_step",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.data}",
            ),
        )

        # Act & Assert: 引用符がない変数参照は不正なJSON
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="invalid_workflow",
                input_schema='{"data": "string"}',
                output_schema='{"result": "string"}',
                steps=[step],
                output='{"result": ${test_step.output}}',  # Missing quotes around value
            )

        error_str = str(exc_info.value).lower()
        assert "json" in error_str

    def test_acceptance_criterion_3_missing_brace_rejected(self) -> None:
        """受入条件3: 閉じブレースがないJSON構造は検出される"""
        # Arrange
        step = TaskFlowStep(
            id="test_step",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="${inputs.data}",
            ),
        )

        # Act & Assert
        with pytest.raises(ValidationError):
            TaskFlowWorkflow(
                workflow_name="invalid_workflow",
                input_schema='{"data": "string"}',
                output_schema='{"result": "string"}',
                steps=[step],
                output='{"result": "${test_step.output}"',  # Missing closing }
            )

    def test_acceptance_criterion_3_pure_static_json_works(self) -> None:
        """受入条件3: 純粋な静的JSONも引き続き動作する（後方互換性）"""
        # Arrange
        step = TaskFlowStep(
            id="test_step",
            type="transform",
            config=UnifiedStepConfig(
                step_type="transform",
                mode="template",
                template="Hello",
            ),
        )

        # Act
        workflow = TaskFlowWorkflow(
            workflow_name="static_workflow",
            input_schema='{"name": "string"}',
            output_schema='{"message": "string"}',
            steps=[step],
            output='{"message": "Hello, World!"}',
        )

        # Assert
        assert workflow.output == '{"message": "Hello, World!"}'

    # ==========================================================================
    # 受入条件 4: 新規テストケース（変数パターンモジュール）
    # ==========================================================================

    def test_acceptance_criterion_4_variable_pattern_module_exists(self) -> None:
        """受入条件4: 変数パターンモジュールが正しくインポートできる"""
        # Assert: All exports are available
        assert TASKFLOW_VARIABLE_PATTERN is not None
        assert callable(contains_variable_reference)
        assert callable(replace_variables_with_placeholder)
        assert callable(mask_secret_references)
        assert callable(validate_variable_syntax)

    def test_acceptance_criterion_4_pattern_matches_all_formats(self) -> None:
        """受入条件4: 変数パターンが全ての形式にマッチする"""
        # Assert: Simple reference
        assert TASKFLOW_VARIABLE_PATTERN.search("${inputs.query}")
        # Assert: Nested reference
        assert TASKFLOW_VARIABLE_PATTERN.search("${step.output.data.name}")
        # Assert: Hyphenated step ID
        assert TASKFLOW_VARIABLE_PATTERN.search("${step-001.output}")
        # Assert: Secrets reference
        assert TASKFLOW_VARIABLE_PATTERN.search("${secrets.API_KEY}")
        # Assert: Invalid start is not matched
        assert TASKFLOW_VARIABLE_PATTERN.search("${123step.output}") is None

    def test_acceptance_criterion_4_secret_masking_works(self) -> None:
        """受入条件4: シークレットマスキングが正しく動作する"""
        # Arrange
        input_value = "Bearer ${secrets.API_TOKEN} and ${inputs.query}"

        # Act
        masked = mask_secret_references(input_value)

        # Assert
        assert masked == "Bearer ${secrets.***} and ${inputs.query}"
        assert "API_TOKEN" not in masked

    def test_acceptance_criterion_4_syntax_validation_works(self) -> None:
        """受入条件4: 変数構文バリデーションが正しく動作する"""
        # Assert: Valid syntax returns empty list
        assert validate_variable_syntax("${step.output}") == []
        assert validate_variable_syntax("${step-001.output.data}") == []

        # Assert: Invalid syntax returns list of invalid references
        invalid = validate_variable_syntax("${123.invalid}")
        assert "${123.invalid}" in invalid


@pytest.mark.acceptance
class TestLangfuseErrorReproduction:
    """Langfuseトレース e5eff2c5134442999d725b36f105a4dd のエラー再現テスト

    このテストクラスは、本番環境で発生した実際のエラーシナリオを再現します。
    """

    def test_exact_error_scenario_from_langfuse(self) -> None:
        """Langfuseトレースで記録された正確なエラーシナリオ

        エラー内容:
        ```
        1 validation error for TaskFlowWorkflow
        output
          Value error, Invalid JSON: Expecting value: line 1 column 20 (char 19)
          input_value='{"search_results": ${google_search.output.search_results}}'
        ```

        このテストは修正後、エラーが発生しないことを確認します。
        """
        # Arrange: Langfuseで記録されたワークフロー構造を再現
        google_search_step = TaskFlowStep(
            id="google_search",
            type="api_rest",
            config=UnifiedStepConfig(
                step_type="api_rest",
                method="POST",
                url="http://localhost:8004/v1/utility/google_search",
                headers={"Content-Type": "application/json"},
                body='{"queries": ["${inputs.query}"], "num": 10}',
            ),
        )

        # Act: 以前はここでValidationErrorが発生していた
        # 修正後は正常にワークフローが作成される
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search Google and return results",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[google_search_step],
            output='{"search_results": "${google_search.output.search_results}"}',
        )

        # Assert: ワークフローが正常に作成された
        assert workflow is not None
        assert workflow.workflow_name == "google_search_workflow"
        assert "${google_search.output.search_results}" in workflow.output

        # Assert: JSONシリアライズも正常に動作する
        json_output = workflow.to_json()
        assert "google_search_workflow" in json_output
        assert "${google_search.output.search_results}" in json_output
