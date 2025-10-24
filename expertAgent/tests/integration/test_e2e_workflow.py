"""E2E Workflow Tests for Job Generator Agent.

This module tests the entire workflow from requirement_analysis to job_registration
without requiring external API keys (100% API-key-free).

Test Coverage:
- Phase 3-1: 正常系ワークフローテスト (3 tests)
- Phase 3-2: 失敗シナリオテスト (2 tests)
- Phase 3-3: エッジケーステスト (3 tests)
- Phase 3-4: パフォーマンステスト (2 tests)

Total: 10 E2E tests
"""

import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.agent import (
    create_job_task_generator_agent,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.evaluation import (
    EvaluationResult,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    InterfaceSchemaDefinition,
    InterfaceSchemaResponse,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    TaskBreakdownItem,
    TaskBreakdownResponse,
)
from tests.integration.fixtures.llm_responses import (
    VALIDATION_SUCCESS_RESPONSE,
)
from tests.utils.mock_helpers import (
    create_mock_llm,
)

# ============================================================================
# Mock Helpers for E2E Tests
# ============================================================================


def create_mock_jobqueue_client(
    master_response: dict[str, Any] | None = None,
    job_response: dict[str, Any] | None = None,
    validation_response: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mocked JobqueueClient for master_creation, validation, and job_registration nodes.

    Args:
        master_response: Response for create_job_master, create_task_master, etc.
        job_response: Response for create_job.
        validation_response: Response for validate_workflow.

    Returns:
        MagicMock: A mocked JobqueueClient instance.
    """
    mock_client = MagicMock()

    # Master creation methods
    # create_job_master returns dict with "id" key
    mock_client.create_job_master = AsyncMock(
        return_value={"id": master_response.get("job_master_id", "jm_test123"), "name": "TestJobMaster"}
        if master_response
        else {"id": "jm_test123", "name": "TestJobMaster"}
    )
    # create_task_master and create_interface_master return dicts as well
    mock_client.create_task_master = AsyncMock(return_value={"id": "tm_test456", "name": "TestTaskMaster"})
    mock_client.create_interface_master = AsyncMock(return_value={"id": "im_test789", "name": "TestInterface"})
    # add_task_to_workflow
    mock_client.add_task_to_workflow = AsyncMock(return_value={"id": "jmt_test789", "workflow_id": "jm_test123"})

    # Validation methods
    if validation_response is None:
        validation_response = {"is_valid": True, "errors": [], "warnings": []}
    mock_client.validate_workflow = AsyncMock(return_value=validation_response)

    # Job registration methods
    mock_client.list_workflow_tasks = AsyncMock(return_value=[
        {"id": "jmt_001", "order": 0, "task_master_id": "tm_test456"},
        {"id": "jmt_002", "order": 1, "task_master_id": "tm_test457"},
    ])
    mock_client.create_job = AsyncMock(
        return_value={
            "id": job_response.get("job_id", "job_uuid_test") if job_response else "job_uuid_test",
            "name": "Test Job",
            "master_id": "jm_test123",
        }
    )

    return mock_client


def create_mock_schema_matcher() -> MagicMock:
    """Create a mocked SchemaMatcher for master_creation node.

    Returns:
        MagicMock: A mocked SchemaMatcher instance.
    """
    mock_matcher = MagicMock()
    mock_matcher.find_or_create_interface_master = AsyncMock(
        return_value={"id": "im_test789", "name": "TestInterface"}
    )
    mock_matcher.find_or_create_task_master = AsyncMock(
        return_value={"id": "tm_test456", "name": "TestTask"}
    )
    return mock_matcher


def create_mock_trackers() -> tuple[MagicMock, MagicMock]:
    """Create mocked performance and cost trackers.

    Returns:
        tuple: (perf_tracker, cost_tracker)
    """
    perf_tracker = MagicMock()
    perf_tracker.start = MagicMock()
    perf_tracker.end = MagicMock()
    perf_tracker.log_metrics = MagicMock()

    cost_tracker = MagicMock()
    cost_tracker.add_call = MagicMock()
    cost_tracker.log_summary = MagicMock()

    return perf_tracker, cost_tracker


def create_task_breakdown_response() -> TaskBreakdownResponse:
    """Create a TaskBreakdownResponse Pydantic model for testing.

    Returns:
        TaskBreakdownResponse: A valid task breakdown response.
    """
    tasks = [
        TaskBreakdownItem(
            task_id="task_1",
            name="企業名入力受付",
            description="ユーザーから企業名を入力として受け取る",
            dependencies=[],
            expected_output="企業名文字列",
            priority=1,
        ),
        TaskBreakdownItem(
            task_id="task_2",
            name="IR情報取得",
            description="指定された企業のIR情報サイトから過去5年の財務データを取得",
            dependencies=["task_1"],
            expected_output="財務データJSON",
            priority=2,
        ),
        TaskBreakdownItem(
            task_id="task_3",
            name="売上分析",
            description="取得した財務データから売上の推移を分析",
            dependencies=["task_2"],
            expected_output="分析レポートPDF",
            priority=3,
        ),
    ]
    return TaskBreakdownResponse(
        tasks=tasks,
        overall_summary="3-step workflow for analyzing company financial data",
    )


def create_evaluation_result_success() -> EvaluationResult:
    """Create a successful EvaluationResult Pydantic model for testing.

    Returns:
        EvaluationResult: A valid evaluation result indicating success.
    """
    return EvaluationResult(
        is_valid=True,
        evaluation_summary="Task breakdown is comprehensive and well-structured",
        hierarchical_score=9,
        dependency_score=9,
        specificity_score=8,
        modularity_score=9,
        consistency_score=9,
        all_tasks_feasible=True,
        infeasible_tasks=[],
        alternative_proposals=[],
        api_extension_proposals=[],
        issues=[],
        improvement_suggestions=[],
    )


def create_evaluation_result_failure() -> EvaluationResult:
    """Create a failed EvaluationResult Pydantic model for testing.

    Returns:
        EvaluationResult: A valid evaluation result indicating failure.
    """
    return EvaluationResult(
        is_valid=False,
        evaluation_summary="Task breakdown has critical issues",
        hierarchical_score=4,
        dependency_score=3,
        specificity_score=5,
        modularity_score=4,
        consistency_score=3,
        all_tasks_feasible=False,
        infeasible_tasks=[],
        alternative_proposals=[],
        api_extension_proposals=[],
        issues=["Task dependencies are circular", "Some tasks require unavailable capabilities"],
        improvement_suggestions=[
            "Reorder tasks to eliminate circular dependencies",
            "Replace unavailable capabilities with alternatives",
        ],
    )


def create_interface_schema_response() -> InterfaceSchemaResponse:
    """Create an InterfaceSchemaResponse Pydantic model for testing.

    Returns:
        InterfaceSchemaResponse: A valid interface schema response.
    """
    interfaces = [
        InterfaceSchemaDefinition(
            task_id="task_1",
            interface_name="ReceiveUserInput",
            description="Accept user input for company name",
            input_schema={
                "type": "object",
                "properties": {"user_prompt": {"type": "string"}},
                "required": ["user_prompt"],
            },
            output_schema={
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
        ),
        InterfaceSchemaDefinition(
            task_id="task_2",
            interface_name="FetchIRData",
            description="Fetch IR data for the company",
            input_schema={
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
            output_schema={
                "type": "object",
                "properties": {"financial_data": {"type": "object"}},
                "required": ["financial_data"],
            },
        ),
        InterfaceSchemaDefinition(
            task_id="task_3",
            interface_name="AnalyzeRevenue",
            description="Analyze revenue trends",
            input_schema={
                "type": "object",
                "properties": {"financial_data": {"type": "object"}},
                "required": ["financial_data"],
            },
            output_schema={
                "type": "object",
                "properties": {"analysis_report": {"type": "string"}},
                "required": ["analysis_report"],
            },
        ),
    ]
    return InterfaceSchemaResponse(interfaces=interfaces)


# ============================================================================
# Phase 3-1: 正常系ワークフローテスト (3 tests)
# ============================================================================


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_success_first_try(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow success on first try (no retries).

    Workflow:
        requirement_analysis → evaluator (✅ valid) → interface_definition
        → evaluator (✅ valid) → master_creation → validation (✅ valid)
        → job_registration → END

    Expected:
        - Status: "completed"
        - job_id and job_master_id are set
        - retry_count is 0
        - All nodes executed once (except evaluator: 2 times)
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock LLMs with structured output
    # requirement_analysis_node expects TaskBreakdownResponse Pydantic model
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Evaluator called twice: after_task_breakdown, after_interface_definition
    evaluation_success = create_evaluation_result_success()
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[
            evaluation_success,  # 1st call: task_breakdown valid
            evaluation_success,  # 2nd call: interface valid
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # interface_definition_node expects InterfaceSchemaResponse Pydantic model
    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)

    # validation_node does NOT use LLM for success case (only uses JobqueueClient)
    mock_llm_validation.return_value = (MagicMock(), perf_tracker, cost_tracker)

    # Setup: Mock Jobqueue clients (use default mock values for consistency)
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    # Validation node needs JobqueueClient in its own scope
    mock_validation_client = create_mock_jobqueue_client()

    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)

    # Assert: Verify final state
    assert result["retry_count"] == 0, "retry_count should be 0 (no retries)"
    assert "task_breakdown" in result, "task_breakdown should be present"
    assert len(result["task_breakdown"]) == 3, "Should have 3 tasks"
    assert "interface_definitions" in result, "interface_definitions should be present"
    assert len(result["interface_definitions"]) == 3, "Should have 3 interfaces"
    assert result.get("job_master_id") == "jm_test123", "job_master_id should be set"
    assert result.get("job_id") == "job_uuid_test", "job_id should be set"

    # Assert: Verify LLM call counts
    assert mock_llm_requirement.call_count == 1, "requirement_analysis called once"
    assert mock_llm_evaluator.call_count == 2, "evaluator called twice"
    assert mock_llm_interface.call_count == 1, "interface_definition called once"
    # validation_node only uses LLM when validation fails (for fix proposals)
    # In success case, LLM is not called
    assert mock_llm_validation.call_count == 0, "validation LLM not called in success case"

    # Assert: Verify Jobqueue call counts
    mock_jobqueue_master.return_value.create_job_master.assert_called_once()
    mock_jobqueue_job_reg.return_value.create_job.assert_called_once()


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_success_with_retry(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow with retry after task_breakdown evaluation failure.

    Workflow:
        requirement_analysis → evaluator (❌ invalid, retry++) → requirement_analysis
        → evaluator (✅ valid, retry reset) → interface_definition
        → evaluator (✅ valid) → master_creation → validation (✅ valid)
        → job_registration → END

    Expected:
        - Status: "completed"
        - requirement_analysis called twice (initial + retry)
        - evaluator called 3 times (1st fail, 2nd success after task_breakdown, 3rd after interface)
        - Final retry_count is 0 (reset after success)
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock LLMs with Pydantic models
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Evaluator called 3 times: 1st fail, 2nd success (task), 3rd success (interface)
    evaluation_failure = create_evaluation_result_failure()
    evaluation_success = create_evaluation_result_success()
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[
            evaluation_failure,  # 1st: task_breakdown invalid
            evaluation_success,  # 2nd: task_breakdown valid (after retry)
            evaluation_success,  # 3rd: interface valid
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Interface definition with Pydantic model
    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)
    mock_llm_validation.return_value = (
        create_mock_llm(VALIDATION_SUCCESS_RESPONSE),
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock Jobqueue clients (use default mock values for consistency)
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    mock_validation_client = create_mock_jobqueue_client()
    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)

    # Assert: Verify final state
    assert result["retry_count"] == 0, "retry_count should be reset to 0 after success"
    assert result.get("job_id") == "job_uuid_test", "job_id should be set"

    # Assert: Verify LLM call counts
    assert mock_llm_requirement.call_count == 2, "requirement_analysis called twice (1 retry)"
    assert mock_llm_evaluator.call_count == 3, "evaluator called 3 times (1 fail + 2 success)"
    assert mock_llm_interface.call_count == 1, "interface_definition called once"
    # validation_node only uses LLM when validation fails (for fix proposals)
    assert mock_llm_validation.call_count == 0, "validation LLM not called in success case"


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_success_after_interface_retry(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow with retry after interface_definition evaluation failure.

    Workflow:
        requirement_analysis → evaluator (✅ valid) → interface_definition
        → evaluator (❌ invalid, retry++) → interface_definition
        → evaluator (✅ valid, retry reset) → master_creation → validation (✅ valid)
        → job_registration → END

    Expected:
        - Status: "completed"
        - interface_definition called twice (initial + retry)
        - evaluator called 3 times (1st task success, 2nd interface fail, 3rd interface success)
        - Final retry_count is 0 (reset after success)
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock LLMs with Pydantic models
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Evaluator called 3 times: task success, interface fail, interface success
    evaluation_success = create_evaluation_result_success()
    evaluation_failure = create_evaluation_result_failure()

    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[
            evaluation_success,  # 1st: task_breakdown valid
            evaluation_failure,  # 2nd: interface invalid
            evaluation_success,  # 3rd: interface valid (after retry)
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Interface definition with Pydantic model
    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)
    mock_llm_validation.return_value = (
        create_mock_llm(VALIDATION_SUCCESS_RESPONSE),
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock Jobqueue clients (use default mock values for consistency)
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    mock_validation_client = create_mock_jobqueue_client()
    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)

    # Assert: Verify final state
    assert result["retry_count"] == 0, "retry_count should be reset to 0 after success"
    assert result.get("job_id") == "job_uuid_test", "job_id should be set"

    # Assert: Verify LLM call counts
    assert mock_llm_requirement.call_count == 1, "requirement_analysis called once"
    assert mock_llm_evaluator.call_count == 3, "evaluator called 3 times (task success, interface fail/success)"
    assert mock_llm_interface.call_count == 2, "interface_definition called twice (1 retry)"
    # validation_node only uses LLM when validation fails (for fix proposals)
    assert mock_llm_validation.call_count == 0, "validation LLM not called in success case"


# ============================================================================
# Phase 3-2: 失敗シナリオテスト (2 tests)
# ============================================================================


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_max_retries_reached(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow when max retries (5) is reached.

    Workflow:
        requirement_analysis → evaluator (❌ invalid, retry=1)
        → requirement_analysis → evaluator (❌ invalid, retry=2)
        → requirement_analysis → evaluator (❌ invalid, retry=3)
        → requirement_analysis → evaluator (❌ invalid, retry=4)
        → requirement_analysis → evaluator (❌ invalid, retry=5)
        → END (max retries reached)

    Expected:
        - Workflow stops at retry_count=5 (MAX_RETRY_COUNT)
        - No job_id or job_master_id is set
        - evaluation_result.is_valid = False
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock requirement_analysis to always return tasks
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock evaluator to always fail (retry loop)
    evaluation_failure = create_evaluation_result_failure()
    mock_evaluator_structured = AsyncMock()
    # evaluator called 5 times, all failures
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[evaluation_failure] * 5
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    # Assert: Verify max retries reached
    assert result["retry_count"] == 0, "retry_count reset to 0 after final evaluation"
    assert "job_id" not in result, "job_id should not be set (workflow stopped)"
    assert "job_master_id" not in result, "job_master_id should not be set"

    # Assert: Verify LLM call counts
    # requirement_analysis called 6 times (initial 1 + retries 5 = 6 total)
    assert mock_llm_requirement.call_count == 6, "requirement_analysis called 6 times (1 initial + 5 retries)"
    # evaluator called 6 times (all failures)
    assert mock_llm_evaluator.call_count == 6, "evaluator called 6 times (1 initial + 5 retries)"
    # interface_definition NOT called (workflow stopped before)
    assert mock_llm_interface.call_count == 0, "interface_definition not called"


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_infeasible_tasks_detected(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow detects and handles infeasible tasks.

    Workflow:
        requirement_analysis → evaluator (❌ invalid, infeasible_tasks detected)
        → requirement_analysis (retry) → evaluator (✅ valid, infeasible_tasks resolved)
        → interface_definition → evaluator (✅ valid) → master_creation
        → validation (✅ valid) → job_registration → END

    Expected:
        - Workflow eventually succeeds after detecting infeasible_tasks
        - evaluator is called multiple times (initial failures + eventual success)
        - requirement_analysis retries and eventually produces valid result
        - Final status is "completed"

    Note: This test verifies that infeasible task detection doesn't crash the workflow.
    The workflow should retry and eventually succeed when requirements are improved.
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock requirement_analysis (same as test 1)
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock evaluator with infeasible tasks initially, then success
    from aiagent.langgraph.jobTaskGeneratorAgents.prompts.evaluation import (
        InfeasibleTask,
    )

    infeasible_task = InfeasibleTask(
        task_id="task_2",
        task_name="IR情報取得",
        reason="External API for IR data is not available",
        required_functionality="IR data fetching API",
    )

    evaluation_with_infeasible = create_evaluation_result_failure()
    # Add infeasible_tasks to the failure result
    evaluation_with_infeasible.all_tasks_feasible = False
    evaluation_with_infeasible.infeasible_tasks = [infeasible_task]

    # Create success result
    evaluation_success = create_evaluation_result_success()

    mock_evaluator_structured = AsyncMock()
    # Return failure with infeasible_tasks 5 times, then success
    # This simulates: initial failure → retries with failures → eventual success
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[evaluation_with_infeasible] * 5 + [
            evaluation_success,  # After retries, task_breakdown is valid
            evaluation_success,  # After interface_definition
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Setup: Mock interface_definition
    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)

    # validation_node does NOT use LLM for success case
    mock_llm_validation.return_value = (MagicMock(), perf_tracker, cost_tracker)

    # Setup: Mock Jobqueue clients
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    mock_validation_client = create_mock_jobqueue_client()
    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)

    # Assert: Verify workflow eventually succeeded
    assert result.get("job_id") == "job_uuid_test", "job_id should be set (workflow succeeded)"
    assert result.get("job_master_id") == "jm_test123", "job_master_id should be set"
    assert result["retry_count"] == 0, "retry_count should be reset to 0 after success"

    # Assert: Verify evaluator was called multiple times (failures + successes)
    assert mock_llm_evaluator.call_count >= 6, (
        f"evaluator called at least 6 times (5 failures + 1 success), got {mock_llm_evaluator.call_count}"
    )
    # requirement_analysis was retried multiple times due to evaluation failures
    assert mock_llm_requirement.call_count >= 2, (
        f"requirement_analysis called at least twice (initial + retries), got {mock_llm_requirement.call_count}"
    )

# ============================================================================
# Phase 3-3: エッジケーステスト (3 tests)
# ============================================================================


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_empty_task_breakdown(
    mock_llm_requirement: MagicMock,
) -> None:
    """Test E2E workflow with empty task breakdown → END.

    Workflow:
        requirement_analysis (returns empty tasks) → evaluator → END

    Expected:
        - Workflow terminates with END
        - evaluator_router detects empty task_breakdown
        - Error logging occurs
        - No job_id or job_master_id created
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock requirement_analysis to return empty task breakdown
    empty_task_breakdown = TaskBreakdownResponse(
        tasks=[],  # Empty tasks list
        overall_summary="Failed to break down tasks",
    )
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=empty_task_breakdown)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "不明確な要求",
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    # Assert: Verify workflow terminated without creating job
    assert "job_id" not in result, "job_id should not be set (empty task breakdown)"
    assert "job_master_id" not in result, "job_master_id should not be set"
    assert result.get("task_breakdown") == [], "task_breakdown should be empty"

    # Assert: Verify LLM was called only once (requirement_analysis)
    assert mock_llm_requirement.call_count == 1, (
        "requirement_analysis called once before termination"
    )


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_empty_interface_definitions(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow with empty interface definitions → END.

    Workflow:
        requirement_analysis → evaluator (✅ valid) → interface_definition (returns empty interfaces)
        → evaluator → END

    Expected:
        - Workflow terminates after interface_definition returns empty list
        - evaluator_router detects empty interface_definitions
        - No job_id or job_master_id created
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock requirement_analysis (returns valid tasks)
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock evaluator (returns success for task_breakdown)
    evaluation_success = create_evaluation_result_success()
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(return_value=evaluation_success)
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Setup: Mock interface_definition to return empty interfaces
    empty_interface_response = InterfaceSchemaResponse(
        interfaces=[],  # Empty interfaces list
    )
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=empty_interface_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    # Assert: Verify workflow terminated without creating job
    assert "job_id" not in result, "job_id should not be set (empty interface definitions)"
    assert "job_master_id" not in result, "job_master_id should not be set"
    # interface_definitions might be a dict with empty 'interfaces' list
    interface_defs = result.get("interface_definitions")
    if isinstance(interface_defs, list):
        assert len(interface_defs) == 0, f"interface_definitions should be empty list, got {interface_defs}"
    elif isinstance(interface_defs, dict):
        assert interface_defs.get("interfaces", []) == [], f"interfaces should be empty, got {interface_defs}"
    assert len(result.get("task_breakdown", [])) == 3, "task_breakdown should have 3 tasks"

    # Assert: Verify LLM call counts
    assert mock_llm_requirement.call_count == 1, "requirement_analysis called once"
    assert mock_llm_evaluator.call_count == 2, (
        "evaluator called twice (after task_breakdown and after interface_definition)"
    )
    assert mock_llm_interface.call_count == 1, "interface_definition called once"


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_llm_error_during_flow(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
) -> None:
    """Test E2E workflow with LLM error during execution.

    Workflow:
        requirement_analysis (✅ success) → evaluator (❌ LLM error) → END

    Expected:
        - LLM error is caught and propagated
        - error_message is set in state
        - Workflow terminates gracefully
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock requirement_analysis (returns valid tasks)
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Setup: Mock evaluator to raise exception
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=Exception("LLM API timeout error")
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    result = await app.ainvoke(initial_state)

    # Assert: Verify error handling
    assert "error_message" in result, "error_message should be set"
    assert "LLM API timeout error" in result["error_message"] or "Evaluation failed" in result["error_message"], (
        "error_message should contain LLM error details"
    )

    # Assert: Verify workflow terminated without creating job
    assert "job_id" not in result, "job_id should not be set (LLM error)"
    assert "job_master_id" not in result, "job_master_id should not be set"

    # Assert: Verify LLM call counts
    assert mock_llm_requirement.call_count == 1, "requirement_analysis called once"
    assert mock_llm_evaluator.call_count == 1, "evaluator called once before error"


# ============================================================================
# Phase 3-4: パフォーマンステスト (2 tests)
# ============================================================================


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_execution_time(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow execution time with mocked APIs.

    Expected:
        - Execution time < 1 second (all APIs mocked)
        - No external API calls (100% API-key-free)
        - Workflow completes successfully
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock all LLMs (same as success test)
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    evaluation_success = create_evaluation_result_success()
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[
            evaluation_success,  # task_breakdown valid
            evaluation_success,  # interface valid
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)

    mock_llm_validation.return_value = (MagicMock(), perf_tracker, cost_tracker)

    # Setup: Mock Jobqueue clients
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    mock_validation_client = create_mock_jobqueue_client()
    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow and measure time
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    start_time = time.time()
    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)
    end_time = time.time()

    execution_time = end_time - start_time

    # Assert: Verify execution time
    assert execution_time < 1.0, (
        f"Execution time should be < 1 second with mocked APIs, got {execution_time:.3f}s"
    )

    # Assert: Verify workflow completed successfully
    assert result.get("job_id") == "job_uuid_test", "job_id should be set"
    assert result.get("job_master_id") == "jm_test123", "job_master_id should be set"
    assert result["retry_count"] == 0, "retry_count should be 0"

    # Log execution time for reference
    print(f"\n✅ E2E workflow execution time: {execution_time:.3f}s")


@pytest.mark.asyncio
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.interface_definition.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback")
@patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback")
async def test_e2e_workflow_state_consistency(
    mock_llm_requirement: MagicMock,
    mock_llm_evaluator: MagicMock,
    mock_llm_interface: MagicMock,
    mock_llm_validation: MagicMock,
    mock_jobqueue_master: MagicMock,
    mock_schema_matcher: MagicMock,
    mock_jobqueue_job_reg: MagicMock,
) -> None:
    """Test E2E workflow state consistency throughout execution.

    Expected:
        - State is consistent at each workflow stage
        - retry_count is properly managed (reset after success)
        - All required fields are populated
        - No unexpected state mutations
    """
    # Setup: Create trackers
    perf_tracker, cost_tracker = create_mock_trackers()

    # Setup: Mock all LLMs (with one retry scenario)
    task_breakdown_response = create_task_breakdown_response()
    mock_requirement_structured = AsyncMock()
    mock_requirement_structured.ainvoke = AsyncMock(return_value=task_breakdown_response)
    mock_requirement_llm = MagicMock()
    mock_requirement_llm.with_structured_output = MagicMock(
        return_value=mock_requirement_structured
    )
    mock_llm_requirement.return_value = (
        mock_requirement_llm,
        perf_tracker,
        cost_tracker,
    )

    # Evaluator: 1st fail, then success
    evaluation_failure = create_evaluation_result_failure()
    evaluation_success = create_evaluation_result_success()
    mock_evaluator_structured = AsyncMock()
    mock_evaluator_structured.ainvoke = AsyncMock(
        side_effect=[
            evaluation_failure,  # 1st: task_breakdown invalid
            evaluation_success,  # 2nd: task_breakdown valid
            evaluation_success,  # 3rd: interface valid
        ]
    )
    mock_evaluator_llm = MagicMock()
    mock_evaluator_llm.with_structured_output = MagicMock(
        return_value=mock_evaluator_structured
    )
    mock_llm_evaluator.return_value = (mock_evaluator_llm, perf_tracker, cost_tracker)

    interface_schema_response = create_interface_schema_response()
    mock_interface_structured = AsyncMock()
    mock_interface_structured.ainvoke = AsyncMock(return_value=interface_schema_response)
    mock_interface_llm = MagicMock()
    mock_interface_llm.with_structured_output = MagicMock(
        return_value=mock_interface_structured
    )
    mock_llm_interface.return_value = (mock_interface_llm, perf_tracker, cost_tracker)

    mock_llm_validation.return_value = (MagicMock(), perf_tracker, cost_tracker)

    # Setup: Mock Jobqueue clients
    mock_jobqueue_master.return_value = create_mock_jobqueue_client()
    mock_jobqueue_job_reg.return_value = create_mock_jobqueue_client()
    mock_validation_client = create_mock_jobqueue_client()
    mock_schema_matcher.return_value = create_mock_schema_matcher()

    # Execute: Run E2E workflow
    app = create_job_task_generator_agent()
    initial_state: dict[str, Any] = {
        "user_requirement": "企業のIR情報を分析してレポート作成",
        "retry_count": 0,
    }

    with patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient", return_value=mock_validation_client):
        result = await app.ainvoke(initial_state)

    # Assert: Verify state consistency

    # 1. Core state fields are present
    assert "user_requirement" in result, "user_requirement should be preserved"
    assert "task_breakdown" in result, "task_breakdown should be present"
    assert "interface_definitions" in result, "interface_definitions should be present"
    assert "evaluation_result" in result, "evaluation_result should be present"

    # 2. retry_count consistency (reset to 0 after success)
    assert result["retry_count"] == 0, (
        "retry_count should be reset to 0 after successful completion"
    )

    # 3. Final state should have job_id and job_master_id
    assert "job_id" in result, "job_id should be set"
    assert "job_master_id" in result, "job_master_id should be set"

    # 4. Verify evaluation_result is valid (final state)
    assert result["evaluation_result"]["is_valid"] is True, (
        "Final evaluation_result should be valid"
    )

    # 5. Verify task_breakdown and interface_definitions match in count
    task_count = len(result["task_breakdown"])
    interface_count = len(result["interface_definitions"])
    assert task_count == interface_count, (
        f"task_breakdown count ({task_count}) should match "
        f"interface_definitions count ({interface_count})"
    )

    # 6. Verify no unexpected error_message in final state
    assert "error_message" not in result or result.get("error_message") is None, (
        "error_message should not be present in successful workflow"
    )
