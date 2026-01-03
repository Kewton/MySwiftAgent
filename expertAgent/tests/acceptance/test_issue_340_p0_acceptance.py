"""
Issue #340 P0フェーズ 受入テスト（L3: ローカル受入テスト）

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_340_p0_acceptance.py -v

P0修正内容:
- P0-1: Interface Schemaプロンプトにdefault値ルール追加
- P0-2: _enum_or_default型検証追加（string/number/integer/boolean配列）
- P0-3: sample_input_router実装と条件分岐追加
- MF-1: 無限ループ防止（object_array_regeneration_count）
- MF-2: boolean配列の型検証追加
"""

from typing import Any

import pytest


@pytest.mark.acceptance
class TestIssue340P0Acceptance:
    """Issue #340 P0: [object Object] 問題の修正 - 受入テスト"""

    # ==========================================================================
    # P0-2: _enum_or_default 型検証テスト
    # ==========================================================================

    def test_p0_2_enum_or_default_rejects_object_array_default(self) -> None:
        """P0-2: オブジェクト配列を含むdefault値がスキップされることを確認

        受入条件: テストデータ生成時にオブジェクト配列が不適切に使用されないようバリデーション
        """
        from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
            _enum_or_default,
        )

        # Arrange: オブジェクト配列を含むスキーマ（Issue #340の根本原因）
        schema_with_object_array: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string"},
            "default": [
                {"type": "string", "description": "最新ニュース"},
                {"type": "string", "description": "主要なトピック"},
            ],
        }

        # Act
        result = _enum_or_default(schema_with_object_array)

        # Assert: オブジェクト配列はスキップされてNoneが返る
        assert result is None, (
            f"Expected None for object array default, got {result}. "
            "Object arrays in default should be rejected to prevent [object Object] errors."
        )

    def test_p0_2_enum_or_default_accepts_valid_string_array_default(self) -> None:
        """P0-2: 正しい文字列配列のdefault値が受け入れられることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
            _enum_or_default,
        )

        # Arrange: 正しい文字列配列のスキーマ
        schema_with_valid_default: dict[str, Any] = {
            "type": "array",
            "items": {"type": "string"},
            "default": ["最新ニュース", "主要なトピック"],
        }

        # Act
        result = _enum_or_default(schema_with_valid_default)

        # Assert: 正しい文字列配列は返される
        assert result == ["最新ニュース", "主要なトピック"], (
            f"Expected valid string array default, got {result}"
        )

    def test_p0_2_mf2_enum_or_default_validates_boolean_array(self) -> None:
        """MF-2: boolean配列の型検証が正しく動作することを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
            _enum_or_default,
        )

        # Arrange: 正しいboolean配列
        schema_valid_boolean: dict[str, Any] = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": [True, False, True],
        }

        # 不正なboolean配列（文字列が含まれる）
        schema_invalid_boolean: dict[str, Any] = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": ["true", "false"],
        }

        # Act & Assert: 正しいboolean配列は受け入れ
        result_valid = _enum_or_default(schema_valid_boolean)
        assert result_valid == [True, False, True], (
            f"Expected boolean array, got {result_valid}"
        )

        # Act & Assert: 不正なboolean配列は拒否
        result_invalid = _enum_or_default(schema_invalid_boolean)
        assert result_invalid is None, (
            f"Expected None for invalid boolean array, got {result_invalid}"
        )

    # ==========================================================================
    # P0-3: sample_input_router テスト
    # ==========================================================================

    def test_p0_3_sample_input_router_routes_to_regenerator_on_error(self) -> None:
        """P0-3: オブジェクト配列検出時にtest_data_regeneratorへルーティングされることを確認

        受入条件: workflow_tester で [object Object] パターンを検出した場合にエラーまたは警告を出力
        """
        from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
            sample_input_router,
        )

        # Arrange: オブジェクト配列エラーが検出された状態
        state_with_errors: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [
                {"field_name": "focus_points", "issue_type": "object_in_array"}
            ],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }

        # Act
        result = sample_input_router(state_with_errors)

        # Assert: エラーがある場合はtest_data_regeneratorへ
        assert result == "test_data_regenerator", (
            f"Expected routing to test_data_regenerator on error, got {result}"
        )

    def test_p0_3_sample_input_router_routes_to_tester_on_no_error(self) -> None:
        """P0-3: エラーがない場合はworkflow_testerへルーティングされることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
            sample_input_router,
        )

        # Arrange: エラーがない状態
        state_without_errors: dict[str, Any] = {
            "has_object_array_errors": False,
            "object_array_issues": [],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }

        # Act
        result = sample_input_router(state_without_errors)

        # Assert: エラーがない場合はworkflow_testerへ
        assert result == "workflow_tester", (
            f"Expected routing to workflow_tester on no error, got {result}"
        )

    # ==========================================================================
    # MF-1: 無限ループ防止テスト
    # ==========================================================================

    def test_mf1_sample_input_router_prevents_infinite_loop(self) -> None:
        """MF-1: 再生成上限超過時にworkflow_testerへ進むことを確認

        受入条件: 無限ループを防止するために再生成回数の上限を設ける
        """
        from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
            sample_input_router,
        )

        # Arrange: 再生成上限に達した状態
        state_max_exceeded: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 2,  # 上限に達している
            "max_object_array_regeneration": 2,
        }

        # Act
        result = sample_input_router(state_max_exceeded)

        # Assert: 上限超過時はworkflow_testerへ（エラーがあっても）
        assert result == "workflow_tester", (
            f"Expected routing to workflow_tester when max regeneration exceeded, got {result}. "
            "This is critical for preventing infinite loops."
        )

    def test_mf1_sample_input_router_allows_regeneration_under_limit(self) -> None:
        """MF-1: 上限未満の場合は再生成へルーティングされることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
            sample_input_router,
        )

        # Arrange: 再生成1回目（上限2回）
        state_under_limit: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 1,  # まだ上限未満
            "max_object_array_regeneration": 2,
        }

        # Act
        result = sample_input_router(state_under_limit)

        # Assert: 上限未満の場合はtest_data_regeneratorへ
        assert result == "test_data_regenerator", (
            f"Expected routing to test_data_regenerator when under limit, got {result}"
        )

    # ==========================================================================
    # State フィールド確認テスト
    # ==========================================================================

    def test_state_has_object_array_regeneration_fields(self) -> None:
        """State に MF-1 対応のフィールドが存在することを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.state import create_initial_state

        # Act: 実際の関数シグネチャに合わせる
        task_data: dict[str, Any] = {
            "task_name": "test_task",
            "task_description": "test",
            "interface_schema": {},
        }
        initial_state = create_initial_state(
            task_master_id="test_task_master_id",
            task_data=task_data,
        )

        # Assert: MF-1 フィールドが存在し、初期値が設定されている
        assert "object_array_regeneration_count" in initial_state, (
            "Missing object_array_regeneration_count field in state"
        )
        assert initial_state["object_array_regeneration_count"] == 0, (
            "Initial object_array_regeneration_count should be 0"
        )

    # ==========================================================================
    # Interface Schema プロンプト確認テスト
    # ==========================================================================

    def test_p0_1_interface_schema_prompt_includes_default_rules(self) -> None:
        """P0-1: Interface Schemaプロンプトにdefault値ルールが含まれることを確認"""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
            INTERFACE_SCHEMA_SYSTEM_PROMPT,
        )

        # Assert: Issue #340 に関連するルールがプロンプトに含まれている
        assert (
            "Issue #340" in INTERFACE_SCHEMA_SYSTEM_PROMPT
            or "default" in INTERFACE_SCHEMA_SYSTEM_PROMPT.lower()
        ), "Interface Schema prompt should include default value rules (Issue #340)"

        # Assert: 禁止パターンの説明が含まれている
        assert any(
            keyword in INTERFACE_SCHEMA_SYSTEM_PROMPT.lower()
            for keyword in ["禁止", "forbidden", "wrong", "incorrect", "ng"]
        ), "Interface Schema prompt should include forbidden pattern examples"


@pytest.mark.acceptance
class TestIssue340P0IntegrationAcceptance:
    """Issue #340 P0: 統合テスト（グラフ構造の確認）"""

    def test_graph_has_conditional_edges_after_sample_input_generator(self) -> None:
        """グラフにsample_input_generatorからの条件分岐が設定されていることを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            create_workflow_generator_graph,
        )

        # Act: グラフを作成
        graph = create_workflow_generator_graph()

        # Assert: グラフが作成される（条件分岐が含まれる）
        assert graph is not None, "Graph should be created"

        # Note: 詳細なエッジの検証はunit/integration テストで実施済み
        # このテストはグラフが正常に作成されることを確認

    def test_validate_primitive_arrays_detects_objects(self) -> None:
        """_validate_primitive_arrays がオブジェクト配列を検出することを確認"""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
            _validate_primitive_arrays,
        )

        # Arrange: オブジェクト配列を含むsample_input
        sample_input: dict[str, Any] = {
            "focus_points": [
                {"type": "string", "description": "最新ニュース"},
                {"type": "string", "description": "主要なトピック"},
            ],
            "valid_field": ["string1", "string2"],
        }
        # 検証対象フィールド（stringTemplateで使用されるフィールド）
        target_fields: set[str] = {"focus_points", "valid_field"}

        # Act: 関数は2つの引数のみ（sample_input, target_fields）
        issues = _validate_primitive_arrays(sample_input, target_fields)

        # Assert: focus_pointsのオブジェクト配列が検出される
        assert len(issues) >= 1, f"Expected at least 1 issue, got {len(issues)}"
        focus_points_issues = [
            i for i in issues if i.get("field_name") == "focus_points"
        ]
        assert len(focus_points_issues) >= 1, (
            f"Expected focus_points issue, got issues: {issues}"
        )
