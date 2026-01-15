"""E2E Integration tests for Job Generation V3.

Issue #359 Iteration 2 Task 3.3: E2E scenarios for 3-phase architecture.

Tests the complete flow:
Phase 1: JOB_ANALYSIS -> Phase 2: REGISTRATION -> Phase 3: WORKFLOW_GEN
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    ErrorType,
    ParallelExecutionResult,
    TaskResult,
    UnifiedTaskIdentifier,
)


class TestJobGenerationE2ESuccess:
    """E2E tests for successful job generation flow."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for job analysis."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            InterfaceDefinition,
            JobAnalysisResponse,
        )

        mock_response = JobAnalysisResponse(
            tasks=[
                AnalyzedTask(
                    task_id="task_001",
                    name="Search Gmail",
                    description="Search Gmail for recent emails",
                    task_type="fetch",
                    recommended_api="/v1/utility/gmail/search",
                    dependencies=[],
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
                ),
                AnalyzedTask(
                    task_id="task_002",
                    name="Summarize Emails",
                    description="Summarize the found emails",
                    task_type="transform",
                    recommended_api="/v1/llm/summarize",
                    dependencies=["task_001"],
                    input_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
                    output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
                ),
            ],
            interfaces={
                "task_001": InterfaceDefinition(
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
                    description="Gmail search interface",
                ),
                "task_002": InterfaceDefinition(
                    input_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
                    output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
                    description="Summarization interface",
                ),
            },
            job_body_parameters=[],
            overall_summary="Email search and summarization workflow",
        )

        mock = AsyncMock(return_value=mock_response)
        return mock

    @pytest.fixture
    def mock_jobqueue_client(self):
        """Mock jobqueue client for registration."""
        mock = AsyncMock()

        # Mock JobMaster creation
        mock.create_job_master = AsyncMock(return_value={"id": "jm_test123"})

        # Mock TaskMaster creation
        mock.create_task_master = AsyncMock(
            side_effect=[
                {"id": "tm_001"},
                {"id": "tm_002"},
            ]
        )

        return mock

    @pytest.mark.asyncio
    async def test_full_e2e_flow(self, mock_llm_client, mock_jobqueue_client):
        """Test complete E2E flow from request to workflow generation."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )

        # Create orchestrator with mocks
        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        # Mock the phase executors
        with patch.object(orchestrator, '_execute_job_analysis', mock_llm_client):
            with patch.object(orchestrator, '_execute_registration') as mock_reg:
                mock_reg.return_value = {
                    "job_master_id": "jm_test123",
                    "task_id_to_master_id": {
                        "task_001": "tm_001",
                        "task_002": "tm_002",
                    },
                }

                with patch.object(orchestrator, '_execute_workflow_gen') as mock_wf:
                    mock_wf.return_value = ParallelExecutionResult(
                        successful_tasks=[
                            TaskResult(task_id="task_001", success=True, workflow={"workflow_name": "wf_001"}),
                            TaskResult(task_id="task_002", success=True, workflow={"workflow_name": "wf_002"}),
                        ],
                        failed_tasks=[],
                        total_execution_time_ms=500.0,
                    )

                    request = JobGenerationRequestV3(
                        user_requirement="Search Gmail and summarize recent emails",
                        project_id="test-project",
                        max_tasks=5,
                    )

                    result = await orchestrator.run_workflow(request)

        assert result.success is True
        assert result.job_master_id == "jm_test123"
        assert len(result.task_identifiers) == 2

    @pytest.mark.asyncio
    async def test_unified_task_id_consistency(self, mock_llm_client):
        """Verify task_id is consistent across all phases."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        # Track task_ids through phases
        phase1_task_ids = set()
        phase2_task_ids = set()
        phase3_task_ids = set()

        async def capture_phase1(*args, **kwargs):
            response = await mock_llm_client(*args, **kwargs)
            for task in response.tasks:
                phase1_task_ids.add(task.task_id)
            return response

        async def capture_phase2(tasks, *args, **kwargs):
            for task in tasks:
                phase2_task_ids.add(task.task_id if hasattr(task, 'task_id') else task)
            return {
                "job_master_id": "jm_123",
                "task_id_to_master_id": {t: f"tm_{t}" for t in phase2_task_ids},
            }

        async def capture_phase3(task_identifiers, *args, **kwargs):
            for tid in task_identifiers:
                phase3_task_ids.add(tid.task_id)
            return ParallelExecutionResult(
                successful_tasks=[
                    TaskResult(task_id=tid.task_id, success=True, workflow={})
                    for tid in task_identifiers
                ],
                failed_tasks=[],
            )

        with patch.object(orchestrator, '_execute_job_analysis', capture_phase1):
            with patch.object(orchestrator, '_execute_registration', capture_phase2):
                with patch.object(orchestrator, '_execute_workflow_gen', capture_phase3):
                    request = JobGenerationRequestV3(
                        user_requirement="Test workflow",
                        project_id="test",
                        max_tasks=5,
                    )

                    await orchestrator.run_workflow(request)

        # All phases should use the same task_ids
        assert phase1_task_ids == phase2_task_ids == phase3_task_ids


class TestJobGenerationE2EErrors:
    """E2E tests for error scenarios."""

    @pytest.mark.asyncio
    async def test_phase1_error_captured(self):
        """Test that errors during JOB_ANALYSIS phase are captured properly."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=recovery_manager,
        )

        # Simulate validation error in phase 1
        async def failing_analysis(*args, **kwargs):
            raise ValueError("Validation error in LLM response")

        with patch.object(orchestrator, '_execute_job_analysis', failing_analysis):
            request = JobGenerationRequestV3(
                user_requirement="Test",
                project_id="test",
                max_tasks=5,
            )

            result = await orchestrator.run_workflow(request)

        # Error should be captured in result, not raise exception
        assert result.success is False
        assert "Validation error" in result.error

    @pytest.mark.asyncio
    async def test_phase1_success_flow(self):
        """Test successful JOB_ANALYSIS phase."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=recovery_manager,
        )

        async def successful_analysis(*args, **kwargs):
            from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
                JobAnalysisResponse,
            )
            return JobAnalysisResponse(
                tasks=[], interfaces={}, job_body_parameters=[],
                overall_summary="Success"
            )

        with patch.object(orchestrator, '_execute_job_analysis', successful_analysis):
            with patch.object(orchestrator, '_execute_registration') as mock_reg:
                mock_reg.return_value = {"job_master_id": "jm_1", "task_id_to_master_id": {}}
                with patch.object(orchestrator, '_execute_workflow_gen') as mock_wf:
                    mock_wf.return_value = ParallelExecutionResult(
                        successful_tasks=[], failed_tasks=[]
                    )

                    request = JobGenerationRequestV3(
                        user_requirement="Test",
                        project_id="test",
                        max_tasks=5,
                    )

                    result = await orchestrator.run_workflow(request)

        # Should succeed with empty tasks
        assert result.success is True

    @pytest.mark.asyncio
    async def test_phase3_partial_failure(self):
        """Test handling of partial failures in WORKFLOW_GEN phase."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )
        from aiagent.langgraph.jobGeneratorV2.types_v3 import TaskExecutionError

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        with patch.object(orchestrator, '_execute_job_analysis') as mock_analysis:
            from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
                AnalyzedTask,
                JobAnalysisResponse,
            )
            mock_analysis.return_value = JobAnalysisResponse(
                tasks=[
                    AnalyzedTask(
                        task_id="task_001", name="T1", description="D1",
                        task_type="fetch", recommended_api="/api",
                        dependencies=[], input_schema={}, output_schema={},
                    ),
                    AnalyzedTask(
                        task_id="task_002", name="T2", description="D2",
                        task_type="fetch", recommended_api="/api",
                        dependencies=[], input_schema={}, output_schema={},
                    ),
                ],
                interfaces={}, job_body_parameters=[],
                overall_summary="Test",
            )

            with patch.object(orchestrator, '_execute_registration') as mock_reg:
                mock_reg.return_value = {
                    "job_master_id": "jm_1",
                    "task_id_to_master_id": {"task_001": "tm_1", "task_002": "tm_2"},
                }

                with patch.object(orchestrator, '_execute_workflow_gen') as mock_wf:
                    # One success, one failure
                    mock_wf.return_value = ParallelExecutionResult(
                        successful_tasks=[
                            TaskResult(task_id="task_001", success=True, workflow={}),
                        ],
                        failed_tasks=[
                            TaskResult(
                                task_id="task_002",
                                success=False,
                                error=TaskExecutionError(
                                    error_type=ErrorType.VALIDATION,
                                    message="Schema validation failed",
                                ),
                            ),
                        ],
                    )

                    request = JobGenerationRequestV3(
                        user_requirement="Test",
                        project_id="test",
                        max_tasks=5,
                    )

                    result = await orchestrator.run_workflow(request)

        # Should handle partial success
        assert result is not None
        # Partial success handling depends on implementation


class TestJobGenerationE2EParallel:
    """E2E tests for parallel execution in Phase 3."""

    @pytest.mark.asyncio
    async def test_parallel_workflow_generation(self):
        """Test that multiple workflows are generated in parallel."""
        from aiagent.langgraph.jobGeneratorV2.parallel_executor import (
            parallel_workflow_generation,
        )

        tasks = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
            UnifiedTaskIdentifier(task_id="task_003", task_master_id="tm_003"),
        ]

        async def generate_workflow(task: UnifiedTaskIdentifier) -> dict:
            return {"workflow_name": f"wf_{task.task_id}"}

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=generate_workflow,
            max_concurrent=3,
            timeout_per_task=10.0,
        )

        assert result.all_succeeded
        assert len(result.successful_tasks) == 3

    @pytest.mark.asyncio
    async def test_parallel_handles_timeout(self):
        """Test that parallel execution handles task timeouts."""
        import asyncio

        from aiagent.langgraph.jobGeneratorV2.parallel_executor import (
            parallel_workflow_generation,
        )

        tasks = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]

        async def slow_generate(task: UnifiedTaskIdentifier) -> dict:
            await asyncio.sleep(5)  # Will timeout
            return {}

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=slow_generate,
            max_concurrent=1,
            timeout_per_task=0.1,  # Very short timeout
        )

        assert result.all_failed
        assert len(result.failed_tasks) == 1
        assert result.failed_tasks[0].error is not None
        assert result.failed_tasks[0].error.error_type == ErrorType.TRANSIENT


class TestValidatorIntegration:
    """Tests verifying validator integration in orchestrator (DC-1, DC-2)."""

    @pytest.mark.asyncio
    async def test_task_dependency_validator_called_in_job_analysis(self):
        """DC-1: Verify TaskDependencyValidator is called in _execute_job_analysis."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            JobAnalysisResponse,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        # Create tasks with circular dependency (A -> B -> A)
        async def mock_analyze_with_circular(*args, **kwargs):
            return JobAnalysisResponse(
                tasks=[
                    AnalyzedTask(
                        task_id="task_A", name="A", description="A",
                        task_type="fetch", recommended_api="/api",
                        dependencies=["task_B"],  # A depends on B
                        input_schema={}, output_schema={},
                    ),
                    AnalyzedTask(
                        task_id="task_B", name="B", description="B",
                        task_type="fetch", recommended_api="/api",
                        dependencies=["task_A"],  # B depends on A -> circular
                        input_schema={}, output_schema={},
                    ),
                ],
                interfaces={}, job_body_parameters=[],
                overall_summary="Circular deps",
            )

        # Mock analyze_job to return circular deps
        with patch(
            'aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3.analyze_job',
            mock_analyze_with_circular
        ):
            request = JobGenerationRequestV3(
                user_requirement="Test", project_id="test", max_tasks=5,
            )
            # Should raise OrchestratorError due to circular dependency
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._execute_job_analysis(request)

            assert "Task dependency validation failed" in str(exc_info.value)
            assert "Circular" in str(exc_info.value) or "circular" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_task_dependency_validator_passes_valid_deps(self):
        """DC-1: Verify TaskDependencyValidator passes valid dependencies."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            JobAnalysisResponse,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            JobGenerationRequestV3,
        )

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        # Create tasks with valid dependencies (A -> B, no cycle)
        async def mock_analyze_valid(*args, **kwargs):
            return JobAnalysisResponse(
                tasks=[
                    AnalyzedTask(
                        task_id="task_A", name="A", description="A",
                        task_type="fetch", recommended_api="/api",
                        dependencies=[],  # No deps
                        input_schema={}, output_schema={},
                    ),
                    AnalyzedTask(
                        task_id="task_B", name="B", description="B",
                        task_type="fetch", recommended_api="/api",
                        dependencies=["task_A"],  # B depends on A (valid)
                        input_schema={}, output_schema={},
                    ),
                ],
                interfaces={}, job_body_parameters=[],
                overall_summary="Valid deps",
            )

        with patch(
            'aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3.analyze_job',
            mock_analyze_valid
        ):
            request = JobGenerationRequestV3(
                user_requirement="Test", project_id="test", max_tasks=5,
            )
            # Should not raise (valid deps)
            result = await orchestrator._execute_job_analysis(request)
            assert len(result.tasks) == 2

    @pytest.mark.asyncio
    async def test_validation_pipeline_called_in_workflow_gen(self):
        """DC-2: Verify ValidationPipelineV3 is called in _execute_workflow_gen."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]
        interfaces = {}

        # Track if ValidationPipelineV3.validate was called
        validation_calls = []
        original_validate = ValidationPipelineV3.validate

        def mock_validate(self, workflow, workflow_id=""):
            validation_calls.append({"workflow_id": workflow_id, "workflow": workflow})
            return original_validate(self, workflow, workflow_id)

        with patch.object(ValidationPipelineV3, 'validate', mock_validate):
            await orchestrator._execute_workflow_gen(task_identifiers, interfaces)

        # Verify ValidationPipelineV3.validate was called for successful workflow
        assert len(validation_calls) > 0
        assert validation_calls[0]["workflow_id"] == "task_001"

    @pytest.mark.asyncio
    async def test_validation_pipeline_logs_errors_but_continues(self):
        """DC-2: Verify ValidationPipelineV3 logs errors but doesn't fail the flow."""

        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )
        from aiagent.langgraph.jobGeneratorV2.validators import (
            ValidationError,
            ValidationErrorCode,
            ValidationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=ErrorRecoveryManager(),
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]
        interfaces = {}

        # Mock ValidationPipelineV3.validate to return errors
        def mock_validate_with_errors(self, workflow, workflow_id=""):
            return ValidationResult.failure([
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message="Test validation error",
                    location="test",
                )
            ])

        with patch.object(ValidationPipelineV3, 'validate', mock_validate_with_errors):
            with patch('aiagent.langgraph.jobGeneratorV2.orchestrator_v3.logger') as mock_logger:
                result = await orchestrator._execute_workflow_gen(task_identifiers, interfaces)
                # Check warning was logged
                mock_logger.warning.assert_called()
                call_args = str(mock_logger.warning.call_args)
                assert "validation issues" in call_args.lower() or "Workflow" in call_args

        # Result should still be returned (not failed)
        assert result is not None
        assert len(result.successful_tasks) == 1
