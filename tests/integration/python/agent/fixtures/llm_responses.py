"""LLM response fixture data for workflow node testing.

This module contains realistic LLM response data captured from actual API calls.
These fixtures are used to test workflow nodes without requiring API keys.
"""

from typing import Any

# ============================================================================
# Validation Node Responses
# ============================================================================

VALIDATION_SUCCESS_RESPONSE: dict[str, Any] = {
    "has_errors": False,
    "errors": [],
    "warnings": [],
    "validation_summary": "All interfaces are valid and compatible",
}

VALIDATION_FAILURE_RESPONSE: dict[str, Any] = {
    "has_errors": True,
    "errors": [
        "Task 'extract_pdf' output schema does not match Task 'upload_to_drive' input schema",
        "Missing required field 'file_path' in Task 'upload_to_drive' input",
    ],
    "warnings": [
        "Task 'send_email' has optional field 'cc' that is rarely used",
    ],
    "fix_proposals": [
        {
            "task_id": "task_extract_pdf",
            "error_type": "schema_mismatch",
            "current_schema": {
                "type": "object",
                "properties": {
                    "pdf_content": {"type": "string"},
                    "page_count": {"type": "integer"},
                },
                "required": ["pdf_content"],
            },
            "fixed_schema": {
                "type": "object",
                "properties": {
                    "pdf_content": {"type": "string"},
                    "page_count": {"type": "integer"},
                    "file_path": {"type": "string"},
                },
                "required": ["pdf_content", "file_path"],
            },
            "fix_explanation": "Add 'file_path' field to output schema to match downstream task requirements",
        }
    ],
}

# ============================================================================
# Interface Definition Node Responses
# ============================================================================

INTERFACE_DEFINITION_SUCCESS: dict[str, Any] = {
    "interfaces": [
        {
            "task_id": "task_1",
            "interface_name": "ReceiveUserInput",
            "description": "Accept user input for company name",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_prompt": {"type": "string"},
                },
                "required": ["user_prompt"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                },
                "required": ["company_name"],
            },
        },
        {
            "task_id": "task_2",
            "interface_name": "AnalyzeFinancialData",
            "description": "Analyze company financial data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                },
                "required": ["company_name"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "revenue_trend": {"type": "array", "items": {"type": "number"}},
                    "business_model_changes": {"type": "string"},
                },
                "required": ["revenue_trend", "business_model_changes"],
            },
        },
    ]
}

INTERFACE_DEFINITION_WITH_JSON_STRINGS: dict[str, Any] = {
    "interfaces": [
        {
            "task_id": "task_1",
            "interface_name": "ProcessData",
            "description": "Process input data",
            # Gemini returns JSON strings instead of dicts
            "input_schema": '{"type": "object", "properties": {"data": {"type": "string"}}}',
            "output_schema": '{"type": "object", "properties": {"result": {"type": "string"}}}',
        }
    ]
}

# ============================================================================
# Evaluator Node Responses
# ============================================================================

EVALUATOR_SUCCESS_AFTER_TASK_BREAKDOWN: dict[str, Any] = {
    "is_valid": True,
    "quality_score": 0.92,
    "feasibility_score": 0.88,
    "evaluation_summary": "Task breakdown is comprehensive and well-structured",
    "strengths": [
        "Clear task separation",
        "All tasks are feasible with available capabilities",
        "Dependencies are well-defined",
    ],
    "weaknesses": [],
    "improvement_suggestions": [],
}

EVALUATOR_FAILURE_AFTER_TASK_BREAKDOWN: dict[str, Any] = {
    "is_valid": False,
    "quality_score": 0.45,
    "feasibility_score": 0.30,
    "evaluation_summary": "Task breakdown has critical issues",
    "strengths": [],
    "weaknesses": [
        "Task dependencies are circular",
        "Some tasks require unavailable capabilities",
    ],
    "improvement_suggestions": [
        "Reorder tasks to eliminate circular dependencies",
        "Replace unavailable capabilities with alternatives",
    ],
}

EVALUATOR_SUCCESS_AFTER_INTERFACE_DEFINITION: dict[str, Any] = {
    "is_valid": True,
    "quality_score": 0.90,
    "feasibility_score": 0.85,
    "evaluation_summary": "Interface definitions are complete and compatible",
    "strengths": [
        "All interfaces are well-defined",
        "Input/output schemas are compatible",
    ],
    "weaknesses": [],
    "improvement_suggestions": [],
}

# ============================================================================
# Requirement Analysis Node Responses
# ============================================================================

REQUIREMENT_ANALYSIS_SUCCESS: dict[str, Any] = {
    "tasks": [
        {
            "task_id": "task_1",
            "task_name": "企業名入力受付",
            "description": "ユーザーから企業名を入力として受け取る",
            "priority": "high",
            "estimated_duration": "1 minute",
            "dependencies": [],
        },
        {
            "task_id": "task_2",
            "task_name": "IR情報取得",
            "description": "指定された企業のIR情報サイトから過去5年の財務データを取得",
            "priority": "high",
            "estimated_duration": "5 minutes",
            "dependencies": ["task_1"],
        },
        {
            "task_id": "task_3",
            "task_name": "売上分析",
            "description": "取得した財務データから売上の推移を分析",
            "priority": "medium",
            "estimated_duration": "3 minutes",
            "dependencies": ["task_2"],
        },
    ],
    "workflow_summary": "3-step workflow for analyzing company financial data",
}

# ============================================================================
# Master Creation Node Responses
# ============================================================================

MASTER_CREATION_SUCCESS: dict[str, Any] = {
    "job_master_id": "jm_01K89W9DBHAPWMMZVHWT2N7GX9",
    "task_masters": [
        {
            "task_master_id": "tm_01K89W9DBHBPXNNZVHXT3M8GY0",
            "task_name": "企業名入力受付",
        },
        {
            "task_master_id": "tm_01K89W9DBHCPXOOZVHYT4N9GZ1",
            "task_name": "IR情報取得",
        },
    ],
    "interface_masters": [
        {
            "interface_master_id": "im_01K89W9DBHDPXPPZVHZT5O0HA2",
            "interface_name": "ReceiveUserInput",
        },
        {
            "interface_master_id": "im_01K89W9DBHEPXQQZVH0T6P1HB3",
            "interface_name": "AnalyzeFinancialData",
        },
    ],
}

# ============================================================================
# Job Registration Node Responses
# ============================================================================

JOB_REGISTRATION_SUCCESS: dict[str, Any] = {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "registered",
    "tasks": [
        {
            "task_id": "task_550e8400-1",
            "task_master_id": "tm_01K89W9DBHBPXNNZVHXT3M8GY0",
        },
        {
            "task_id": "task_550e8400-2",
            "task_master_id": "tm_01K89W9DBHCPXOOZVHYT4N9GZ1",
        },
    ],
}

# ============================================================================
# Error Responses
# ============================================================================

VALIDATION_EXCEPTION_RESPONSE: dict[str, Any] = {
    "error": "Failed to validate workflow",
    "error_type": "ValidationError",
    "error_message": "Interface schema validation failed",
}

INTERFACE_DEFINITION_EXCEPTION_RESPONSE: dict[str, Any] = {
    "error": "Failed to define interfaces",
    "error_type": "InterfaceDefinitionError",
    "error_message": "LLM API call failed",
}
