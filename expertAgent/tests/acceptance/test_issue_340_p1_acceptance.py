"""
Issue #340 P1フェーズ 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_340_p1_acceptance.py -v

P1修正内容:
- P1-4: test_data_regenerationプロンプトに配列制約ルール追加
- P1-5: object_array_issues引き渡し（test_data_regenerator）
- P1-6: LLM Evaluationプロンプト・ノード修正
- P1-7: self_repair_nodeにobject_array_issuesフィードバック追加
"""

from typing import Any

import pytest


@pytest.mark.acceptance
class TestIssue340P1Acceptance:
    """Issue #340 P1: Layer 2/3 実行時検出強化 - 受入テスト"""

    # ==========================================================================
    # P1-4: test_data_regeneration プロンプト確認テスト
    # ==========================================================================

    def test_p1_4_test_data_regeneration_prompt_includes_array_constraints(
        self,
    ) -> None:
        """P1-4: test_data_regenerationプロンプトに配列制約ルールが含まれることを確認

        受入条件: テストデータ再生成時にオブジェクト配列問題が明示される
        """
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Assert: Issue #340 配列制約セクションが含まれている
        assert "Issue #340" in TEST_DATA_REGENERATION_SYSTEM_PROMPT, (
            "TEST_DATA_REGENERATION_SYSTEM_PROMPT should include Issue #340 reference"
        )

        # Assert: プリミティブ型のみルールが含まれている
        assert (
            "プリミティブ" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
            or "primitive" in TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
        ), "TEST_DATA_REGENERATION_SYSTEM_PROMPT should include primitive type rule"

        # Assert: オブジェクト禁止パターンが含まれている
        assert (
            "禁止" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
            or "prohibited" in TEST_DATA_REGENERATION_SYSTEM_PROMPT.lower()
        ), "TEST_DATA_REGENERATION_SYSTEM_PROMPT should include object prohibition rule"

    # ==========================================================================
    # P1-5: object_array_issues 引き渡しテスト
    # ==========================================================================

    def test_p1_5_test_data_regenerator_merges_object_array_issues(self) -> None:
        """P1-5: test_data_regeneratorがobject_array_issuesをマージすることを確認

        受入条件: 再生成時にオブジェクト配列問題が明示される
        """
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            _build_regenerator_input,
        )

        # Arrange: object_array_issuesを含むstate
        mock_state: dict[str, Any] = {
            "interface_schema": {
                "focus_points": {"type": "array", "items": {"type": "string"}}
            },
            "sample_input": {"focus_points": ["test"]},
            "task_description": "Test task",
            "test_data_issues": ["Previous issue"],
            "object_array_issues": [
                {
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object at index 0",
                    "suggestion": "Use primitive types only",
                }
            ],
        }

        # Act
        result = _build_regenerator_input(mock_state)

        # Assert: object_array_issuesがマージされている
        assert (
            "object_array" in result.lower() or "object_in_array" in result.lower()
        ), (
            f"_build_regenerator_input should include object_array_issues in output, got: {result[:500]}"
        )

    # ==========================================================================
    # P1-6: LLM Evaluation プロンプト・ノード確認テスト
    # ==========================================================================

    def test_p1_6_llm_evaluation_prompt_includes_array_validation_criteria(
        self,
    ) -> None:
        """P1-6: LLM Evaluationプロンプトに配列検証基準が含まれることを確認

        受入条件: LLM評価で[object Object]パターンを検出した場合にスコア減点
        """
        from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
            LLM_EVALUATION_SYSTEM_PROMPT,
        )

        # Assert: Issue #340 参照が含まれている
        assert "Issue #340" in LLM_EVALUATION_SYSTEM_PROMPT, (
            "LLM_EVALUATION_SYSTEM_PROMPT should include Issue #340 reference"
        )

        # Assert: [object Object] パターン検出ルールが含まれている
        assert (
            "[object Object]" in LLM_EVALUATION_SYSTEM_PROMPT
            or "object Object" in LLM_EVALUATION_SYSTEM_PROMPT
        ), (
            "LLM_EVALUATION_SYSTEM_PROMPT should include [object Object] pattern detection"
        )

    def test_p1_6_llm_evaluator_detects_object_array_errors(self) -> None:
        """P1-6: llm_evaluatorがobject_array_errorsを検出してregenをトリガーすることを確認"""
        import asyncio

        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        # Arrange: object_array_errorsがある状態
        mock_state: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [
                {"field_name": "focus_points", "issue_type": "object_in_array"}
            ],
            "test_result": {"status": "success"},
            "is_valid": True,
            "task_description": "Test task",
            "interface_schema": {},
            "generated_workflow": "test: workflow",
            "sample_input": {},
        }

        # Act
        result = asyncio.get_event_loop().run_until_complete(
            llm_evaluator_node(mock_state)
        )

        # Assert: needs_test_data_regenerationがTrueになる
        assert result.get("needs_test_data_regeneration") is True, (
            f"llm_evaluator should set needs_test_data_regeneration=True when object_array_errors exist, "
            f"got: {result.get('needs_test_data_regeneration')}"
        )

        # Assert: failure_reasonがtest_data_quality
        llm_result = result.get("llm_evaluation_result", {})
        assert llm_result.get("failure_reason") == "test_data_quality", (
            f"failure_reason should be 'test_data_quality', got: {llm_result.get('failure_reason')}"
        )

    # ==========================================================================
    # P1-7: self_repair_node 修正テスト
    # ==========================================================================

    def test_p1_7_self_repair_includes_object_array_feedback(self) -> None:
        """P1-7: self_repair_nodeがobject_array_issuesをフィードバックに含めることを確認

        受入条件: 自己修復フィードバックにオブジェクト配列問題が含まれる
        """
        import asyncio

        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        # Arrange: object_array_issuesを含むstate
        mock_state: dict[str, Any] = {
            "object_array_issues": [
                {
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object",
                    "suggestion": "Use primitive types only",
                }
            ],
            "validation_errors": [],
            "schema_validation_issues": [],
            "retry_count": 0,
            "max_retry": 3,
            "repair_history": [],
            "generated_workflow": "test: workflow",
            "task_description": "Test task",
            "interface_schema": {},
        }

        # Act
        result = asyncio.get_event_loop().run_until_complete(
            self_repair_node(mock_state)
        )

        # Assert: フィードバックにobject_array_issuesが含まれる
        error_feedback = result.get("error_feedback", "")
        assert (
            "object_array" in error_feedback.lower() or "Issue #340" in error_feedback
        ), (
            f"error_feedback should include object_array references, got: {error_feedback[:500]}"
        )

    def test_p1_7_self_repair_resets_object_array_state(self) -> None:
        """P1-7: self_repair_nodeがobject_array状態をリセットすることを確認"""
        import asyncio

        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        # Arrange: object_array関連フィールドがある状態
        mock_state: dict[str, Any] = {
            "object_array_issues": [{"field_name": "test"}],
            "has_object_array_errors": True,
            "object_array_regeneration_count": 2,
            "validation_errors": ["Some error"],
            "schema_validation_issues": [],
            "retry_count": 0,
            "max_retry": 3,
            "repair_history": [],
            "generated_workflow": "test: workflow",
            "task_description": "Test task",
            "interface_schema": {},
        }

        # Act
        result = asyncio.get_event_loop().run_until_complete(
            self_repair_node(mock_state)
        )

        # Assert: object_array状態がリセットされる
        assert result.get("object_array_issues") == [], (
            f"object_array_issues should be reset to [], got: {result.get('object_array_issues')}"
        )
        assert result.get("has_object_array_errors") is False, (
            f"has_object_array_errors should be False, got: {result.get('has_object_array_errors')}"
        )
        assert result.get("object_array_regeneration_count") == 0, (
            f"object_array_regeneration_count should be 0, got: {result.get('object_array_regeneration_count')}"
        )


@pytest.mark.acceptance
class TestIssue340P1IntegrationAcceptance:
    """Issue #340 P1: 統合テスト（フロー全体の確認）"""

    def test_p1_all_prompts_have_issue_340_references(self) -> None:
        """全P1関連プロンプトにIssue #340参照が含まれることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
            LLM_EVALUATION_SYSTEM_PROMPT,
        )
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        prompts = {
            "TEST_DATA_REGENERATION_SYSTEM_PROMPT": TEST_DATA_REGENERATION_SYSTEM_PROMPT,
            "LLM_EVALUATION_SYSTEM_PROMPT": LLM_EVALUATION_SYSTEM_PROMPT,
        }

        for name, prompt in prompts.items():
            assert "Issue #340" in prompt, f"{name} should include Issue #340 reference"
