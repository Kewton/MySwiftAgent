"""Unit tests for YamlGeneratorSubWorkflow.

Issue #342 Phase D.3: Tests for YAML generation sub-workflow.
"""


import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
)


class TestYamlGeneratorSubWorkflowExists:
    """Test that YamlGeneratorSubWorkflow exists and is importable."""

    def test_yaml_generator_importable(self):
        """YamlGeneratorSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        assert YamlGeneratorSubWorkflow is not None

    def test_yaml_generator_has_generate_method(self):
        """YamlGeneratorSubWorkflow should have generate method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        assert hasattr(generator, "generate")
        assert callable(generator.generate)

    def test_yaml_generation_result_importable(self):
        """YamlGenerationResult should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        assert YamlGenerationResult is not None

    def test_prompt_constants_exist(self):
        """Prompt constants should be defined."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YAML_GENERATION_SYSTEM_PROMPT,
        )

        assert YAML_GENERATION_SYSTEM_PROMPT is not None
        assert "GraphAI" in YAML_GENERATION_SYSTEM_PROMPT


class TestYamlGeneratorDataclasses:
    """Test dataclasses defined in yaml_generator."""

    def test_workflow_node_definition_creation(self):
        """WorkflowNodeDefinition should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            WorkflowNodeDefinition,
        )

        node = WorkflowNodeDefinition(
            node_id="task_001",
            agent="fetchAgent",
            inputs={"data": ":source.user_input"},
            params={"task_master_id": "tm_001"},
            is_result=True,
        )
        assert node.node_id == "task_001"
        assert node.agent == "fetchAgent"
        assert node.is_result is True

    def test_workflow_node_definition_defaults(self):
        """WorkflowNodeDefinition should have defaults."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            WorkflowNodeDefinition,
        )

        node = WorkflowNodeDefinition(
            node_id="task_001",
            agent="fetchAgent",
        )
        assert node.inputs == {}
        assert node.params == {}
        assert node.is_result is False

    def test_yaml_generation_result_creation(self):
        """YamlGenerationResult should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        result = YamlGenerationResult(
            yaml_content="version: \"0.6\"",
            workflow_name="test_workflow",
            node_count=3,
            generation_method="template",
        )
        assert result.yaml_content == "version: \"0.6\""
        assert result.workflow_name == "test_workflow"
        assert result.node_count == 3


class TestYamlGeneratorGenerate:
    """Test YamlGeneratorSubWorkflow.generate() method."""

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"emails": {"type": "array"}}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object", "properties": {"emails": {"type": "array"}}},
                output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
            ),
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and summarize emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_generate_returns_result(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """generate should return YamlGenerationResult."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        result = await generator.generate(
            task_master_ids=["tm_task_001", "tm_task_002"],
            job_master_id="jm_123",
            interfaces=sample_interfaces,
            context=mock_context,
        )

        assert isinstance(result, YamlGenerationResult)
        assert result.yaml_content is not None
        assert result.workflow_name is not None
        assert result.node_count == 2

    @pytest.mark.asyncio
    async def test_generate_empty_task_masters_raises_error(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """generate should raise WorkflowError for empty task masters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await generator.generate(
                task_master_ids=[],
                job_master_id="jm_123",
                interfaces=sample_interfaces,
                context=mock_context,
            )

        assert "No task masters provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_creates_valid_yaml(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """generate should create valid YAML structure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        result = await generator.generate(
            task_master_ids=["tm_task_001", "tm_task_002"],
            job_master_id="jm_123",
            interfaces=sample_interfaces,
            context=mock_context,
        )

        yaml_content = result.yaml_content

        # Check required sections
        assert "version:" in yaml_content
        assert "nodes:" in yaml_content
        assert "isResult: true" in yaml_content

    @pytest.mark.asyncio
    async def test_generate_creates_task_chain(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """generate should create proper task chaining."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        result = await generator.generate(
            task_master_ids=["tm_task_001", "tm_task_002"],
            job_master_id="jm_123",
            interfaces=sample_interfaces,
            context=mock_context,
        )

        yaml_content = result.yaml_content

        # First task should reference user_input
        assert ":source.user_input" in yaml_content

        # Second task should reference first task
        assert ":source.task_001" in yaml_content


class TestYamlGeneratorBuildWorkflowNodes:
    """Test workflow node building logic."""

    def test_build_single_node(self):
        """Should build single node correctly."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        nodes = generator._build_workflow_nodes(
            task_master_ids=["tm_task_001"],
            interfaces={},
        )

        assert len(nodes) == 1
        assert nodes[0].node_id == "task_001"
        assert nodes[0].is_result is True  # Only node is result

    def test_build_multiple_nodes(self):
        """Should build multiple nodes with proper chaining."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        nodes = generator._build_workflow_nodes(
            task_master_ids=["tm_task_001", "tm_task_002", "tm_task_003"],
            interfaces={},
        )

        assert len(nodes) == 3

        # First node uses user_input
        assert nodes[0].inputs["data"] == ":source.user_input"
        assert nodes[0].is_result is False

        # Second node references first
        assert nodes[1].inputs["data"] == ":source.task_001"
        assert nodes[1].is_result is False

        # Third node references second and is result
        assert nodes[2].inputs["data"] == ":source.task_002"
        assert nodes[2].is_result is True

    def test_build_nodes_preserves_task_master_id(self):
        """Should include task_master_id in params."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        nodes = generator._build_workflow_nodes(
            task_master_ids=["tm_task_001"],
            interfaces={},
        )

        assert nodes[0].params["task_master_id"] == "tm_task_001"


class TestYamlGeneratorGenerateYaml:
    """Test YAML string generation."""

    def test_generate_yaml_includes_version(self):
        """Generated YAML should include version."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            WorkflowNodeDefinition,
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow(graphai_version="0.6")
        nodes = [
            WorkflowNodeDefinition(
                node_id="task_001",
                agent="fetchAgent",
                is_result=True,
            )
        ]

        yaml_content = generator._generate_yaml("test_workflow", nodes)

        assert 'version: "0.6"' in yaml_content

    def test_generate_yaml_includes_comment(self):
        """Generated YAML should include workflow name comment."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            WorkflowNodeDefinition,
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        nodes = [
            WorkflowNodeDefinition(
                node_id="task_001",
                agent="fetchAgent",
                is_result=True,
            )
        ]

        yaml_content = generator._generate_yaml("my_workflow", nodes)

        assert "# GraphAI Workflow: my_workflow" in yaml_content


class TestYamlGeneratorInitialization:
    """Test YamlGeneratorSubWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow()
        # Issue #342 Phase 1: Default version is 0.5 per BASE_RULES
        assert generator._graphai_version == "0.5"
        assert generator._use_llm_generation is False

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGeneratorSubWorkflow,
        )

        generator = YamlGeneratorSubWorkflow(
            graphai_version="0.7",
            use_llm_generation=True,
        )
        assert generator._graphai_version == "0.7"
        assert generator._use_llm_generation is True


class TestDeadCodeRemoval:
    """Test that dead code has been removed.

    Issue #342 V2: create_yaml_generation_prompt was removed and superseded
    by PromptBuilderSubWorkflow.build()
    """

    def test_create_yaml_generation_prompt_removed(self):
        """create_yaml_generation_prompt should no longer exist."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            yaml_generator,
        )

        # Function was removed in Issue #342 V2
        assert not hasattr(yaml_generator, "create_yaml_generation_prompt")

    def test_prompt_builder_exists_as_replacement(self):
        """PromptBuilderSubWorkflow should exist as the replacement."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder import (
            PromptBuilderSubWorkflow,
        )

        builder = PromptBuilderSubWorkflow()
        assert hasattr(builder, "build")
        assert callable(builder.build)
