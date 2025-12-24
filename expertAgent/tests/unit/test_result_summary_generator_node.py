"""Unit tests for Result Summary Generator Node.

This module tests the Result Summary Generator node which creates
Markdown summaries of the validation and evaluation results.
"""

import pytest

from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def success_state() -> WorkflowGeneratorState:
    """Create a successful state for testing."""
    return {
        "task_master_id": "tm_01ABC123",
        "task_data": {
            "name": "Get company information",
            "description": "Retrieve company information from database",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"company_name": {"type": "string"}},
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"company_info": {"type": "object"}},
                },
            },
        },
        "max_retry": 3,
        "retry_count": 0,
        "yaml_content": "version: 0.5\nnodes:\n  source: {}\n",
        "workflow_name": "get_company_info",
        "sample_input": {"company_name": "Toyota Motor Corporation"},
        "test_http_status": 200,
        "test_execution_result": {
            "results": {
                "output": {"company_info": {"name": "Toyota"}, "status": "success"}
            },
            "errors": {},
            "logs": [],
        },
        "validation_result": {"is_valid": True, "issues": []},
        "validation_errors": [],
        "is_valid": True,
        "status": "validated",
        "max_test_data_regeneration": 2,
        "test_data_regeneration_count": 0,
        "needs_test_data_regeneration": False,
        "evaluation_score": 85,
        "llm_evaluation_result": {
            "overall_score": 85,
            "structural_score": 90,
            "requirement_score": 85,
            "output_quality_score": 80,
            "error_handling_score": 75,
            "test_data_quality_score": 85,
            "test_data_issues": [],
            "needs_test_data_regeneration": False,
            "suggested_test_data": None,
            "strengths": ["Good structure", "Uses recommended API"],
            "weaknesses": ["No retry logic"],
            "suggestions": ["Add error handling"],
            "is_acceptable": True,
            "failure_reason": "none",
            "confidence": 0.9,
        },
        "test_data_quality_score": 85,
        "test_data_issues": [],
    }


@pytest.fixture
def state_with_regeneration() -> WorkflowGeneratorState:
    """Create a state with test data regeneration history."""
    return {
        "task_master_id": "tm_01ABC123",
        "task_data": {
            "name": "Get company information",
            "description": "Retrieve company information from database",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"company_name": {"type": "string"}},
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {"company_info": {"type": "object"}},
                },
            },
        },
        "max_retry": 3,
        "retry_count": 1,
        "yaml_content": "version: 0.5\nnodes:\n  source: {}\n",
        "workflow_name": "get_company_info",
        "sample_input": {"company_name": "Toyota Motor Corporation"},
        "regenerated_sample_input": {"company_name": "Toyota Motor Corporation"},
        "test_http_status": 200,
        "test_execution_result": {
            "results": {
                "output": {"company_info": {"name": "Toyota"}, "status": "success"}
            },
            "errors": {},
            "logs": [],
        },
        "validation_result": {"is_valid": True, "issues": []},
        "validation_errors": [],
        "is_valid": True,
        "status": "validated",
        "max_test_data_regeneration": 2,
        "test_data_regeneration_count": 1,
        "needs_test_data_regeneration": False,
        "evaluation_score": 85,
        "llm_evaluation_result": {
            "overall_score": 85,
            "structural_score": 90,
            "requirement_score": 85,
            "output_quality_score": 80,
            "error_handling_score": 75,
            "test_data_quality_score": 85,
            "test_data_issues": [],
            "needs_test_data_regeneration": False,
            "suggested_test_data": None,
            "strengths": ["Good structure"],
            "weaknesses": [],
            "suggestions": [],
            "is_acceptable": True,
            "failure_reason": "none",
            "confidence": 0.9,
        },
        "test_data_quality_score": 85,
        "test_data_issues": [],
        "repair_history": [
            {
                "attempt": 1,
                "type": "test_data_regeneration",
                "previous_data": {"company_name": "sample_text"},
                "new_data": {"company_name": "Toyota Motor Corporation"},
                "issues": ["Non-realistic company name"],
            }
        ],
    }


class TestResultSummaryGeneratorNode:
    """Test result_summary_generator_node."""

    @pytest.mark.asyncio
    async def test_result_summary_success(self, success_state: WorkflowGeneratorState):
        """Test successful summary generation."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(success_state)

        assert result["validation_summary"] is not None
        assert result["summary_markdown"] is not None
        assert result["status"] == "success"
        assert "get_company_info" in result["summary_markdown"]

    @pytest.mark.asyncio
    async def test_result_summary_contains_scores(
        self, success_state: WorkflowGeneratorState
    ):
        """Test that summary contains evaluation scores."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(success_state)

        markdown = result["summary_markdown"]
        assert "85" in markdown  # Overall score
        assert "90" in markdown or "structural" in markdown.lower()  # Structural score

    @pytest.mark.asyncio
    async def test_result_summary_contains_test_data_info(
        self, state_with_regeneration: WorkflowGeneratorState
    ):
        """Test that summary contains test data regeneration information."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(state_with_regeneration)

        markdown = result["summary_markdown"]
        # Should contain info about regeneration
        assert "1" in markdown  # Regeneration count
        # Should mention test data
        assert "test" in markdown.lower() or "data" in markdown.lower()

    @pytest.mark.asyncio
    async def test_result_summary_overall_status_success(
        self, success_state: WorkflowGeneratorState
    ):
        """Test that overall_status is 'success' for valid workflow."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(success_state)

        summary = result["validation_summary"]
        assert summary["overall_status"] == "success"

    @pytest.mark.asyncio
    async def test_result_summary_overall_status_partial(
        self, state_with_regeneration: WorkflowGeneratorState
    ):
        """Test that overall_status is 'partial' for workflow with retries."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(state_with_regeneration)

        summary = result["validation_summary"]
        # Since there was regeneration, it might be partial
        assert summary["overall_status"] in ["success", "partial"]

    @pytest.mark.asyncio
    async def test_result_summary_markdown_format(
        self, success_state: WorkflowGeneratorState
    ):
        """Test that summary is valid Markdown format."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        result = await result_summary_generator_node(success_state)

        markdown = result["summary_markdown"]
        # Check for Markdown elements
        assert "#" in markdown  # Headers
        assert "|" in markdown  # Tables


class TestValidationSummaryModel:
    """Test ValidationSummary model."""

    def test_validation_summary_creation(self):
        """Test ValidationSummary model creation."""
        from aiagent.langgraph.workflowGeneratorAgents.models.summary import (
            LLMEvaluationSummary,
            RuleBasedValidationSummary,
            TestDataEvaluationSummary,
            ValidationSummary,
        )

        rule_based = RuleBasedValidationSummary(
            yaml_syntax_valid=True,
            http_status_valid=True,
            graphai_execution_valid=True,
            output_schema_valid=True,
            issues=[],
        )

        llm_eval = LLMEvaluationSummary(
            overall_score=85,
            structural_score=90,
            requirement_score=85,
            output_quality_score=80,
            error_handling_score=75,
            test_data_quality_score=85,
            strengths=["Good"],
            weaknesses=[],
            suggestions=[],
        )

        test_data_eval = TestDataEvaluationSummary(
            quality_score=85,
            source="auto_generated",
            issues=[],
            regeneration_history=[],
        )

        summary = ValidationSummary(
            task_master_id="tm_01ABC123",
            task_name="Get company info",
            workflow_name="get_company_info",
            generated_at="2024-12-24T10:00:00",
            overall_status="success",
            rule_based_validation=rule_based,
            llm_evaluation=llm_eval,
            test_data_evaluation=test_data_eval,
            final_score=85,
            recommended_actions=[],
            retry_count=0,
            max_retry=3,
            test_data_regeneration_count=0,
            max_test_data_regeneration=2,
        )

        assert summary.overall_status == "success"
        assert summary.final_score == 85
        assert summary.test_data_evaluation.quality_score == 85

    def test_validation_summary_overall_status_enum(self):
        """Test ValidationSummary overall_status values."""
        from aiagent.langgraph.workflowGeneratorAgents.models.summary import (
            LLMEvaluationSummary,
            RuleBasedValidationSummary,
            TestDataEvaluationSummary,
            ValidationSummary,
        )

        rule_based = RuleBasedValidationSummary(
            yaml_syntax_valid=True,
            http_status_valid=True,
            graphai_execution_valid=True,
            output_schema_valid=True,
            issues=[],
        )

        llm_eval = LLMEvaluationSummary(
            overall_score=85,
            structural_score=90,
            requirement_score=85,
            output_quality_score=80,
            error_handling_score=75,
            test_data_quality_score=85,
            strengths=[],
            weaknesses=[],
            suggestions=[],
        )

        test_data_eval = TestDataEvaluationSummary(
            quality_score=85,
            source="auto_generated",
            issues=[],
            regeneration_history=[],
        )

        # Test valid status values
        for status in ["success", "partial", "failed"]:
            summary = ValidationSummary(
                task_master_id="tm_01ABC123",
                task_name="Test",
                workflow_name="test",
                generated_at="2024-12-24T10:00:00",
                overall_status=status,
                rule_based_validation=rule_based,
                llm_evaluation=llm_eval,
                test_data_evaluation=test_data_eval,
                final_score=85,
                recommended_actions=[],
                retry_count=0,
                max_retry=3,
                test_data_regeneration_count=0,
                max_test_data_regeneration=2,
            )
            assert summary.overall_status == status

    def test_test_data_evaluation_summary_source_enum(self):
        """Test TestDataEvaluationSummary source values."""
        from aiagent.langgraph.workflowGeneratorAgents.models.summary import (
            TestDataEvaluationSummary,
        )

        # Test valid source values
        for source in ["auto_generated", "llm_regenerated"]:
            eval_summary = TestDataEvaluationSummary(
                quality_score=85,
                source=source,
                issues=[],
                regeneration_history=[],
            )
            assert eval_summary.source == source


class TestResultSummaryGeneratorHelpers:
    """Test helper functions in result_summary_generator."""

    @pytest.mark.asyncio
    async def test_result_summary_with_none_test_data_quality_score(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation when test_data_quality_score is None (covers line 106)."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_no_quality_score = {
            **success_state,
            "test_data_quality_score": None,  # Explicitly set to None
        }

        result = await result_summary_generator_node(state_no_quality_score)

        # Should default to 0 for the quality score
        summary = result["validation_summary"]
        assert summary["test_data_evaluation"]["quality_score"] == 0

    @pytest.mark.asyncio
    async def test_result_summary_overall_status_failed(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation when is_valid is False (covers line 132)."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_invalid = {
            **success_state,
            "is_valid": False,
            "retry_count": 0,
            "test_data_regeneration_count": 0,
        }

        result = await result_summary_generator_node(state_invalid)

        summary = result["validation_summary"]
        assert summary["overall_status"] == "failed"

    @pytest.mark.asyncio
    async def test_result_summary_with_validation_errors(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation with validation errors."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_with_errors = {
            **success_state,
            "validation_errors": ["yaml syntax error", "graphai node error", "output error"],
            "test_http_status": 500,
        }

        result = await result_summary_generator_node(state_with_errors)

        summary = result["validation_summary"]
        # Rule-based validation should reflect errors
        rb = summary["rule_based_validation"]
        assert rb["yaml_syntax_valid"] is False
        assert rb["http_status_valid"] is False
        assert rb["graphai_execution_valid"] is False
        assert rb["output_schema_valid"] is False

    @pytest.mark.asyncio
    async def test_result_summary_with_empty_llm_evaluation(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation with None llm_evaluation_result."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_no_llm_result = {
            **success_state,
            "llm_evaluation_result": None,
        }

        result = await result_summary_generator_node(state_no_llm_result)

        summary = result["validation_summary"]
        # Should use defaults (0) for scores
        llm_eval = summary["llm_evaluation"]
        assert llm_eval["overall_score"] == 0

    @pytest.mark.asyncio
    async def test_determine_overall_status_partial_with_retry(
        self, success_state: WorkflowGeneratorState
    ):
        """Test overall status is partial when retry_count > 0."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_with_retry = {
            **success_state,
            "is_valid": True,
            "retry_count": 1,
            "test_data_regeneration_count": 0,
        }

        result = await result_summary_generator_node(state_with_retry)

        summary = result["validation_summary"]
        assert summary["overall_status"] == "partial"

    @pytest.mark.asyncio
    async def test_determine_overall_status_partial_with_regen(
        self, success_state: WorkflowGeneratorState
    ):
        """Test overall status is partial when test_data_regeneration_count > 0."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_with_regen = {
            **success_state,
            "is_valid": True,
            "retry_count": 0,
            "test_data_regeneration_count": 1,
        }

        result = await result_summary_generator_node(state_with_regen)

        summary = result["validation_summary"]
        assert summary["overall_status"] == "partial"

    @pytest.mark.asyncio
    async def test_result_summary_with_empty_repair_history(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation with empty repair_history."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_empty_history = {
            **success_state,
            "repair_history": [],
            "test_data_regeneration_count": 1,  # Has regen count but no history entries
        }

        result = await result_summary_generator_node(state_empty_history)

        summary = result["validation_summary"]
        assert summary["test_data_evaluation"]["regeneration_history"] == []

    @pytest.mark.asyncio
    async def test_result_summary_with_mixed_repair_history(
        self, success_state: WorkflowGeneratorState
    ):
        """Test summary generation filters only test_data_regeneration entries."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.result_summary_generator import (
            result_summary_generator_node,
        )

        state_mixed_history = {
            **success_state,
            "repair_history": [
                {"type": "test_data_regeneration", "details": "regen1"},
                {"type": "workflow_repair", "details": "repair1"},  # Should be filtered out
                {"type": "test_data_regeneration", "details": "regen2"},
            ],
            "test_data_regeneration_count": 2,
        }

        result = await result_summary_generator_node(state_mixed_history)

        summary = result["validation_summary"]
        regen_history = summary["test_data_evaluation"]["regeneration_history"]
        # Should only have 2 test_data_regeneration entries
        assert len(regen_history) == 2
        for entry in regen_history:
            assert entry["type"] == "test_data_regeneration"
