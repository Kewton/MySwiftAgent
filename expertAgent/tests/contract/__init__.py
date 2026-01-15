"""Contract tests for ExpertAgent/GraphAiServer schema compatibility.

Issue #356: TaskFlow Contract Tests implementation.

This package provides contract tests that verify:
1. JSON string fields are correctly converted to objects
2. Pydantic model outputs are compatible with TaskFlowAdapter
3. Converted workflows pass GraphAiServer validation
"""
