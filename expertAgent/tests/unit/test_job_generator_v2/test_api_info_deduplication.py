"""Tests for API information deduplication.

Issue #343 Task 2.5: Test API info deduplication and deprecation warnings.

When both recommended_apis and api_mappings are provided, a warning
should be raised to alert about potential duplication.
"""

import warnings

import pytest


class TestAPIInfoDuplicationWarning:
    """Test warnings for duplicate API information."""

    def test_warns_on_duplicate_api_info(self) -> None:
        """Test that warning is raised when both sources provided."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        with pytest.warns(
            DeprecationWarning, match="API information may be duplicated"
        ):
            assemble_prompt(
                task_name="test",
                task_description="Test task",
                input_schema={},
                output_schema={},
                recommended_apis=["json_stringify"],
                api_mappings=[
                    {
                        "api_name": "json_stringify",
                        "agent_type": "fetchAgent",
                        "endpoint_url": "http://example.com/api",
                        "http_method": "POST",
                    }
                ],
            )

    def test_no_warning_with_only_recommended_apis(self) -> None:
        """Test that no warning when only recommended_apis provided."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        # Should not raise any warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assemble_prompt(
                task_name="test",
                task_description="Test task",
                input_schema={},
                output_schema={},
                recommended_apis=["json_stringify"],
                api_mappings=None,
            )

            # Filter for DeprecationWarning about API duplication
            api_warnings = [
                x
                for x in w
                if issubclass(x.category, DeprecationWarning)
                and "API information" in str(x.message)
            ]
            assert len(api_warnings) == 0

    def test_no_warning_with_only_api_mappings(self) -> None:
        """Test that no warning when only api_mappings provided."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assemble_prompt(
                task_name="test",
                task_description="Test task",
                input_schema={},
                output_schema={},
                recommended_apis=None,
                api_mappings=[
                    {
                        "api_name": "test_api",
                        "agent_type": "fetchAgent",
                        "endpoint_url": "http://example.com/api",
                        "http_method": "POST",
                    }
                ],
            )

            api_warnings = [
                x
                for x in w
                if issubclass(x.category, DeprecationWarning)
                and "API information" in str(x.message)
            ]
            assert len(api_warnings) == 0

    def test_no_warning_with_neither(self) -> None:
        """Test that no warning when neither provided."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            assemble_prompt(
                task_name="test",
                task_description="Test task",
                input_schema={},
                output_schema={},
                recommended_apis=None,
                api_mappings=None,
            )

            api_warnings = [
                x
                for x in w
                if issubclass(x.category, DeprecationWarning)
                and "API information" in str(x.message)
            ]
            assert len(api_warnings) == 0


class TestWarningMessage:
    """Test warning message content."""

    def test_warning_suggests_api_schema_injector(self) -> None:
        """Test that warning mentions APISchemaInjector as solution."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        with pytest.warns(DeprecationWarning) as record:
            assemble_prompt(
                task_name="test",
                task_description="Test task",
                input_schema={},
                output_schema={},
                recommended_apis=["test_api"],
                api_mappings=[
                    {
                        "api_name": "test_api",
                        "agent_type": "fetchAgent",
                        "endpoint_url": "http://example.com",
                        "http_method": "POST",
                    }
                ],
            )

        # Check that warning message suggests using APISchemaInjector
        warning_messages = [str(r.message) for r in record]
        assert any("APISchemaInjector" in msg for msg in warning_messages), (
            "Warning should suggest using APISchemaInjector"
        )


class TestAPISchemaInjectorPriority:
    """Test that APISchemaInjector is used for API info."""

    def test_api_schema_injector_is_used(self) -> None:
        """Test that APISchemaInjector is called for API info."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        mock_injector = MagicMock()
        mock_injector.inject.return_value = "## API Schemas\nInjected content"

        _prompt = assemble_prompt(
            task_name="test",
            task_description="Test task",
            input_schema={},
            output_schema={},
            recommended_apis=["json_stringify"],
            api_injector=mock_injector,
        )

        # APISchemaInjector.inject should be called
        mock_injector.inject.assert_called_once()

    def test_prompt_contains_injected_api_info(self) -> None:
        """Test that prompt contains API info from injector."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
            assemble_prompt,
        )

        prompt = assemble_prompt(
            task_name="test",
            task_description="Test task",
            input_schema={},
            output_schema={},
            recommended_apis=["json_stringify"],
        )

        # The prompt should contain API schema information
        # (from APISchemaInjector)
        rendered = prompt.render()
        assert (
            "json_stringify" in rendered.lower()
            or "Request Schema" in rendered
            or "API" in rendered
        )
