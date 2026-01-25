"""Integration Tests for Issue #404: TaskFlow Generator derived_fields Support.

Issue #404: taskflowGeneratorAgentの生成ワークフローがinterfaceDefinitionsと整合しない問題

This test module contains:
- IT-001〜IT-003: 複数依存を持つワークフロー生成のE2Eテスト [AC-9]
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


class TestWorkflowGenerationWithDerivedFields:
    """Integration tests for workflow generation with derived_fields.

    AC-9: 結合テスト - 複数依存を持つワークフロー生成のE2Eテスト
    """

    @pytest.fixture
    def mock_llm_result(self) -> dict[str, Any]:
        """Create a mock LLM result for TaskFlow generation."""
        return {
            "workflow_name": "test_workflow",
            "steps": [
                {
                    "id": "step_1",
                    "type": "api_rest",
                    "config": {
                        "url": "https://api.example.com/search",
                        "method": "POST",
                    },
                }
            ],
            "input": {"query": "string", "recipient_email": "string"},
            "output": {"results": "array", "recipient_email": "string"},
        }

    @pytest.mark.asyncio
    async def test_it_001_adapter_to_generator_derived_fields_flow(self) -> None:
        """IT-001: Adapter -> Generator flow preserves derived_fields."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorAdapter()

        # Create interfaces with derived_fields
        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                    }
                },
                description="Search task with email",
                derived_fields={
                    "email_subject": {
                        "template": "Search results for: {query}",
                        "type": "string",
                        "description": "Generated email subject",
                    }
                },
            ),
        }

        # Convert using adapter
        converted = adapter._convert_interfaces(interfaces)

        # Verify derived_fields preserved
        assert "task_001" in converted
        assert "derived_fields" in converted["task_001"]
        assert "email_subject" in converted["task_001"]["derived_fields"]

        # Verify can be used by TaskFlowLLMGenerator
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()
        prompt = generator._build_user_prompt(
            task_definitions=[
                {"name": "Search", "description": "Search task", "task_type": "fetch"}
            ],
            interfaces=converted,
            examples=[],
        )

        # derived_fields info should be in prompt
        assert "email_subject" in prompt

    @pytest.mark.asyncio
    async def test_it_002_multi_task_passthrough_chain(self) -> None:
        """IT-002: Multi-task chain with passthrough works correctly."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        # Setup: 3-task chain with passthrough requirement
        task_definitions = [
            {"name": "Search", "description": "Search Gmail", "task_type": "fetch"},
            {"name": "Summarize", "description": "Summarize results", "task_type": "transform"},
            {"name": "Send Email", "description": "Send email", "task_type": "send"},
        ]

        interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                    }
                },
                "derived_fields": {
                    "email_subject": {
                        "template": "Results: {query}",
                        "type": "string",
                    }
                },
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "recipient_email": {"type": "string"},
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                    }
                },
                "derived_fields": {},
            },
            "task_003": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "sent": {"type": "boolean"},
                    }
                },
                "derived_fields": {},
            },
        }

        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
            "task_003": ["task_002"],
        }

        # Enhance each task's output schema
        enhanced_task_001 = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=interfaces["task_001"]["output_schema"],
            all_interfaces=interfaces,
            task_dependencies=task_dependencies,
        )

        enhanced_task_002 = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_002",
            current_output_schema=interfaces["task_002"]["output_schema"],
            all_interfaces=interfaces,
            task_dependencies=task_dependencies,
        )

        # Verify passthrough chain
        # task_001 output should include recipient_email for task_002
        assert "recipient_email" in enhanced_task_001.get("properties", {})

        # task_002 output should include recipient_email for task_003
        assert "recipient_email" in enhanced_task_002.get("properties", {})

    @pytest.mark.asyncio
    async def test_it_003_backward_compatibility_no_derived_fields(self) -> None:
        """IT-003: Backward compatibility - workflows without derived_fields work."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorAdapter()

        # Old-style interfaces without derived_fields
        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Simple task",
                # derived_fields defaults to empty dict
            ),
        }

        # Should not raise exception
        converted = adapter._convert_interfaces(interfaces)

        # Should have derived_fields as empty dict
        assert "derived_fields" in converted["task_001"]
        assert converted["task_001"]["derived_fields"] == {}

        # Prompt generation should also work
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()
        prompt = generator._build_user_prompt(
            task_definitions=[
                {"name": "Simple", "description": "Simple task", "task_type": "fetch"}
            ],
            interfaces=converted,
            examples=[],
        )

        # Should generate valid prompt without errors
        assert "task_001" in prompt or "Simple" in prompt
