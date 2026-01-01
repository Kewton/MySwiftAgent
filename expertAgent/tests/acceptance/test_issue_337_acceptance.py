"""
Issue #337 受入テスト（L3: ローカル受入テスト）

タスクチェーン Ready-to-Use Output 原則の導入 - Phase 1

受入条件:
1. derived_fields を含む output_interface が定義可能
2. ワークフロー生成LLMが derived_fields を正しく出力に含める（Phase 2）
3. 下流タスクが文字列加工なしでデータを使用可能（Phase 2）

本テストは Phase 1 の受入条件1に焦点を当てます。
Phase 2 受入条件（LLM統合）は別途テストします。

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_337_acceptance.py -v

前提条件:
- expertAgent がインストールされていること
"""
from typing import Any

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    DerivedFieldDefinition,
    InterfaceSchemaDefinition,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.template_validator import (
    get_template_variables,
    validate_derived_fields,
    validate_template,
)
from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import (
    check_derived_fields_for_downstream_tasks,
)


@pytest.mark.acceptance
class TestIssue337AcceptancePhase1:
    """
    Issue #337: タスクチェーン Ready-to-Use Output 原則の導入

    Phase 1 受入条件: derived_fields を含む output_interface が定義可能
    """

    # ==========================================================================
    # 受入条件1: derived_fields を含む output_interface が定義可能
    # ==========================================================================

    def test_ac1_derived_field_definition_can_be_created(self) -> None:
        """受入条件1-1: DerivedFieldDefinition が作成可能

        設計書の仕様:
        - template: テンプレート文字列（{variable} 形式）
        - type: 生成値の型（デフォルト "string"）
        - description: オプショナルな説明
        - source_mapping: 変数名→ソースパスのマッピング（オプション）
        """
        # Arrange & Act
        derived_field = DerivedFieldDefinition(
            template="検索結果サマリ: {query}",
            type="string",
            description="メール件名として使用",
            source_mapping={"query": "source.user_input.query"},
        )

        # Assert
        assert derived_field.template == "検索結果サマリ: {query}"
        assert derived_field.type == "string"
        assert derived_field.description == "メール件名として使用"
        assert derived_field.source_mapping == {"query": "source.user_input.query"}

    def test_ac1_derived_field_minimal_creation(self) -> None:
        """受入条件1-2: DerivedFieldDefinition が最小構成で作成可能

        template のみ必須、他はオプション
        """
        # Arrange & Act
        derived_field = DerivedFieldDefinition(
            template="{summary_text}"
        )

        # Assert
        assert derived_field.template == "{summary_text}"
        assert derived_field.type == "string"  # デフォルト
        assert derived_field.description is None
        assert derived_field.source_mapping is None

    def test_ac1_interface_schema_with_derived_fields(self) -> None:
        """受入条件1-3: InterfaceSchemaDefinition に derived_fields を含めることが可能

        設計書の仕様:
        - derived_fields は dict[str, DerivedFieldDefinition] 型
        - デフォルトは空の dict
        """
        # Arrange
        derived_fields = {
            "email_subject": DerivedFieldDefinition(
                template="検索結果サマリ: {query}",
                type="string",
            ),
            "email_body": DerivedFieldDefinition(
                template="{summary_text}\n\n重要ポイント:\n{key_points}",
                type="string",
            ),
        }

        # Act
        interface_schema = InterfaceSchemaDefinition(
            task_id="summarize_task",
            interface_name="summarize_interface",
            description="要約タスクのインターフェース",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary_text": {"type": "string"},
                    "key_points": {"type": "string"},
                },
            },
            derived_fields=derived_fields,
        )

        # Assert
        assert len(interface_schema.derived_fields) == 2
        assert "email_subject" in interface_schema.derived_fields
        assert "email_body" in interface_schema.derived_fields
        assert interface_schema.derived_fields["email_subject"].template == "検索結果サマリ: {query}"

    def test_ac1_interface_schema_without_derived_fields(self) -> None:
        """受入条件1-4: derived_fields なしの InterfaceSchemaDefinition（後方互換性）

        既存の InterfaceSchemaDefinition は影響なし
        """
        # Arrange & Act
        interface_schema = InterfaceSchemaDefinition(
            task_id="existing_task",
            interface_name="existing_interface",
            description="既存タスクのインターフェース",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )

        # Assert
        assert interface_schema.derived_fields == {}  # デフォルト空dict

    def test_ac1_interface_schema_serialization_with_derived_fields(self) -> None:
        """受入条件1-5: derived_fields を含む InterfaceSchemaDefinition が JSON シリアライズ可能

        JobQueue 登録時に JSON 形式で保存されるため
        """
        # Arrange
        interface_schema = InterfaceSchemaDefinition(
            task_id="task_1",
            interface_name="interface_1",
            description="テスト用",
            input_schema={"type": "object"},
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            derived_fields={
                "formatted_result": DerivedFieldDefinition(
                    template="結果: {result}",
                    source_mapping={"result": "task_1.result"},
                ),
            },
        )

        # Act
        serialized = interface_schema.model_dump()

        # Assert
        assert "derived_fields" in serialized
        assert "formatted_result" in serialized["derived_fields"]
        assert serialized["derived_fields"]["formatted_result"]["template"] == "結果: {result}"
        assert serialized["derived_fields"]["formatted_result"]["source_mapping"] == {
            "result": "task_1.result"
        }

    # ==========================================================================
    # テンプレート変数抽出・検証機能
    # ==========================================================================

    def test_template_variable_extraction(self) -> None:
        """テンプレート変数抽出: {variable} 形式の変数が正しく抽出される"""
        # Arrange
        template = "検索結果サマリ: {query}\n\n{summary_text}\n\n重要ポイント:\n{key_points}"

        # Act
        variables = get_template_variables(template)

        # Assert
        assert set(variables) == {"query", "summary_text", "key_points"}

    def test_template_validation_with_properties(self) -> None:
        """テンプレート検証: properties に存在する変数は解決済み扱い

        設計書のソース解決ルール:
        - 優先順位1: 同一タスクの properties に存在 → 同一タスク出力から取得
        """
        # Arrange
        template = "{summary_text}\n{key_points}"
        properties: dict[str, Any] = {
            "summary_text": {"type": "string"},
            "key_points": {"type": "string"},
        }

        # Act
        unresolved = validate_template(template, properties)

        # Assert
        assert unresolved == []  # すべて解決済み

    def test_template_validation_with_source_mapping(self) -> None:
        """テンプレート検証: source_mapping で指定された変数は解決済み扱い

        設計書のソース解決ルール:
        - 優先順位3: source_mapping で明示的に指定 → 指定パスから取得
        """
        # Arrange
        template = "検索結果: {query}"
        properties: dict[str, Any] = {}  # properties に query なし
        source_mapping = {"query": "source.user_input.query"}

        # Act
        unresolved = validate_template(template, properties, source_mapping)

        # Assert
        assert unresolved == []  # source_mapping で解決

    def test_template_validation_unresolved_warning(self) -> None:
        """テンプレート検証: 未解決変数は警告リストに含まれる

        設計書のソース解決ルール:
        - 優先順位2: properties に存在しない → source.user_input から取得（警告）
        """
        # Arrange
        template = "検索結果: {query}"
        properties: dict[str, Any] = {}  # properties に query なし

        # Act
        unresolved = validate_template(template, properties)

        # Assert
        assert "query" in unresolved  # 未解決として報告

    def test_derived_fields_validation(self) -> None:
        """x-derived-fields 全体検証: 複数の derived_fields を一括検証"""
        # Arrange
        output_schema: dict[str, Any] = {
            "properties": {
                "summary_text": {"type": "string"},
                "key_points": {"type": "string"},
            },
            "x-derived-fields": {
                "email_subject": {
                    "template": "検索結果サマリ: {query}",  # query は properties にない
                    "type": "string",
                },
                "email_body": {
                    "template": "{summary_text}\n{key_points}",  # 両方 properties にある
                    "type": "string",
                },
            },
        }

        # Act
        errors = validate_derived_fields(output_schema)

        # Assert
        assert len(errors) == 1  # email_subject のみ警告
        assert errors[0]["field"] == "email_subject"
        assert "query" in errors[0]["unresolved_variables"]

    # ==========================================================================
    # 評価ノード derived_fields チェック機能
    # ==========================================================================

    def test_evaluator_checks_email_derived_fields(self) -> None:
        """評価ノード: メール送信タスクに対して email_subject/email_body を要求"""
        # Arrange
        tasks = [
            {"task_id": "summarize", "task_type": "summarization"},
            {"task_id": "send_email", "task_type": "email_send"},
        ]
        interface_definitions: dict[str, dict[str, Any]] = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    # x-derived-fields が未定義
                },
            },
        }

        # Act
        issues = check_derived_fields_for_downstream_tasks(tasks, interface_definitions)

        # Assert
        assert len(issues) == 2
        assert any("email_subject" in issue for issue in issues)
        assert any("email_body" in issue for issue in issues)

    def test_evaluator_passes_with_complete_derived_fields(self) -> None:
        """評価ノード: 必要な derived_fields が定義されていれば問題なし"""
        # Arrange
        tasks = [
            {"task_id": "summarize", "task_type": "summarization"},
            {"task_id": "send_email", "task_type": "email_send"},
        ]
        interface_definitions: dict[str, dict[str, Any]] = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    "x-derived-fields": {
                        "email_subject": {"template": "件名: {query}"},
                        "email_body": {"template": "{summary}"},
                    },
                },
            },
        }

        # Act
        issues = check_derived_fields_for_downstream_tasks(tasks, interface_definitions)

        # Assert
        assert issues == []  # 問題なし

    def test_evaluator_checks_slack_derived_fields(self) -> None:
        """評価ノード: Slack送信タスクに対して slack_title/slack_message を要求"""
        # Arrange
        tasks = [
            {"task_id": "summarize", "task_type": "summarization"},
            {"task_id": "send_slack", "task_type": "slack_notification"},
        ]
        interface_definitions: dict[str, dict[str, Any]] = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    # x-derived-fields が未定義
                },
            },
        }

        # Act
        issues = check_derived_fields_for_downstream_tasks(tasks, interface_definitions)

        # Assert
        assert len(issues) >= 1
        assert any("slack" in issue.lower() for issue in issues)


@pytest.mark.acceptance
class TestIssue337AcceptanceIntegration:
    """
    Issue #337: 統合シナリオテスト

    メール送信ワークフローを想定した統合テスト
    """

    def test_full_scenario_email_workflow_derived_fields(self) -> None:
        """統合シナリオ: Google検索→要約→メール送信のフル構成

        設計書の机上シミュレーション結果を検証:
        - 要約タスクの output_schema に x-derived-fields が含まれる
        - email_subject と email_body が定義される
        - テンプレート変数が適切に解決される
        """
        # Arrange: 要約タスクのインターフェース定義
        summarize_interface = InterfaceSchemaDefinition(
            task_id="summarize",
            interface_name="summarize_interface",
            description="検索結果を要約するタスク",
            input_schema={
                "type": "object",
                "properties": {
                    "search_results": {"type": "array"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "summary_text": {"type": "string"},
                    "key_points": {"type": "string"},
                },
            },
            derived_fields={
                "email_subject": DerivedFieldDefinition(
                    template="検索結果サマリ: {query}",
                    type="string",
                    source_mapping={"query": "source.user_input.query"},
                ),
                "email_body": DerivedFieldDefinition(
                    template="{summary_text}\n\n重要ポイント:\n{key_points}",
                    type="string",
                ),
            },
        )

        # Assert: インターフェース定義が正しい
        assert len(summarize_interface.derived_fields) == 2

        # Act: テンプレート検証
        email_subject_def = summarize_interface.derived_fields["email_subject"]
        email_body_def = summarize_interface.derived_fields["email_body"]

        # email_subject: {query} は source_mapping で解決
        subject_unresolved = validate_template(
            email_subject_def.template,
            summarize_interface.output_schema.get("properties", {}),
            email_subject_def.source_mapping,
        )
        assert subject_unresolved == []

        # email_body: {summary_text}, {key_points} は properties から解決
        body_unresolved = validate_template(
            email_body_def.template,
            summarize_interface.output_schema.get("properties", {}),
            email_body_def.source_mapping,
        )
        assert body_unresolved == []

        # Act: 評価ノードチェック
        tasks = [
            {"task_id": "search", "task_type": "google_search"},
            {"task_id": "summarize", "task_type": "summarization"},
            {"task_id": "send_email", "task_type": "email_send"},
        ]

        # output_schema に x-derived-fields を追加（InterfaceMaster 登録時の形式）
        interface_definitions: dict[str, dict[str, Any]] = {
            "search": {
                "output_schema": {"properties": {"results": {"type": "array"}}},
            },
            "summarize": {
                "output_schema": {
                    "properties": {
                        "summary_text": {"type": "string"},
                        "key_points": {"type": "string"},
                    },
                    "x-derived-fields": {
                        "email_subject": {"template": "検索結果サマリ: {query}"},
                        "email_body": {"template": "{summary_text}\n\n重要ポイント:\n{key_points}"},
                    },
                },
            },
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interface_definitions)

        # Assert: 問題なし
        assert issues == [], f"Unexpected issues: {issues}"
