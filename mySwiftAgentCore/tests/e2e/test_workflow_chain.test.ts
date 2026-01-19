/**
 * E2E Workflow Chain Tests
 *
 * Issue #379: E2E tests for workflow chain execution
 *
 * Test scenarios:
 * - 3-step chain execution (task_001 -> task_002 -> task_003)
 * - stepResults passing between steps
 * - Template variable expansion ($steps.xxx, $input.xxx)
 * - Secrets injection
 * - MSW mock interception
 * - Parallel workflow execution
 * - Error handling and propagation
 */

import { describe, test, expect, beforeAll, afterAll, afterEach } from 'vitest';
import { TaskFlowEngine } from '../../src/taskflowEngine/TaskFlowEngine.js';
import { mockServer } from './mocks/server.js';
import {
  createLlmMockHandler,
  createApiMockHandler,
  createErrorMockHandler,
  requestTracker,
  MOCK_LLM_CONTENT,
} from './mocks/handlers.js';
import {
  expectWorkflowSuccess,
  expectWorkflowFailed,
  expectStepResultsPassed,
  expectNoSecretsLeaked,
  expectParallelExecution,
  expectErrorPropagation,
} from './utils/assertions.js';

// Import test fixtures
import chainWorkflow from './fixtures/workflows/chain-test-workflow.json';
import parallelWorkflow from './fixtures/workflows/parallel-test-workflow.json';
import errorWorkflow from './fixtures/workflows/error-test-workflow.json';

describe('E2E Workflow Chain Tests', () => {
  let engine: TaskFlowEngine;

  // MSW lifecycle
  beforeAll(() => {
    mockServer.start();
  });

  afterEach(() => {
    mockServer.reset();
  });

  afterAll(() => {
    mockServer.stop();
  });

  // Engine setup
  beforeAll(() => {
    engine = new TaskFlowEngine({
      defaultTimeout: 30000,
    });
  });

  /**
   * TC-002: Basic 3-step chain execution
   * AC-2: 3-step chain test scenario
   */
  describe('test_task_chain_success', () => {
    test('should execute 3-step chain workflow successfully', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'test query for e2e' },
          secrets: {
            OPENAI_API_KEY: 'test-api-key-mock',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');
      expect(result.stepResults).toHaveLength(3);

      // Verify step order
      const stepIds = result.stepResults.map((r) => r.stepId);
      expect(stepIds).toEqual(['task_001', 'task_002', 'task_003']);

      // All steps should succeed
      expectWorkflowSuccess(
        {
          success: result.status === 'success',
          workflowId: result.workflowId,
          workflowName: result.workflowName,
          status: result.status,
          stepResults: result.stepResults,
          errors: result.errors,
        },
        { expectedStepCount: 3 }
      );
    });
  });

  /**
   * TC-003: stepResults passing verification
   * AC-3: stepResults passing between steps
   */
  describe('test_step_results_passed_correctly', () => {
    test('should pass stepResults correctly between steps', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'step results test' },
          secrets: {
            OPENAI_API_KEY: 'test-api-key-mock',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // Check task_001 output
      const task001 = result.stepResults.find((r) => r.stepId === 'task_001');
      expect(task001).toBeDefined();
      expect(task001!.output).toBeDefined();

      // Check task_002 received task_001 results (via LLM prompt)
      const task002 = result.stepResults.find((r) => r.stepId === 'task_002');
      expect(task002).toBeDefined();
      expect(task002!.output).toBeDefined();

      // Verify LLM was called with proper context
      const llmCalls = requestTracker.getRequestsByUrl('openai.com');
      expect(llmCalls.length).toBeGreaterThan(0);

      // Check task_003 received task_002 results
      const task003 = result.stepResults.find((r) => r.stepId === 'task_003');
      expect(task003).toBeDefined();
      expect(task003!.output).toBeDefined();

      // Verify response structure
      expectStepResultsPassed(
        {
          success: true,
          workflowId: result.workflowId,
          workflowName: result.workflowName,
          status: result.status,
          stepResults: result.stepResults,
        },
        'task_001',
        'task_002',
        'search_results'
      );
    });
  });

  /**
   * TC-004: Template variable expansion ($steps format)
   * AC-4: Template variable expansion
   */
  describe('test_template_variable_expansion_steps_format', () => {
    test('should expand $steps.stepId.field format correctly', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'template expansion test' },
          secrets: {
            OPENAI_API_KEY: 'test-api-key-mock',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // task_003 uses $steps.task_002.content
      const task003 = result.stepResults.find((r) => r.stepId === 'task_003');
      expect(task003).toBeDefined();

      const output = task003!.output as Record<string, unknown>;
      // The summary should contain the LLM mock content
      expect(output.summary).toBe(MOCK_LLM_CONTENT);
    });
  });

  /**
   * TC-005: Template variable expansion ($input format)
   * AC-4: Template variable expansion
   */
  describe('test_template_variable_expansion_input_format', () => {
    test('should expand $input.field format correctly', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());
      const testQuery = 'input expansion test query';

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: testQuery },
          secrets: {
            OPENAI_API_KEY: 'test-api-key-mock',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // task_003 uses $input.query -> original_query
      const task003 = result.stepResults.find((r) => r.stepId === 'task_003');
      expect(task003).toBeDefined();

      const output = task003!.output as Record<string, unknown>;
      expect(output.original_query).toBe(testQuery);

      // Also check output mapping
      expect(result.metadata?.output).toBeDefined();
      const finalOutput = result.metadata!.output as Record<string, unknown>;
      expect(finalOutput.original_query).toBe(testQuery);
    });
  });

  /**
   * TC-006: Secrets injection verification
   * AC-5: Secrets injection
   */
  describe('test_secrets_injection', () => {
    test('should inject secrets correctly and not leak them', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());
      const secretValue = 'super-secret-api-key-12345';

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'secrets test' },
          secrets: {
            OPENAI_API_KEY: secretValue,
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // Verify LLM was called (which requires the secret)
      const llmCalls = requestTracker.getRequestsByUrl('openai.com');
      expect(llmCalls.length).toBeGreaterThan(0);

      // Verify Authorization header was set
      const llmCall = llmCalls[0];
      expect(llmCall!.headers['authorization']).toContain('Bearer');

      // Verify secret is not leaked in response
      expectNoSecretsLeaked(
        {
          success: result.status === 'success',
          workflowId: result.workflowId,
          workflowName: result.workflowName,
          status: result.status,
          stepResults: result.stepResults,
          metadata: result.metadata,
        },
        [secretValue]
      );
    });
  });

  /**
   * TC-007: MSW mock interception verification
   * AC-7: LLM API cost suppression
   */
  describe('test_msw_mock_intercepts_llm_calls', () => {
    test('should intercept LLM API calls with MSW mock', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'mock interception test' },
          secrets: {
            OPENAI_API_KEY: 'test-mock-key',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // Verify MSW intercepted the request
      const allRequests = requestTracker.getRequests();
      expect(allRequests.length).toBeGreaterThan(0);

      // Verify it was an OpenAI API call
      const llmCalls = requestTracker.getRequestsByUrl('openai.com');
      expect(llmCalls.length).toBe(1);

      // Verify the response came from mock
      const task002 = result.stepResults.find((r) => r.stepId === 'task_002');
      expect(task002).toBeDefined();

      const output = task002!.output as { content: string };
      expect(output.content).toBe(MOCK_LLM_CONTENT);
    });

    test('should complete E2E test quickly with mocks (no real API delay)', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());
      const startTime = Date.now();

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: 'performance test' },
          secrets: {
            OPENAI_API_KEY: 'test-mock-key',
          },
        }
      );

      const duration = Date.now() - startTime;

      // Assert
      expect(result.status).toBe('success');
      // Should complete in under 5 seconds (real API would take longer)
      expect(duration).toBeLessThan(5000);
    });
  });

  /**
   * TC-009: Parallel workflow execution
   * AC-2: Test scenario variety
   */
  describe('test_parallel_workflow_execution', () => {
    test('should execute parallel steps correctly', async () => {
      // Act
      const result = await engine.execute(
        parallelWorkflow as any,
        {
          inputs: { search_query: 'parallel test', category: 'tech' },
        }
      );

      // Assert
      expect(result.status).toBe('success');
      expect(result.stepResults).toHaveLength(4);

      // Verify parallel steps executed
      const parallelA = result.stepResults.find((r) => r.stepId === 'parallel_task_a');
      const parallelB = result.stepResults.find((r) => r.stepId === 'parallel_task_b');

      expect(parallelA).toBeDefined();
      expect(parallelB).toBeDefined();
      expect(parallelA!.status).toBe('success');
      expect(parallelB!.status).toBe('success');

      // Verify merge step received both results
      const mergeStep = result.stepResults.find((r) => r.stepId === 'merge_step');
      expect(mergeStep).toBeDefined();
      expect(mergeStep!.status).toBe('success');

      const mergeOutput = mergeStep!.output as Record<string, unknown>;
      expect(mergeOutput.combined_a).toBe('Processed by task A');
      expect(mergeOutput.combined_b).toBe('Processed by task B');

      // Use custom assertion
      expectParallelExecution(
        {
          success: true,
          workflowId: result.workflowId,
          workflowName: result.workflowName,
          status: result.status,
          stepResults: result.stepResults,
        },
        ['parallel_task_a', 'parallel_task_b']
      );
    });
  });

  /**
   * TC-010: Error handling and propagation
   * AC-2: Test scenario variety
   */
  describe('test_error_handling_propagation', () => {
    test('should handle and propagate errors correctly', async () => {
      // Arrange - Add error mock handler
      mockServer.use(
        createErrorMockHandler('http://mock-error-service/api/test', 500, 'Simulated error')
      );

      // Act
      const result = await engine.execute(
        errorWorkflow as any,
        {
          inputs: { should_fail: true },
        }
      );

      // Assert
      expect(['failed', 'partial_success']).toContain(result.status);
      expect(result.errors).toBeDefined();
      expect(result.errors!.length).toBeGreaterThan(0);

      // Verify error step failed
      const errorStep = result.stepResults.find((r) => r.stepId === 'error_step');
      expect(errorStep).toBeDefined();
      expect(errorStep!.status).toBe('failed');

      // Verify error details
      expectErrorPropagation(
        {
          success: result.status === 'success',
          workflowId: result.workflowId,
          workflowName: result.workflowName,
          status: result.status,
          stepResults: result.stepResults,
          errors: result.errors,
        },
        'error_step',
        'HTTP_ERROR'
      );
    });

    test('should continue with successful steps after error', async () => {
      // Arrange - Successful mock
      mockServer.use(
        createApiMockHandler('http://mock-error-service/api/test', 'POST', {
          success: true,
          message: 'No error this time',
        })
      );

      // Act
      const result = await engine.execute(
        errorWorkflow as any,
        {
          inputs: { should_fail: false },
        }
      );

      // Assert
      expect(result.status).toBe('success');
      expect(result.stepResults.every((r) => r.status === 'success')).toBe(true);
    });
  });

  /**
   * Additional edge case tests
   */
  describe('edge_cases', () => {
    test('should handle empty inputs gracefully', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: {},
          secrets: {
            OPENAI_API_KEY: 'test-api-key',
          },
        }
      );

      // Assert - Should still execute (query will be undefined)
      expect(result.status).toBe('success');
    });

    test('should handle special characters in inputs', async () => {
      // Arrange
      mockServer.use(createLlmMockHandler());
      const specialQuery = "test with 'quotes' and \"double quotes\" and <html> tags";

      // Act
      const result = await engine.execute(
        chainWorkflow as any,
        {
          inputs: { query: specialQuery },
          secrets: {
            OPENAI_API_KEY: 'test-api-key',
          },
        }
      );

      // Assert
      expect(result.status).toBe('success');

      // Verify input was preserved
      const task003 = result.stepResults.find((r) => r.stepId === 'task_003');
      const output = task003!.output as Record<string, unknown>;
      expect(output.original_query).toBe(specialQuery);
    });
  });
});
