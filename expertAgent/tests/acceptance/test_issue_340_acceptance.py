"""
Issue #340 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_340_acceptance.py -v

Issue #340: stringTemplateAgent がオブジェクトを [object Object] に変換し HTTP 500 を引き起こす
"""
import pytest
from typing import Any

from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    _get_string_template_input_fields,
    _object_array_issue,
    _validate_primitive_arrays,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_tester import (
    _detect_object_object_pattern,
)
from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    TYPE_VALIDATION_RULES,
)


@pytest.mark.acceptance
class TestIssue340Acceptance:
    """Issue #340: stringTemplateAgent [object Object] 変換問題の受入テスト"""

    # ==========================================================================
    # 受入条件1: stringTemplateAgent 入力フィールド抽出
    # ==========================================================================

    def test_acceptance_get_string_template_input_fields_extracts_fields(
        self,
    ) -> None:
        """受入条件: stringTemplateAgent の入力フィールドを正しく抽出する

        検証: YAMLからstringTemplateAgentノードのuser_input参照フィールドを抽出
        """
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
      focus_points: :source.user_input.focus_points
    params:
      template: "検索結果: ${search_results} / ${focus_points}"
  output:
    agent: copyAgent
    inputs:
      result: :build_prompt
    isResult: true
"""
        fields = _get_string_template_input_fields(yaml_content)

        # 受入基準: search_results と focus_points が抽出される
        assert "search_results" in fields
        assert "focus_points" in fields
        assert len(fields) == 2

    def test_acceptance_get_string_template_input_fields_no_string_template(
        self,
    ) -> None:
        """受入条件: stringTemplateAgentがない場合は空セットを返す"""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  output:
    agent: copyAgent
    inputs:
      data: :source.user_input.data
    isResult: true
"""
        fields = _get_string_template_input_fields(yaml_content)

        # 受入基準: stringTemplateAgentがなければ空セット
        assert len(fields) == 0

    # ==========================================================================
    # 受入条件2: オブジェクト配列検出
    # ==========================================================================

    def test_acceptance_validate_primitive_arrays_detects_objects(self) -> None:
        """受入条件: オブジェクト配列を含む sample_input を検出する

        検証: focus_points がオブジェクト配列の場合、issue が生成される
        """
        sample_input: dict[str, Any] = {
            "search_results": [{"title": "Sample", "url": "https://example.com"}],
            "focus_points": [
                {"type": "string", "description": "ニュース"},
                {"type": "string", "description": "技術"},
            ],
        }
        target_fields = {"search_results", "focus_points"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # 受入基準: 両方のフィールドでオブジェクト配列が検出される
        assert len(issues) >= 2
        assert all(issue["issue_type"] == "object_in_array" for issue in issues)
        assert any(issue["field_name"] == "search_results" for issue in issues)
        assert any(issue["field_name"] == "focus_points" for issue in issues)

    def test_acceptance_validate_primitive_arrays_allows_primitives(self) -> None:
        """受入条件: プリミティブ型配列は issue を生成しない

        検証: focus_points が文字列配列の場合、issue は生成されない
        """
        sample_input: dict[str, Any] = {
            "focus_points": ["ニュース", "技術", "ビジネス"],
            "numbers": [1, 2, 3],
            "mixed": [True, False],
        }
        target_fields = {"focus_points", "numbers", "mixed"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # 受入基準: プリミティブ型配列は許可される
        assert len(issues) == 0

    def test_acceptance_validate_non_target_field_ignored(self) -> None:
        """受入条件: 対象外フィールドはバリデーション対象外

        検証: target_fields に含まれないフィールドは検証されない
        """
        sample_input: dict[str, Any] = {
            "search_results": [{"title": "Sample"}],  # オブジェクト配列
            "focus_points": ["ニュース"],  # プリミティブ配列
        }
        target_fields = {"focus_points"}  # search_results は対象外

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # 受入基準: search_results は対象外なので検出されない
        assert len(issues) == 0

    # ==========================================================================
    # 受入条件3: [object Object] パターン検出
    # ==========================================================================

    def test_acceptance_detect_object_object_pattern_in_string(self) -> None:
        """受入条件: 文字列内の [object Object] パターンを検出する

        検証: 実行結果に [object Object] が含まれる場合、issue が生成される
        """
        execution_result: dict[str, Any] = {
            "prompt": "検索結果: [object Object],[object Object]",
            "response": "正常なレスポンス",
        }

        issues = _detect_object_object_pattern(execution_result)

        # 受入基準: [object Object] パターンが検出される
        assert len(issues) >= 1
        assert issues[0]["issue_type"] == "object_object_detected"
        assert "[object Object]" in issues[0]["actual_value"]

    def test_acceptance_detect_object_object_pattern_nested(self) -> None:
        """受入条件: ネストされた構造内の [object Object] パターンを検出する"""
        execution_result: dict[str, Any] = {
            "data": {
                "inner": {
                    "result": "値: [object Object]",
                }
            }
        }

        issues = _detect_object_object_pattern(execution_result)

        # 受入基準: ネストされた構造内でも検出される
        assert len(issues) >= 1
        assert "data.inner.result" in issues[0]["field_name"]

    def test_acceptance_detect_object_object_pattern_clean_result(self) -> None:
        """受入条件: [object Object] がない場合は issue が生成されない"""
        execution_result: dict[str, Any] = {
            "prompt": "正常なプロンプト",
            "response": '{"result": "正常なJSON"}',
            "items": ["item1", "item2"],
        }

        issues = _detect_object_object_pattern(execution_result)

        # 受入基準: クリーンな結果では issue なし
        assert len(issues) == 0

    # ==========================================================================
    # 受入条件4: Issue構造生成
    # ==========================================================================

    def test_acceptance_object_array_issue_structure(self) -> None:
        """受入条件: Issue構造が正しいフォーマットで生成される"""
        issue = _object_array_issue("focus_points", 0, "dict")

        # 受入基準: 必須フィールドが含まれる
        assert issue["node_id"] == "sample_input"
        assert issue["issue_type"] == "object_in_array"
        assert issue["severity"] == "error"
        assert issue["field_name"] == "focus_points"
        assert "focus_points" in issue["message"]
        assert "stringTemplateAgent" in issue["message"]
        assert "suggestion" in issue

    # ==========================================================================
    # 受入条件5: TYPE_VALIDATION_RULES 配列制約
    # ==========================================================================

    def test_acceptance_type_validation_rules_contains_array_constraint(
        self,
    ) -> None:
        """受入条件: TYPE_VALIDATION_RULES に配列型制約が含まれる

        検証: Issue #340 の配列制約セクションが存在する
        """
        # 受入基準: 配列型制約セクションが存在する
        assert "配列の型制約" in TYPE_VALIDATION_RULES or "Issue #340" in TYPE_VALIDATION_RULES
        assert "[object Object]" in TYPE_VALIDATION_RULES
        assert "stringTemplateAgent" in TYPE_VALIDATION_RULES

    def test_acceptance_type_validation_rules_shows_forbidden_pattern(
        self,
    ) -> None:
        """受入条件: TYPE_VALIDATION_RULES に禁止パターンが記載されている"""
        # 受入基準: 禁止パターン（オブジェクト配列）の例が記載
        assert "❌" in TYPE_VALIDATION_RULES or "禁止" in TYPE_VALIDATION_RULES

    def test_acceptance_type_validation_rules_shows_correct_pattern(
        self,
    ) -> None:
        """受入条件: TYPE_VALIDATION_RULES に正しいパターンが記載されている"""
        # 受入基準: 正しいパターン（プリミティブ配列）の例が記載
        assert "✅" in TYPE_VALIDATION_RULES or "正しい" in TYPE_VALIDATION_RULES

    # ==========================================================================
    # 統合テスト: 実際のワークフローシナリオ
    # ==========================================================================

    def test_acceptance_integration_object_array_detection_workflow(self) -> None:
        """受入条件: オブジェクト配列検出のワークフロー全体テスト

        v1.36 で失敗した「検索結果の分析」タスクのシナリオを検証
        """
        # シナリオ: 検索結果分析タスクでオブジェクト配列が生成された場合
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
      focus_points: :source.user_input.focus_points
    params:
      template: |
        検索結果を分析してください。
        検索結果: ${search_results}
        分析ポイント: ${focus_points}
  analyze:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/aiagent/utility/jsonoutput
      body:
        user_input: :build_prompt
        model_name: gemini-2.0-flash
    params:
      method: POST
  output:
    agent: copyAgent
    inputs:
      result: :analyze.result
    isResult: true
"""
        # Step 1: stringTemplateAgent 入力フィールドを抽出
        target_fields = _get_string_template_input_fields(yaml_content)
        assert "search_results" in target_fields
        assert "focus_points" in target_fields

        # Step 2: v1.36相当の問題のあるテストデータ
        problematic_sample_input: dict[str, Any] = {
            "search_results": [
                {"title": "Sample Title", "link": "https://example.com", "snippet": "sample_text"}
            ],
            "focus_points": [
                {"type": "string", "description": "最新ニュース"},
                {"type": "string", "description": "主要なトピック"},
            ],
        }

        # Step 3: オブジェクト配列検出
        issues = _validate_primitive_arrays(problematic_sample_input, target_fields)

        # 受入基準: v1.36 で問題となったオブジェクト配列が検出される
        assert len(issues) >= 2
        field_names = [issue["field_name"] for issue in issues]
        assert "search_results" in field_names
        assert "focus_points" in field_names

        # Step 4: 正しいテストデータ（プリミティブ配列）の場合
        correct_sample_input: dict[str, Any] = {
            "search_results": '{"title": "Sample Title", "link": "https://example.com"}',  # JSONシリアライズ済み文字列
            "focus_points": ["最新ニュース", "主要なトピック"],  # プリミティブ配列
        }

        correct_issues = _validate_primitive_arrays(correct_sample_input, target_fields)

        # 受入基準: 正しいテストデータでは issue なし
        assert len(correct_issues) == 0

    def test_acceptance_integration_runtime_object_object_detection(self) -> None:
        """受入条件: ランタイム [object Object] 検出の統合テスト

        workflow_tester が実行結果の [object Object] パターンを検出することを検証
        """
        # シナリオ: stringTemplateAgent が [object Object] を出力した場合
        simulated_execution_result: dict[str, Any] = {
            "build_prompt": "検索結果: [object Object],[object Object] / 分析ポイント: [object Object],[object Object]",
            "analyze": {
                "error": "Failed to parse JSON",
                "raw_response": "Invalid input containing [object Object]",
            },
        }

        # [object Object] パターンを検出
        issues = _detect_object_object_pattern(simulated_execution_result)

        # 受入基準: 複数の [object Object] パターンが検出される
        assert len(issues) >= 2
        assert all(issue["issue_type"] == "object_object_detected" for issue in issues)
