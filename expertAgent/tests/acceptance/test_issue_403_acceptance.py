"""
Issue #403 受入テスト（L3: ローカル受入テスト）

body_template生成でinterfaceDefinitionsを考慮した複数タスクからのデータ集約

前提条件:
- サービスが起動していること (./scripts/dev-hybrid.sh start --local-only)
- myVaultに必要なAPIキーが設定されていること

実行方法:
  cd expertAgent && uv run pytest tests/acceptance/test_issue_403_acceptance.py -v -s
"""

from unittest.mock import MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.types_old import (
    InterfaceSchema,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)


@pytest.mark.acceptance
class TestIssue403Acceptance:
    """Issue #403: body_template生成でinterfaceDefinitionsを考慮した複数タスクからのデータ集約。

    受入条件:
    - AC-1: interfaceDefinitionsの入力要件を解析して必要なフィールドを特定する
    - AC-2: 各フィールドの取得元タスクをdependenciesから決定する
    - AC-3: 複数タスクからのデータを集約するbody_templateを生成する
    - AC-4: task_006のbody_templateが{keyword, summary, recipient_email}を正しく参照する
    - AC-5: 既存の単一依存タスクでも正しく動作する（後方互換性）
    - AC-6: 依存タスクの出力にフィールドが存在しない場合、user_inputからフォールバック取得
    - AC-7: interfacesが存在しないタスクの場合、従来の動作にフォールバック
    - AC-8: 単体テスト - _find_field_sourceの正常系・異常系テスト
    - AC-9: 単体テスト - _build_body_templateの複数依存タスクテスト
    - AC-10: 結合テスト - 複数依存を持つワークフローのE2E登録テスト
    """

    # ==========================================================================
    # TC-001〜TC-003: _find_field_source テスト
    # ==========================================================================

    def test_tc001_find_field_source_single_dependency(self) -> None:
        """TC-001: 単一依存でフィールドを正しく解決できる。

        受入条件: AC-2, AC-8
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {"query": {"type": "string"}}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
        }
        task_order_map = {"task_001": 0}
        dependencies = ["task_001"]

        # Act
        result = manager._find_field_source(
            field="keyword",
            dependencies=dependencies,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        assert result == "task_001", f"Expected 'task_001', got {result}"

    def test_tc002_find_field_source_multiple_deps_first_match(self) -> None:
        """TC-002: 複数依存で依存順序優先で解決できる。

        受入条件: AC-2, AC-8
        設計方針: DP-1 (依存順序優先)
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        # task_001とtask_003の両方がkeywordを出力
        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={"properties": {}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
        }
        task_order_map = {"task_001": 0, "task_003": 2}
        dependencies = ["task_001", "task_003"]

        # Act
        result = manager._find_field_source(
            field="keyword",
            dependencies=dependencies,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert: 依存順序で最初のtask_001が選択される
        assert result == "task_001", f"Expected 'task_001', got {result}"

    def test_tc003_find_field_source_field_not_found(self) -> None:
        """TC-003: フィールドが見つからない場合Noneを返却。

        受入条件: AC-6, AC-8
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
        }
        task_order_map = {"task_001": 0}
        dependencies = ["task_001"]

        # Act
        result = manager._find_field_source(
            field="nonexistent_field",
            dependencies=dependencies,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        assert result is None, f"Expected None, got {result}"

    # ==========================================================================
    # TC-004〜TC-006: _build_body_template テスト
    # ==========================================================================

    def test_tc004_build_body_template_multi_dependency_aggregation(self) -> None:
        """TC-004: 複数タスクからデータを集約するbody_templateを生成。

        受入条件: AC-1, AC-2, AC-3, AC-4, AC-9

        Issue本文のシナリオ:
        - task_001 (order=0): output={keyword}
        - task_004 (order=3): output={processed}
        - task_005 (order=4): output={summary, recipient_email}
        - task_006 (order=5): dependencies=[task_001, task_004, task_005], input={keyword, summary, recipient_email}
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_006",
            name="Send Email",
            description="Send email",
            task_type="send",
            recommended_api="/api/email/send",
            dependencies=["task_001", "task_004", "task_005"],
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {"query": {"type": "string"}}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
            "task_004": InterfaceSchema(
                task_id="task_004",
                input_schema={"properties": {}},
                output_schema={"properties": {"processed": {"type": "boolean"}}},
            ),
            "task_005": InterfaceSchema(
                task_id="task_005",
                input_schema={"properties": {}},
                output_schema={
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
            ),
            "task_006": InterfaceSchema(
                task_id="task_006",
                input_schema={
                    "properties": {
                        "keyword": {"type": "string"},
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
                output_schema={
                    "properties": {
                        "email_subject": {"type": "string"},
                        "email_body": {"type": "string"},
                    }
                },
            ),
        }

        task_order_map = {
            "task_001": 0,
            "task_002": 1,
            "task_003": 2,
            "task_004": 3,
            "task_005": 4,
            "task_006": 5,
        }

        # Act
        result = manager._build_body_template(
            order=5,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        assert result["workflow"] == "__PENDING__"
        assert result["project"] == "{{job.body.project}}"
        assert isinstance(result["inputs"], dict), "inputs should be a dict"

        inputs = result["inputs"]
        # AC-4: task_006のbody_templateが正しいフィールドを参照
        assert inputs.get("keyword") == "{{tasks[0].output_data.keyword}}", (
            f"keyword: {inputs.get('keyword')}"
        )
        assert inputs.get("summary") == "{{tasks[4].output_data.summary}}", (
            f"summary: {inputs.get('summary')}"
        )
        assert (
            inputs.get("recipient_email") == "{{tasks[4].output_data.recipient_email}}"
        ), f"recipient_email: {inputs.get('recipient_email')}"

    def test_tc005_build_body_template_backward_compatibility(self) -> None:
        """TC-005: 後方互換性 - オプション引数省略時に従来動作を維持。

        受入条件: AC-5, AC-7
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        # Act: オプション引数なしで呼び出し（従来の呼び出し方法）
        result = manager._build_body_template(order=1)

        # Assert: 従来形式のテンプレート
        assert result["workflow"] == "__PENDING__"
        assert result["project"] == "{{job.body.project}}"
        assert result["inputs"] == "{{tasks[0].output_data}}", (
            f"Expected string format, got: {result['inputs']}"
        )

    def test_tc006_build_body_template_fallback_with_user_input(self) -> None:
        """TC-006: フィールド未発見時のuser_inputフォールバック。

        受入条件: AC-6
        設計方針: DP-3 (フォールバック+ログ出力)
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Process",
            description="Process data",
            task_type="transform",
            recommended_api="/api/process",
            dependencies=["task_001"],
        )

        # task_001は 'keyword' のみを出力、task_002は 'missing_field' も必要
        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "properties": {
                        "keyword": {"type": "string"},
                        "missing_field": {"type": "string"},
                    }
                },
                output_schema={"properties": {"result": {"type": "string"}}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Act
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        inputs = result["inputs"]
        assert isinstance(inputs, dict)
        # keywordは依存タスクから取得
        assert inputs.get("keyword") == "{{tasks[0].output_data.keyword}}"
        # missing_fieldはuser_inputからフォールバック
        assert inputs.get("missing_field") == "{{job.body.user_input.missing_field}}", (
            f"Expected fallback to user_input, got: {inputs.get('missing_field')}"
        )

    # ==========================================================================
    # TC-007: E2E結合テスト
    # ==========================================================================

    def test_tc007_e2e_multi_dependency_workflow_registration(self) -> None:
        """TC-007: E2E結合テスト - 複数依存ワークフロー登録。

        受入条件: AC-10

        このテストはtask_order_mapの構築から_build_body_templateへの引き渡しまでの
        フローをシミュレートし、3タスク依存シナリオでbody_templateが
        正しく生成されることを確認する。
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        # マルチ依存シナリオのタスク定義
        sorted_tasks: list[TaskDefinition] = [
            TaskDefinition(
                id="task_001",
                name="Keyword Search",
                description="Search for keywords",
                task_type="fetch",
                recommended_api="/api/search",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_005",
                name="Summarize",
                description="Summarize content",
                task_type="transform",
                recommended_api="/api/summarize",
                dependencies=["task_001"],
            ),
            TaskDefinition(
                id="task_006",
                name="Send Email",
                description="Send email with results",
                task_type="send",
                recommended_api="/api/email/send",
                dependencies=["task_001", "task_005"],
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {"query": {"type": "string"}}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
            "task_005": InterfaceSchema(
                task_id="task_005",
                input_schema={"properties": {"keyword": {"type": "string"}}},
                output_schema={
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
            ),
            "task_006": InterfaceSchema(
                task_id="task_006",
                input_schema={
                    "properties": {
                        "keyword": {"type": "string"},
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
                output_schema={
                    "properties": {
                        "email_subject": {"type": "string"},
                        "email_body": {"type": "string"},
                    }
                },
            ),
        }

        # Issue #403: Build task_order_map as in create_masters
        task_order_map: dict[str, int] = {
            task.id: order for order, task in enumerate(sorted_tasks)
        }

        # Act: task_006のbody_templateを生成（order=2）
        task_006 = sorted_tasks[2]
        result = manager._build_body_template(
            order=2,
            task=task_006,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        assert result["workflow"] == "__PENDING__"
        assert result["project"] == "{{job.body.project}}"

        # inputsが辞書形式であることを確認
        inputs = result["inputs"]
        assert isinstance(inputs, dict), f"Expected dict inputs, got: {type(inputs)}"

        # 各フィールドが正しいタスクを参照していることを確認
        # task_001はorder=0、task_005はorder=1
        assert inputs.get("keyword") == "{{tasks[0].output_data.keyword}}", (
            f"keyword: {inputs.get('keyword')}"
        )
        assert inputs.get("summary") == "{{tasks[1].output_data.summary}}", (
            f"summary: {inputs.get('summary')}"
        )
        assert (
            inputs.get("recipient_email") == "{{tasks[1].output_data.recipient_email}}"
        ), f"recipient_email: {inputs.get('recipient_email')}"

    # ==========================================================================
    # TC-008: 単一依存タスクテスト（後方互換性確認）
    # ==========================================================================

    def test_tc008_single_dependency_task_still_works(self) -> None:
        """TC-008: 単一依存タスクでの後方互換性。

        受入条件: AC-5

        複数依存機能追加後も、単一依存タスクが正しく動作することを確認。
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Process",
            description="Process data",
            task_type="transform",
            recommended_api="/api/process",
            dependencies=["task_001"],
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"result": {"type": "string"}}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"properties": {"result": {"type": "string"}}},
                output_schema={"properties": {"processed": {"type": "boolean"}}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Act
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        inputs = result["inputs"]
        assert isinstance(inputs, dict)
        # 単一フィールドの場合でも正しく参照される
        assert inputs.get("result") == "{{tasks[0].output_data.result}}"


# =============================================================================
# 追加テスト: エッジケース
# =============================================================================


@pytest.mark.acceptance
class TestIssue403EdgeCases:
    """Issue #403: エッジケーステスト。"""

    def test_first_task_uses_user_input(self) -> None:
        """最初のタスク（order=0）はuser_inputを使用する。"""
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_001",
            name="First Task",
            description="First task",
            task_type="fetch",
            recommended_api="/api/search",
            dependencies=[],
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {"query": {"type": "string"}}},
                output_schema={"properties": {"keyword": {"type": "string"}}},
            ),
        }

        task_order_map = {"task_001": 0}

        # Act
        result = manager._build_body_template(
            order=0,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert
        assert result["inputs"] == "{{job.body.user_input}}"

    def test_interfaces_not_provided_falls_back_to_legacy(self) -> None:
        """interfacesが提供されない場合、従来の動作にフォールバック。

        受入条件: AC-7
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Task",
            description="Task",
            task_type="transform",
            recommended_api="/api/process",
            dependencies=["task_001"],
        )

        # Act: interfacesをNoneで呼び出し
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=None,
            task_order_map=None,
        )

        # Assert: 従来形式
        assert result["inputs"] == "{{tasks[0].output_data}}"

    def test_task_not_in_interfaces_falls_back_to_legacy(self) -> None:
        """タスクがinterfacesに存在しない場合、従来の動作にフォールバック。

        受入条件: AC-7
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Task",
            description="Task",
            task_type="transform",
            recommended_api="/api/process",
            dependencies=["task_001"],
        )

        # task_002がinterfacesに存在しない
        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"result": {"type": "string"}}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Act
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert: 従来形式にフォールバック
        assert result["inputs"] == "{{tasks[0].output_data}}"

    def test_empty_input_schema_produces_empty_inputs(self) -> None:
        """入力スキーマが空の場合、空のinputsを返す。

        Note: 空のinput_schemaは「必要な入力がない」ことを意味する。
        この場合、multi-dependency templateのロジックが適用され、
        空のinputs辞書が返される（フォールバックではない）。
        """
        # Arrange
        manager = MasterManagerSubWorkflow(
            jobqueue_client=MagicMock(),
            engine="taskflow",
        )

        task = TaskDefinition(
            id="task_002",
            name="Task",
            description="Task",
            task_type="transform",
            recommended_api="/api/process",
            dependencies=["task_001"],
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"properties": {}},
                output_schema={"properties": {"result": {"type": "string"}}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"properties": {}},  # 空のinput_schema
                output_schema={"properties": {"processed": {"type": "boolean"}}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Act
        result = manager._build_body_template(
            order=1,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Assert: 空のinput_schemaは空のinputs辞書を返す
        # （必要な入力フィールドがないため）
        assert result["inputs"] == {}, f"Expected empty dict, got: {result['inputs']}"
        assert result["workflow"] == "__PENDING__"
        assert result["project"] == "{{job.body.project}}"
