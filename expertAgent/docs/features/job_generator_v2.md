# Job Generator V2 Architecture

## Overview

Job Generator V2 is a refactored architecture for the Job/Task Auto-Generation system in ExpertAgent. It addresses the infinite loop bug (retry_count issue) and provides improved maintainability through clear phase separation and proper error recovery.

**Issues**: #342 (V2 Architecture), #350 (TaskFlow Engine)

**Status**: Available via feature flag (default: disabled)

---

## Workflow Engine Selection (Issue #350)

V2 supports two workflow generation engines:

| Engine | Format | Default | Model | Use Case |
|--------|--------|---------|-------|----------|
| `taskflow` | JSON | ✅ | gpt-5-mini | OpenAI Structured Output |
| `graphai` | YAML | - | claude-haiku-4-5 | Legacy GraphAI workflows |

### TaskFlow V2 Engine (Default)

TaskFlow V2 generates JSON workflows compatible with OpenAI Structured Output.

**Key Features:**
- OpenAI Structured Output compatibility (no Union types)
- UnifiedStepConfig model (single config for all step types)
- JSON string fields for dynamic schemas

**Environment Variables:**
```bash
WORKFLOW_GENERATOR_ENGINE=taskflow           # Engine selection (default)
WORKFLOW_GENERATOR_V2_MODEL=gpt-5-mini       # LLM model for generation
WORKFLOW_GENERATOR_V2_TEMPERATURE=0.3        # Generation temperature
```

**Performance Note:**
- gpt-5-mini with complex schemas: 1-5 minutes (OpenAI processing)
- gemini-3-flash-preview: 5-20 seconds (faster, but less accurate)

### GraphAI Engine (Legacy)

GraphAI generates YAML workflows for the original GraphAI execution engine.

```bash
WORKFLOW_GENERATOR_ENGINE=graphai            # Use GraphAI engine
WORKFLOW_GENERATOR_MODEL=claude-haiku-4-5    # LLM model
```

See: [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)

### Programmatic Engine Selection

```python
from aiagent.langgraph.jobGeneratorV2 import JobGeneratorV2Adapter

# Use TaskFlow (default)
adapter = JobGeneratorV2Adapter(engine="taskflow")

# Use GraphAI
adapter = JobGeneratorV2Adapter(engine="graphai")
```

---

## Key Improvements

### 1. Phase-Based Architecture

V2 separates job generation into 4 distinct phases:

| Phase | Purpose | Workflow |
|-------|---------|----------|
| **TASK_BREAKDOWN** | Decompose requirements into tasks | TaskBreakdownWorkflow |
| **INTERFACE_DESIGN** | Define I/O schemas for tasks | InterfaceDesignWorkflow |
| **REGISTRATION** | Register masters in jobqueue | RegistrationWorkflow |
| **WORKFLOW_GEN** | Generate workflow (TaskFlow JSON or GraphAI YAML) | WorkflowGenWorkflow |

### 2. Per-Phase Retry Management

The critical bug fix: Each phase now has its own `RetryState` instead of a global `retry_count`:

```python
# V1 (buggy): Global retry_count that could be reset
retry_count = state.get("retry_count", 0)  # BUG: Could be reset incorrectly

# V2 (fixed): Per-phase retry tracking
context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count  # Phase-specific
context.total_retry_count()  # Total across all phases
```

### 3. Error Recovery Strategy

`ErrorRecoveryManager` makes intelligent decisions about recovery:

- **RETRY_CURRENT**: Retry the current phase (transient errors)
- **ROLLBACK_ONE**: Go back one phase (compatibility issues)
- **ROLLBACK_TO_BREAKDOWN**: Go back to task breakdown (fundamental issues)
- **RELAXATION**: Request requirement relaxation from user
- **FAIL_FAST**: Stop immediately (fatal errors)

## Enabling V2

### Environment Variable

```bash
# Enable V2 architecture
export USE_JOB_GENERATOR_V2=true

# Or in .env file
USE_JOB_GENERATOR_V2=true
```

### Checking Feature Flag Status

```python
from core.feature_flags import use_job_generator_v2

if use_job_generator_v2():
    print("V2 is enabled")
else:
    print("V1 is in use")
```

## Architecture

### Component Diagram

```
JobGeneratorV2Adapter
    |
    v
JobGenerationOrchestrator
    |-- ErrorRecoveryManager
    |-- ProgressReporter (optional)
    |
    +-- Phase: TASK_BREAKDOWN
    |       |-- TaskDecomposerSubWorkflow
    |       |-- FeasibilitySubWorkflow
    |       +-- AlternativeSubWorkflow
    |
    +-- Phase: INTERFACE_DESIGN
    |       |-- SchemaGeneratorSubWorkflow
    |       |-- CompatibilityCheckerSubWorkflow
    |       +-- SchemaEnricherSubWorkflow
    |
    +-- Phase: REGISTRATION
    |       |-- MasterManagerSubWorkflow
    |       +-- JobRegistrarSubWorkflow
    |
    +-- Phase: WORKFLOW_GEN
            |-- EngineStrategy (TaskFlow or GraphAI)
            |   |-- TaskFlowGeneratorStrategy (JSON)
            |   +-- GraphAIGeneratorStrategy (YAML)
            +-- TestRunnerSubWorkflow
```

### ExecutionContext

The `ExecutionContext` carries state and dependencies through the workflow:

```python
context = (
    ContextBuilder()
    .with_job_id(job_id)
    .with_user_requirement(requirement)
    .with_max_retries(total=5, per_phase=3)
    .with_llm_context(LLMContext(model_name="claude-haiku-4-5"))
    .build()
)
```

## Usage Example

### Direct API Usage

```python
from aiagent.langgraph.jobGeneratorV2 import JobGeneratorV2Adapter

adapter = JobGeneratorV2Adapter(
    max_retry=5,
    langfuse_handler=callback_handler,  # Optional: for observability
)

response = await adapter.generate(
    user_requirement="Search Gmail and summarize recent emails",
    project_id="my-project",
    max_tasks=10,
)

if response.status == "success":
    print(f"Job created: {response.job_master_id}")
else:
    print(f"Error: {response.error_message}")
```

### Via API Endpoint

When `USE_JOB_GENERATOR_V2=true`:

```bash
curl -X POST http://localhost:8004/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "Search Gmail and summarize recent emails",
    "max_retry": 5
  }'
```

## Migration from V1

### What Changes

1. **Error handling**: V2 uses `WorkflowError` with specific `ErrorType`
2. **State management**: V2 uses `ExecutionContext` instead of LangGraph state
3. **Retry logic**: Per-phase limits prevent infinite loops

### What Stays the Same

1. **API interface**: Same request/response format
2. **Job output**: Same JobMaster, TaskMaster registration
3. **Workflow YAML**: Same GraphAI YAML format

### Testing V2

1. Enable V2:
   ```bash
   export USE_JOB_GENERATOR_V2=true
   ```

2. Run tests:
   ```bash
   cd expertAgent
   uv run pytest tests/integration/test_job_generator_v2_integration.py -v
   ```

3. Run acceptance tests:
   ```bash
   uv run pytest tests/acceptance/test_issue_342_acceptance.py -v
   ```

## Differences from V1

| Aspect | V1 | V2 |
|--------|----|----|
| Retry tracking | Global `retry_count` in state | Per-phase `RetryState` |
| State management | LangGraph state dict | `ExecutionContext` dataclass |
| Error recovery | Manual checks | `ErrorRecoveryManager` |
| Phase separation | Implicit in node flow | Explicit `Phase` enum |
| Testability | Requires full graph | Each workflow testable |
| Infinite loop risk | Possible (bug) | Prevented by design |
| Workflow engine | GraphAI only | TaskFlow (default) + GraphAI |
| Output format | YAML only | JSON (TaskFlow) + YAML (GraphAI) |

## Configuration

### Settings

```python
# core/config.py
USE_JOB_GENERATOR_V2: bool = False  # Enable V2 architecture
JOB_GENERATOR_MAX_TOKENS: int = 32768
JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL: str = "claude-haiku-4-5"

# TaskFlow V2 settings (Issue #350)
WORKFLOW_GENERATOR_ENGINE: str = "taskflow"  # "taskflow" or "graphai"
WORKFLOW_GENERATOR_V2_MODEL: str = "gemini-3-flash-preview"  # LLM model
WORKFLOW_GENERATOR_V2_TEMPERATURE: float = 0.3  # Generation temperature
```

### Retry Limits

- Default total retries: 5
- Default per-phase retries: 3
- Configurable via `ContextBuilder.with_max_retries()`

## Troubleshooting

### V2 Not Activating

1. Check feature flag:
   ```python
   from core.config import settings
   print(settings.USE_JOB_GENERATOR_V2)
   ```

2. Ensure environment variable is set before importing:
   ```bash
   USE_JOB_GENERATOR_V2=true python -c "from core.config import settings; print(settings.USE_JOB_GENERATOR_V2)"
   ```

### Retry Limits Exceeded

If you see "Maximum retries exceeded" errors:

1. Check per-phase limits:
   ```python
   context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count
   ```

2. Check total limits:
   ```python
   context.total_retry_count()
   ```

3. Increase limits if needed (not recommended for production):
   ```python
   adapter = JobGeneratorV2Adapter(max_retry=10)
   ```

## Future Work

1. **Rollback support**: Full implementation of rollback strategies
2. **Progress reporting**: Real-time progress updates via SSE
3. **A/B testing**: Compare V1 and V2 performance metrics
4. **Full V2 migration**: Deprecate V1 after stabilization
