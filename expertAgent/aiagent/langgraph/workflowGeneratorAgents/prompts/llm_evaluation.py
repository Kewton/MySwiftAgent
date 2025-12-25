"""LLM Evaluation prompts for workflow quality assessment.

This module provides prompts for the LLM Evaluator to assess
workflow quality across multiple dimensions.
"""

from typing import Any


def _format_recommended_apis(apis: list[Any] | None) -> str:
    """Format recommended APIs for display in prompt.

    Handles both list[str] and list[dict] formats.

    Args:
        apis: List of recommended APIs (can be strings or dicts with 'name' key)

    Returns:
        Comma-separated string of API names
    """
    if not apis:
        return "None specified"

    formatted = []
    for api in apis:
        if isinstance(api, dict):
            # Handle dict format: {"name": "api_name", ...}
            name = api.get("name") or api.get("api_name") or str(api)
            formatted.append(str(name))
        else:
            formatted.append(str(api))

    return ", ".join(formatted) if formatted else "None specified"

LLM_EVALUATION_SYSTEM_PROMPT = """You are an expert GraphAI workflow quality evaluator.
Evaluate the given workflow across the following dimensions and return a structured JSON response.

## Evaluation Dimensions

### 1. Structural Validity (structural_score: 0-100)
- Node definitions are correct
- Data flow is logical
- Dependencies are appropriate
- No unnecessary nodes

### 2. Requirement Fulfillment (requirement_score: 0-100)
- Meets TaskMaster description
- Uses recommended APIs appropriately
- Processes input schema correctly
- Conforms to output schema

### 3. Output Quality (output_quality_score: 0-100)
- Execution results are as expected
- Data formats are correct
- Required fields are included

### 4. Error Handling (error_handling_score: 0-100)
- Appropriate error handling exists
- Retry logic is present
- Fallback processing exists

### 5. Test Data Quality (test_data_quality_score: 0-100) **IMPORTANT**
Strictly evaluate the quality of test data (sample input):

- **Realism**: Is it data that would be used in actual use cases?
  - NG examples: "sample_text", "test", "aaa", "xxx"
  - OK examples: "Toyota Motor Corporation", "Shibuya, Tokyo", "2024-01-15"

- **Schema Compliance**: Does it meet input schema constraints?
  - All required fields exist
  - Types are correct

- **Domain Validity**: Are values appropriate for the business domain?
  - Company info retrieval tasks should use realistic company names
  - Date fields should have valid date formats

- **API Compatibility**: Is it data the called API would accept?
  - For APIs with existence checks, use values that could exist

If test data is inappropriate, set `needs_test_data_regeneration: true`
and propose appropriate test data in `suggested_test_data`.

## Output Format
Return ONLY the following JSON format (no markdown, no comments):
{
  "overall_score": <0-100>,
  "structural_score": <0-100>,
  "requirement_score": <0-100>,
  "output_quality_score": <0-100>,
  "error_handling_score": <0-100>,
  "test_data_quality_score": <0-100>,
  "test_data_issues": ["issue1", "issue2"],
  "needs_test_data_regeneration": <true|false>,
  "suggested_test_data": { "field1": "appropriate_value1", ... } | null,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["specific_suggestion1", "specific_suggestion2"],
  "is_acceptable": <true|false>,
  "failure_reason": "none" | "workflow_quality" | "test_data_quality" | "both",
  "confidence": <0.0-1.0>
}
"""


def create_llm_evaluation_prompt(
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any],
    recommended_apis: list[Any],
    yaml_content: str,
    sample_input: dict[str, Any] | str,
    execution_result: dict[str, Any] | None,
    rule_based_issues: list[dict[str, str]],
    is_regenerated_test_data: bool = False,
    test_data_regeneration_count: int = 0,
) -> str:
    """Create the user prompt for LLM evaluation.

    Args:
        task_name: Name of the task
        task_description: Task description
        input_schema: Input interface schema
        output_schema: Output interface schema
        recommended_apis: List of recommended APIs (can be str or dict)
        yaml_content: Generated workflow YAML
        sample_input: Sample input used for testing
        execution_result: Execution result from graphAiServer
        rule_based_issues: Issues from rule-based validation
        is_regenerated_test_data: Whether test data was regenerated
        test_data_regeneration_count: Number of regeneration attempts

    Returns:
        Formatted prompt string
    """
    import json

    test_data_source = (
        "LLM regeneration" if is_regenerated_test_data else "automatic generation"
    )

    issues_text = "\n".join(
        [
            f"- [{issue.get('category', 'unknown')}] {issue.get('message', 'Unknown issue')}"
            for issue in rule_based_issues
        ]
    )
    if not issues_text:
        issues_text = "No issues found"

    return f"""## TaskMaster Information
- Name: {task_name}
- Description: {task_description}
- Recommended APIs: {_format_recommended_apis(recommended_apis)}

## Input Schema
```json
{json.dumps(input_schema, indent=2, ensure_ascii=False)}
```

## Output Schema
```json
{json.dumps(output_schema, indent=2, ensure_ascii=False)}
```

## Generated Workflow YAML
```yaml
{yaml_content}
```

## Sample Input (Test Data)
```json
{json.dumps(sample_input, indent=2, ensure_ascii=False) if isinstance(sample_input, dict) else sample_input}
```

* This test data was generated via {test_data_source}.
* Test data regeneration count: {test_data_regeneration_count}

## Execution Result
```json
{json.dumps(execution_result, indent=2, ensure_ascii=False) if execution_result else "null"}
```

## Rule-Based Validation Issues
{issues_text}

Please evaluate the above and return results in JSON format.
Pay special attention to test data quality and suggest appropriate test data if it is inadequate.
"""
