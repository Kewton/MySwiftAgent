"""Tests for UnifiedTaskIdentifier name/description fields.

Issue: E2Eテストで「調査結果レポートメール」が「情報要求メール」として送信された
Root Cause: UnifiedTaskIdentifierにname/descriptionが欠落し、ワークフロー生成LLMに正しいタスク意図が伝わらない

This test file verifies:
- AC-1: UnifiedTaskIdentifierにname, descriptionフィールドが存在する
- AC-2: to_unified_identifier()がname, descriptionを保持する
- AC-3: _build_task_identifiers()がname, descriptionを保持する
- AC-4: _execute_workflow_gen()がTaskRequestに正しいname, descriptionを設定する
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import AnalyzedTask
from aiagent.langgraph.jobGeneratorV2.types import UnifiedTaskIdentifier


class TestUnifiedTaskIdentifierNameDescription:
    """AC-1: UnifiedTaskIdentifierにname, descriptionフィールドが存在する"""

    def test_unified_task_identifier_has_name_field(self):
        """UnifiedTaskIdentifierにnameフィールドが存在する"""
        identifier = UnifiedTaskIdentifier(
            task_id="task_001",
            name="メールコンテンツ作成",
        )
        assert identifier.name == "メールコンテンツ作成"

    def test_unified_task_identifier_has_description_field(self):
        """UnifiedTaskIdentifierにdescriptionフィールドが存在する"""
        identifier = UnifiedTaskIdentifier(
            task_id="task_001",
            description="サマリとキーワード情報を使用して、メール本文を作成する",
        )
        assert (
            identifier.description
            == "サマリとキーワード情報を使用して、メール本文を作成する"
        )

    def test_unified_task_identifier_name_description_optional(self):
        """name, descriptionはオプショナル（後方互換性）"""
        identifier = UnifiedTaskIdentifier(task_id="task_001")
        assert identifier.name is None
        assert identifier.description is None

    def test_with_master_id_preserves_name_description(self):
        """with_master_id()がname, descriptionを保持する"""
        identifier = UnifiedTaskIdentifier(
            task_id="task_001",
            name="メールコンテンツ作成",
            description="サマリとキーワード情報を使用して、メール本文を作成する",
        )

        updated = identifier.with_master_id("tm_abc123")

        assert updated.task_id == "task_001"
        assert updated.task_master_id == "tm_abc123"
        assert updated.name == "メールコンテンツ作成"
        assert (
            updated.description
            == "サマリとキーワード情報を使用して、メール本文を作成する"
        )

    def test_hash_still_based_on_task_id_only(self):
        """hashはtask_idのみに基づく（既存動作を維持）"""
        id1 = UnifiedTaskIdentifier(task_id="task_001", name="Name1")
        id2 = UnifiedTaskIdentifier(task_id="task_001", name="Name2")

        assert hash(id1) == hash(id2)

    def test_equality_still_based_on_task_id_only(self):
        """等価性はtask_idのみに基づく（既存動作を維持）"""
        id1 = UnifiedTaskIdentifier(task_id="task_001", name="Name1")
        id2 = UnifiedTaskIdentifier(task_id="task_001", name="Name2")

        assert id1 == id2


class TestAnalyzedTaskToUnifiedIdentifier:
    """AC-2: to_unified_identifier()がname, descriptionを保持する"""

    def test_to_unified_identifier_preserves_name(self):
        """to_unified_identifier()がnameを保持する"""
        task = AnalyzedTask(
            task_id="task_006",
            name="メールコンテンツ作成",
            description="サマリとキーワード情報を使用して、メール本文を作成する",
            task_type="transform",
            recommended_api="email_template",
        )

        identifier = task.to_unified_identifier()

        assert identifier.task_id == "task_006"
        assert identifier.name == "メールコンテンツ作成"

    def test_to_unified_identifier_preserves_description(self):
        """to_unified_identifier()がdescriptionを保持する"""
        task = AnalyzedTask(
            task_id="task_006",
            name="メールコンテンツ作成",
            description="サマリとキーワード情報を使用して、メール本文を作成する",
            task_type="transform",
            recommended_api="email_template",
        )

        identifier = task.to_unified_identifier()

        assert (
            identifier.description
            == "サマリとキーワード情報を使用して、メール本文を作成する"
        )


class TestBuildTaskIdentifiers:
    """AC-3: _build_task_identifiers()がname, descriptionを保持する"""

    def test_build_task_identifiers_preserves_name_description(self):
        """_build_task_identifiers()がname, descriptionを保持する"""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        tasks = [
            AnalyzedTask(
                task_id="task_006",
                name="メールコンテンツ作成",
                description="サマリとキーワード情報を使用して、メール本文を作成する",
                task_type="transform",
                recommended_api="email_template",
            ),
        ]
        task_id_to_master_id = {"task_006": "tm_abc123"}

        identifiers = orchestrator._build_task_identifiers(tasks, task_id_to_master_id)

        assert len(identifiers) == 1
        assert identifiers[0].task_id == "task_006"
        assert identifiers[0].task_master_id == "tm_abc123"
        assert identifiers[0].name == "メールコンテンツ作成"
        assert (
            identifiers[0].description
            == "サマリとキーワード情報を使用して、メール本文を作成する"
        )


class TestExecuteWorkflowGen:
    """AC-4: _execute_workflow_gen()がTaskRequestに正しいname, descriptionを設定する"""

    @pytest.mark.asyncio
    async def test_execute_workflow_gen_uses_correct_name(self):
        """_execute_workflow_gen()がTaskRequestに正しいnameを設定する"""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        # Mock the workflow generator client
        mock_client = AsyncMock()
        mock_client.fetch_capabilities = AsyncMock(return_value=[])
        mock_client.generate_workflows = AsyncMock(
            return_value=MagicMock(
                status=MagicMock(value="success"),
                workflows={},
                recovery_suggestion=None,
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        orchestrator = JobGenerationOrchestrator(
            workflow_generator_client=mock_client,
        )

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_006",
                task_master_id="tm_abc123",
                name="メールコンテンツ作成",
                description="サマリとキーワード情報を使用して、メール本文を作成する",
            ),
        ]
        interfaces = {
            "task_006": InterfaceDefinition(
                input_schema={"summary": {"type": "string"}},
                output_schema={"body": {"type": "string"}},
            ),
        }

        await orchestrator._execute_workflow_gen(
            task_identifiers,
            interfaces,
            project_id="test_project",
        )

        # Verify the TaskRequest was created with correct name
        call_args = mock_client.generate_workflows.call_args
        tasks = (
            call_args.kwargs.get("tasks")
            or call_args[1].get("tasks")
            or call_args[0][0]
        )

        assert len(tasks) == 1
        assert tasks[0].name == "メールコンテンツ作成"
        assert (
            tasks[0].description
            == "サマリとキーワード情報を使用して、メール本文を作成する"
        )

    @pytest.mark.asyncio
    async def test_execute_workflow_gen_not_uses_fixed_string(self):
        """_execute_workflow_gen()が固定文字列を使用しない"""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        mock_client = AsyncMock()
        mock_client.fetch_capabilities = AsyncMock(return_value=[])
        mock_client.generate_workflows = AsyncMock(
            return_value=MagicMock(
                status=MagicMock(value="success"),
                workflows={},
                recovery_suggestion=None,
            )
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        orchestrator = JobGenerationOrchestrator(
            workflow_generator_client=mock_client,
        )

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_006",
                task_master_id="tm_abc123",
                name="メールコンテンツ作成",
                description="サマリとキーワード情報を使用して、メール本文を作成する",
            ),
        ]
        interfaces = {
            "task_006": InterfaceDefinition(
                input_schema={},
                output_schema={},
            ),
        }

        await orchestrator._execute_workflow_gen(
            task_identifiers,
            interfaces,
            project_id="test_project",
        )

        call_args = mock_client.generate_workflows.call_args
        tasks = (
            call_args.kwargs.get("tasks")
            or call_args[1].get("tasks")
            or call_args[0][0]
        )

        # 固定文字列が使用されていないことを確認
        assert tasks[0].name != "Task task_006"
        assert tasks[0].name != f"Task {tasks[0].task_id}"
        assert tasks[0].description != "Workflow for task task_006"
        assert tasks[0].description != f"Workflow for task {tasks[0].task_id}"
