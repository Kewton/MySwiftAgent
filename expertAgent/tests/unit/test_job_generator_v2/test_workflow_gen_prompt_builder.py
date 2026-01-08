"""Tests for PromptBuilderSubWorkflow.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""


from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
    PromptBuilderSubWorkflow,
    WorkflowPrompt,
    assemble_prompt,
    build_task_context,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.rules import (
    ALL_AGENT_RULES,
    API_RULES,
    BASE_RULES,
    REFERENCE_RULES,
    get_agent_rules,
    get_api_rules,
    get_base_rules,
    get_reference_rules,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.system import (
    WORKFLOW_GENERATOR_SYSTEM_PROMPT,
    get_system_prompt,
)


class TestBaseRules:
    """Tests for base rules."""

    def test_get_base_rules_not_empty(self):
        """Test get_base_rules returns non-empty string."""
        rules = get_base_rules()
        assert rules
        assert len(rules) > 0

    def test_base_rules_contains_version(self):
        """Test base rules mention version."""
        assert "version" in BASE_RULES.lower()
        assert "0.5" in BASE_RULES

    def test_base_rules_contains_source(self):
        """Test base rules mention source node."""
        assert "source" in BASE_RULES.lower()

    def test_base_rules_contains_result(self):
        """Test base rules mention isResult."""
        assert "isResult" in BASE_RULES or "result" in BASE_RULES.lower()


class TestAgentRules:
    """Tests for agent-specific rules."""

    def test_get_agent_rules_all(self):
        """Test get_agent_rules returns all rules when no filter."""
        rules = get_agent_rules()
        assert rules
        assert "fetchAgent" in rules

    def test_get_agent_rules_filtered(self):
        """Test get_agent_rules filters by agent names."""
        rules = get_agent_rules(["fetchAgent"])
        assert "fetchAgent" in rules
        # Should still include basic structure
        assert "Agent" in rules

    def test_all_agent_rules_contains_fetch(self):
        """Test ALL_AGENT_RULES contains fetchAgent rules."""
        assert "fetchAgent" in ALL_AGENT_RULES
        assert "inputs" in ALL_AGENT_RULES

    def test_all_agent_rules_contains_string_template(self):
        """Test ALL_AGENT_RULES contains stringTemplateAgent rules."""
        assert "stringTemplateAgent" in ALL_AGENT_RULES

    def test_all_agent_rules_contains_map(self):
        """Test ALL_AGENT_RULES contains mapAgent rules."""
        assert "mapAgent" in ALL_AGENT_RULES


class TestReferenceRules:
    """Tests for reference rules."""

    def test_get_reference_rules_not_empty(self):
        """Test get_reference_rules returns non-empty string."""
        rules = get_reference_rules()
        assert rules
        assert len(rules) > 0

    def test_reference_rules_contains_colon_syntax(self):
        """Test reference rules mention : syntax."""
        assert ":" in REFERENCE_RULES

    def test_reference_rules_contains_source(self):
        """Test reference rules mention :source."""
        assert ":source" in REFERENCE_RULES


class TestApiRules:
    """Tests for API rules."""

    def test_get_api_rules_not_empty(self):
        """Test get_api_rules returns non-empty string."""
        rules = get_api_rules()
        assert rules
        assert len(rules) > 0

    def test_api_rules_contains_base_url(self):
        """Test API rules mention base URL placeholder."""
        assert "EXPERTAGENT_BASE_URL" in API_RULES

    def test_api_rules_contains_timeout(self):
        """Test API rules mention timeout."""
        assert "timeout" in API_RULES.lower()


class TestSystemPrompt:
    """Tests for system prompt."""

    def test_get_system_prompt_verbose(self):
        """Test get_system_prompt returns verbose prompt."""
        prompt = get_system_prompt(verbose=True)
        assert prompt
        assert len(prompt) > 100  # Should be substantial

    def test_get_system_prompt_short(self):
        """Test get_system_prompt returns shorter prompt when not verbose."""
        prompt = get_system_prompt(verbose=False)
        assert prompt
        verbose_prompt = get_system_prompt(verbose=True)
        assert len(prompt) < len(verbose_prompt)

    def test_system_prompt_mentions_graphai(self):
        """Test system prompt mentions GraphAI."""
        assert "GraphAI" in WORKFLOW_GENERATOR_SYSTEM_PROMPT

    def test_system_prompt_mentions_yaml(self):
        """Test system prompt mentions YAML."""
        assert "YAML" in WORKFLOW_GENERATOR_SYSTEM_PROMPT


class TestBuildTaskContext:
    """Tests for build_task_context function."""

    def test_build_task_context_basic(self):
        """Test building basic task context."""
        context = build_task_context(
            task_name="Test Task",
            task_description="A test task",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )
        assert "Test Task" in context
        assert "A test task" in context
        assert "Input Schema" in context
        assert "Output Schema" in context

    def test_build_task_context_with_dependencies(self):
        """Test building task context with dependencies."""
        context = build_task_context(
            task_name="Dependent Task",
            task_description="Depends on other tasks",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            dependencies=["task_1", "task_2"],
        )
        assert "Dependencies" in context
        assert "task_1" in context
        assert "task_2" in context

    def test_build_task_context_json_formatted(self):
        """Test that schemas are JSON formatted."""
        context = build_task_context(
            task_name="JSON Task",
            task_description="Has JSON schema",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            output_schema={"type": "object"},
        )
        assert '"type"' in context
        assert '"properties"' in context


class TestAssemblePrompt:
    """Tests for assemble_prompt function."""

    def test_assemble_prompt_returns_workflow_prompt(self):
        """Test assemble_prompt returns WorkflowPrompt."""
        prompt = assemble_prompt(
            task_name="Assemble Test",
            task_description="Test assembly",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert isinstance(prompt, WorkflowPrompt)

    def test_assemble_prompt_has_all_components(self):
        """Test assembled prompt has all required components."""
        prompt = assemble_prompt(
            task_name="Complete Test",
            task_description="Test all components",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert prompt.system
        assert prompt.rules
        assert prompt.task_context

    def test_assemble_prompt_with_apis(self):
        """Test assembled prompt with API constraints."""
        prompt = assemble_prompt(
            task_name="API Test",
            task_description="Test with APIs",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=["Gmail検索"],
        )
        assert prompt.api_constraints  # May be empty if API not found
        # But should not raise error


class TestWorkflowPrompt:
    """Tests for WorkflowPrompt dataclass."""

    def test_workflow_prompt_render(self):
        """Test WorkflowPrompt render method."""
        prompt = WorkflowPrompt(
            system="System prompt",
            rules="Rules section",
            api_constraints="API constraints",
            examples=[],
            task_context="Task context",
        )
        rendered = prompt.render()
        assert "Rules section" in rendered
        assert "Task context" in rendered

    def test_workflow_prompt_render_with_error_feedback(self):
        """Test WorkflowPrompt render includes error feedback."""
        prompt = WorkflowPrompt(
            system="System prompt",
            rules="Rules",
            api_constraints="",
            examples=[],
            task_context="Task",
            error_feedback="Fix these errors",
        )
        rendered = prompt.render()
        assert "Fix these errors" in rendered


class TestPromptBuilderSubWorkflow:
    """Tests for PromptBuilderSubWorkflow class."""

    def test_create_prompt_builder(self):
        """Test creating PromptBuilderSubWorkflow."""
        builder = PromptBuilderSubWorkflow()
        assert builder is not None

    def test_build_prompt(self):
        """Test building a prompt."""
        builder = PromptBuilderSubWorkflow()
        prompt = builder.build(
            task_name="Builder Test",
            task_description="Test the builder",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert isinstance(prompt, WorkflowPrompt)
        assert prompt.system
        assert prompt.rules

    def test_build_prompt_with_apis(self):
        """Test building prompt with recommended APIs."""
        builder = PromptBuilderSubWorkflow()
        prompt = builder.build(
            task_name="API Builder Test",
            task_description="Test with APIs",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=["google_search"],
        )
        assert isinstance(prompt, WorkflowPrompt)
