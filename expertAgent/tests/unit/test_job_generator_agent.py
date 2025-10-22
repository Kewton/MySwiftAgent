"""Unit tests for Job/Task Generator Agent routing logic."""

from aiagent.langgraph.jobTaskGeneratorAgents.agent import (
    evaluator_router,
    validation_router,
)
from aiagent.langgraph.jobTaskGeneratorAgents.state import JobTaskGeneratorState


class TestEvaluatorRouter:
    """Test evaluator_router function."""

    def test_after_task_breakdown_valid_routes_to_interface_definition(self):
        """Test that valid task breakdown routes to interface_definition."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [
                {"task_id": "task_001", "name": "Task 1", "description": "Test task"}
            ],
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": True,
                "hierarchical_score": 8,
                "dependency_score": 8,
                "specificity_score": 8,
                "modularity_score": 8,
                "consistency_score": 8,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
                "issues": [],
                "improvement_suggestions": [],
            },
            "evaluator_stage": "after_task_breakdown",
            "retry_count": 0,
            "error_message": None,
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": None,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
        }

        result = evaluator_router(state)
        assert result == "interface_definition"

    def test_after_task_breakdown_invalid_routes_to_retry(self):
        """Test that invalid task breakdown routes to requirement_analysis (retry)."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [
                {"task_id": "task_001", "name": "Task 1", "description": "Test task"}
            ],
            "evaluation_result": {
                "is_valid": False,
                "all_tasks_feasible": True,
                "hierarchical_score": 6,
                "dependency_score": 8,
                "specificity_score": 8,
                "modularity_score": 8,
                "consistency_score": 8,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
                "issues": ["Some issue"],
                "improvement_suggestions": ["Some suggestion"],
            },
            "evaluator_stage": "after_task_breakdown",
            "retry_count": 0,
            "error_message": None,
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": None,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
        }

        result = evaluator_router(state)
        assert result == "requirement_analysis"

    def test_after_task_breakdown_empty_task_breakdown_routes_to_end(self):
        """Test that empty task_breakdown routes to END.

        This test validates the bug fix where evaluator_router incorrectly
        referenced 'task_breakdown_result' (dict) instead of 'task_breakdown' (list).
        """
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [],  # Empty task breakdown
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": True,
                "hierarchical_score": 8,
                "dependency_score": 8,
                "specificity_score": 8,
                "modularity_score": 8,
                "consistency_score": 8,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
                "issues": [],
                "improvement_suggestions": [],
            },
            "evaluator_stage": "after_task_breakdown",
            "retry_count": 0,
            "error_message": None,
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": None,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
        }

        result = evaluator_router(state)
        assert result == "END"

    def test_after_interface_definition_valid_routes_to_master_creation(self):
        """Test that valid interface definition routes to master_creation."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [
                {"task_id": "task_001", "name": "Task 1", "description": "Test task"}
            ],
            "interface_definitions": {
                "task_001": {
                    "interface_master_id": 1,
                    "interface_name": "TestInterface",
                    "input_schema": {},
                    "output_schema": {},
                }
            },
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": True,
                "hierarchical_score": 8,
                "dependency_score": 8,
                "specificity_score": 8,
                "modularity_score": 8,
                "consistency_score": 8,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
                "issues": [],
                "improvement_suggestions": [],
            },
            "evaluator_stage": "after_interface_definition",
            "retry_count": 0,
            "error_message": None,
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": None,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
        }

        result = evaluator_router(state)
        assert result == "master_creation"

    def test_max_retries_routes_to_end(self):
        """Test that max retries routes to END."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [
                {"task_id": "task_001", "name": "Task 1", "description": "Test task"}
            ],
            "evaluation_result": {
                "is_valid": False,
                "all_tasks_feasible": True,
                "hierarchical_score": 6,
                "dependency_score": 8,
                "specificity_score": 8,
                "modularity_score": 8,
                "consistency_score": 8,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
                "issues": ["Some issue"],
                "improvement_suggestions": ["Some suggestion"],
            },
            "evaluator_stage": "after_task_breakdown",
            "retry_count": 5,  # Max retries reached
            "error_message": None,
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": None,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
        }

        result = evaluator_router(state)
        assert result == "END"


class TestValidationRouter:
    """Test validation_router function."""

    def test_valid_routes_to_job_registration(self):
        """Test that valid validation routes to job_registration."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [],
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": 123,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_result": None,
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": {
                "is_valid": True,
                "errors": [],
            },
            "retry_count": 0,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
            "error_message": None,
        }

        result = validation_router(state)
        assert result == "job_registration"

    def test_invalid_routes_to_retry(self):
        """Test that invalid validation routes to interface_definition (retry)."""
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "task_breakdown": [],
            "interface_definitions": [],
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": 123,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_result": None,
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "validation_result": {
                "is_valid": False,
                "errors": ["Some validation error"],
            },
            "retry_count": 0,
            "validation_errors": [],
            "job_id": None,
            "status": "initialized",
            "error_message": None,
        }

        result = validation_router(state)
        assert result == "interface_definition"
