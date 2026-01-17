# Issue #363 Integration Action Plan

**Status**: Ready for execution  
**Priority**: P0 (Critical - Dead Code Found)  
**Estimated Effort**: 4 hours  

---

## Problem Statement

TDD implementation completed with 93.32% unit test coverage, but verification reveals:
- **2 components are dead code** (never called in production)
- **4 components lack integration tests**
- **0 integration tests exist**

This indicates a gap between "unit tests passing" and "features actually working in production."

---

## Root Cause Analysis

| Issue | Root Cause | Prevention |
|-------|-----------|------------|
| TaskFlowDefinitionAdapter unused | Adapter was implemented but not connected to WorkflowLoader | TDD should include "usage verification" step |
| TaskFlowEngine facade unused | Handlers were written to use WorkflowExecutor directly | Architecture review should verify design patterns are followed |
| CodeJsSandbox not instantiated | Default registry creates executor without sandbox | Integration test would have caught runtime failure |
| No integration tests | TDD phase only checked unit test coverage | PM Auto-Dev should enforce integration test creation |

---

## Action Plan

### Phase 1: Fix Dead Code (P0 - 1 hour)

#### Task 1.1: Connect TaskFlowDefinitionAdapter to WorkflowLoader

**File**: `mySwiftAgentCore/src/taskflowEngine/loader/WorkflowLoader.ts`

**Changes**:
```typescript
// Add import at top (after line 10)
import { TaskFlowDefinitionAdapter } from '../adapter/TaskFlowDefinitionAdapter.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';

// Change return type (line 54)
async loadWorkflow(filePath: string): Promise<InternalWorkflowDefinition> {
  // ... existing code ...
  
  // After line 62, replace direct return with:
  const internalWorkflow = TaskFlowDefinitionAdapter.toInternal(parsed);
  return internalWorkflow;
}

// Update loadWorkflowsForProject return type (line 77)
async loadWorkflowsForProject(projectId: string): Promise<InternalWorkflowDefinition[]> {
  // ... existing code ...
}
```

**Test Changes**: Update `tests/unit/taskflowEngine/loader/WorkflowLoader.test.ts` to expect `InternalWorkflowDefinition` return type.

**Verification**:
```bash
# Verify adapter is now called
grep -n "TaskFlowDefinitionAdapter.toInternal" mySwiftAgentCore/src/taskflowEngine/loader/WorkflowLoader.ts
```

---

#### Task 1.2: Use TaskFlowEngine Facade in Handlers

**File**: `mySwiftAgentCore/src/taskflowEngine/api/handlers.ts`

**Changes**:
```typescript
// Change import (line 9)
import { TaskFlowEngine } from '../TaskFlowEngine.js';

// Update HandlerDependencies (line 16)
export interface HandlerDependencies {
  registry: WorkflowRegistry;
  executor: TaskFlowEngine;  // Changed from WorkflowExecutor
  validator: SchemaValidator;
  tracer?: LangfuseTracer;
}

// In createExecuteHandler, the execute call remains the same
// TaskFlowEngine.execute() has compatible signature with WorkflowExecutor.execute()
```

**File**: `mySwiftAgentCore/src/taskflowEngine/api/routes.ts`

**Changes**:
```typescript
// Update initialization code to create TaskFlowEngine instead of WorkflowExecutor
import { createTaskFlowEngine } from '../TaskFlowEngine.js';

// Replace WorkflowExecutor instantiation with:
const engine = createTaskFlowEngine({
  nodeRegistry: registry,
  defaultTimeout: 30000,
});
```

**Verification**:
```bash
# Verify TaskFlowEngine is now used
grep -n "new TaskFlowEngine\|createTaskFlowEngine" mySwiftAgentCore/src/taskflowEngine/api/routes.ts
```

---

### Phase 2: Fix Runtime Issues (P0 - 30 minutes)

#### Task 2.1: Instantiate CodeJsSandbox in Default Registry

**File**: `mySwiftAgentCore/src/taskflowEngine/nodes/index.ts`

**Changes**:
```typescript
// Add import (after line 35)
import { createCodeJsSandbox } from '../sandbox/CodeJsSandbox.js';

// Update createDefaultNodeRegistry (line 40)
export function createDefaultNodeRegistry(whitelist?: ScriptWhitelist): NodeRegistry {
  const registry = new NodeRegistry();
  
  // Create sandbox instance
  const sandbox = whitelist 
    ? createCodeJsSandbox(whitelist) 
    : createCodeJsSandbox();

  registry.register('api_rest', new ApiRestNodeExecutor());
  registry.register('transform', new TransformNodeExecutor());
  registry.register('code_js', new CodeJsNodeExecutor(sandbox));  // Pass sandbox instance
  registry.register('llm', new LlmNodeExecutor());
  registry.register('parallel', new ParallelNodeExecutor());
  registry.register('action', new ActionNodeExecutor());

  return registry;
}
```

**Verification**:
```bash
# Verify sandbox is instantiated
grep -n "createCodeJsSandbox()" mySwiftAgentCore/src/taskflowEngine/nodes/index.ts
```

---

### Phase 3: Create Integration Tests (P1 - 2.5 hours)

#### Task 3.1: Create Integration Test Structure

```bash
mkdir -p mySwiftAgentCore/tests/integration/taskflowEngine
```

---

#### Task 3.2: Test Adapter Integration

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_adapter_integration.ts`

```typescript
/**
 * Integration test: TaskFlowDefinitionAdapter in WorkflowLoader
 */
import { describe, it, expect } from 'vitest';
import { WorkflowLoader } from '../../../src/taskflowEngine/loader/WorkflowLoader.js';
import type { InternalWorkflowDefinition } from '../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('Adapter Integration', () => {
  it('should convert TaskFlowDefinition to InternalWorkflowDefinition when loading', async () => {
    const loader = new WorkflowLoader({ basePath: 'tests/fixtures/workflows' });
    
    // Load a workflow file (TaskFlowDefinition format)
    const workflow = await loader.loadWorkflow('tests/fixtures/workflows/sample.json');
    
    // Verify it's converted to InternalWorkflowDefinition
    expect(workflow).toHaveProperty('inputSchema');
    expect(workflow).toHaveProperty('outputSchema');
    expect(workflow).toHaveProperty('outputMapping');
    expect(workflow.steps[0]).toHaveProperty('params');
  });
});
```

---

#### Task 3.3: Test CodeJsSandbox Integration

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_code_js_integration.ts`

```typescript
/**
 * Integration test: CodeJsSandbox in workflow execution
 */
import { describe, it, expect } from 'vitest';
import { TaskFlowEngine } from '../../../src/taskflowEngine/TaskFlowEngine.js';
import type { WorkflowDefinition } from '../../../src/shared/types/workflow.types.js';

describe('CodeJS Sandbox Integration', () => {
  it('should execute JavaScript in sandbox during workflow', async () => {
    const engine = new TaskFlowEngine();
    
    const workflow: WorkflowDefinition = {
      id: 'test-code-js',
      name: 'Test Code JS',
      version: '1.0.0',
      steps: [
        {
          id: 'step1',
          type: 'code_js',
          config: {
            script: 'return { result: input.value * 2 };'
          }
        }
      ]
    };
    
    const result = await engine.execute(workflow, {
      inputs: { value: 5 }
    });
    
    expect(result.status).toBe('completed');
    expect(result.stepResults[0].output).toEqual({ result: 10 });
  });
  
  it('should fail if sandbox is not configured', async () => {
    // This test verifies our fix worked
    const engine = new TaskFlowEngine();
    
    const workflow: WorkflowDefinition = {
      id: 'test-code-js-no-sandbox',
      name: 'Test Code JS No Sandbox',
      version: '1.0.0',
      steps: [
        {
          id: 'step1',
          type: 'code_js',
          config: {
            script: 'return { result: 42 };'
          }
        }
      ]
    };
    
    const result = await engine.execute(workflow, {});
    
    // Should not fail - sandbox should be configured
    expect(result.status).not.toBe('failed');
  });
});
```

---

#### Task 3.4: Test Parallel Execution Integration

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_parallel_execution_integration.ts`

```typescript
/**
 * Integration test: ParallelExecutionManager in workflow
 */
import { describe, it, expect } from 'vitest';
import { TaskFlowEngine } from '../../../src/taskflowEngine/TaskFlowEngine.js';
import type { WorkflowDefinition } from '../../../src/shared/types/workflow.types.js';

describe('Parallel Execution Integration', () => {
  it('should execute parallel steps with resource limits', async () => {
    const engine = new TaskFlowEngine({ maxConcurrentSteps: 2 });
    
    const workflow: WorkflowDefinition = {
      id: 'test-parallel',
      name: 'Test Parallel',
      version: '1.0.0',
      steps: [
        {
          id: 'parallel1',
          type: 'parallel',
          config: {
            steps: ['step1', 'step2', 'step3'],
            maxConcurrency: 2
          }
        },
        {
          id: 'step1',
          type: 'action',
          dependsOn: ['parallel1']
        },
        {
          id: 'step2',
          type: 'action',
          dependsOn: ['parallel1']
        },
        {
          id: 'step3',
          type: 'action',
          dependsOn: ['parallel1']
        }
      ]
    };
    
    const result = await engine.execute(workflow, {});
    
    expect(result.status).toBe('completed');
    expect(result.stepResults).toHaveLength(4); // parallel + 3 steps
  });
});
```

---

#### Task 3.5: Test Langfuse Tracing Integration

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_tracing_integration.ts`

```typescript
/**
 * Integration test: LangfuseTracer in workflow execution
 */
import { describe, it, expect, vi } from 'vitest';
import { TaskFlowEngine } from '../../../src/taskflowEngine/TaskFlowEngine.js';
import { createLangfuseTracer } from '../../../src/taskflowEngine/tracer/LangfuseTracer.js';

describe('Tracing Integration', () => {
  it('should trace workflow execution', async () => {
    const tracer = createLangfuseTracer({ enabled: true });
    const startSpy = vi.spyOn(tracer, 'startWorkflowTrace');
    const endSpy = vi.spyOn(tracer, 'endWorkflowTrace');
    
    // Note: This test requires updating handlers to accept tracer
    // Or creating a custom executor config with tracer
    
    expect(startSpy).toHaveBeenCalled();
    expect(endSpy).toHaveBeenCalled();
  });
});
```

---

#### Task 3.6: Test REST API Integration

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_rest_api_integration.ts`

```typescript
/**
 * Integration test: TaskFlowClient with actual API
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { TaskFlowClient } from '../../../src/taskflowEngine/client/TaskFlowClient.js';
import { createApp } from '../../../src/index.js';
import type { Server } from 'http';

describe('REST API Integration', () => {
  let server: Server;
  let client: TaskFlowClient;
  
  beforeAll(async () => {
    const app = await createApp();
    server = app.listen(0); // Random port
    const address = server.address();
    const port = typeof address === 'object' ? address?.port : 8000;
    client = new TaskFlowClient({ baseUrl: `http://localhost:${port}` });
  });
  
  afterAll(() => {
    server.close();
  });
  
  it('should execute workflow via REST API', async () => {
    // Assumes a test workflow is registered
    const result = await client.executeWorkflow({
      project: 'test',
      workflow: 'sample',
      inputs: { value: 42 }
    });
    
    expect(result.status).toBe('completed');
  });
});
```

---

#### Task 3.7: Test Complete E2E Flow

**File**: `mySwiftAgentCore/tests/integration/taskflowEngine/test_workflow_e2e.ts`

```typescript
/**
 * Integration test: Complete workflow execution flow
 */
import { describe, it, expect } from 'vitest';
import { WorkflowLoader } from '../../../src/taskflowEngine/loader/WorkflowLoader.js';
import { WorkflowRegistry } from '../../../src/taskflowEngine/registry/WorkflowRegistry.js';
import { TaskFlowEngine } from '../../../src/taskflowEngine/TaskFlowEngine.js';

describe('Workflow E2E', () => {
  it('should load, register, and execute workflow', async () => {
    // 1. Load workflow from file
    const loader = new WorkflowLoader({ basePath: 'tests/fixtures/workflows' });
    const workflows = await loader.loadWorkflowsForProject('test');
    expect(workflows.length).toBeGreaterThan(0);
    
    // 2. Register workflow
    const registry = new WorkflowRegistry();
    workflows.forEach(w => registry.registerForProject('test', w));
    
    // 3. Get workflow from registry
    const workflow = registry.getWorkflow('test', workflows[0].name);
    expect(workflow).toBeDefined();
    
    // 4. Execute workflow
    const engine = new TaskFlowEngine();
    const result = await engine.execute(workflow!, { inputs: {} });
    
    expect(result.status).toBe('completed');
  });
});
```

---

### Phase 4: Update Test Configuration (15 minutes)

#### Task 4.1: Update vitest.config.ts

Ensure integration tests are included:

```typescript
// In vitest.config.ts
export default defineConfig({
  test: {
    include: [
      'tests/unit/**/*.test.ts',
      'tests/integration/**/*.test.ts'  // Add this line
    ],
    coverage: {
      include: ['src/**/*.ts'],
      exclude: ['tests/**', 'src/**/*.test.ts']
    }
  }
});
```

---

#### Task 4.2: Create Test Fixtures

```bash
mkdir -p mySwiftAgentCore/tests/fixtures/workflows/test/workflows
```

**File**: `mySwiftAgentCore/tests/fixtures/workflows/test/workflows/sample.json`

```json
{
  "workflow_name": "sample",
  "version": "1.0.0",
  "input_schema": {
    "type": "object",
    "properties": {
      "value": { "type": "number" }
    }
  },
  "output_schema": {
    "type": "object"
  },
  "steps": [
    {
      "id": "step1",
      "type": "transform",
      "description": "Sample transform",
      "config": {
        "transformation": "return { result: input.value * 2 };"
      }
    }
  ]
}
```

---

## Execution Order

1. ✅ **Phase 1**: Fix dead code (Tasks 1.1, 1.2)
2. ✅ **Phase 2**: Fix runtime issues (Task 2.1)
3. ⚠️ **Phase 3**: Create integration tests (Tasks 3.1-3.7)
4. ⚠️ **Phase 4**: Update test configuration (Tasks 4.1-4.2)

**Note**: Phases 1-2 should be completed immediately (P0). Phases 3-4 can be done in next iteration (P1).

---

## Verification Commands

After completing the action plan:

```bash
# Verify adapter is connected
grep -n "TaskFlowDefinitionAdapter.toInternal" mySwiftAgentCore/src/taskflowEngine/loader/WorkflowLoader.ts

# Verify TaskFlowEngine is used
grep -n "TaskFlowEngine" mySwiftAgentCore/src/taskflowEngine/api/handlers.ts

# Verify sandbox is instantiated
grep -n "createCodeJsSandbox()" mySwiftAgentCore/src/taskflowEngine/nodes/index.ts

# Run integration tests
cd mySwiftAgentCore
npm run test:integration

# Verify no dead code
# Re-run this verification script
```

---

## Success Criteria

- [ ] TaskFlowDefinitionAdapter is called in WorkflowLoader
- [ ] TaskFlowEngine facade is used in API handlers
- [ ] CodeJsSandbox is instantiated in default node registry
- [ ] 6 integration test files created and passing
- [ ] All integration tests pass
- [ ] Re-run verification shows 0 dead code

---

## Estimated Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1 (Dead Code Fix) | 1 hour | 🔴 Todo |
| Phase 2 (Runtime Fix) | 30 min | 🔴 Todo |
| Phase 3 (Integration Tests) | 2.5 hours | 🔴 Todo |
| Phase 4 (Test Config) | 15 min | 🔴 Todo |
| **Total** | **4 hours** | |

---

**Action Plan Created**: 2026-01-16  
**Ready for Execution**: Yes  
**Next Step**: Execute Phase 1 (Fix Dead Code)
