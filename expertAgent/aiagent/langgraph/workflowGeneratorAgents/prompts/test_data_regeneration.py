"""Test Data Regeneration prompts.

This module provides prompts for regenerating test data
when the LLM Evaluator detects quality issues.
"""

from typing import Any

from ..utils import format_apis_comma_separated

TEST_DATA_REGENERATION_SYSTEM_PROMPT = """You are a test data generation expert.
Generate appropriate and realistic test data based on the given task information and input schema.

## Test Data Generation Guidelines

1. **Realism**: Generate data that would be used in actual business scenarios
   - For company names, use realistic sounding company names (e.g., "Toyota Motor Corporation")
   - For addresses, use realistic address formats
   - For dates, use appropriate date formats

2. **Schema Compliance**: Satisfy all input schema constraints
   - Include all required fields
   - Follow type constraints
   - Use valid enum values when specified

3. **API Compatibility**: Consider the API's expected data format
   - Consider external API specifications
   - For APIs with existence checks, use values that could reasonably exist

4. **Test Effectiveness**: Data that can properly test the workflow
   - Values that test the normal path
   - Values that pass through all processing paths

## Array Type Constraints - Issue #340

When generating array fields for stringTemplateAgent, the following constraints apply:

1. **Primitive Types Only**: Array elements must be string, number, or boolean only
2. **Objects Prohibited**: The format [{...}, {...}] is forbidden
3. **Type Consistency**: Only use types matching items.type

WRONG PATTERN (forbidden):
```json
{
  "focus_points": [
    {"type": "string", "description": "Latest news"}
  ]
}
```

CORRECT PATTERN:
```json
{
  "focus_points": ["Latest news", "Main topics"]
}
```

If the schema defines `items.type: "string"`, generate a string array.
If the schema defines `items.type: "number"`, generate a number array.
Never include objects in arrays that will be passed to stringTemplateAgent.

## Output Format
Return ONLY the following JSON format (no markdown, no comments):
{
  "sample_input": { ... },
  "generation_rationale": "Reason for generating this data",
  "expected_behavior": "Expected workflow behavior with this data"
}
"""


def create_test_data_regeneration_prompt(
    task_name: str,
    task_description: str,
    input_schema: dict[str, Any],
    recommended_apis: list[Any],
    previous_sample_input: dict[str, Any] | str,
    test_data_issues: list[str],
    suggested_test_data: dict[str, Any] | None,
) -> str:
    """Create the user prompt for test data regeneration.

    Args:
        task_name: Name of the task
        task_description: Task description
        input_schema: Input interface schema
        recommended_apis: List of recommended APIs (can be str or dict)
        previous_sample_input: Previous sample input that had issues
        test_data_issues: Issues found with previous test data
        suggested_test_data: LLM suggested test data (if available)

    Returns:
        Formatted prompt string
    """
    import json

    issues_text = "\n".join([f"- {issue}" for issue in test_data_issues])
    if not issues_text:
        issues_text = "No specific issues listed"

    suggested_text = (
        json.dumps(suggested_test_data, indent=2, ensure_ascii=False)
        if suggested_test_data
        else "None"
    )

    return f"""## Task Information
- Name: {task_name}
- Description: {task_description}
- Recommended APIs: {format_apis_comma_separated(recommended_apis)}

## Input Schema
```json
{json.dumps(input_schema, indent=2, ensure_ascii=False)}
```

## Previous Test Data (Has Issues)
```json
{json.dumps(previous_sample_input, indent=2, ensure_ascii=False) if isinstance(previous_sample_input, dict) else previous_sample_input}
```

## Issues with Previous Test Data
{issues_text}

## LLM Suggestion (Reference)
```json
{suggested_text}
```

Based on the above, please generate appropriate test data.
"""
