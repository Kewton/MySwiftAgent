# Integration Action Plan - Issue #358

**Status**: 🔴 BLOCKED - Dead Code Detected
**Required**: Integration before proceeding to acceptance phase

---

## Verification Results

- **Integration Rate**: 33.33%
- **Dead Code Count**: 6 features
- **Critical Issues**: 2
- **Status**: FAILED

**Verification Files**:
- JSON Result: `verification-result.json`
- Summary: `verification-summary.md`
- Diagram: `integration-gap-diagram.md`

---

## Critical Blockers

### 🚨 Blocker 1: BodyTemplateValidator Not Integrated

**Feature**: BodyTemplateValidator (F1)
**File**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py`
**Problem**: Class exists but is never imported or called in production code

**Impact**: 
- 420 lines of validator code is dead
- 36 unit tests pass but validate nothing in production
- Body template validation never occurs

**Required Fix**: Integrate into MasterManagerSubWorkflow

---

### 🚨 Blocker 2: compare_schemas Not Used

**Feature**: compare_schemas (F7)
**File**: `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/schema_comparator.py`
**Problem**: Function implemented but never called anywhere

**Impact**:
- Unnecessary code
- Unclear whether it's needed or field_in_schema is sufficient

**Required Fix**: Either integrate or remove

---

## Integration Checklist for TDD Phase Re-run

### Step 1: Import BodyTemplateValidator

**File**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

**Location**: Top of file (after existing imports)

```python
from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
    BodyTemplateValidator,
    BodyTemplateValidationResult,
)
```

**Verification**:
```bash
grep -n "from.*body_template_validator import" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
# Expected: Match found at line ~40
```

---

### Step 2: Add Validator Instance

**File**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

**Location**: `MasterManagerSubWorkflow.__init__()` method (line ~150)

**Before**:
```python
def __init__(
    self,
    graphai_server_url: str = "http://localhost:8005",
    default_timeout_sec: int = 60,
    jobqueue_client: JobqueueClient | None = None,
    engine: str = "taskflow",
) -> None:
    self._graphai_server_url = graphai_server_url
    self._default_timeout_sec = default_timeout_sec
    self._jobqueue_client = jobqueue_client
    self._engine = engine
```

**After**:
```python
def __init__(
    self,
    graphai_server_url: str = "http://localhost:8005",
    default_timeout_sec: int = 60,
    jobqueue_client: JobqueueClient | None = None,
    engine: str = "taskflow",
) -> None:
    self._graphai_server_url = graphai_server_url
    self._default_timeout_sec = default_timeout_sec
    self._jobqueue_client = jobqueue_client
    self._engine = engine
    self._validator = BodyTemplateValidator()  # ADD THIS LINE
```

**Verification**:
```bash
grep -n "_validator = BodyTemplateValidator()" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
# Expected: Match found in __init__ method
```

---

### Step 3: Call Validator in create_masters()

**File**: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py`

**Location**: Inside the task loop, after line 320 (`body_template = self._build_body_template(order)`)

**Context** (lines 315-330):
```python
output_interface_id = mapping["output_id"]

# Build body template for task chaining
body_template = self._build_body_template(order)

# INSERT VALIDATION HERE ↓

task_master_id = await self._create_task_master(
    task=task,
    input_interface_id=input_interface_id,
    output_interface_id=output_interface_id,
    body_template=body_template,
    context=context,
)
```

**Add This Code**:
```python
# Issue #358: Validate body_template before creating TaskMaster
# Collect output schemas for tasks[N].output_data validation
output_schemas: dict[str, dict[str, Any]] = {}
for idx, t in enumerate(sorted_tasks[:order]):
    if t.id in interfaces:
        output_schemas[str(idx)] = interfaces[t.id].output_schema

# Get current task's input schema
current_input_schema = interfaces[task.id].input_schema

# Validate body_template
validation_result: BodyTemplateValidationResult = self._validator.validate(
    body_template=body_template,
    input_schema=current_input_schema,
    output_schemas=output_schemas,
    task_index=order,
)

# Raise error if validation failed
if not validation_result.is_valid:
    error_messages = [e.message for e in validation_result.errors]
    logger.error(
        "Body template validation failed for task %s: %s",
        task.name,
        "; ".join(error_messages),
    )
    raise WorkflowError(
        f"Body template validation failed for task '{task.name}': {'; '.join(error_messages)}",
        ErrorType.VALIDATION,
        Phase.REGISTRATION,
    )

# Log warnings but continue
if validation_result.warnings:
    for warning in validation_result.warnings:
        logger.warning(
            "Body template warning for task %s: %s",
            task.name,
            warning.message,
        )

logger.info(
    "Body template validation passed for task %s (required fields: %s)",
    task.name,
    validation_result.required_fields,
)
```

**Verification**:
```bash
# Check validator is called
grep -n "self._validator.validate" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
# Expected: Match found in create_masters method

# Check error handling
grep -n "Body template validation failed" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
# Expected: Match found
```

---

### Step 4: Handle compare_schemas Decision

**Option A: Remove compare_schemas (Recommended)**

If `field_in_schema` is sufficient (it's currently used everywhere):

```bash
# Remove function
sed -i '' '/^def compare_schemas/,/^def /d' expertAgent/aiagent/langgraph/jobGeneratorV2/validators/schema_comparator.py

# Remove tests
rm expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/test_schema_comparator.py

# Update __all__
# Edit schema_comparator.py __all__ to remove "compare_schemas"
```

**Option B: Integrate compare_schemas**

If it provides better functionality, update body_template_validator.py to use it instead of field_in_schema.

**Verification**:
```bash
# If removed
grep -n "compare_schemas" expertAgent/aiagent/langgraph/jobGeneratorV2/validators/
# Expected: No matches (or only in comments/docs)

# If integrated
grep -n "compare_schemas\(" expertAgent/aiagent/langgraph/jobGeneratorV2/validators/body_template_validator.py
# Expected: Match found in actual usage
```

---

### Step 5: Update Integration Tests

**File**: `expertAgent/tests/integration/test_registration_validation.py`

**Add New Test**:
```python
@pytest.mark.asyncio
async def test_master_manager_calls_validator():
    """Test that MasterManagerSubWorkflow actually calls BodyTemplateValidator.
    
    This test verifies production integration, not just validator functionality.
    """
    from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
        MasterManagerSubWorkflow,
    )
    
    # Create workflow manager
    manager = MasterManagerSubWorkflow(engine="taskflow")
    
    # Verify validator exists
    assert hasattr(manager, "_validator")
    assert isinstance(manager._validator, BodyTemplateValidator)
    
    # Create invalid task that will fail validation
    invalid_task = TaskDefinition(
        id="task1",
        name="invalid_task",
        description="Task with invalid body_template",
        priority=1,
        recommended_api="test_api",
    )
    
    # Create interface with required field "user_input"
    interface = InterfaceSchema(
        input_schema={
            "type": "object",
            "properties": {
                "user_input": {"type": "string"}
            },
            "required": ["user_input"]
        },
        output_schema={}
    )
    
    # Create context
    context = ExecutionContext(...)
    
    # Execute create_masters - should fail validation
    with pytest.raises(WorkflowError) as exc_info:
        await manager.create_masters(
            tasks=[invalid_task],
            interfaces={"task1": interface},
            project_id="test",
            context=context,
        )
    
    # Verify error message is from validation
    assert "Body template validation failed" in str(exc_info.value)
```

**Verification**:
```bash
pytest expertAgent/tests/integration/test_registration_validation.py::test_master_manager_calls_validator -v
# Expected: PASSED
```

---

### Step 6: Create Acceptance Tests

**File**: `expertAgent/tests/acceptance/test_issue_358_acceptance.py`

**Template**:
```python
"""Acceptance tests for Issue #358: Body Template Validator.

These tests verify E2E integration of body_template validation in the
registration workflow.

Test Cases:
- TC-001: Valid body_template passes validation
- TC-002: Missing field reference is detected
- TC-003: Invalid task reference is detected
- TC-009: Warnings are logged but workflow continues
"""

import pytest
from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_tc_001_valid_body_template_passes(
    api_client,
    test_project_id,
):
    """TC-001: Valid body_template passes validation during registration.
    
    Steps:
    1. Create workflow with valid body_template
    2. Execute registration phase
    3. Assert validation passed
    4. Assert TaskMaster created successfully
    """
    # ... implementation ...


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_tc_002_missing_field_detected(
    api_client,
    test_project_id,
):
    """TC-002: Missing field in input_schema is detected and rejected.
    
    Steps:
    1. Create workflow with {{job.body.missing_field}}
    2. Execute registration phase
    3. Assert WorkflowError raised
    4. Assert error message mentions missing field
    5. Assert TaskMaster NOT created
    """
    # ... implementation ...


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_tc_003_invalid_task_reference_detected(
    api_client,
    test_project_id,
):
    """TC-003: Invalid tasks[N].output_data reference is detected.
    
    Steps:
    1. Create workflow with {{tasks[99].output_data}}
    2. Execute registration phase
    3. Assert WorkflowError raised
    4. Assert error message mentions invalid task index
    """
    # ... implementation ...


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_tc_009_warnings_logged_workflow_continues(
    api_client,
    test_project_id,
    caplog,
):
    """TC-009: Warnings are logged but workflow continues.
    
    Steps:
    1. Create workflow that triggers warnings (not errors)
    2. Execute registration phase
    3. Assert validation passed with warnings
    4. Assert warnings are in logs
    5. Assert TaskMaster created successfully
    """
    # ... implementation ...
```

**Verification**:
```bash
# Run acceptance tests locally
make acceptance-test-agent

# Or specific test
pytest expertAgent/tests/acceptance/test_issue_358_acceptance.py -v
# Expected: All tests PASSED
```

---

## Post-Integration Verification

After completing all steps, run these commands to verify integration:

### 1. Check Import

```bash
grep -n "from.*body_template_validator import" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
```

**Expected**: Match found (should show line number)

---

### 2. Check Instantiation

```bash
grep -n "_validator = BodyTemplateValidator()" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
```

**Expected**: Match found in `__init__` method

---

### 3. Check Validation Call

```bash
grep -n "self._validator.validate" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
```

**Expected**: Match found in `create_masters` method

---

### 4. Check Error Handling

```bash
grep -n "Body template validation failed" expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
```

**Expected**: Match found in error raising code

---

### 5. Run Tests

```bash
# Unit tests
pytest expertAgent/tests/unit/langgraph/jobGeneratorV2/validators/ -v

# Integration tests
pytest expertAgent/tests/integration/test_registration_validation.py -v

# Acceptance tests (local only)
pytest expertAgent/tests/acceptance/test_issue_358_acceptance.py -v
```

**Expected**: All tests PASSED

---

### 6. Static Analysis

```bash
cd expertAgent
ruff check aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
mypy aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py
```

**Expected**: 0 errors

---

### 7. Re-run Verification Agent

```bash
# This should be done by PM Auto-Dev after integration
# Expected result:
# - integration_rate: 100%
# - dead_code_detected: []
# - verification_status: "PASS"
```

---

## Success Criteria

Integration is complete when ALL of these are true:

- [ ] BodyTemplateValidator imported in master_manager.py
- [ ] Validator instantiated in `__init__`
- [ ] `validator.validate()` called in `create_masters()`
- [ ] WorkflowError raised on validation failure
- [ ] Warnings logged on validation warnings
- [ ] compare_schemas either integrated or removed
- [ ] Integration test verifies actual production call
- [ ] Acceptance tests created and passing (locally)
- [ ] All unit tests still passing
- [ ] All integration tests still passing
- [ ] Ruff/MyPy: 0 errors
- [ ] Re-verification shows 100% integration rate
- [ ] Re-verification shows 0 dead code

---

## Files Modified Summary

**Production Code**:
1. `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py` (+45 lines)
2. `expertAgent/aiagent/langgraph/jobGeneratorV2/validators/schema_comparator.py` (optional: -80 lines if removing compare_schemas)

**Test Code**:
1. `expertAgent/tests/integration/test_registration_validation.py` (+50 lines)
2. `expertAgent/tests/acceptance/test_issue_358_acceptance.py` (+200 lines, NEW FILE)

**Estimated Total Changes**: +295 lines (or +215 if removing compare_schemas)

---

## Timeline Estimate

| Task | Estimated Time |
|------|---------------|
| Import and instantiate validator | 5 minutes |
| Add validation call with error handling | 15 minutes |
| Handle compare_schemas decision | 10 minutes |
| Update integration tests | 20 minutes |
| Create acceptance tests | 45 minutes |
| Run all tests and fix issues | 30 minutes |
| **TOTAL** | **2 hours** |

---

## Next Phase: PM Auto-Dev Actions

1. **Re-run TDD Phase** with this action plan
2. Execute all 7 integration steps
3. Verify all success criteria met
4. Run re-verification agent
5. If verification passes (100% integration, 0 dead code):
   - Proceed to Acceptance Phase
6. If verification fails:
   - Review verification report
   - Fix remaining issues
   - Re-run verification

---

**Document Created**: 2026-01-13
**For Issue**: #358
**Phase**: Integration (between TDD and Acceptance)
**Status**: READY FOR EXECUTION
