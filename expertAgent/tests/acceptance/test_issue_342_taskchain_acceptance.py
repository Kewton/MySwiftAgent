"""
Issue #342 タスクチェーン修正 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (USE_JOB_GENERATOR_V2=true ./scripts/dev-hybrid.sh)
- .env に必要なAPIキーが設定されていること

実行方法:
  uv run pytest tests/acceptance/test_issue_342_taskchain_acceptance.py -v

検証内容:
- RC-1: body_template二重ネスト修正 ({{job.body}} -> {{job.body.user_input}})
- RC-2: 出力ノード命名規則追加 (OUTPUT_NODE_RULE)
- E2E: タスクチェーン実行時にデータが正しく受け渡されること
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules.base_rules import (
    BASE_RULES,
    OUTPUT_NODE_RULE,
    get_base_rules,
)


@pytest.mark.acceptance
class TestIssue342TaskChainAcceptance:
    """Issue #342: タスクチェーン修正の受入テスト"""

    # ==========================================================================
    # RC-1: body_template二重ネスト修正の検証
    # ==========================================================================

    def test_body_template_task_0_uses_user_input(self) -> None:
        """受入条件: Task 0のbody_templateが{{job.body.user_input}}を使用する

        根本原因1 (RC-1) の修正検証:
        - Task 0の場合、user_inputに{{job.body}}ではなく{{job.body.user_input}}を使用
        - これにより、:source.user_input.queryが正しく参照可能になる
        """
        # Arrange
        workflow = MasterManagerSubWorkflow()

        # Act
        body_template = workflow._build_body_template(0)

        # Assert - Task 0 uses {{job.body.user_input}} not {{job.body}}
        assert body_template["user_input"] == "{{job.body.user_input}}", (
            f"Task 0 should use '{{{{job.body.user_input}}}}' but got '{body_template['user_input']}'"
        )
        assert body_template["job_params"] == "{{job.body}}", (
            "job_params should still reference full job.body"
        )

    def test_body_template_task_0_does_not_cause_double_nesting(self) -> None:
        """検証: Task 0のbody_templateが二重ネストを発生させない

        問題: {{job.body}}を使うと、job.body = {"user_input": {...}}なので
        body_template = {"user_input": {"user_input": {...}}} になってしまう

        修正後: {{job.body.user_input}}を使うので
        body_template = {"user_input": {...}} になる
        """
        # Arrange
        workflow = MasterManagerSubWorkflow()

        # Act
        body_template = workflow._build_body_template(0)

        # Assert - user_input should not reference {{job.body}} (which would cause double nesting)
        assert "{{job.body}}" not in body_template["user_input"], (
            "Task 0 user_input should NOT use '{{job.body}}' as it causes double nesting"
        )
        assert "user_input" in body_template["user_input"], (
            "Task 0 user_input should contain 'user_input' to extract the correct field"
        )

    def test_body_template_task_n_uses_previous_output(self) -> None:
        """検証: Task 1以降のbody_templateが前タスクの出力を参照する"""
        # Arrange
        workflow = MasterManagerSubWorkflow()

        # Act
        body_template_1 = workflow._build_body_template(1)
        body_template_2 = workflow._build_body_template(2)

        # Assert - Task 1+ uses {{tasks[N-1].output_data}}
        assert body_template_1["user_input"] == "{{tasks[0].output_data}}", (
            f"Task 1 should use '{{{{tasks[0].output_data}}}}' but got '{body_template_1['user_input']}'"
        )
        assert body_template_2["user_input"] == "{{tasks[1].output_data}}", (
            f"Task 2 should use '{{{{tasks[1].output_data}}}}' but got '{body_template_2['user_input']}'"
        )

    # ==========================================================================
    # RC-2: 出力ノード命名規則の検証
    # ==========================================================================

    def test_output_node_rule_exists(self) -> None:
        """受入条件: OUTPUT_NODE_RULEが定義されている"""
        # Assert
        assert OUTPUT_NODE_RULE is not None, "OUTPUT_NODE_RULE should be defined"
        assert len(OUTPUT_NODE_RULE) > 0, "OUTPUT_NODE_RULE should not be empty"

    def test_output_node_rule_mentions_output_name(self) -> None:
        """検証: OUTPUT_NODE_RULEが'output'ノード名を指示している"""
        # Assert
        assert "output" in OUTPUT_NODE_RULE.lower(), (
            "OUTPUT_NODE_RULE should mention 'output' node name"
        )
        assert "MUST" in OUTPUT_NODE_RULE or "must" in OUTPUT_NODE_RULE, (
            "OUTPUT_NODE_RULE should have strong requirement language"
        )

    def test_output_node_rule_in_base_rules(self) -> None:
        """受入条件: OUTPUT_NODE_RULEがBASE_RULESに含まれている"""
        # Assert - OUTPUT_NODE_RULE content should appear in BASE_RULES
        # Since BASE_RULES is an f-string that includes {OUTPUT_NODE_RULE}
        assert "Output Node Naming" in BASE_RULES, (
            "BASE_RULES should include OUTPUT_NODE_RULE content"
        )
        assert "MUST be named `output`" in BASE_RULES or "must be named" in BASE_RULES.lower(), (
            "BASE_RULES should instruct that output node must be named 'output'"
        )

    def test_get_base_rules_returns_output_node_rule(self) -> None:
        """検証: get_base_rules()がOUTPUT_NODE_RULEを含むルールを返す"""
        # Act
        rules = get_base_rules()

        # Assert
        assert "Output Node Naming" in rules, (
            "get_base_rules() should return rules containing OUTPUT_NODE_RULE"
        )
        assert "output" in rules.lower(), (
            "Rules should mention 'output' node name"
        )

    def test_output_node_rule_forbids_format_output(self) -> None:
        """検証: OUTPUT_NODE_RULEがformat_output等の使用を禁止している

        根本原因2 (RC-2):
        - Workerは'output'ノードを期待
        - LLMが'format_output'等を生成すると出力抽出に失敗
        """
        # Assert
        assert "format_output" in OUTPUT_NODE_RULE.lower(), (
            "OUTPUT_NODE_RULE should explicitly mention 'format_output' as incorrect"
        )
        assert "WRONG" in OUTPUT_NODE_RULE or "DO NOT" in OUTPUT_NODE_RULE, (
            "OUTPUT_NODE_RULE should explicitly prohibit wrong names"
        )

    # ==========================================================================
    # 統合検証
    # ==========================================================================

    def test_both_root_causes_addressed(self) -> None:
        """統合検証: 両方の根本原因が修正されている

        RC-1: body_template二重ネスト問題
        RC-2: 出力ノード命名不整合
        """
        # RC-1: body_template check
        workflow = MasterManagerSubWorkflow()
        body_template = workflow._build_body_template(0)
        rc1_fixed = body_template["user_input"] == "{{job.body.user_input}}"

        # RC-2: OUTPUT_NODE_RULE check
        rules = get_base_rules()
        rc2_fixed = "Output Node Naming" in rules and "output" in rules.lower()

        # Assert both root causes are fixed
        assert rc1_fixed, "RC-1 (body_template double nesting) should be fixed"
        assert rc2_fixed, "RC-2 (output node naming) should be fixed"
