# Integration Action Plan - Issue #364

**Goal**: Fix 2 critical integration gaps and 5 dead code instances  
**Estimated Time**: 1-2 hours  
**Priority**: P0 (Blocking)

---

## Task 1: Integrate Real Validators into ValidationPipeline

**File**: `mySwiftAgentCore/src/taskflowGeneratorAgent/validator/ValidationPipeline.ts`  
**Time**: 15 minutes  
**Priority**: P0

### Current State
```typescript
// Lines 108-118
private createDefaultValidators(): Validator[] {
  return [
    new SchemaValidatorStub(),
    new DependencyValidatorStub(),
    new VariableValidatorStub(),
    new CapabilityValidatorStub(),
    new SecurityValidatorStub(),
  ];
}
```

### Required Changes

1. Add imports at the top of the file:
```typescript
import { SchemaValidator } from './validators/SchemaValidator.js';
import { DependencyValidator } from './validators/DependencyValidator.js';
import { VariableValidator } from './validators/VariableValidator.js';
import { CapabilityValidator } from './validators/CapabilityValidator.js';
import { SecurityValidator } from './validators/SecurityValidator.js';
```

2. Replace the `createDefaultValidators()` method:
```typescript
private createDefaultValidators(): Validator[] {
  return [
    new SchemaValidator(),
    new DependencyValidator(),
    new VariableValidator(),
    new CapabilityValidator(),
    new SecurityValidator(),
  ];
}
```

3. Delete stub validator classes (lines 121-210):
```typescript
// Remove these classes:
// - SchemaValidatorStub
// - DependencyValidatorStub
// - VariableValidatorStub
// - CapabilityValidatorStub
// - SecurityValidatorStub
```

### Verification Steps
```bash
# Run unit tests
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
npm test -- validator/ValidationPipeline.test.ts

# Verify imports
grep -n "import.*Validator" src/taskflowGeneratorAgent/validator/ValidationPipeline.ts

# Verify no stubs remain
grep -n "ValidatorStub" src/taskflowGeneratorAgent/validator/ValidationPipeline.ts
# (Should return no results)
```

---

## Task 2: Mount API Routes in Main Router

**File**: `mySwiftAgentCore/src/api/routes.ts`  
**Time**: 30 minutes  
**Priority**: P0

### Current State
```typescript
// Lines 95-102 (stub endpoint)
app.get('/api/v1/generator', (c) => {
  return c.json({
    service: 'TaskFlow Generator Agent',
    status: 'stub',
    message: 'TaskFlow Generator Agent API is not yet implemented',
  });
});
```

### Required Changes

1. Add imports at the top of the file:
```typescript
import { createGeneratorApi } from '../taskflowGeneratorAgent/api/routes.js';
import type { HandlerDependencies } from '../taskflowGeneratorAgent/api/handlers.js';
```

2. Extend `ApiConfig` interface to include dependencies:
```typescript
export interface ApiConfig {
  serviceName: string;
  version: string;
  startTime: Date;
  myVaultBaseUrl?: string;
  // Add these:
  llmClient?: any;  // Will be properly typed later
  workflowRegistry?: any;  // Will be properly typed later
  langfuseConfig?: {
    enabled?: boolean;
    publicKey?: string;
    secretKey?: string;
    baseUrl?: string;
  };
}
```

3. Replace stub endpoint with real route mounting:
```typescript
// Remove lines 95-102 (stub endpoint)

// Add after health routes mounting (around line 56):
// Mount TaskFlow Generator API if dependencies provided
if (config.llmClient && config.workflowRegistry) {
  const generatorDeps: HandlerDependencies = {
    llmClient: config.llmClient,
    registry: config.workflowRegistry,
    langfuseConfig: config.langfuseConfig,
  };
  
  const generatorApi = createGeneratorApi(generatorDeps);
  app.route('/', generatorApi);
} else {
  // Keep stub for now if dependencies not provided
  app.get('/api/v1/generator', (c) => {
    return c.json({
      service: 'TaskFlow Generator Agent',
      status: 'waiting_for_dependencies',
      message: 'LLM client and workflow registry not configured',
    });
  });
}
```

4. Update `src/index.ts` to provide dependencies:
```typescript
// In createApp() function, before mounting API routes:
// TODO: Initialize dependencies (Issue #364 - Phase 2)
// For now, pass undefined to keep stub endpoint
const apiRoutes = createApiRoutes({
  serviceName: SERVICE_NAME,
  version: VERSION,
  startTime,
  myVaultBaseUrl: process.env['MYVAULT_BASE_URL'],
  // llmClient: undefined,  // TODO: Initialize in Phase 2
  // workflowRegistry: undefined,  // TODO: Initialize in Phase 2
  langfuseConfig: {
    enabled: process.env['LANGFUSE_ENABLED'] === 'true',
    publicKey: process.env['LANGFUSE_PUBLIC_KEY'],
    secretKey: process.env['LANGFUSE_SECRET_KEY'],
    baseUrl: process.env['LANGFUSE_BASE_URL'],
  },
});
```

### Verification Steps
```bash
# Build the project
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
npm run build

# Check imports
grep -n "createGeneratorApi" src/api/routes.ts

# Verify stub is replaced with conditional mounting
grep -n "createGeneratorApi\|waiting_for_dependencies" src/api/routes.ts
```

---

## Task 3: Create Integration Test

**File**: `mySwiftAgentCore/tests/integration/taskflowGeneratorAgent/api.integration.test.ts`  
**Time**: 1 hour  
**Priority**: P1

### Create Test File
```typescript
/**
 * Integration tests for TaskFlow Generator Agent API
 * Issue #364
 */

import { describe, test, expect, beforeAll, afterAll } from 'vitest';
import { Hono } from 'hono';
import { createGeneratorApi } from '../../../src/taskflowGeneratorAgent/api/routes.js';
import type { HandlerDependencies } from '../../../src/taskflowGeneratorAgent/api/handlers.js';

describe('TaskFlow Generator Agent API - Integration', () => {
  let app: Hono;
  let mockLLMClient: any;
  let mockRegistry: any;

  beforeAll(() => {
    // Create mock dependencies
    mockLLMClient = {
      generateStructured: async (prompt: string, schema: any) => ({
        data: {
          workflow_name: 'test_workflow',
          description: 'Test workflow',
          steps: [],
          final_step: 'step_1',
        },
        metadata: {
          model: 'test-model',
          promptTokens: 100,
          completionTokens: 200,
          latencyMs: 1000,
        },
      }),
    };

    mockRegistry = {
      register: async () => ({ success: true }),
    };

    const deps: HandlerDependencies = {
      llmClient: mockLLMClient,
      registry: mockRegistry,
      langfuseConfig: { enabled: false },
    };

    app = createGeneratorApi(deps);
  });

  test('POST /api/v1/generator/workflow/batch - success', async () => {
    const request = {
      tasks: [
        {
          task_id: 'task_1',
          description: 'Test task',
          constraints: {},
        },
      ],
      capabilities: [],
      options: {
        validate_before_register: false,
      },
    };

    const response = await app.request('/api/v1/generator/workflow/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    });

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.success).toBe(true);
    expect(data.workflows).toBeDefined();
  });

  test('POST /api/v1/generator/workflow/batch - validation error', async () => {
    const invalidRequest = {
      tasks: [],  // Empty tasks array
    };

    const response = await app.request('/api/v1/generator/workflow/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(invalidRequest),
    });

    expect(response.status).toBe(400);
    const data = await response.json();
    expect(data.error).toBe('VALIDATION_ERROR');
  });

  test('GET /api/v1/generator/health - success', async () => {
    const response = await app.request('/api/v1/generator/health');

    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.timestamp).toBeDefined();
  });
});
```

### Create Test Directory
```bash
mkdir -p /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore/tests/integration/taskflowGeneratorAgent
```

### Verification Steps
```bash
# Run integration tests
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
npm test -- tests/integration/taskflowGeneratorAgent/api.integration.test.ts

# Verify test file exists
ls -la tests/integration/taskflowGeneratorAgent/api.integration.test.ts
```

---

## Task 4: Cleanup - Remove Stub Validators

**File**: `mySwiftAgentCore/src/taskflowGeneratorAgent/validator/ValidationPipeline.ts`  
**Time**: 5 minutes  
**Priority**: P2 (After Task 1 is complete)

### Action
Delete lines 121-210 (stub validator classes):
- `SchemaValidatorStub`
- `DependencyValidatorStub`
- `VariableValidatorStub`
- `CapabilityValidatorStub`
- `SecurityValidatorStub`

### Verification
```bash
# Verify no stubs remain
grep -n "Stub" src/taskflowGeneratorAgent/validator/ValidationPipeline.ts
# (Should return no results)

# Count lines (should be ~110 lines instead of ~218)
wc -l src/taskflowGeneratorAgent/validator/ValidationPipeline.ts
```

---

## Final Verification

After completing all tasks, run:

```bash
# 1. Run all tests
cd /Users/maenokota/share/work/github_kewton/MySwiftAgent/mySwiftAgentCore
npm test

# 2. Build project
npm run build

# 3. Verify no stub validators
grep -rn "ValidatorStub" src/taskflowGeneratorAgent/

# 4. Verify API routes mounted
grep -n "createGeneratorApi" src/api/routes.ts

# 5. Verify real validators imported
grep -n "import.*Validator.*from.*validators" src/taskflowGeneratorAgent/validator/ValidationPipeline.ts
```

---

## Success Criteria

- [ ] All 5 real validators are imported and used in `ValidationPipeline`
- [ ] Stub validator classes are removed
- [ ] API routes are conditionally mounted in main router
- [ ] Integration test file created and passing
- [ ] All unit tests still pass
- [ ] Build succeeds without errors
- [ ] Re-run verification agent shows PASS status

**Estimated Total Time**: 1-2 hours  
**Dependencies**: None (tasks can be done in parallel except cleanup)  
**Risk**: Low (all fixes are straightforward)
