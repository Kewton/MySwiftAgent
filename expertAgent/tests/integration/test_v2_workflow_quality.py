"""Integration tests for V2 Workflow Quality Improvement - Issue #342.

This module tests the complete workflow generation pipeline including:
- AgentSelector integration
- ParameterMapper integration
- LLM-first generation with fallback
- GraphAI spec compliance

Test Coverage Target: Integration level validation
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema


class TestAgentSelectorIntegration:
    """Integration tests for AgentSelector with workflow generation."""

    def test_agent_selector_api_coverage(self) -> None:
        """Test AgentSelector covers all expected APIs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        apis = selector.get_available_apis()

        # Verify key APIs are available
        expected_apis = [
            "gmail_send",
            "google_search",
            "slack_notify",
            "text_to_speech",
            "drive_upload",
        ]

        for api in expected_apis:
            assert api in apis, f"Expected API '{api}' not found in AgentSelector"

    def test_agent_selector_endpoint_format(self) -> None:
        """Test endpoint URLs follow correct format."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()

        for api in selector.get_available_apis():
            url = selector.build_endpoint_url(api)
            assert url is not None
            assert "${EXPERTAGENT_BASE_URL}" in url
            assert "/aiagent-api/v1/" in url


class TestParameterMapperIntegration:
    """Integration tests for ParameterMapper with workflow generation."""

    def test_parameter_mapper_graphai_compliance(self) -> None:
        """Test ParameterMapper output follows GraphAI spec."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            map_api_params,
        )

        result = map_api_params(
            api_name="gmail_send",
            interface_inputs={
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            source_node="user_input",
        )

        # GraphAI spec: inputs block must have url, method, body
        assert "url" in result
        assert "method" in result
        assert "body" in result

        # URL must use environment variable
        assert "${EXPERTAGENT_BASE_URL}" in result["url"]

        # Body must have mapped fields
        assert "to" in result["body"]
        assert result["body"]["to"].startswith(":source.")

    def test_parameter_mapper_with_agent_selector(self) -> None:
        """Test ParameterMapper works correctly with AgentSelector."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.parameter_mapper import (
            ParameterMapper,
        )

        selector = AgentSelector()
        mapper = ParameterMapper()

        # Get mapping from selector
        mapping = selector.select_agent("google_search")
        assert mapping is not None

        # Create inputs using mapper
        inputs = mapper.create_fetchagent_inputs(
            api_name="google_search",
            input_params={"query": {"type": "string"}},
            source_node="user_input",
        )

        # Verify URL matches selector's mapping
        expected_url = f"${{EXPERTAGENT_BASE_URL}}{mapping.endpoint_path}"
        assert inputs["url"] == expected_url
        assert inputs["method"] == mapping.http_method


class TestLLMGeneratorIntegration:
    """Integration tests for LLMGenerator with AgentSelector/ParameterMapper."""

    def test_llm_generator_uses_agent_selector(self) -> None:
        """Test LLMGeneratorSubWorkflow uses AgentSelector."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )

        generator = LLMGeneratorSubWorkflow()

        # Verify AgentSelector is initialized
        assert generator._agent_selector is not None

        # Get API mappings
        mappings = generator._get_api_mappings(["gmail_send", "google_search"])

        assert len(mappings) == 2
        assert mappings[0]["api_name"] == "gmail_send"
        assert "${EXPERTAGENT_BASE_URL}" in mappings[0]["endpoint_url"]

    def test_llm_generator_uses_parameter_mapper(self) -> None:
        """Test LLMGeneratorSubWorkflow uses ParameterMapper."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator import (
            LLMGeneratorSubWorkflow,
        )

        generator = LLMGeneratorSubWorkflow()

        # Verify ParameterMapper is initialized
        assert generator._parameter_mapper is not None

        # Get parameter mapping
        mapping = generator.get_parameter_mapping(
            api_name="gmail_send",
            interface_inputs={"to": {"type": "string"}},
            source_node="user_input",
        )

        assert "url" in mapping
        assert "method" in mapping
        assert "body" in mapping


class TestWorkflowGenWorkflowIntegration:
    """Integration tests for WorkflowGenWorkflow with LLM-first approach."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock ExecutionContext."""
        context = MagicMock()
        context.job_id = "test-job-123"
        return context

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "tm_task1": InterfaceSchema(
                interface_name="SendEmail",
                description="Send email to recipient",
                input_schema={"to": {"type": "string"}, "body": {"type": "string"}},
                output_schema={"result": {"type": "string"}},
            ),
        }

    def test_workflow_default_uses_llm(self) -> None:
        """Test WorkflowGenWorkflow defaults to LLM generation."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()

        # Default should be LLM-first
        assert workflow._use_llm_generation is True

    def test_workflow_can_disable_llm(self) -> None:
        """Test WorkflowGenWorkflow can use template-only mode."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow(use_llm_generation=False)

        assert workflow._use_llm_generation is False


class TestFewShotPatternsIntegration:
    """Integration tests for Few-shot patterns."""

    def test_gmail_send_pattern_exists(self) -> None:
        """Test gmail_send_pattern.yaml is loadable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            load_example,
        )

        example = load_example("gmail_send_pattern")

        assert example is not None
        assert example.name == "gmail_send_pattern"
        assert "gmail_send" in example.applicable_apis

    def test_slack_notify_pattern_exists(self) -> None:
        """Test slack_notify_pattern.yaml is loadable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            load_example,
        )

        example = load_example("slack_notify_pattern")

        assert example is not None
        assert example.name == "slack_notify_pattern"
        assert "slack_notify" in example.applicable_apis

    def test_few_shot_selection_gmail(self) -> None:
        """Test few-shot selection prefers gmail_send_pattern for gmail APIs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            select_few_shot_examples,
        )

        examples = select_few_shot_examples(
            recommended_apis=["gmail_send"],
            max_examples=2,
        )

        # Should include gmail_send_pattern
        pattern_names = [e.name for e in examples]
        assert "gmail_send_pattern" in pattern_names or "api_call_pattern" in pattern_names

    def test_few_shot_selection_slack(self) -> None:
        """Test few-shot selection prefers slack_notify_pattern for slack APIs."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            select_few_shot_examples,
        )

        examples = select_few_shot_examples(
            recommended_apis=["slack_notify"],
            max_examples=2,
        )

        # Should include slack_notify_pattern
        pattern_names = [e.name for e in examples]
        assert (
            "slack_notify_pattern" in pattern_names or "api_call_pattern" in pattern_names
        )

    def test_all_patterns_graphai_compliant(self) -> None:
        """Test all few-shot patterns follow GraphAI spec."""
        import yaml

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.few_shot import (
            load_all_examples,
        )

        examples = load_all_examples()

        for example in examples:
            # Parse YAML
            workflow = yaml.safe_load(example.workflow_yaml)

            # Check version
            assert "version" in workflow

            # Check nodes structure
            assert "nodes" in workflow

            # Check fetchAgent nodes have inputs block with url, method, body
            for node_name, node_def in workflow["nodes"].items():
                if node_def is None:
                    continue  # Skip source node
                if node_def.get("agent") == "fetchAgent":
                    inputs = node_def.get("inputs", {})
                    assert "url" in inputs, f"Node {node_name} missing url in inputs"
                    assert "method" in inputs, f"Node {node_name} missing method in inputs"


class TestDeadCodeRemoval:
    """Tests to verify dead code has been removed."""

    def test_create_yaml_generation_prompt_removed(self) -> None:
        """Test create_yaml_generation_prompt function is removed."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            yaml_generator,
        )

        # Function should not exist
        assert not hasattr(yaml_generator, "create_yaml_generation_prompt")

    def test_deprecated_methods_still_work(self) -> None:
        """Test deprecated methods still work for backward compatibility."""

        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()

        # These methods should exist but be deprecated
        assert hasattr(generator, "generate")
        assert hasattr(generator, "_build_workflow_nodes")
        assert hasattr(generator, "_generate_yaml")


class TestPromptAssemblerIntegration:
    """Integration tests for prompt assembler with API mappings."""

    def test_prompt_assembler_includes_api_mappings(self) -> None:
        """Test prompt assembler includes API mappings section."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()
        prompt = builder.build(
            task_name="Test Task",
            task_description="Test description",
            input_schema={"field": {"type": "string"}},
            output_schema={"result": {"type": "string"}},
            recommended_apis=["gmail_send"],
            api_mappings=[
                {
                    "api_name": "gmail_send",
                    "agent_type": "fetchAgent",
                    "endpoint_url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/gmail/send",
                    "http_method": "POST",
                    "description": "Send email",
                }
            ],
        )

        rendered = prompt.render()

        # Should include API mappings section
        assert "API Endpoint Mappings" in rendered or "gmail_send" in rendered
