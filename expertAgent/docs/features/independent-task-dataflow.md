# Independent Task Dataflow Specification

## Overview

This document describes the dataflow specification for independent tasks in the Job Generator V2 workflow system.

## Definitions

### Independent Task

A task is considered **independent** when its `dependencies` field is empty (`dependencies=[]`).

```python
TaskDefinition(
    id="task_001",
    name="Keyword Search",
    dependencies=[],  # Empty = independent task
)
```

### Dependent Task

A task is considered **dependent** when its `dependencies` field contains one or more task IDs.

```python
TaskDefinition(
    id="task_003",
    name="Send Report",
    dependencies=["task_001", "task_002"],  # Has dependencies
)
```

## Dataflow Rules

### Rule 1: Independent Tasks Use User Input

All independent tasks (regardless of their execution order) receive data directly from `job.body.user_input`.

```
body_template.inputs = "{{job.body.user_input}}"
```

**Why**: Independent tasks have no preceding tasks to receive data from, so they must get their input from the user.

### Rule 2: Dependent Tasks Use Field References

Dependent tasks receive data from their dependency tasks using field-level references.

```python
body_template.inputs = {
    "keyword": "{{tasks[0].output_data.keyword}}",
    "summary": "{{tasks[1].output_data.summary}}",
}
```

**Why**: Dependent tasks need to aggregate outputs from multiple preceding tasks.

### Rule 3: Legacy Compatibility

When `_build_body_template` is called without the `task` parameter (legacy call), it falls back to the previous behavior:
- `order == 0`: uses `{{job.body.user_input}}`
- `order > 0`: uses `{{tasks[order-1].output_data}}`

## Schema Merging

When multiple independent tasks exist, their input schemas are merged into a single `user_input_schema`.

### Merge Process

1. Iterate through all tasks in topological order
2. For each independent task (`dependencies=[]`):
   - Extract `properties` from `input_schema`
   - Extract `required` fields from `input_schema`
   - Merge into the combined schema

### Field Conflict Handling

#### Same Field, Same Type (Warning)

When the same field name appears in multiple independent tasks with the **same type**:
- Log a warning with both type information
- Continue processing (last definition wins)

```python
logger.warning(
    "Field '%s' from task '%s' overrides previous definition. "
    "Existing type: %s, New type: %s",
    field_name, task.name, existing_type, new_type,
)
```

#### Same Field, Different Type (Error)

When the same field name appears in multiple independent tasks with **different types**:
- Raise `ValueError` with both type information
- Job generation is aborted

```python
raise ValueError(
    f"Field '{field_name}' has conflicting types: "
    f"'{existing_type}' vs '{new_type}' (task: {task.name})"
)
```

## Examples

### Example 1: Two Independent Tasks

```python
# Task definitions
tasks = [
    TaskDefinition(id="task_001", dependencies=[]),  # Independent
    TaskDefinition(id="task_002", dependencies=[]),  # Independent
    TaskDefinition(id="task_003", dependencies=["task_001", "task_002"]),
]

# Generated body_templates
task_001: inputs = "{{job.body.user_input}}"  # Independent
task_002: inputs = "{{job.body.user_input}}"  # Independent (not {{tasks[0].output_data}})
task_003: inputs = {                           # Dependent
    "field_a": "{{tasks[0].output_data.field_a}}",
    "field_b": "{{tasks[1].output_data.field_b}}",
}
```

### Example 2: Schema Merging

```python
# task_001 input_schema
{
    "properties": {"keyword": {"type": "string"}},
    "required": ["keyword"]
}

# task_002 input_schema
{
    "properties": {"recipient_email": {"type": "string"}},
    "required": ["recipient_email"]
}

# Merged user_input_schema
{
    "type": "object",
    "properties": {
        "keyword": {"type": "string"},
        "recipient_email": {"type": "string"}
    },
    "required": ["keyword", "recipient_email"]
}
```

## Troubleshooting

### Issue: Second independent task not receiving user input

**Symptom**: The second independent task receives empty or incorrect data.

**Cause**: The task may have been incorrectly assigned a dependency.

**Solution**: Verify that the task's `dependencies` field is empty (`[]`).

### Issue: ValueError with conflicting types

**Symptom**: Job generation fails with `ValueError: Field 'X' has conflicting types`.

**Cause**: Two independent tasks define the same field with different types.

**Solution**:
1. Rename one of the conflicting fields to be unique
2. Or ensure both fields use the same type

### Issue: Warning about field override

**Symptom**: Warning log about field override appears.

**Cause**: Two independent tasks define the same field with the same type.

**Solution**: This is usually intentional (e.g., common fields like `project`). Review the warning to ensure it's expected behavior.

## Related Issues

- **Issue #403**: Multi-dependency field aggregation
- **Issue #408**: User input field name validation
- **Issue #409**: Multiple independent tasks dataflow fix

## Implementation Details

### Affected Methods

- `MasterManagerSubWorkflow._build_body_template()`: Determines data source for each task
- `MasterManagerSubWorkflow._get_user_input_schema()`: Merges schemas from all independent tasks

### Test Coverage

- Unit tests: `tests/unit/test_job_generator_v2/test_registration/test_master_manager.py`
- Integration tests: `tests/integration/langgraph/test_issue_409_integration.py`
- Acceptance tests: `tests/acceptance/test_issue_409_acceptance.py`
