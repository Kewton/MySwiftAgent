"""Unit tests for TestRunnerSubWorkflow.

Issue #342 Phase D.3: Tests for workflow test runner sub-workflow.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
)


class TestTestRunnerSubWorkflowExists:
    """Test that TestRunnerSubWorkflow exists and is importable."""

    def test_test_runner_importable(self):
        """TestRunnerSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        assert TestRunnerSubWorkflow is not None

    def test_test_runner_has_run_tests_method(self):
        """TestRunnerSubWorkflow should have run_tests method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        assert hasattr(runner, "run_tests")
        assert callable(runner.run_tests)

    def test_test_run_result_importable(self):
        """TestRunResult should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunResult,
        )

        assert TestRunResult is not None


class TestTestRunnerDataclasses:
    """Test dataclasses defined in test_runner."""

    def test_test_input_creation(self):
        """TestInput should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestInput,
        )

        test_input = TestInput(
            input_data={"query": "test"},
            description="Test case 1",
            expected_output_type="object",
        )
        assert test_input.input_data == {"query": "test"}
        assert test_input.description == "Test case 1"

    def test_test_input_defaults(self):
        """TestInput should have defaults."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestInput,
        )

        test_input = TestInput(input_data={"data": "value"})
        assert test_input.description == "Default test input"
        assert test_input.expected_output_type == "object"

    def test_test_result_creation(self):
        """TestResult should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestResult,
        )

        result = TestResult(
            success=True,
            input_data={"query": "test"},
            output_data={"result": "success"},
            error=None,
            execution_time_ms=100,
        )
        assert result.success is True
        assert result.output_data == {"result": "success"}

    def test_test_result_defaults(self):
        """TestResult should have defaults."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestResult,
        )

        result = TestResult(success=False)
        assert result.input_data == {}
        assert result.output_data is None
        assert result.error is None
        assert result.execution_time_ms == 0

    def test_test_run_result_creation(self):
        """TestRunResult should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunResult,
        )

        result = TestRunResult(
            tests_run=3,
            tests_passed=2,
            tests_failed=1,
            results=[],
            skipped=False,
        )
        assert result.tests_run == 3
        assert result.tests_passed == 2
        assert result.tests_failed == 1

    def test_test_run_result_defaults(self):
        """TestRunResult should have defaults."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunResult,
        )

        result = TestRunResult()
        assert result.tests_run == 0
        assert result.tests_passed == 0
        assert result.tests_failed == 0
        assert result.results == []
        assert result.skipped is False


class TestTestRunnerRunTests:
    """Test TestRunnerSubWorkflow.run_tests() method."""

    @pytest.fixture
    def sample_yaml(self) -> str:
        """Create sample YAML for testing."""
        return """# GraphAI Workflow
version: "0.6"

nodes:
  task_001:
    agent: fetchAgent
    inputs:
      data: :source.user_input
    isResult: true
"""

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={"type": "object"},
            ),
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Test workflow",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_run_tests_returns_result(
        self,
        sample_yaml: str,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """run_tests should return TestRunResult."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
            TestRunResult,
        )

        runner = TestRunnerSubWorkflow(enable_execution=False)
        result = await runner.run_tests(
            workflow_yaml=sample_yaml,
            interfaces=sample_interfaces,
            context=mock_context,
        )

        assert isinstance(result, TestRunResult)

    @pytest.mark.asyncio
    async def test_run_tests_skipped_when_disabled(
        self,
        sample_yaml: str,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """run_tests should skip when execution is disabled."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow(enable_execution=False)
        result = await runner.run_tests(
            workflow_yaml=sample_yaml,
            interfaces=sample_interfaces,
            context=mock_context,
        )

        assert result.skipped is True
        assert result.tests_run == 0

    @pytest.mark.asyncio
    async def test_run_tests_executes_when_enabled(
        self,
        sample_yaml: str,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """run_tests should execute when enabled."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow(enable_execution=True)
        result = await runner.run_tests(
            workflow_yaml=sample_yaml,
            interfaces=sample_interfaces,
            context=mock_context,
        )

        assert result.skipped is False
        assert result.tests_run >= 1

    @pytest.mark.asyncio
    async def test_run_tests_empty_yaml_raises_error(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """run_tests should raise WorkflowError for empty YAML."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await runner.run_tests(
                workflow_yaml="",
                interfaces=sample_interfaces,
                context=mock_context,
            )

        assert "No workflow YAML provided" in str(exc_info.value)


class TestTestRunnerGenerateSampleInputs:
    """Test sample input generation."""

    def test_generate_from_schema(self):
        """Should generate sample input from schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                },
                output_schema={"type": "object"},
            ),
        }

        inputs = runner._generate_sample_inputs(interfaces)

        assert len(inputs) >= 1
        assert "query" in inputs[0].input_data or "count" in inputs[0].input_data

    def test_generate_basic_input_when_empty(self):
        """Should generate basic input when no interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        inputs = runner._generate_sample_inputs({})

        assert len(inputs) == 1
        assert "query" in inputs[0].input_data


class TestTestRunnerGenerateSampleFromSchema:
    """Test sample data generation from JSON Schema."""

    def test_generate_string_property(self):
        """Should generate sample string."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        sample = runner._generate_sample_from_schema(schema)

        assert "name" in sample
        assert isinstance(sample["name"], str)

    def test_generate_integer_property(self):
        """Should generate sample integer."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        schema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
            },
        }

        sample = runner._generate_sample_from_schema(schema)

        assert "count" in sample
        assert isinstance(sample["count"], int)

    def test_generate_boolean_property(self):
        """Should generate sample boolean."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        schema = {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
            },
        }

        sample = runner._generate_sample_from_schema(schema)

        assert "enabled" in sample
        assert isinstance(sample["enabled"], bool)

    def test_generate_multiple_properties(self):
        """Should generate multiple properties."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }

        sample = runner._generate_sample_from_schema(schema)

        assert "name" in sample
        assert "age" in sample
        assert "active" in sample


class TestTestRunnerValidateYaml:
    """Test YAML validation."""

    @pytest.mark.asyncio
    async def test_validate_valid_yaml(self):
        """Should validate correct YAML."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        yaml_content = """
version: "0.6"
nodes:
  task_001:
    agent: fetchAgent
    isResult: true
"""

        is_valid, errors = await runner.validate_workflow_yaml(yaml_content)

        assert is_valid is True
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_missing_version(self):
        """Should detect missing version."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        yaml_content = """
nodes:
  task_001:
    agent: fetchAgent
    isResult: true
"""

        is_valid, errors = await runner.validate_workflow_yaml(yaml_content)

        assert is_valid is False
        assert "Missing version field" in errors

    @pytest.mark.asyncio
    async def test_validate_missing_nodes(self):
        """Should detect missing nodes."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        yaml_content = """
version: "0.6"
"""

        is_valid, errors = await runner.validate_workflow_yaml(yaml_content)

        assert is_valid is False
        assert "Missing nodes field" in errors

    @pytest.mark.asyncio
    async def test_validate_missing_result_node(self):
        """Should detect missing result node."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        yaml_content = """
version: "0.6"
nodes:
  task_001:
    agent: fetchAgent
"""

        is_valid, errors = await runner.validate_workflow_yaml(yaml_content)

        assert is_valid is False
        assert "No result node defined" in errors

    @pytest.mark.asyncio
    async def test_validate_empty_yaml(self):
        """Should detect empty YAML."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()

        is_valid, errors = await runner.validate_workflow_yaml("")

        assert is_valid is False
        assert "Empty workflow content" in errors


class TestTestRunnerInitialization:
    """Test TestRunnerSubWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow()
        assert runner._enable_execution is False
        assert runner._timeout_sec == 30

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunnerSubWorkflow,
        )

        runner = TestRunnerSubWorkflow(
            enable_execution=True,
            timeout_sec=60,
        )
        assert runner._enable_execution is True
        assert runner._timeout_sec == 60
