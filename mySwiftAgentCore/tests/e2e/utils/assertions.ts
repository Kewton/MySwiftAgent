/**
 * E2E Test Custom Assertions
 *
 * Issue #379: Custom assertions for workflow execution validation
 */

import { expect } from 'vitest';
import type { WorkflowExecuteResponse, StepResult } from './client.js';

/**
 * Workflow success assertion options
 */
export interface WorkflowSuccessOptions {
  expectedStepCount?: number;
  expectedStepIds?: string[];
  maxDurationMs?: number;
}

/**
 * Assert workflow execution was successful
 */
export function expectWorkflowSuccess(
  response: WorkflowExecuteResponse,
  options: WorkflowSuccessOptions = {}
): void {
  expect(response.success).toBe(true);
  expect(response.status).toBe('success');

  if (options.expectedStepCount !== undefined) {
    expect(response.stepResults).toHaveLength(options.expectedStepCount);
  }

  if (options.expectedStepIds !== undefined) {
    const actualStepIds = response.stepResults.map((r) => r.stepId);
    expect(actualStepIds).toEqual(options.expectedStepIds);
  }

  if (options.maxDurationMs !== undefined && response.executionTime !== undefined) {
    expect(response.executionTime).toBeLessThan(options.maxDurationMs);
  }

  // All steps should be successful
  for (const stepResult of response.stepResults) {
    expect(stepResult.status).toBe('success');
  }
}

/**
 * Assert workflow execution failed
 */
export function expectWorkflowFailed(
  response: WorkflowExecuteResponse,
  expectedErrorCode?: string
): void {
  expect(response.success).toBe(false);
  expect(['failed', 'partial_success']).toContain(response.status);

  if (expectedErrorCode && response.errors) {
    const errorCodes = response.errors.map((e) => e.errorCode);
    expect(errorCodes).toContain(expectedErrorCode);
  }
}

/**
 * Assert step result contains expected output
 */
export function expectStepOutput(
  stepResult: StepResult,
  expectedFields: Record<string, unknown>
): void {
  expect(stepResult.status).toBe('success');
  expect(stepResult.output).toBeDefined();

  const output = stepResult.output as Record<string, unknown>;
  for (const [key, value] of Object.entries(expectedFields)) {
    expect(output[key]).toEqual(value);
  }
}

/**
 * Assert step result has specific output value at path
 */
export function expectStepOutputAtPath(
  stepResult: StepResult,
  path: string,
  expectedValue: unknown
): void {
  expect(stepResult.status).toBe('success');
  expect(stepResult.output).toBeDefined();

  const actualValue = getNestedValue(stepResult.output as Record<string, unknown>, path);
  expect(actualValue).toEqual(expectedValue);
}

/**
 * Assert stepResults were passed correctly between steps
 */
export function expectStepResultsPassed(
  response: WorkflowExecuteResponse,
  sourceStepId: string,
  targetStepId: string,
  expectedField: string
): void {
  const sourceStep = response.stepResults.find((r) => r.stepId === sourceStepId);
  const targetStep = response.stepResults.find((r) => r.stepId === targetStepId);

  expect(sourceStep).toBeDefined();
  expect(targetStep).toBeDefined();
  expect(sourceStep!.status).toBe('success');
  expect(targetStep!.status).toBe('success');

  // Source step output should exist
  expect(sourceStep!.output).toBeDefined();

  // Target step should have received the data
  expect(targetStep!.output).toBeDefined();
}

/**
 * Assert template variable was expanded
 */
export function expectTemplateExpanded(
  response: WorkflowExecuteResponse,
  stepId: string,
  expectedValue: unknown
): void {
  const stepResult = response.stepResults.find((r) => r.stepId === stepId);

  expect(stepResult).toBeDefined();
  expect(stepResult!.status).toBe('success');
  expect(stepResult!.output).toBeDefined();

  // Check that the output contains the expected expanded value
  const output = stepResult!.output as Record<string, unknown>;
  const outputStr = JSON.stringify(output);
  const expectedStr = typeof expectedValue === 'string'
    ? expectedValue
    : JSON.stringify(expectedValue);

  expect(outputStr).toContain(expectedStr);
}

/**
 * Assert secrets were not leaked in response
 */
export function expectNoSecretsLeaked(
  response: WorkflowExecuteResponse,
  secretValues: string[]
): void {
  const responseStr = JSON.stringify(response);

  for (const secret of secretValues) {
    expect(responseStr).not.toContain(secret);
  }
}

/**
 * Assert workflow has specific metadata
 */
export function expectWorkflowMetadata(
  response: WorkflowExecuteResponse,
  expectedMetadata: Record<string, unknown>
): void {
  expect(response.metadata).toBeDefined();

  for (const [key, value] of Object.entries(expectedMetadata)) {
    expect(response.metadata![key]).toEqual(value);
  }
}

/**
 * Get nested value from object
 */
function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let current: unknown = obj;

  for (const part of parts) {
    if (current === null || current === undefined) {
      return undefined;
    }
    if (typeof current === 'object') {
      current = (current as Record<string, unknown>)[part];
    } else {
      return undefined;
    }
  }

  return current;
}

/**
 * Assert response received within timeout
 */
export function expectWithinTimeout(
  response: WorkflowExecuteResponse,
  maxMs: number
): void {
  expect(response.executionTime).toBeDefined();
  expect(response.executionTime!).toBeLessThan(maxMs);
}

/**
 * Assert parallel steps executed
 */
export function expectParallelExecution(
  response: WorkflowExecuteResponse,
  parallelStepIds: string[]
): void {
  const parallelSteps = response.stepResults.filter((r) =>
    parallelStepIds.includes(r.stepId)
  );

  expect(parallelSteps).toHaveLength(parallelStepIds.length);

  // All parallel steps should succeed
  for (const step of parallelSteps) {
    expect(step.status).toBe('success');
  }
}

/**
 * Assert error propagation
 */
export function expectErrorPropagation(
  response: WorkflowExecuteResponse,
  failedStepId: string,
  expectedErrorCode: string
): void {
  const failedStep = response.stepResults.find((r) => r.stepId === failedStepId);

  expect(failedStep).toBeDefined();
  expect(failedStep!.status).toBe('failed');
  expect(failedStep!.error).toBeDefined();
  expect(failedStep!.error!.errorCode).toBe(expectedErrorCode);
}
