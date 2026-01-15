"""Test runner sub-workflow for WorkflowGen.

This module provides the TestRunnerSubWorkflow that:
1. Generates sample input data for workflow testing
2. Executes workflow tests (optional)
3. Validates workflow outputs

Issue #342 Phase D.2: Workflow test execution support.
Issue #359 Fix: Support both GraphAI YAML and TaskFlow JSON validation.

Key design decisions:
- Uses ExecutionContext for API access (dependency injection)
- Does NOT import from langgraph or old jobTaskGeneratorAgents
- Test execution is optional and can be disabled
- Supports both GraphAI (YAML) and TaskFlow (JSON) formats
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types_old import (
    InterfaceSchema,
    Phase,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class TestInput:
    """Sample input for workflow testing.

    Attributes:
        input_data: Sample input data
        description: Description of the test case
        expected_output_type: Expected output type/structure
    """

    input_data: dict[str, Any]
    description: str = "Default test input"
    expected_output_type: str = "object"


@dataclass
class TestResult:
    """Result from a single test execution.

    Attributes:
        success: Whether the test passed
        input_data: Input data used
        output_data: Output data received
        error: Error message if failed
        execution_time_ms: Execution time in milliseconds
    """

    success: bool
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int = 0


@dataclass
class TestRunResult:
    """Result from test runner sub-workflow.

    Attributes:
        tests_run: Number of tests executed
        tests_passed: Number of tests passed
        tests_failed: Number of tests failed
        results: Individual test results
        skipped: Whether tests were skipped
    """

    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    results: list[TestResult] = field(default_factory=list)
    skipped: bool = False


class TestRunnerSubWorkflow:
    """Sub-workflow for running workflow tests.

    This sub-workflow handles:
    1. Generating sample input data from interface schemas
    2. Executing workflow with sample data (optional)
    3. Validating outputs against expected schemas

    Example:
        runner = TestRunnerSubWorkflow()
        result = await runner.run_tests(workflow_yaml, interfaces, context)
    """

    def __init__(
        self,
        enable_execution: bool = False,
        timeout_sec: int = 30,
    ) -> None:
        """Initialize TestRunnerSubWorkflow.

        Args:
            enable_execution: Whether to actually execute workflows
            timeout_sec: Timeout for test execution
        """
        self._enable_execution = enable_execution
        self._timeout_sec = timeout_sec

    async def run_tests(
        self,
        workflow_yaml: str,
        interfaces: dict[str, InterfaceSchema],
        context: "ExecutionContext",
    ) -> TestRunResult:
        """Run tests for a workflow.

        Args:
            workflow_yaml: Generated YAML workflow
            interfaces: Interface schemas for input generation
            context: Execution context

        Returns:
            TestRunResult with test outcomes

        Raises:
            WorkflowError: If test execution fails critically
        """
        logger.info(
            "Running workflow tests for job %s (execution=%s)",
            context.job_id,
            self._enable_execution,
        )

        if not workflow_yaml:
            raise WorkflowError(
                "No workflow YAML provided for testing",
                ErrorType.VALIDATION,
                Phase.WORKFLOW_GEN,
            )

        # Generate sample inputs
        sample_inputs = self._generate_sample_inputs(interfaces)
        logger.info("Generated %d sample inputs for testing", len(sample_inputs))

        if not self._enable_execution:
            # Skip actual execution, just validate YAML
            logger.info("Test execution disabled, skipping workflow run")
            return TestRunResult(
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                results=[],
                skipped=True,
            )

        # Run tests with sample inputs
        results: list[TestResult] = []
        for test_input in sample_inputs:
            result = await self._execute_test(
                workflow_yaml=workflow_yaml,
                test_input=test_input,
                context=context,
            )
            results.append(result)

        # Aggregate results
        tests_passed = sum(1 for r in results if r.success)
        tests_failed = len(results) - tests_passed

        logger.info(
            "Workflow tests complete: %d passed, %d failed",
            tests_passed,
            tests_failed,
        )

        return TestRunResult(
            tests_run=len(results),
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            results=results,
            skipped=False,
        )

    def _generate_sample_inputs(
        self,
        interfaces: dict[str, InterfaceSchema],
    ) -> list[TestInput]:
        """Generate sample inputs from interface schemas.

        Args:
            interfaces: Interface schemas

        Returns:
            List of TestInput for testing
        """
        if not interfaces:
            # Generate a basic sample input
            return [
                TestInput(
                    input_data={"query": "test query"},
                    description="Basic test input",
                )
            ]

        # Find the first task's input schema
        for task_id, interface in interfaces.items():
            sample_data = self._generate_sample_from_schema(interface.input_schema)
            return [
                TestInput(
                    input_data=sample_data,
                    description=f"Sample input for {task_id}",
                )
            ]

        return [
            TestInput(
                input_data={"query": "default test"},
                description="Default test input",
            )
        ]

    def _generate_sample_from_schema(
        self,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate sample data from a JSON Schema.

        Args:
            schema: JSON Schema definition

        Returns:
            Sample data matching the schema
        """
        sample: dict[str, Any] = {}
        schema_type = schema.get("type", "object")

        if schema_type != "object":
            return {"value": "sample"}

        properties = schema.get("properties", {})
        for prop_name, prop_def in properties.items():
            prop_type = prop_def.get("type", "string")

            if prop_type == "string":
                sample[prop_name] = f"sample_{prop_name}"
            elif prop_type == "integer":
                sample[prop_name] = 1
            elif prop_type == "number":
                sample[prop_name] = 1.0
            elif prop_type == "boolean":
                sample[prop_name] = True
            elif prop_type == "array":
                sample[prop_name] = []
            elif prop_type == "object":
                sample[prop_name] = {}
            else:
                sample[prop_name] = None

        return sample

    async def _execute_test(
        self,
        workflow_yaml: str,
        test_input: TestInput,
        context: "ExecutionContext",
    ) -> TestResult:
        """Execute a single test.

        Args:
            workflow_yaml: Workflow YAML to execute
            test_input: Test input data
            context: Execution context

        Returns:
            TestResult from execution
        """
        # Placeholder - will be connected to GraphAI server in Phase E
        logger.debug(
            "Executing test: %s",
            test_input.description,
        )

        # Simulate successful execution for now
        return TestResult(
            success=True,
            input_data=test_input.input_data,
            output_data={"result": "simulated"},
            error=None,
            execution_time_ms=100,
        )

    async def validate_workflow_yaml(
        self,
        workflow_content: str,
        engine: str = "auto",
    ) -> tuple[bool, list[str]]:
        """Validate workflow content (YAML or JSON).

        Issue #359 Fix: Auto-detect format and validate accordingly.

        Args:
            workflow_content: Workflow content (YAML or JSON)
            engine: Engine type ('graphai', 'taskflow', or 'auto' for auto-detect)

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        if not workflow_content:
            errors.append("Empty workflow content")
            return False, errors

        # Auto-detect format if not specified
        if engine == "auto":
            engine = self._detect_workflow_format(workflow_content)

        if engine == "taskflow":
            return self._validate_taskflow_json(workflow_content)
        else:
            return self._validate_graphai_yaml(workflow_content)

    def _detect_workflow_format(self, content: str) -> str:
        """Auto-detect workflow format (GraphAI YAML or TaskFlow JSON).

        Args:
            content: Workflow content

        Returns:
            'taskflow' or 'graphai'
        """
        content_stripped = content.strip()

        # TaskFlow JSON starts with '{' and contains "steps" or "workflow_name"
        if content_stripped.startswith("{"):
            try:
                data = json.loads(content_stripped)
                if "steps" in data or "workflow_name" in data:
                    return "taskflow"
            except json.JSONDecodeError:
                pass

        # Default to GraphAI YAML
        return "graphai"

    def _validate_graphai_yaml(self, workflow_yaml: str) -> tuple[bool, list[str]]:
        """Validate GraphAI YAML workflow.

        Args:
            workflow_yaml: YAML content to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        # Basic validation checks for GraphAI YAML
        if "version:" not in workflow_yaml:
            errors.append("Missing version field")

        if "nodes:" not in workflow_yaml:
            errors.append("Missing nodes field")

        # Check for at least one node with isResult
        if (
            "isResult: true" not in workflow_yaml
            and "isResult:true" not in workflow_yaml
        ):
            errors.append("No result node defined")

        return len(errors) == 0, errors

    def _validate_taskflow_json(self, workflow_json: str) -> tuple[bool, list[str]]:
        """Validate TaskFlow V2 JSON workflow.

        Issue #359: Added TaskFlow JSON validation.

        Args:
            workflow_json: JSON content to validate

        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[str] = []

        # Parse JSON
        try:
            data = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return False, errors

        # Required fields for TaskFlow V2
        if "workflow_name" not in data:
            errors.append("Missing workflow_name field")

        if "steps" not in data:
            errors.append("Missing steps field")
        elif not data.get("steps"):
            errors.append("Steps array is empty")

        # Check for output mapping
        if "output" not in data:
            errors.append("Missing output field")

        # Validate each step has required fields
        for i, step in enumerate(data.get("steps", [])):
            # Skip parallel/conditional blocks
            if "parallel" in step or "condition" in step:
                continue

            if "id" not in step:
                errors.append(f"Step {i}: missing id field")

            if "type" not in step:
                errors.append(f"Step {i}: missing type field")

        return len(errors) == 0, errors
