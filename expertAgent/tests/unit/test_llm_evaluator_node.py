"""Unit tests for LLM Evaluator Node.

This module tests the LLM Evaluator node which performs semantic evaluation
of generated workflows including test data quality assessment.
"""

from typing import Any
from unittest.mock import patch

import pytest

from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def base_state() -> WorkflowGeneratorState:
    """Create base state for testing."""
    return {
        "task_master_id": "tm_01ABC123",
        "task_data": {
            "name": "Get company information",
            "description": "Retrieve company information from database",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Company name to search",
                        },
                    },
                    "required": ["company_name"],
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "company_info": {"type": "object"},
                        "status": {"type": "string"},
                    },
                    "required": ["company_info", "status"],
                },
            },
            "recommended_apis": ["company_search_api"],
        },
        "max_retry": 3,
        "retry_count": 0,
        "yaml_content": """version: 0.5
nodes:
  source: {}
  fetch_company:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/api/v1/company/search
      method: POST
      body:
        query: :source.company_name
    timeout: 60000
  output:
    agent: copyAgent
    inputs:
      result:
        company_info: :fetch_company.data
        status: "success"
    isResult: true
""",
        "workflow_name": "get_company_info",
        "sample_input": {"company_name": "Toyota Motor Corporation"},
        "test_http_status": 200,
        "test_execution_result": {
            "results": {
                "output": {
                    "company_info": {"name": "Toyota", "industry": "Automotive"},
                    "status": "success",
                }
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
    }


@pytest.fixture
def low_quality_test_data_state(
    base_state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Create state with low-quality test data."""
    return {
        **base_state,
        "sample_input": {"company_name": "sample_text"},  # Low quality test data
    }


@pytest.fixture
def mock_evaluation_result() -> dict[str, Any]:
    """Create mock LLM evaluation result."""
    return {
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
    }


@pytest.fixture
def mock_low_test_data_quality_result() -> dict[str, Any]:
    """Create mock LLM evaluation result with low test data quality."""
    return {
        "overall_score": 60,
        "structural_score": 85,
        "requirement_score": 80,
        "output_quality_score": 70,
        "error_handling_score": 70,
        "test_data_quality_score": 30,  # Low score
        "test_data_issues": [
            "Test data uses placeholder 'sample_text' instead of realistic company name",
            "Test data does not represent actual business scenario",
        ],
        "needs_test_data_regeneration": True,
        "suggested_test_data": {"company_name": "Toyota Motor Corporation"},
        "strengths": ["Good structure"],
        "weaknesses": ["Low quality test data"],
        "suggestions": ["Use realistic company names"],
        "is_acceptable": False,
        "failure_reason": "test_data_quality",
        "confidence": 0.85,
    }


class TestLLMEvaluatorNode:
    """Test llm_evaluator_node."""

    @pytest.mark.asyncio
    async def test_llm_evaluator_high_score(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test LLM evaluator with high-quality workflow and test data."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(base_state)

            assert result["evaluation_score"] == 85
            assert result["llm_evaluation_result"] is not None
            assert result["is_valid"] is True
            assert result["needs_test_data_regeneration"] is False
            assert result["test_data_quality_score"] == 85

    @pytest.mark.asyncio
    async def test_llm_evaluator_low_score(self, base_state: WorkflowGeneratorState):
        """Test LLM evaluator with low-quality workflow."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        low_score_result = {
            "overall_score": 50,
            "structural_score": 60,
            "requirement_score": 45,
            "output_quality_score": 50,
            "error_handling_score": 40,
            "test_data_quality_score": 60,
            "test_data_issues": [],
            "needs_test_data_regeneration": False,
            "suggested_test_data": None,
            "strengths": [],
            "weaknesses": ["Poor structure", "Missing requirements"],
            "suggestions": ["Restructure workflow"],
            "is_acceptable": False,
            "failure_reason": "workflow_quality",
            "confidence": 0.8,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**low_score_result)

            result = await llm_evaluator_node(base_state)

            assert result["evaluation_score"] == 50
            assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_llm_evaluator_low_test_data_quality(
        self,
        low_quality_test_data_state: WorkflowGeneratorState,
        mock_low_test_data_quality_result: dict[str, Any],
    ):
        """Test LLM evaluator detecting low-quality test data."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(
                **mock_low_test_data_quality_result
            )

            result = await llm_evaluator_node(low_quality_test_data_state)

            assert result["test_data_quality_score"] == 30
            assert result["needs_test_data_regeneration"] is True
            assert (
                result["test_data_issues"]
                == mock_low_test_data_quality_result["test_data_issues"]
            )
            assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_llm_evaluator_timeout_fallback(
        self, base_state: WorkflowGeneratorState
    ):
        """Test LLM evaluator fallback on timeout."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = None  # Simulate timeout

            result = await llm_evaluator_node(base_state)

            # Should use fallback evaluation
            assert result["llm_evaluation_result"] is not None
            assert result["evaluation_score"] is not None
            # Fallback should be conservative
            assert result["evaluation_score"] >= 0

    @pytest.mark.asyncio
    async def test_llm_evaluator_invalid_response_fallback(
        self, base_state: WorkflowGeneratorState
    ):
        """Test LLM evaluator fallback on invalid LLM response."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.side_effect = ValueError("Invalid JSON response")

            result = await llm_evaluator_node(base_state)

            # Should use fallback evaluation
            assert result["llm_evaluation_result"] is not None
            assert "error_feedback" in result or "evaluation_score" in result

    @pytest.mark.asyncio
    async def test_llm_evaluator_max_regeneration_reached(
        self,
        base_state: WorkflowGeneratorState,
        mock_low_test_data_quality_result: dict[str, Any],
    ):
        """Test that needs_test_data_regeneration is False when max count reached."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_max_regen = {
            **base_state,
            "test_data_regeneration_count": 2,  # Already at max
            "max_test_data_regeneration": 2,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(
                **mock_low_test_data_quality_result
            )

            result = await llm_evaluator_node(state_max_regen)

            # Even if LLM says regeneration needed, should be False due to max count
            assert result["needs_test_data_regeneration"] is False


class TestLLMEvaluationResult:
    """Test LLMEvaluationResult model."""

    def test_evaluation_result_validation(self):
        """Test LLMEvaluationResult field validation."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )

        # Valid result
        result = LLMEvaluationResult(
            overall_score=85,
            structural_score=90,
            requirement_score=85,
            output_quality_score=80,
            error_handling_score=75,
            test_data_quality_score=85,
            test_data_issues=[],
            needs_test_data_regeneration=False,
            suggested_test_data=None,
            strengths=["Good"],
            weaknesses=[],
            suggestions=[],
            is_acceptable=True,
            failure_reason="none",
            confidence=0.9,
        )

        assert result.overall_score == 85
        assert result.is_acceptable is True

    def test_evaluation_result_score_bounds(self):
        """Test LLMEvaluationResult score bounds validation."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )

        # Score below 0 should raise error
        with pytest.raises(ValueError):
            LLMEvaluationResult(
                overall_score=-1,
                structural_score=90,
                requirement_score=85,
                output_quality_score=80,
                error_handling_score=75,
                test_data_quality_score=85,
                test_data_issues=[],
                needs_test_data_regeneration=False,
                suggested_test_data=None,
                strengths=[],
                weaknesses=[],
                suggestions=[],
                is_acceptable=False,
                failure_reason="none",
                confidence=0.5,
            )

        # Score above 100 should raise error
        with pytest.raises(ValueError):
            LLMEvaluationResult(
                overall_score=101,
                structural_score=90,
                requirement_score=85,
                output_quality_score=80,
                error_handling_score=75,
                test_data_quality_score=85,
                test_data_issues=[],
                needs_test_data_regeneration=False,
                suggested_test_data=None,
                strengths=[],
                weaknesses=[],
                suggestions=[],
                is_acceptable=False,
                failure_reason="none",
                confidence=0.5,
            )

    def test_evaluation_result_failure_reason_enum(self):
        """Test LLMEvaluationResult failure_reason validation."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )

        # Valid failure reasons
        for reason in ["none", "workflow_quality", "test_data_quality", "both"]:
            result = LLMEvaluationResult(
                overall_score=50,
                structural_score=50,
                requirement_score=50,
                output_quality_score=50,
                error_handling_score=50,
                test_data_quality_score=50,
                test_data_issues=[],
                needs_test_data_regeneration=False,
                suggested_test_data=None,
                strengths=[],
                weaknesses=[],
                suggestions=[],
                is_acceptable=False,
                failure_reason=reason,
                confidence=0.5,
            )
            assert result.failure_reason == reason


class TestLLMEvaluatorSampleInputConversion:
    """Test sample input conversion in llm_evaluator_node."""

    @pytest.mark.asyncio
    async def test_llm_evaluator_with_none_sample_input(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test LLM evaluator with None sample input."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_none_input = {
            **base_state,
            "sample_input": None,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(state_none_input)

            mock_call.assert_called_once()
            assert result["evaluation_score"] == 85

    @pytest.mark.asyncio
    async def test_llm_evaluator_with_string_sample_input(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test LLM evaluator with string sample input (non-dict)."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_string_input = {
            **base_state,
            "sample_input": "just a string value",
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(state_string_input)

            mock_call.assert_called_once()
            assert result["evaluation_score"] == 85

    @pytest.mark.asyncio
    async def test_llm_evaluator_with_int_sample_input(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test LLM evaluator with integer sample input (non-dict)."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_int_input = {
            **base_state,
            "sample_input": 42,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(state_int_input)

            mock_call.assert_called_once()
            assert result["evaluation_score"] == 85

    @pytest.mark.asyncio
    async def test_llm_evaluator_with_list_sample_input(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test LLM evaluator with list sample input (non-dict)."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_list_input = {
            **base_state,
            "sample_input": [1, 2, 3],
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(state_list_input)

            mock_call.assert_called_once()
            assert result["evaluation_score"] == 85


class TestFallbackEvaluation:
    """Test fallback evaluation creation."""

    @pytest.mark.asyncio
    async def test_fallback_evaluation_with_invalid_state(
        self, base_state: WorkflowGeneratorState
    ):
        """Test fallback evaluation when state is_valid is False."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        state_invalid = {
            **base_state,
            "is_valid": False,
            "validation_errors": ["Error 1", "Error 2", "Error 3", "Error 4"],
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = None  # Force fallback

            result = await llm_evaluator_node(state_invalid)

            # Fallback should have lower scores for invalid state
            assert result["evaluation_score"] == 40  # Base score for invalid
            assert result["llm_evaluation_result"]["evaluation_model"] == "fallback"
            # Only first 3 errors should be in weaknesses
            assert len(result["llm_evaluation_result"]["weaknesses"]) <= 3

    @pytest.mark.asyncio
    async def test_fallback_evaluation_with_valid_state(
        self, base_state: WorkflowGeneratorState
    ):
        """Test fallback evaluation when state is_valid is True."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = None  # Force fallback

            result = await llm_evaluator_node(base_state)

            # Fallback should have higher scores for valid state
            assert result["evaluation_score"] == 70  # Base score for valid
            assert (
                "Rule-based validation passed"
                in result["llm_evaluation_result"]["strengths"]
            )


class TestHasCriticalWeakness:
    """Test Issue #338: _has_critical_weakness function."""

    def test_detect_critical_keyword(self):
        """Test detection of 'Critical' keyword in weaknesses."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = ["Critical: Missing output node"]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 1
        assert "Critical" in issues[0]

    def test_detect_critical_uppercase(self):
        """Test detection of 'CRITICAL' uppercase keyword."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = ["CRITICAL: Search results not returned"]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 1

    def test_detect_critical_lowercase(self):
        """Test detection of 'critical' lowercase keyword."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = ["critical issue: data format mismatch"]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 1

    def test_detect_japanese_critical(self):
        """Test detection of Japanese '致命的' keyword."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = ["致命的: 出力ノードがありません"]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 1

    def test_detect_japanese_juudai(self):
        """Test detection of Japanese '重大' keyword."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = ["重大な問題: インターフェース不整合"]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 1

    def test_no_critical_with_warning(self):
        """Test no critical detected with only warnings."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = [
            "Warning: Consider adding error handling",
            "Minor: Inefficient loop structure",
        ]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is False
        assert len(issues) == 0

    def test_no_critical_with_empty_list(self):
        """Test no critical detected with empty weaknesses."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        has_critical, issues = _has_critical_weakness([])

        assert has_critical is False
        assert len(issues) == 0

    def test_multiple_critical_issues(self):
        """Test detection of multiple critical issues."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _has_critical_weakness,
        )

        weaknesses = [
            "Critical: Missing output node",
            "Warning: Consider adding docs",
            "Critical: Schema mismatch",
            "致命的: データ形式エラー",
        ]
        has_critical, issues = _has_critical_weakness(weaknesses)

        assert has_critical is True
        assert len(issues) == 3  # 2 Critical + 1 致命的


class TestLLMEvaluatorNodeCriticalWeakness:
    """Test Issue #338: llm_evaluator_node critical weakness detection."""

    @pytest.mark.asyncio
    async def test_llm_evaluator_detects_critical_weakness(
        self, base_state: WorkflowGeneratorState
    ):
        """Test that llm_evaluator_node sets has_critical_weakness."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        critical_result = {
            "overall_score": 72,  # Above threshold
            "structural_score": 75,
            "requirement_score": 70,
            "output_quality_score": 70,
            "error_handling_score": 70,
            "test_data_quality_score": 60,
            "test_data_issues": [],
            "needs_test_data_regeneration": False,
            "suggested_test_data": None,
            "strengths": ["Good structure"],
            "weaknesses": ["Critical: Missing search_results in output"],
            "suggestions": ["Add search_results to output"],
            "is_acceptable": True,  # LLM says acceptable
            "failure_reason": "none",  # LLM didn't set failure
            "confidence": 0.8,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**critical_result)

            result = await llm_evaluator_node(base_state)

            # Issue #338: Should detect critical weakness programmatically
            assert result["has_critical_weakness"] is True
            assert len(result["critical_issues"]) == 1
            assert "Critical" in result["critical_issues"][0]
            # is_acceptable should be False due to critical weakness
            assert result["is_acceptable"] is False

    @pytest.mark.asyncio
    async def test_llm_evaluator_no_critical_weakness(
        self, base_state: WorkflowGeneratorState, mock_evaluation_result: dict[str, Any]
    ):
        """Test that llm_evaluator_node sets has_critical_weakness=False."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**mock_evaluation_result)

            result = await llm_evaluator_node(base_state)

            # No critical weakness
            assert result["has_critical_weakness"] is False
            assert result["critical_issues"] == []
            # Should be acceptable (high scores, no critical)
            assert result["is_acceptable"] is True

    @pytest.mark.asyncio
    async def test_llm_evaluator_is_acceptable_includes_critical_check(
        self, base_state: WorkflowGeneratorState
    ):
        """Test that is_acceptable considers critical weakness."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            llm_evaluator_node,
        )

        # All scores high but has critical weakness
        high_score_critical_result = {
            "overall_score": 85,
            "structural_score": 90,
            "requirement_score": 85,
            "output_quality_score": 80,
            "error_handling_score": 80,
            "test_data_quality_score": 85,
            "test_data_issues": [],
            "needs_test_data_regeneration": False,
            "suggested_test_data": None,
            "strengths": ["Excellent structure"],
            "weaknesses": ["Critical: Data type mismatch"],
            "suggestions": [],
            "is_acceptable": True,
            "failure_reason": "none",
            "confidence": 0.9,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_call:
            mock_call.return_value = LLMEvaluationResult(**high_score_critical_result)

            result = await llm_evaluator_node(base_state)

            # Even with high scores, critical weakness should make it not acceptable
            assert result["has_critical_weakness"] is True
            assert result["is_acceptable"] is False


class TestFormatFeedback:
    """Test _format_feedback function."""

    def test_format_feedback_with_all_fields(self):
        """Test feedback formatting with all fields populated."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _format_feedback,
        )

        evaluation = LLMEvaluationResult(
            overall_score=85,
            structural_score=90,
            requirement_score=85,
            output_quality_score=80,
            error_handling_score=75,
            test_data_quality_score=85,
            test_data_issues=[],
            needs_test_data_regeneration=False,
            suggested_test_data=None,
            strengths=["Good structure", "Clean code"],
            weaknesses=["Missing docs"],
            suggestions=["Add documentation"],
            is_acceptable=True,
            failure_reason="none",
            confidence=0.9,
        )

        feedback = _format_feedback(evaluation)

        assert "Overall Score: 85/100" in feedback
        assert "Structural: 90" in feedback
        assert "Requirements: 85" in feedback
        assert "Strengths:" in feedback
        assert "Good structure" in feedback
        assert "Clean code" in feedback
        assert "Weaknesses:" in feedback
        assert "Missing docs" in feedback
        assert "Suggestions:" in feedback
        assert "Add documentation" in feedback

    def test_format_feedback_with_empty_lists(self):
        """Test feedback formatting with empty strengths/weaknesses/suggestions."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            LLMEvaluationResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
            _format_feedback,
        )

        evaluation = LLMEvaluationResult(
            overall_score=50,
            structural_score=50,
            requirement_score=50,
            output_quality_score=50,
            error_handling_score=50,
            test_data_quality_score=50,
            test_data_issues=[],
            needs_test_data_regeneration=False,
            suggested_test_data=None,
            strengths=[],
            weaknesses=[],
            suggestions=[],
            is_acceptable=False,
            failure_reason="workflow_quality",
            confidence=0.5,
        )

        feedback = _format_feedback(evaluation)

        assert "Overall Score: 50/100" in feedback
        # Empty lists should not add section headers
        assert "Strengths:" not in feedback
        assert "Weaknesses:" not in feedback
        assert "Suggestions:" not in feedback
