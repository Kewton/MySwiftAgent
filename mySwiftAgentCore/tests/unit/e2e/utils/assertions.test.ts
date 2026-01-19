/**
 * Unit Tests for E2E Custom Assertions
 *
 * Issue #379: Tests for E2E assertion utilities
 */

import { describe, test, expect } from 'vitest';
import {
  expectWorkflowSuccess,
  expectWorkflowFailed,
  expectStepOutput,
  expectStepOutputAtPath,
  expectStepResultsPassed,
  expectTemplateExpanded,
  expectNoSecretsLeaked,
  expectWorkflowMetadata,
  expectWithinTimeout,
  expectParallelExecution,
  expectErrorPropagation,
} from '../../../e2e/utils/assertions.js';
import type {
  WorkflowExecuteResponse,
  StepResult,
} from '../../../e2e/utils/client.js';

// Helper to create mock responses
function createMockResponse(
  overrides: Partial<WorkflowExecuteResponse> = {}
): WorkflowExecuteResponse {
  return {
    success: true,
    workflowId: 'test-workflow',
    workflowName: 'Test Workflow',
    status: 'success',
    stepResults: [
      {
        stepId: 'step_001',
        stepName: 'Step 1',
        status: 'success',
        output: { key: 'value' },
      },
    ],
    ...overrides,
  };
}

describe('expectWorkflowSuccess', () => {
  test('should pass for successful workflow', () => {
    const response = createMockResponse();
    expect(() => expectWorkflowSuccess(response)).not.toThrow();
  });

  test('should fail for unsuccessful workflow', () => {
    const response = createMockResponse({
      success: false,
      status: 'failed',
    });
    expect(() => expectWorkflowSuccess(response)).toThrow();
  });

  test('should verify step count when specified', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 's1', stepName: 'S1', status: 'success' },
        { stepId: 's2', stepName: 'S2', status: 'success' },
      ],
    });

    expect(() =>
      expectWorkflowSuccess(response, { expectedStepCount: 2 })
    ).not.toThrow();

    expect(() =>
      expectWorkflowSuccess(response, { expectedStepCount: 3 })
    ).toThrow();
  });

  test('should verify step IDs when specified', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 'step_a', stepName: 'A', status: 'success' },
        { stepId: 'step_b', stepName: 'B', status: 'success' },
      ],
    });

    expect(() =>
      expectWorkflowSuccess(response, { expectedStepIds: ['step_a', 'step_b'] })
    ).not.toThrow();

    expect(() =>
      expectWorkflowSuccess(response, { expectedStepIds: ['step_a', 'step_c'] })
    ).toThrow();
  });

  test('should fail if any step failed', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 's1', stepName: 'S1', status: 'success' },
        { stepId: 's2', stepName: 'S2', status: 'failed' },
      ],
    });

    expect(() => expectWorkflowSuccess(response)).toThrow();
  });
});

describe('expectWorkflowFailed', () => {
  test('should pass for failed workflow', () => {
    const response = createMockResponse({
      success: false,
      status: 'failed',
    });
    expect(() => expectWorkflowFailed(response)).not.toThrow();
  });

  test('should pass for partial_success', () => {
    const response = createMockResponse({
      success: false,
      status: 'partial_success',
    });
    expect(() => expectWorkflowFailed(response)).not.toThrow();
  });

  test('should fail for successful workflow', () => {
    const response = createMockResponse();
    expect(() => expectWorkflowFailed(response)).toThrow();
  });

  test('should verify error code when specified', () => {
    const response = createMockResponse({
      success: false,
      status: 'failed',
      errors: [{ errorCode: 'SPECIFIC_ERROR', errorMessage: 'error' }],
    });

    expect(() =>
      expectWorkflowFailed(response, 'SPECIFIC_ERROR')
    ).not.toThrow();

    expect(() => expectWorkflowFailed(response, 'OTHER_ERROR')).toThrow();
  });
});

describe('expectStepOutput', () => {
  test('should pass when output contains expected fields', () => {
    const stepResult: StepResult = {
      stepId: 'test',
      stepName: 'Test',
      status: 'success',
      output: { field1: 'value1', field2: 123 },
    };

    expect(() =>
      expectStepOutput(stepResult, { field1: 'value1' })
    ).not.toThrow();
  });

  test('should fail when output does not match', () => {
    const stepResult: StepResult = {
      stepId: 'test',
      stepName: 'Test',
      status: 'success',
      output: { field1: 'value1' },
    };

    expect(() =>
      expectStepOutput(stepResult, { field1: 'wrong' })
    ).toThrow();
  });

  test('should fail for failed step', () => {
    const stepResult: StepResult = {
      stepId: 'test',
      stepName: 'Test',
      status: 'failed',
      output: { field1: 'value1' },
    };

    expect(() => expectStepOutput(stepResult, { field1: 'value1' })).toThrow();
  });
});

describe('expectStepOutputAtPath', () => {
  test('should access nested values', () => {
    const stepResult: StepResult = {
      stepId: 'test',
      stepName: 'Test',
      status: 'success',
      output: {
        level1: {
          level2: {
            value: 'deep value',
          },
        },
      },
    };

    expect(() =>
      expectStepOutputAtPath(stepResult, 'level1.level2.value', 'deep value')
    ).not.toThrow();
  });

  test('should fail for wrong path', () => {
    const stepResult: StepResult = {
      stepId: 'test',
      stepName: 'Test',
      status: 'success',
      output: { key: 'value' },
    };

    expect(() =>
      expectStepOutputAtPath(stepResult, 'wrong.path', 'value')
    ).toThrow();
  });
});

describe('expectStepResultsPassed', () => {
  test('should verify steps exist and are successful', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 'source', stepName: 'Source', status: 'success', output: { data: 'test' } },
        { stepId: 'target', stepName: 'Target', status: 'success', output: { received: 'test' } },
      ],
    });

    expect(() =>
      expectStepResultsPassed(response, 'source', 'target', 'data')
    ).not.toThrow();
  });

  test('should fail if source step not found', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 'target', stepName: 'Target', status: 'success', output: {} },
      ],
    });

    expect(() =>
      expectStepResultsPassed(response, 'source', 'target', 'data')
    ).toThrow();
  });
});

describe('expectTemplateExpanded', () => {
  test('should verify value is in output', () => {
    const response = createMockResponse({
      stepResults: [
        {
          stepId: 'test',
          stepName: 'Test',
          status: 'success',
          output: { result: 'expanded value here' },
        },
      ],
    });

    expect(() =>
      expectTemplateExpanded(response, 'test', 'expanded value')
    ).not.toThrow();
  });

  test('should fail if value not found', () => {
    const response = createMockResponse({
      stepResults: [
        {
          stepId: 'test',
          stepName: 'Test',
          status: 'success',
          output: { result: 'other value' },
        },
      ],
    });

    expect(() =>
      expectTemplateExpanded(response, 'test', 'expected value')
    ).toThrow();
  });
});

describe('expectNoSecretsLeaked', () => {
  test('should pass when no secrets in response', () => {
    const response = createMockResponse({
      stepResults: [
        {
          stepId: 'test',
          stepName: 'Test',
          status: 'success',
          output: { data: 'safe data' },
        },
      ],
    });

    expect(() =>
      expectNoSecretsLeaked(response, ['secret123', 'api-key'])
    ).not.toThrow();
  });

  test('should fail when secret found in response', () => {
    const response = createMockResponse({
      stepResults: [
        {
          stepId: 'test',
          stepName: 'Test',
          status: 'success',
          output: { data: 'contains secret123 here' },
        },
      ],
    });

    expect(() =>
      expectNoSecretsLeaked(response, ['secret123'])
    ).toThrow();
  });
});

describe('expectWorkflowMetadata', () => {
  test('should verify metadata fields', () => {
    const response = createMockResponse({
      metadata: { key1: 'value1', key2: 123 },
    });

    expect(() =>
      expectWorkflowMetadata(response, { key1: 'value1' })
    ).not.toThrow();
  });

  test('should fail for missing metadata', () => {
    const response = createMockResponse({
      metadata: undefined,
    });

    expect(() => expectWorkflowMetadata(response, { key: 'value' })).toThrow();
  });
});

describe('expectWithinTimeout', () => {
  test('should pass when within timeout', () => {
    const response = createMockResponse({
      executionTime: 1000,
    });

    expect(() => expectWithinTimeout(response, 5000)).not.toThrow();
  });

  test('should fail when over timeout', () => {
    const response = createMockResponse({
      executionTime: 10000,
    });

    expect(() => expectWithinTimeout(response, 5000)).toThrow();
  });
});

describe('expectParallelExecution', () => {
  test('should verify all parallel steps succeeded', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 'parallel_a', stepName: 'A', status: 'success' },
        { stepId: 'parallel_b', stepName: 'B', status: 'success' },
        { stepId: 'other', stepName: 'Other', status: 'success' },
      ],
    });

    expect(() =>
      expectParallelExecution(response, ['parallel_a', 'parallel_b'])
    ).not.toThrow();
  });

  test('should fail if parallel step failed', () => {
    const response = createMockResponse({
      stepResults: [
        { stepId: 'parallel_a', stepName: 'A', status: 'success' },
        { stepId: 'parallel_b', stepName: 'B', status: 'failed' },
      ],
    });

    expect(() =>
      expectParallelExecution(response, ['parallel_a', 'parallel_b'])
    ).toThrow();
  });
});

describe('expectErrorPropagation', () => {
  test('should verify error on specific step', () => {
    const response = createMockResponse({
      success: false,
      status: 'failed',
      stepResults: [
        {
          stepId: 'error_step',
          stepName: 'Error',
          status: 'failed',
          error: { errorCode: 'TEST_ERROR', errorMessage: 'test error' },
        },
      ],
    });

    expect(() =>
      expectErrorPropagation(response, 'error_step', 'TEST_ERROR')
    ).not.toThrow();
  });

  test('should fail for wrong error code', () => {
    const response = createMockResponse({
      success: false,
      status: 'failed',
      stepResults: [
        {
          stepId: 'error_step',
          stepName: 'Error',
          status: 'failed',
          error: { errorCode: 'ACTUAL_ERROR', errorMessage: 'error' },
        },
      ],
    });

    expect(() =>
      expectErrorPropagation(response, 'error_step', 'EXPECTED_ERROR')
    ).toThrow();
  });
});
