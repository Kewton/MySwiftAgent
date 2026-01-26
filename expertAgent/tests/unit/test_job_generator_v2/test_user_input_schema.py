"""Unit tests for user_input_schema explicit definition.

This module tests the bug fix for E2E email not sent issue:
- LLM changed field names (email -> recipient_email)
- Validation only warned instead of erroring
- user_input_schema was inferred from independent tasks instead of explicit

Bug ID: 20260126_email_not_sent

Test Plan:
1. Test user_input_schema field exists in JobAnalysisResponse
2. Test JOB_ANALYSIS_SYSTEM_PROMPT contains user input consistency rules
3. Test _build_multi_dependency_template raises error on field mismatch
4. Test _get_user_input_schema uses LLM-provided schema when available
"""

from typing import Any

import pytest

from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
    JOB_ANALYSIS_SYSTEM_PROMPT,
    JobAnalysisResponse,
)
from aiagent.langgraph.jobGeneratorV2.types_old import InterfaceSchema, TaskDefinition
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)


class TestUserInputSchemaField:
    """Tests for user_input_schema field in JobAnalysisResponse."""

    def test_job_analysis_response_has_user_input_schema_field(self) -> None:
        """JobAnalysisResponse should have user_input_schema field.

        AC: user_input_schema field exists in JobAnalysisResponse
        """
        response = JobAnalysisResponse()
        assert hasattr(response, "user_input_schema")
        assert isinstance(response.user_input_schema, dict)

    def test_user_input_schema_default_is_empty_dict(self) -> None:
        """user_input_schema should default to empty dict.

        AC: Default value is empty dict (backward compatible)
        """
        response = JobAnalysisResponse()
        assert response.user_input_schema == {}

    def test_user_input_schema_can_be_set(self) -> None:
        """user_input_schema can be set with schema values.

        AC: user_input_schema can define field types
        """
        schema = {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["keyword", "email"],
        }
        response = JobAnalysisResponse(user_input_schema=schema)
        assert response.user_input_schema == schema
        assert "keyword" in response.user_input_schema["properties"]
        assert "email" in response.user_input_schema["properties"]


class TestPromptImprovements:
    """Tests for LLM prompt improvements."""

    def test_prompt_contains_user_input_consistency_rules(self) -> None:
        """JOB_ANALYSIS_SYSTEM_PROMPT should contain user input consistency rules.

        AC: Prompt instructs LLM to maintain consistent field names
        """
        # Check for user input field consistency rules
        assert "user_input_schema" in JOB_ANALYSIS_SYSTEM_PROMPT.lower() or \
               "user input" in JOB_ANALYSIS_SYSTEM_PROMPT.lower()

    def test_prompt_contains_field_name_preservation_rule(self) -> None:
        """JOB_ANALYSIS_SYSTEM_PROMPT should instruct not to rename fields.

        AC: Prompt explicitly tells LLM not to change field names like email
        """
        prompt_lower = JOB_ANALYSIS_SYSTEM_PROMPT.lower()
        # Should contain rules about not changing field names
        assert "email" in prompt_lower or "field name" in prompt_lower or \
               "consistent" in prompt_lower

    def test_prompt_contains_user_input_schema_section(self) -> None:
        """JOB_ANALYSIS_SYSTEM_PROMPT should have user_input_schema section.

        AC: Prompt has explicit section for defining user input schema
        """
        # Check for section about user input schema
        assert "user_input_schema" in JOB_ANALYSIS_SYSTEM_PROMPT or \
               "User Input Schema" in JOB_ANALYSIS_SYSTEM_PROMPT


class TestValidationStrictness:
    """Tests for validation strictness (WARNING -> ERROR)."""

    def test_field_mismatch_raises_error(self) -> None:
        """_build_multi_dependency_template should raise error on field mismatch.

        AC: When a required field is not found in user_input_schema,
            raise UserInputFieldMismatchError instead of just logging warning
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.errors import (
            UserInputFieldMismatchError,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Task that requires 'recipient_email' but user_input_schema has 'email'
        task = TaskDefinition(
            id="task_002",
            name="send_email",
            description="Send email",
            task_type="send",
            recommended_api="/api/send",
            dependencies=["task_001"],
            priority=5,
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "recipient_email": {"type": "string"},  # Wrong name!
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # user_input_schema has 'email', not 'recipient_email'
        user_input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "email": {"type": "string"},  # Correct name
            },
        }

        with pytest.raises(UserInputFieldMismatchError) as exc_info:
            manager._build_multi_dependency_template(
                task=task,
                interfaces=interfaces,
                task_order_map=task_order_map,
                user_input_schema=user_input_schema,
            )

        # Error message should indicate the mismatch
        assert "recipient_email" in str(exc_info.value)
        assert "email" in str(exc_info.value) or "Available fields" in str(exc_info.value)


class TestUserInputSchemaPriority:
    """Tests for user_input_schema priority in _get_user_input_schema."""

    def test_get_user_input_schema_prioritizes_llm_schema(self) -> None:
        """_get_user_input_schema should prioritize LLM-provided schema.

        AC: When JobAnalysisResponse.user_input_schema is set,
            use it instead of inferring from independent tasks
        """
        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Independent task with inferred schema
        tasks = [
            TaskDefinition(
                id="task_001",
                name="search",
                description="Search",
                task_type="fetch",
                recommended_api="/api/search",
                dependencies=[],
                priority=1,
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},  # Inferred: 'query'
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # LLM-provided schema uses 'keyword' instead of 'query'
        llm_user_input_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "email": {"type": "string"},
            },
        }

        # Current implementation only uses independent tasks
        # After fix, should use llm_user_input_schema when provided
        result = manager._get_user_input_schema(
            sorted_tasks=tasks,
            interfaces=interfaces,
            llm_user_input_schema=llm_user_input_schema,  # New parameter
        )

        # Should return LLM schema, not inferred schema
        assert result is not None
        assert "keyword" in result.get("properties", {})
        assert "email" in result.get("properties", {})

    def test_get_user_input_schema_falls_back_to_inference(self) -> None:
        """_get_user_input_schema should fall back to inference if no LLM schema.

        AC: Backward compatibility - if LLM schema is None, infer from tasks
        """
        manager = MasterManagerSubWorkflow(engine="taskflow")

        tasks = [
            TaskDefinition(
                id="task_001",
                name="search",
                description="Search",
                task_type="fetch",
                recommended_api="/api/search",
                dependencies=[],
                priority=1,
            ),
        ]

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                    },
                    "required": ["keyword"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # No LLM schema provided (None)
        result = manager._get_user_input_schema(
            sorted_tasks=tasks,
            interfaces=interfaces,
            llm_user_input_schema=None,  # New parameter with None
        )

        # Should fall back to inference from independent tasks
        assert result is not None
        assert "keyword" in result.get("properties", {})


class TestUserInputFieldMismatchErrorClass:
    """Tests for UserInputFieldMismatchError exception class."""

    def test_error_class_exists(self) -> None:
        """UserInputFieldMismatchError should exist in errors module.

        AC: New exception class is defined
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.errors import (
            UserInputFieldMismatchError,
        )

        assert UserInputFieldMismatchError is not None

    def test_error_class_is_exception(self) -> None:
        """UserInputFieldMismatchError should be an Exception.

        AC: Can be raised and caught as exception
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.errors import (
            UserInputFieldMismatchError,
        )

        assert issubclass(UserInputFieldMismatchError, Exception)

    def test_error_has_informative_message(self) -> None:
        """UserInputFieldMismatchError should provide informative message.

        AC: Error message includes field name and available fields
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.errors import (
            UserInputFieldMismatchError,
        )

        error = UserInputFieldMismatchError(
            field_name="recipient_email",
            available_fields=["keyword", "email"],
        )

        error_str = str(error)
        assert "recipient_email" in error_str
        assert "email" in error_str or "Available" in error_str
