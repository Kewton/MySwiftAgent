"""Integration test for Issue #342 V2 API response with task_breakdown.

This test verifies that the V2 Job Generator returns task_breakdown
and interface_definitions in the response.
"""


from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator
from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceDesignOutput,
    InterfaceSchema,
    JobGenerationResult,
    Phase,
    PhaseStatus,
    RegistrationOutput,
    TaskBreakdownOutput,
    TaskDefinition,
    WorkflowGenOutput,
    WorkflowGenPhaseOutput,
)


class TestV2ResponseTaskBreakdown:
    """Integration tests for V2 response with task_breakdown."""

    def test_job_generation_result_includes_tasks(self) -> None:
        """Test that JobGenerationResult properly includes tasks and interfaces."""
        # Arrange
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Search",
                description="Search for data",
                task_type="search",
                recommended_api="/api/search",
                priority=1,
            ),
            TaskDefinition(
                id="task_002",
                name="Process",
                description="Process data",
                task_type="process",
                recommended_api="/api/process",
                priority=2,
                dependencies=["task_001"],
            ),
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Search interface",
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Process interface",
            ),
        }

        # Act
        result = JobGenerationResult(
            success=True,
            job_id="job-123",
            job_master_id="master-123",
            task_master_ids=["tm-001", "tm-002"],
            workflow_yaml="nodes: {}",
            tasks=tasks,
            interfaces=interfaces,
        )

        # Assert
        assert result.tasks is not None
        assert len(result.tasks) == 2
        assert result.tasks[0].id == "task_001"
        assert result.tasks[1].id == "task_002"
        assert result.interfaces is not None
        assert len(result.interfaces) == 2
        assert "task_001" in result.interfaces
        assert "task_002" in result.interfaces

    def test_orchestrator_create_result_includes_tasks(self) -> None:
        """Test that orchestrator._create_result includes tasks from phase_outputs."""
        # Arrange
        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager)

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task",
                description="Description",
                task_type="test",
                recommended_api="/api",
            )
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
        }

        # Create task workflow output for each task
        task_workflow = WorkflowGenOutput(
            status=PhaseStatus.SUCCESS,
            task_id="task_001",
            workflow_yaml="nodes: {}",
        )

        phase_outputs = {
            Phase.TASK_BREAKDOWN: TaskBreakdownOutput(
                status=PhaseStatus.SUCCESS,
                tasks=tasks,
            ),
            Phase.INTERFACE_DESIGN: InterfaceDesignOutput(
                status=PhaseStatus.SUCCESS,
                interfaces=interfaces,
            ),
            Phase.REGISTRATION: RegistrationOutput(
                status=PhaseStatus.SUCCESS,
                job_master_id="master-123",
                task_master_ids=["tm-001"],
                job_id="job-123",
            ),
            Phase.WORKFLOW_GEN: WorkflowGenPhaseOutput(
                status=PhaseStatus.SUCCESS,
                task_workflows={"task_001": task_workflow},
            ),
        }

        # Act
        result = orchestrator._create_result(phase_outputs)

        # Assert
        assert result.success is True
        assert result.tasks is not None
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "task_001"
        assert result.interfaces is not None
        assert "task_001" in result.interfaces

    def test_adapter_convert_result_returns_task_breakdown(self) -> None:
        """Test that adapter._convert_result returns task_breakdown in response."""
        # Arrange
        adapter = JobGeneratorV2Adapter(max_retry=3)

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Gmail Search",
                description="Search Gmail",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
            ),
            TaskDefinition(
                id="task_002",
                name="Send Email",
                description="Send email with results",
                task_type="email_send",
                recommended_api="/v1/utility/gmail/send",
                priority=2,
                dependencies=["task_001"],
            ),
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                description="Gmail search interface",
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object", "properties": {"to": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
                description="Email send interface",
            ),
        }

        result = JobGenerationResult(
            success=True,
            job_id="job-123",
            job_master_id="master-123",
            task_master_ids=["tm-001", "tm-002"],
            workflow_yaml="nodes: {}",
            tasks=tasks,
            interfaces=interfaces,
        )

        # Act
        response = adapter._convert_result(result, "job-123")

        # Assert
        assert response.status == "success"
        assert response.task_breakdown is not None
        assert len(response.task_breakdown) == 2

        # Verify task_breakdown structure
        assert response.task_breakdown[0]["task_id"] == "task_001"
        assert response.task_breakdown[0]["name"] == "Gmail Search"
        assert response.task_breakdown[0]["task_type"] == "gmail_search"
        assert response.task_breakdown[1]["task_id"] == "task_002"
        assert response.task_breakdown[1]["dependencies"] == ["task_001"]

        # Verify interface_definitions structure
        assert response.interface_definitions is not None
        assert len(response.interface_definitions) == 2
        assert "task_001" in response.interface_definitions
        assert "task_002" in response.interface_definitions
        assert "input_schema" in response.interface_definitions["task_001"]
        assert "output_schema" in response.interface_definitions["task_001"]
        assert "description" in response.interface_definitions["task_001"]

    def test_end_to_end_flow_includes_task_breakdown(self) -> None:
        """Test the complete flow from phase_outputs to response task_breakdown."""
        # Arrange: Create phase outputs as would be produced by the workflow
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Search",
                description="Search task",
                task_type="search",
                recommended_api="/api/search",
            ),
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

        # Create task workflow output for each task
        task_workflow = WorkflowGenOutput(
            status=PhaseStatus.SUCCESS,
            task_id="task_001",
            workflow_yaml="nodes: {}",
        )

        phase_outputs = {
            Phase.TASK_BREAKDOWN: TaskBreakdownOutput(
                status=PhaseStatus.SUCCESS,
                tasks=tasks,
            ),
            Phase.INTERFACE_DESIGN: InterfaceDesignOutput(
                status=PhaseStatus.SUCCESS,
                interfaces=interfaces,
            ),
            Phase.REGISTRATION: RegistrationOutput(
                status=PhaseStatus.SUCCESS,
                job_master_id="master-123",
                task_master_ids=["tm-001"],
                job_id="job-123",
            ),
            Phase.WORKFLOW_GEN: WorkflowGenPhaseOutput(
                status=PhaseStatus.SUCCESS,
                task_workflows={"task_001": task_workflow},
            ),
        }

        # Act: Simulate orchestrator creating result
        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager)
        job_result = orchestrator._create_result(phase_outputs)

        # Act: Simulate adapter converting result
        adapter = JobGeneratorV2Adapter(max_retry=3)
        response = adapter._convert_result(job_result, "job-123")

        # Assert: Full end-to-end verification
        assert response.status == "success"
        assert response.task_breakdown is not None
        assert len(response.task_breakdown) == 1
        assert response.task_breakdown[0]["task_id"] == "task_001"
        assert response.interface_definitions is not None
        assert "task_001" in response.interface_definitions
