"""Unit tests for evaluator_node.

These tests verify the evaluator node's behavior including:
- Valid task breakdown evaluation (all quality scores high)
- Invalid task breakdown (low quality scores)
- Infeasible tasks detection and proposals
- Alternative solutions using existing APIs
- API extension proposals
- Empty task breakdown error handling
- LLM error handling
- Retry count reset behavior
- Derived fields check for downstream tasks (Issue #337)

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import (
    check_derived_fields_for_downstream_tasks,
    evaluator_node,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.evaluation import (
    AlternativeProposal,
    APIExtensionProposal,
    APISpecificityCheckResult,
    EvaluationResult,
    InfeasibleTask,
)
from tests.utils.mock_helpers import (
    create_mock_task_breakdown,
    create_mock_workflow_state,
)


@pytest.mark.unit
class TestEvaluatorNode:
    """Unit tests for evaluator_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_valid_task_breakdown(self, mock_invoke_llm):
        """Test evaluation with valid task breakdown (high quality scores).

        Priority: High
        This is the happy path where all quality criteria are met.
        """
        # Create mock evaluation result (all valid)
        mock_eval_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="All quality criteria met. Tasks are well-structured and feasible.",
            hierarchical_score=9,
            dependency_score=9,
            specificity_score=9,
            modularity_score=8,
            consistency_score=9,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        # Create mock API specificity check result (all APIs are specific)
        mock_api_check_response = APISpecificityCheckResult(
            all_apis_specific=True,
            issues=[],
            summary="All APIs are properly specified.",
        )

        # Setup mock invoke_structured_llm with side_effect for two calls
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.side_effect = [
            # First call: evaluation
            StructuredCallResult(
                result=mock_eval_response,
                recovered_via_json=False,
                raw_text=None,
                model_name="test-model",
            ),
            # Second call: API specificity check
            StructuredCallResult(
                result=mock_api_check_response,
                recovered_via_json=False,
                raw_text=None,
                model_name="test-model",
            ),
        ]

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=2,  # Should be reset to 0
            user_requirement="Create a data analysis workflow",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify results
        assert "evaluation_result" in result
        assert result["evaluation_result"]["is_valid"] is True
        assert result["evaluation_result"]["hierarchical_score"] == 9
        assert result["evaluation_result"]["dependency_score"] == 9
        assert result["evaluation_result"]["all_tasks_feasible"] is True
        assert result["evaluation_result"]["all_apis_specific"] is True
        assert len(result["evaluation_result"]["infeasible_tasks"]) == 0

        # Verify retry_count is NOT modified by evaluator (it's managed by requirement_analysis/interface_definition)
        assert result["retry_count"] == 2, "evaluator should not modify retry_count"

        # evaluation_feedback should be None for valid results
        assert result.get("evaluation_feedback") is None

        # Verify invoke_structured_llm was called twice (eval + API specificity check)
        assert mock_invoke_llm.call_count == 2

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_invalid_with_low_scores(self, mock_invoke_llm):
        """Test evaluation with invalid task breakdown (low quality scores).

        Priority: High
        This tests when quality scores are below threshold.
        """
        # Create mock evaluation result (invalid - low scores)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Quality scores are below threshold. Tasks need improvement.",
            hierarchical_score=4,
            dependency_score=5,
            specificity_score=3,
            modularity_score=4,
            consistency_score=5,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[
                "Task descriptions are too vague",
                "Dependencies are not clearly defined",
            ],
            improvement_suggestions=[
                "Add more specific input/output definitions",
                "Clarify task dependencies",
            ],
        )

        # Setup mock invoke_structured_llm
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=1,
            user_requirement="Analyze sales data",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify results
        assert result["evaluation_result"]["is_valid"] is False
        assert result["evaluation_result"]["hierarchical_score"] == 4
        assert result["evaluation_result"]["specificity_score"] == 3
        assert len(result["evaluation_result"]["issues"]) == 2
        assert len(result["evaluation_result"]["improvement_suggestions"]) == 2

        # Verify evaluation_feedback is generated for invalid results
        assert "evaluation_feedback" in result
        assert result["evaluation_feedback"] is not None
        assert "品質スコア" in result["evaluation_feedback"]
        assert "改善提案" in result["evaluation_feedback"]

        # Verify retry_count is NOT modified by evaluator
        assert result["retry_count"] == 1

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_with_infeasible_tasks(self, mock_invoke_llm):
        """Test evaluation with infeasible tasks detected.

        Priority: High
        This tests when some tasks cannot be implemented with current APIs.
        """
        # Create mock infeasible tasks
        infeasible_task = InfeasibleTask(
            task_id="task_002",
            task_name="Send SMS notification",
            reason="SMS API is not available in current expertAgent capabilities",
            required_functionality="SMS sending capability via direct API",
        )

        # Create mock evaluation result (with infeasible tasks)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Some tasks are infeasible with current capabilities.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[infeasible_task],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=["task_002 (Send SMS notification) is not feasible"],
            improvement_suggestions=["Consider using email instead of SMS"],
        )

        # Setup mock invoke_structured_llm
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send notifications via SMS",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify infeasible tasks detection
        assert result["evaluation_result"]["is_valid"] is False
        assert result["evaluation_result"]["all_tasks_feasible"] is False
        assert len(result["evaluation_result"]["infeasible_tasks"]) == 1
        assert (
            result["evaluation_result"]["infeasible_tasks"][0]["task_id"] == "task_002"
        )
        assert (
            result["evaluation_result"]["infeasible_tasks"][0]["task_name"]
            == "Send SMS notification"
        )

        # Verify evaluation_feedback includes infeasible tasks
        assert "実現不可能なタスク" in result["evaluation_feedback"]
        assert "Send SMS notification" in result["evaluation_feedback"]

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_with_alternative_proposals(self, mock_invoke_llm):
        """Test evaluation with alternative proposals using existing APIs.

        Priority: Medium
        This tests when alternative solutions are proposed.
        """
        # Create mock alternative proposal
        alternative = AlternativeProposal(
            task_id="task_002",
            alternative_approach="Use Gmail API to send email instead of SMS",
            api_to_use="gmail_send_email",
            implementation_note="Use Gmail API to send email notifications instead of SMS",
        )

        # Create mock evaluation result (with alternatives)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Alternative approaches proposed using existing APIs.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[],
            alternative_proposals=[alternative],
            api_extension_proposals=[],
            issues=["SMS API not available"],
            improvement_suggestions=["Use email instead"],
        )

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send notifications",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify alternative proposals
        assert len(result["evaluation_result"]["alternative_proposals"]) == 1
        assert (
            result["evaluation_result"]["alternative_proposals"][0]["task_id"]
            == "task_002"
        )
        assert (
            result["evaluation_result"]["alternative_proposals"][0]["api_to_use"]
            == "gmail_send_email"
        )

        # Verify evaluation_feedback includes alternatives
        assert "代替案の提案" in result["evaluation_feedback"]
        assert "gmail_send_email" in result["evaluation_feedback"]

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_with_api_extension_proposals(self, mock_invoke_llm):
        """Test evaluation with API extension proposals.

        Priority: Medium
        This tests when new API features are proposed.
        """
        # Create mock API extension proposal
        api_extension = APIExtensionProposal(
            task_id="task_002",
            proposed_api_name="sms_send",
            functionality="Send SMS notifications to phone numbers",
            priority="high",
            rationale="Many users need SMS notifications for urgent alerts, which email cannot provide",
        )

        # Create mock evaluation result (with API extensions)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="API extensions proposed for missing functionality.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[api_extension],
            issues=["SMS functionality not available"],
            improvement_suggestions=["Add SMS API support"],
        )

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send SMS notifications",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify API extension proposals
        assert len(result["evaluation_result"]["api_extension_proposals"]) == 1
        assert (
            result["evaluation_result"]["api_extension_proposals"][0][
                "proposed_api_name"
            ]
            == "sms_send"
        )
        assert (
            result["evaluation_result"]["api_extension_proposals"][0]["priority"]
            == "high"
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_empty_task_breakdown(self, mock_invoke_llm):
        """Test error handling when task_breakdown is empty.

        Priority: Medium
        This tests edge case where no tasks are provided.
        """
        # Note: mock_invoke_llm won't be called due to empty check in evaluator_node

        # Create test state with empty task_breakdown
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Some requirement",
            task_breakdown=[],  # Empty
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Evaluation requires a task breakdown" in result["error_message"]
        assert result["evaluation_result"] is None

        # Verify LLM was NOT called (early return)
        mock_invoke_llm.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_llm_error(self, mock_invoke_llm):
        """Test error handling when LLM invocation fails.

        Priority: Medium
        This tests exception handling.
        """
        # Setup mock invoke_structured_llm to raise exception
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )

        mock_invoke_llm.side_effect = StructuredLLMError("LLM API timeout")

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Analyze data",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "LLM API timeout" in result["error_message"]

        # evaluation_result should not be in result
        assert "evaluation_result" not in result

        # Verify invoke_structured_llm was called
        mock_invoke_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_retry_count_reset(self, mock_invoke_llm):
        """Test that retry_count is always reset to 0 after evaluation.

        Priority: Low
        This verifies the retry_count reset behavior.
        """
        # Create mock evaluation result
        mock_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="Valid",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=8,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Test Case 1: retry_count=3 should NOT be modified by evaluator
        task_breakdown = create_mock_task_breakdown(2)
        state = create_mock_workflow_state(
            retry_count=3,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await evaluator_node(state)
        assert result["retry_count"] == 3, "evaluator should not modify retry_count"

        # Test Case 2: retry_count=0 should remain 0
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await evaluator_node(state)
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_evaluator_skips_api_specificity_check_at_max_retry(
        self, mock_invoke_llm
    ):
        """Test that API specificity check is skipped at max retry count.

        Priority: High
        When retry_count >= MAX_RETRY_COUNT (5), the evaluator should skip
        the API specificity check to allow graceful degradation.
        If is_valid and all_tasks_feasible are True, the workflow can proceed
        even with abstract API names.
        """
        # Create mock evaluation result (valid)
        mock_eval_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="Valid task breakdown.",
            hierarchical_score=9,
            dependency_score=9,
            specificity_score=8,
            modularity_score=8,
            consistency_score=9,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        # Setup mock invoke_structured_llm - only one call expected (no API specificity check)
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_eval_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state with retry_count at MAX_RETRY_COUNT (5)
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=5,  # MAX_RETRY_COUNT
            user_requirement="Create podcast workflow",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify results
        assert "evaluation_result" in result
        assert result["evaluation_result"]["is_valid"] is True
        assert result["evaluation_result"]["all_tasks_feasible"] is True
        # At max retry, all_apis_specific should be True (skipped check)
        assert result["evaluation_result"]["all_apis_specific"] is True

        # Verify invoke_structured_llm was called only ONCE (no API specificity check)
        # This proves the API specificity check was skipped
        assert mock_invoke_llm.call_count == 1

        # No evaluation feedback should be generated for valid result
        assert result.get("evaluation_feedback") is None


@pytest.mark.unit
class TestCheckDerivedFieldsForDownstreamTasks:
    """Unit tests for check_derived_fields_for_downstream_tasks function.

    Issue #337: Ready-to-Use Output principle - ensure derived_fields
    are defined for downstream tasks that need them.
    """

    def test_no_email_task(self) -> None:
        """Test with tasks that don't require derived_fields."""
        tasks = [
            {"task_id": "search", "task_type": "search", "task_name": "Google Search"},
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
        ]
        interfaces: dict = {}

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert issues == []

    def test_email_task_with_missing_derived_fields(self) -> None:
        """Test that missing email derived_fields are detected."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "send_email",
                "task_type": "email_send",
                "task_name": "Send Email",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    # Missing x-derived-fields!
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert len(issues) == 2
        assert any("email_subject" in issue for issue in issues)
        assert any("email_body" in issue for issue in issues)
        assert any("Summarize" in issue for issue in issues)

    def test_email_task_with_complete_derived_fields(self) -> None:
        """Test that properly defined derived_fields pass validation."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "send_email",
                "task_type": "email_send",
                "task_name": "Send Email",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    "x-derived-fields": {
                        "email_subject": {"template": "Summary: {query}"},
                        "email_body": {"template": "{summary}"},
                    },
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert issues == []

    def test_email_task_with_partial_derived_fields(self) -> None:
        """Test that partial derived_fields are detected."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "send_email",
                "task_type": "email_send",
                "task_name": "Send Email",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    "x-derived-fields": {
                        "email_subject": {"template": "Summary: {query}"},
                        # Missing email_body!
                    },
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert len(issues) == 1
        assert "email_body" in issues[0]

    def test_mail_task_type_variation(self) -> None:
        """Test that 'mail' in task_type is also detected."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "send_mail",
                "task_type": "gmail_send",
                "task_name": "Send Mail",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert len(issues) == 2

    def test_slack_task_with_missing_derived_fields(self) -> None:
        """Test that missing Slack derived_fields are detected."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "notify_slack",
                "task_type": "slack_notification",
                "task_name": "Slack Notify",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert len(issues) == 1
        assert "slack" in issues[0].lower()

    def test_slack_task_with_slack_message(self) -> None:
        """Test that slack_message alone satisfies Slack requirement."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "notify_slack",
                "task_type": "slack_notification",
                "task_name": "Slack Notify",
            },
        ]
        interfaces = {
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    "x-derived-fields": {
                        "slack_message": {"template": "{summary}"},
                    },
                }
            }
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert issues == []

    def test_first_task_is_email(self) -> None:
        """Test that first task being email doesn't cause issues."""
        tasks = [
            {
                "task_id": "send_email",
                "task_type": "email_send",
                "task_name": "Send Email",
            },
        ]
        interfaces: dict = {}

        # First task has no preceding task, so no derived_fields needed
        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert issues == []

    def test_multiple_email_tasks(self) -> None:
        """Test chain with multiple email tasks."""
        tasks = [
            {"task_id": "search", "task_type": "search", "task_name": "Search"},
            {"task_id": "email1", "task_type": "email_send", "task_name": "Email 1"},
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {"task_id": "email2", "task_type": "email_send", "task_name": "Email 2"},
        ]
        interfaces = {
            "search": {
                "output_schema": {
                    "properties": {"results": {"type": "array"}},
                    # Missing derived_fields for email1
                }
            },
            "summarize": {
                "output_schema": {
                    "properties": {"summary": {"type": "string"}},
                    "x-derived-fields": {
                        "email_subject": {"template": "Summary"},
                        "email_body": {"template": "{summary}"},
                    },
                }
            },
        }

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        # Only email1's preceding task (search) is missing derived_fields
        assert len(issues) == 2
        assert any("Search" in issue for issue in issues)
        assert not any("Summarize" in issue for issue in issues)

    def test_empty_tasks_list(self) -> None:
        """Test with empty tasks list."""
        issues = check_derived_fields_for_downstream_tasks([], {})
        assert issues == []

    def test_missing_interface_for_task(self) -> None:
        """Test when interface definition is missing for a task."""
        tasks = [
            {
                "task_id": "summarize",
                "task_type": "summarization",
                "task_name": "Summarize",
            },
            {
                "task_id": "send_email",
                "task_type": "email_send",
                "task_name": "Send Email",
            },
        ]
        interfaces: dict = {}  # No interfaces defined

        issues = check_derived_fields_for_downstream_tasks(tasks, interfaces)
        assert len(issues) == 2  # Both email_subject and email_body missing
