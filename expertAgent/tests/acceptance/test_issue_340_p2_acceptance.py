"""
Issue #340 P2フェーズ 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_340_p2_acceptance.py -v

P2修正内容:
- P2-8: workflow_validator配列検証（Layer 4: ワークフロー検証）
- P2-9: interface_definition default検証（Layer 0: スキーマ生成時検証）
"""

from typing import Any

import pytest


@pytest.mark.acceptance
class TestIssue340P2Acceptance:
    """Issue #340 P2: Layer 4 ワークフロー検証強化 - 受入テスト"""

    # ==========================================================================
    # P2-8: workflow_validator 配列検証テスト
    # ==========================================================================

    def test_p2_8_validate_workflow_arrays_detects_object_arrays(self) -> None:
        """P2-8: validate_workflow_arraysがオブジェクト配列を検出することを確認

        受入条件: ワークフロー生成時にオブジェクト配列が検出される
        """
        from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
            validate_workflow_arrays,
        )

        # Arrange: オブジェクト配列（items.type=object）への参照を含むワークフロー
        # Note: 関数は :source.user_input.xxx パターンを検出する
        workflow_yaml = """
version: 0.5
nodes:
  source: {}
  stringTemplate1:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
    params:
      template: "Results: ${search_results}"
  output:
    agent: copyAgent
    inputs:
      text: :stringTemplate1.text
    isResult: true
"""
        # interface_schemaでsearch_resultsがオブジェクト配列として定義
        interface_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "search_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                },
            },
        }

        # Act
        issues = validate_workflow_arrays(workflow_yaml, interface_schema)

        # Assert: オブジェクト配列が検出される
        assert len(issues) >= 1, (
            f"Expected at least 1 issue for object array, got {len(issues)}"
        )
        assert any(
            "search_results" in str(issue.get("field_name", "")) for issue in issues
        ), f"Expected issue for search_results field, got: {issues}"

    def test_p2_8_validate_workflow_arrays_accepts_primitive_arrays(self) -> None:
        """P2-8: プリミティブ配列は問題なしと判定されることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
            validate_workflow_arrays,
        )

        # Arrange: プリミティブ配列（items.type=string）への参照を含むワークフロー
        workflow_yaml = """
version: 0.5
nodes:
  source: {}
  stringTemplate1:
    agent: stringTemplateAgent
    inputs:
      focus_points: :source.user_input.focus_points
    params:
      template: "Focus: ${focus_points}"
  output:
    agent: copyAgent
    inputs:
      text: :stringTemplate1.text
    isResult: true
"""
        # interface_schemaでfocus_pointsがプリミティブ配列として定義
        interface_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

        # Act
        issues = validate_workflow_arrays(workflow_yaml, interface_schema)

        # Assert: 問題なし（プリミティブ配列はOK）
        assert len(issues) == 0, f"Expected no issues for primitive array, got {issues}"

    def test_p2_8_validate_workflow_arrays_function_exists(self) -> None:
        """P2-8: validate_workflow_arrays関数がエクスポートされていることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.utils import (
            validate_workflow_arrays,
        )

        # Assert: 関数がインポートできる
        assert callable(validate_workflow_arrays), (
            "validate_workflow_arrays should be callable"
        )

    # ==========================================================================
    # P2-9: interface_definition default検証テスト
    # ==========================================================================

    def test_p2_9_normalize_removes_object_array_default(self) -> None:
        """P2-9: normalize_json_schema_propertiesがオブジェクト配列defaultを除去することを確認

        受入条件: Interface Schema生成時にdefault値の型検証が行われる
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        # Arrange: オブジェクト配列のdefaultを含む完全なスキーマ
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [
                        {"type": "string", "description": "最新ニュース"},
                        {"type": "string", "description": "主要なトピック"},
                    ],
                }
            },
        }

        # Act
        normalized = normalize_json_schema_properties(schema)

        # Assert: defaultが除去されている
        assert "default" not in normalized.get("properties", {}).get(
            "focus_points", {}
        ), (
            f"Expected default to be removed, got: {normalized.get('properties', {}).get('focus_points')}"
        )

    def test_p2_9_normalize_keeps_valid_string_array_default(self) -> None:
        """P2-9: 正しいプリミティブ配列defaultは保持されることを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            normalize_json_schema_properties,
        )

        # Arrange: 正しいプリミティブ配列のdefaultを含む完全なスキーマ
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["最新ニュース", "主要なトピック"],
                }
            },
        }

        # Act
        normalized = normalize_json_schema_properties(schema)

        # Assert: defaultが保持されている
        assert normalized.get("properties", {}).get("focus_points", {}).get(
            "default"
        ) == [
            "最新ニュース",
            "主要なトピック",
        ], (
            f"Expected default to be kept, got: {normalized.get('properties', {}).get('focus_points')}"
        )

    def test_p2_9_validate_array_default_helper_exists(self) -> None:
        """P2-9: _validate_array_defaultヘルパー関数が存在することを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            _validate_array_default,
        )

        # Assert: 関数が存在する
        assert callable(_validate_array_default), (
            "_validate_array_default should be callable"
        )


@pytest.mark.acceptance
class TestIssue340P2IntegrationAcceptance:
    """Issue #340 P2: 統合テスト（全フェーズ確認）"""

    def test_p2_all_layers_have_issue_340_implementation(self) -> None:
        """全Layer (0-4) にIssue #340対応が実装されていることを確認"""
        # Layer 0: interface_definition
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
            _validate_array_default,
        )

        # Layer 1: sample_input_generator
        from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
            _enum_or_default,
            _validate_primitive_arrays,
        )

        # Layer 3: llm_evaluation
        from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
            LLM_EVALUATION_SYSTEM_PROMPT,
        )

        # Layer 2: test_data_regeneration prompt
        from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
            TEST_DATA_REGENERATION_SYSTEM_PROMPT,
        )

        # Layer 4: workflow_validator
        from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
            validate_workflow_arrays,
        )

        # Assert: All functions/prompts exist
        assert callable(_validate_array_default), "Layer 0: _validate_array_default"
        assert callable(_enum_or_default), "Layer 1: _enum_or_default"
        assert callable(_validate_primitive_arrays), (
            "Layer 1: _validate_primitive_arrays"
        )
        assert "Issue #340" in TEST_DATA_REGENERATION_SYSTEM_PROMPT, (
            "Layer 2: Issue #340 in prompt"
        )
        assert "Issue #340" in LLM_EVALUATION_SYSTEM_PROMPT, (
            "Layer 3: Issue #340 in prompt"
        )
        assert callable(validate_workflow_arrays), "Layer 4: validate_workflow_arrays"

    def test_p2_5_layer_defense_architecture_complete(self) -> None:
        """5層防御アーキテクチャが完成していることを確認"""
        # Import all layer implementations
        layers_implemented = {
            "Layer 0 (Schema Generation)": False,
            "Layer 1 (Test Data Generation)": False,
            "Layer 2 (Prompt Constraints)": False,
            "Layer 3 (Runtime Detection)": False,
            "Layer 4 (Workflow Validation)": False,
        }

        try:
            from aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition import (
                _validate_array_default,
            )

            assert callable(_validate_array_default)
            layers_implemented["Layer 0 (Schema Generation)"] = True
        except ImportError:
            pass

        try:
            from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
                _validate_primitive_arrays,
            )

            assert callable(_validate_primitive_arrays)
            layers_implemented["Layer 1 (Test Data Generation)"] = True
        except ImportError:
            pass

        try:
            from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
                TEST_DATA_REGENERATION_SYSTEM_PROMPT,
            )

            if "Issue #340" in TEST_DATA_REGENERATION_SYSTEM_PROMPT:
                layers_implemented["Layer 2 (Prompt Constraints)"] = True
        except ImportError:
            pass

        try:
            from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
                llm_evaluator_node,
            )

            assert callable(llm_evaluator_node)
            layers_implemented["Layer 3 (Runtime Detection)"] = True
        except ImportError:
            pass

        try:
            from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
                validate_workflow_arrays,
            )

            assert callable(validate_workflow_arrays)
            layers_implemented["Layer 4 (Workflow Validation)"] = True
        except ImportError:
            pass

        # Assert: All 5 layers are implemented
        for layer, implemented in layers_implemented.items():
            assert implemented, f"{layer} is not implemented"

        assert all(layers_implemented.values()), (
            f"5-layer defense architecture incomplete: {layers_implemented}"
        )
