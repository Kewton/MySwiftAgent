"""Unit Tests for Issue #404: TaskFlow Generator derived_fields Support.

Issue #404: taskflowGeneratorAgentの生成ワークフローがinterfaceDefinitionsと整合しない問題

This test module contains:
- UT-001〜UT-003: adapter._convert_interfaces() derived_fields tests [AC-13]
- UT-004〜UT-006: _build_user_prompt() derived_fields tests [AC-14]
- UT-007〜UT-015: _enhance_output_schema_with_passthrough() tests [AC-7, AC-8]
"""

from __future__ import annotations

from typing import Any

import pytest


class TestAdapterConvertInterfaces:
    """Tests for adapter._convert_interfaces() derived_fields support.

    AC-10: adapter._convert_interfaces()でderived_fieldsが保持される
    AC-13: 単体テスト - _convert_interfaces()でderived_fields保持の検証
    """

    def test_ut_001_convert_interfaces_preserves_derived_fields(self) -> None:
        """UT-001: derived_fieldsが空でない場合、変換後も保持される."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorAdapter()

        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                description="Search task",
                derived_fields={
                    "email_subject": {
                        "template": "Search results: {query}",
                        "type": "string",
                    }
                },
            )
        }

        result = adapter._convert_interfaces(interfaces)

        assert "task_001" in result
        assert "derived_fields" in result["task_001"]
        assert "email_subject" in result["task_001"]["derived_fields"]
        assert result["task_001"]["derived_fields"]["email_subject"]["template"] == "Search results: {query}"

    def test_ut_002_convert_interfaces_empty_derived_fields(self) -> None:
        """UT-002: derived_fieldsが空の場合、空のdictが保持される."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorAdapter()

        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Simple task",
                derived_fields={},
            )
        }

        result = adapter._convert_interfaces(interfaces)

        assert "task_001" in result
        assert "derived_fields" in result["task_001"]
        assert result["task_001"]["derived_fields"] == {}

    def test_ut_003_convert_interfaces_multiple_tasks(self) -> None:
        """UT-003: 複数タスクのderived_fieldsが正しく変換される."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorAdapter()

        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Task 1",
                derived_fields={
                    "field_a": {"template": "A: {value}", "type": "string"}
                },
            ),
            "task_002": InterfaceDefinition(
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Task 2",
                derived_fields={
                    "field_b": {"template": "B: {value}", "type": "string"},
                    "field_c": {"template": "C: {value}", "type": "number"},
                },
            ),
        }

        result = adapter._convert_interfaces(interfaces)

        assert len(result) == 2
        assert result["task_001"]["derived_fields"]["field_a"]["type"] == "string"
        assert result["task_002"]["derived_fields"]["field_b"]["template"] == "B: {value}"
        assert result["task_002"]["derived_fields"]["field_c"]["type"] == "number"


class TestBuildUserPromptDerivedFields:
    """Tests for _build_user_prompt() derived_fields output.

    AC-11: taskflow_generator._build_user_prompt()でderived_fieldsがプロンプトに含まれる
    AC-14: 単体テスト - _build_user_prompt()でderived_fields出力の検証
    """

    def test_ut_004_build_user_prompt_includes_derived_fields(self) -> None:
        """UT-004: derived_fieldsがある場合、プロンプトに含まれる."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        task_definitions = [
            {"name": "Search Task", "description": "Search for emails", "task_type": "fetch"}
        ]
        interfaces = {
            "task_001": {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "derived_fields": {
                    "email_subject": {
                        "template": "Results for: {query}",
                        "type": "string",
                        "description": "Email subject line",
                    }
                },
            }
        }

        prompt = generator._build_user_prompt(
            task_definitions=task_definitions,
            interfaces=interfaces,
            examples=[],
        )

        assert "derived_fields" in prompt.lower() or "Derived Fields" in prompt
        assert "email_subject" in prompt
        assert "Results for: {query}" in prompt

    def test_ut_005_build_user_prompt_empty_derived_fields_skip(self) -> None:
        """UT-005: derived_fieldsが空の場合、セクションがスキップされる."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        task_definitions = [
            {"name": "Simple Task", "description": "A simple task", "task_type": "transform"}
        ]
        interfaces = {
            "task_001": {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "derived_fields": {},
            }
        }

        prompt = generator._build_user_prompt(
            task_definitions=task_definitions,
            interfaces=interfaces,
            examples=[],
        )

        # Empty derived_fields should not add a derived fields section
        # Count occurrences - should be minimal (possibly in general rules)
        derived_count = prompt.lower().count("derived_fields")
        assert derived_count == 0 or "empty" in prompt.lower()

    def test_ut_006_build_user_prompt_no_derived_fields_key(self) -> None:
        """UT-006: derived_fieldsキーがない場合も正常に動作する(後方互換性)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        task_definitions = [
            {"name": "Legacy Task", "description": "A legacy task", "task_type": "fetch"}
        ]
        interfaces = {
            "task_001": {
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                # No derived_fields key - backward compatibility test
            }
        }

        # Should not raise exception
        prompt = generator._build_user_prompt(
            task_definitions=task_definitions,
            interfaces=interfaces,
            examples=[],
        )

        assert "task_001" in prompt or "Legacy Task" in prompt
        # No crash, backward compatible


class TestEnhanceOutputSchemaWithPassthrough:
    """Tests for _enhance_output_schema_with_passthrough() method.

    AC-1: 生成されるワークフローJSONのinput_schemaがinterfaceDefinitionsと一致する
    AC-2: 後続タスクで必要なフィールドが自動的にパススルーとしてoutput_schemaに追加される
    AC-3: ユーザー入力から提供されるrecipient_emailが、必要なタスクに正しく伝播される
    AC-5: 既存のワークフロー（パススルー不要なもの）の動作に影響しない
    AC-6: interfacesが存在しないタスクの場合、従来の動作にフォールバックする
    AC-7: 単体テスト - _enhance_output_schema_with_passthroughの正常系・異常系テスト
    AC-8: 単体テスト - パススルーフィールド追加の検証テスト
    """

    def test_ut_007_enhance_adds_missing_passthrough_field(self) -> None:
        """UT-007: 後続タスクに必要なフィールドがoutput_schemaに追加される."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_task_id = "task_001"
        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "results": {"type": "array"}
            }
        }
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
                "output_schema": current_output_schema,
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "recipient_email": {"type": "string"},  # This needs passthrough
                    }
                },
                "output_schema": {"type": "object"},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id=current_task_id,
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # recipient_email should be added as passthrough
        assert "properties" in enhanced
        assert "recipient_email" in enhanced["properties"]

    def test_ut_008_enhance_no_change_when_all_fields_present(self) -> None:
        """UT-008: 全フィールドが既存の場合、変更なし."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "results": {"type": "array"},
                "recipient_email": {"type": "string"},
            }
        }
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "recipient_email": {"type": "string"},
                    }
                },
                "output_schema": {},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # No new fields should be added
        original_keys = set(current_output_schema.get("properties", {}).keys())
        enhanced_keys = set(enhanced.get("properties", {}).keys())
        assert original_keys == enhanced_keys

    def test_ut_009_enhance_no_downstream_tasks(self) -> None:
        """UT-009: 後続タスクがない場合、変更なし (AC-5)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"results": {"type": "array"}}
        }
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # Should return schema unchanged
        assert enhanced == current_output_schema

    def test_ut_010_enhance_multiple_downstream_tasks(self) -> None:
        """UT-010: 複数の後続タスクの入力要件を集約する."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"data": {"type": "object"}}
        }
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                        "email": {"type": "string"},
                    }
                },
                "output_schema": {},
            },
            "task_003": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                        "subject": {"type": "string"},
                    }
                },
                "output_schema": {},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
            "task_003": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        props = enhanced.get("properties", {})
        assert "email" in props
        assert "subject" in props

    def test_ut_011_enhance_interface_not_found_fallback(self) -> None:
        """UT-011: interfaceが見つからない場合、元のスキーマを返す (AC-6)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"results": {"type": "array"}}
        }
        # task_002 has dependency on task_001 but no interface for task_002
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],  # task_002 depends on task_001 but has no interface
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # Should return original schema (fallback behavior)
        assert enhanced == current_output_schema

    def test_ut_012_enhance_empty_output_schema(self) -> None:
        """UT-012: 空のoutput_schemaに対してもpassthrough追加が動作する."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {}
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "recipient_email": {"type": "string"},
                    }
                },
                "output_schema": {},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # Should add passthrough field
        assert "properties" in enhanced
        assert "recipient_email" in enhanced["properties"]

    def test_ut_013_enhance_preserves_original_properties(self) -> None:
        """UT-013: パススルー追加時に元のプロパティが保持される."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "original_field": {"type": "string", "description": "Original"},
            },
            "required": ["original_field"],
        }
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "new_field": {"type": "string"},
                    }
                },
                "output_schema": {},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # Original properties preserved
        assert "original_field" in enhanced["properties"]
        assert enhanced["properties"]["original_field"]["description"] == "Original"
        # New field added
        assert "new_field" in enhanced["properties"]

    def test_ut_014_enhance_handles_exception_gracefully(self) -> None:
        """UT-014: 例外発生時に元のスキーマを返す (Fail-Safe設計)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        current_output_schema: dict[str, Any] = {
            "type": "object",
            "properties": {"safe_field": {"type": "string"}}
        }
        # Invalid data that might cause exception
        all_interfaces: dict[str, Any] = {
            "task_001": {
                "input_schema": {},
                "output_schema": current_output_schema,
            },
            "task_002": {
                # Malformed input_schema - properties is not a dict
                "input_schema": {
                    "type": "object",
                    "properties": None,  # This should trigger error handling
                },
                "output_schema": {},
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
        }

        enhanced = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=current_output_schema,
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )

        # Should return original schema on error (Fail-Safe)
        assert enhanced == current_output_schema

    def test_ut_015_enhance_recipient_email_passthrough(self) -> None:
        """UT-015: recipient_emailが正しくパススルーされる (AC-3 E2E)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.taskflow_generator import (
            TaskFlowLLMGenerator,
        )

        generator = TaskFlowLLMGenerator()

        # Scenario: task_001 (search) -> task_002 (summarize) -> task_003 (send_email)
        # recipient_email is provided as user_input and must reach task_003
        all_interfaces: dict[str, Any] = {
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
            },
            "task_002": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "recipient_email": {"type": "string"},  # Passthrough needed
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                    }
                },
            },
            "task_003": {
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},  # Final destination
                    }
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "sent": {"type": "boolean"},
                    }
                },
            },
        }
        task_dependencies: dict[str, list[str]] = {
            "task_001": [],
            "task_002": ["task_001"],
            "task_003": ["task_002"],
        }

        # Enhance task_001's output (should add recipient_email for task_002)
        enhanced_task_001 = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_001",
            current_output_schema=all_interfaces["task_001"]["output_schema"],
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )
        assert "recipient_email" in enhanced_task_001["properties"]

        # Enhance task_002's output (should add recipient_email for task_003)
        enhanced_task_002 = generator._enhance_output_schema_with_passthrough(
            current_task_id="task_002",
            current_output_schema=all_interfaces["task_002"]["output_schema"],
            all_interfaces=all_interfaces,
            task_dependencies=task_dependencies,
        )
        assert "recipient_email" in enhanced_task_002["properties"]
