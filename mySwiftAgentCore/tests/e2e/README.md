# E2E Tests for TaskFlowEngine

Issue #379: Workflow chain E2E testing infrastructure

## Overview

This directory contains end-to-end tests for the TaskFlowEngine workflow execution system.
The tests verify:

- Workflow chain execution (task_001 -> task_002 -> task_003)
- stepResults passing between steps
- Template variable expansion (`$steps.xxx`, `$input.xxx`)
- Secrets injection
- Parallel workflow execution
- Error handling and propagation

## Directory Structure

```
tests/e2e/
|-- test_workflow_chain.test.ts   # Main E2E test file
|-- setup.ts                      # Test environment setup
|-- fixtures/
|   +-- workflows/
|       |-- chain-test-workflow.json     # 3-step chain test
|       |-- parallel-test-workflow.json  # Parallel execution test
|       +-- error-test-workflow.json     # Error handling test
|-- mocks/
|   |-- handlers.ts               # MSW mock handlers
|   +-- server.ts                 # MSW server configuration
+-- utils/
    |-- client.ts                 # API client for E2E tests
    +-- assertions.ts             # Custom test assertions
```

## Running E2E Tests

### Prerequisites

- Node.js 20+
- npm installed

### Commands

```bash
# Run all E2E tests
npm run test:e2e

# Run with watch mode
npm run test:e2e:watch

# Run specific test file
npm run test:e2e -- test_workflow_chain.test.ts

# Run specific test case
npm run test:e2e -- --grep "should execute 3-step chain"
```

## Mock Service Worker (MSW)

E2E tests use MSW to mock external HTTP calls:

- **LLM APIs**: OpenAI/Anthropic API calls are mocked to avoid costs
- **External APIs**: REST API calls are intercepted and return mock responses

### Why MSW?

1. **No API costs**: Tests don't make real LLM API calls
2. **Fast execution**: No network latency
3. **Deterministic**: Mock responses are predictable
4. **Realistic**: HTTP-level mocking simulates real network behavior

### Custom Mock Handlers

```typescript
import { mockServer, createLlmMockHandler, createApiMockHandler } from './mocks/server';

// Add custom mock for a specific test
mockServer.use(
  createLlmMockHandler({
    choices: [{ message: { content: 'Custom response' } }]
  })
);

// Mock error response
mockServer.use(
  createErrorMockHandler('http://api.com/endpoint', 500, 'Server error')
);
```

## Test Workflows

### chain-test-workflow.json

A 3-step chain workflow:

1. **task_001** (transform): Mock search results
2. **task_002** (llm): Summarize results (mocked)
3. **task_003** (transform): Format output

### parallel-test-workflow.json

Tests parallel execution:

1. **search_step**: Initial data
2. **parallel_task_a** + **parallel_task_b**: Run in parallel
3. **merge_step**: Combine results

### error-test-workflow.json

Tests error handling:

1. **init_step**: Initialize
2. **error_step**: API call that can fail (mocked)
3. **final_step**: Should handle upstream errors

## Custom Assertions

```typescript
import {
  expectWorkflowSuccess,
  expectWorkflowFailed,
  expectStepResultsPassed,
  expectNoSecretsLeaked,
} from './utils/assertions';

// Verify workflow succeeded
expectWorkflowSuccess(response, { expectedStepCount: 3 });

// Verify workflow failed with specific error
expectWorkflowFailed(response, 'HTTP_ERROR');

// Verify step results were passed
expectStepResultsPassed(response, 'task_001', 'task_002', 'search_results');

// Verify secrets not leaked
expectNoSecretsLeaked(response, ['api-key-value']);
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| NODE_ENV | Execution environment | `test` |
| PORT | Server port | `8006` |
| MSW_ENABLED | Enable MSW mocking | `true` |

## CI Integration

E2E tests run automatically on:

- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop`

See `.github/workflows/e2e-test.yml` for CI configuration.

## Adding New Tests

1. Create a new workflow fixture in `fixtures/workflows/`
2. Add mock handlers if needed in `mocks/handlers.ts`
3. Write test cases in a new test file or extend `test_workflow_chain.test.ts`
4. Use custom assertions for consistent validation

## Debugging

### View Intercepted Requests

```typescript
import { requestTracker, getTrackedRequests } from './mocks/handlers';

// After test execution
console.log('Intercepted requests:', getTrackedRequests());
console.log('LLM calls:', getLlmApiCalls());
```

### Disable MSW for Debugging

```typescript
// Temporarily bypass MSW to see real API behavior
mockServer.use(
  http.all('*', ({ request }) => {
    console.log('Request:', request.url);
    return passthrough();
  })
);
```

## Related Documentation

- [design-policy.md](../../dev-reports/feature/issue/379/design-policy.md)
- [work-plan.md](../../dev-reports/feature/issue/379/work-plan.md)
- [acceptance-plan.md](../../dev-reports/feature/issue/379/acceptance-plan.md)
