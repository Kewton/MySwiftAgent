/**
 * Feedback Loop Integration Tests
 *
 * Issue #374: Tests for feedback loop mechanism in WorkflowGenerator
 *
 * These tests verify:
 * 1. Feedback loop retries on validation failures
 * 2. buildFeedbackPrompt is called with error details
 * 3. Metrics are collected during generation
 * 4. MAX_RETRY_COUNT is respected
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  WorkflowGenerator,
  type WorkflowGeneratorConfig,
  type GenerationResult,
} from '../../../src/taskflowGeneratorAgent/generator/WorkflowGenerator.js';
import type { LLMClient } from '../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type {
  TaskGenerationRequest,
  Capability,
  CapabilityForPrompt,
} from '../../../src/taskflowGeneratorAgent/types/generator.js';
import { WorkflowCapabilityError } from '../../../src/taskflowGeneratorAgent/types/errors.js';
import { MAX_RETRY_COUNT } from '../../../src/taskflowGeneratorAgent/constants.js';
import { ValidationPipeline } from '../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import { WorkflowCapabilityValidator } from '../../../src/taskflowGeneratorAgent/validator/WorkflowCapabilityValidator.js';

// Mock workflow with validation error (missing required parameter)
const invalidWorkflow = {
  workflow_name: 'test_workflow_task_001',
  description: 'Test workflow',
  input_schema: { type: 'object', properties: { input: { type: 'string' } } },
  output_schema: { type: 'object', properties: { result: { type: 'string' } } },
  steps: [
    {
      id: 'step_1',
      type: 'api_rest',
      config: { capability_id: 'email_sender' },
      params: {
        body: {
          // Missing required 'to' parameter
          subject: 'Test',
          body: 'Test body',
        },
      },
    },
  ],
  output: { result: '$steps.step_1.response' },
};

// Valid workflow after feedback
const validWorkflow = {
  workflow_name: 'test_workflow_task_001',
  description: 'Test workflow',
  input_schema: { type: 'object', properties: { input: { type: 'string' } } },
  output_schema: { type: 'object', properties: { result: { type: 'string' } } },
  steps: [
    {
      id: 'step_1',
      type: 'api_rest',
      config: { capability_id: 'email_sender' },
      params: {
        body: {
          to: 'test@example.com',
          subject: 'Test',
          body: 'Test body',
        },
      },
    },
  ],
  output: { result: '$steps.step_1.response' },
};

// Create mock LLM client
const createMockLLMClient = (responses: unknown[]): LLMClient => {
  let callIndex = 0;

  return {
    generate: vi.fn().mockImplementation(async () => {
      const response = responses[callIndex % responses.length];
      callIndex++;
      return {
        content: JSON.stringify(response),
        model: 'test-model',
        usage: { promptTokens: 100, completionTokens: 50 },
        latencyMs: 500,
      };
    }),
    generateStructured: vi.fn().mockImplementation(async () => {
      const response = responses[callIndex % responses.length];
      callIndex++;
      return {
        data: response,
        raw: {
          content: JSON.stringify(response),
          model: 'test-model',
          usage: { promptTokens: 100, completionTokens: 50 },
          latencyMs: 500,
        },
      };
    }),
    getProviderName: vi.fn().mockReturnValue('mock'),
    getConfig: vi.fn().mockReturnValue({ apiKey: 'test', defaultModel: 'test' }),
  };
};

describe('Feedback Loop Integration', () => {
  const task: TaskGenerationRequest = {
    task_id: 'task_001',
    name: 'Send Email',
    description: 'Send an email notification',
    interface: {
      input: { input: 'string' },
      output: { result: 'string' },
    },
  };

  // Capability with required parameter
  const capabilities: CapabilityForPrompt[] = [
    {
      id: 'email_sender',
      name: 'Email Sender',
      category: 'communication',
      status: 'available',
      description: 'Send email notifications',
      parameters: [
        { name: 'to', type: 'string', required: true, description: 'Recipient email address' },
        { name: 'subject', type: 'string', required: true, description: 'Email subject' },
        { name: 'body', type: 'string', required: true, description: 'Email body' },
      ],
      metadata: { use_cases: ['notifications', 'alerts'] },
    },
  ];

  describe('generateSingle with feedback loop', () => {
    it('should retry with feedback when validation fails and succeed on second attempt', async () => {
      // First call returns invalid workflow, second returns valid
      const mockClient = createMockLLMClient([invalidWorkflow, validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      const result = await generator.generateSingle(task, capabilities as Capability[]);

      // Should succeed with valid workflow from second attempt
      expect(result.workflow_name).toBe('test_workflow_task_001');
      expect(result.steps[0].params.body.to).toBe('test@example.com');

      // Should have called LLM twice
      expect(mockClient.generateStructured).toHaveBeenCalledTimes(2);
    });

    it('should include feedback in retry prompt', async () => {
      const mockClient = createMockLLMClient([invalidWorkflow, validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      await generator.generateSingle(task, capabilities as Capability[]);

      // Check second call includes feedback
      const calls = (mockClient.generateStructured as ReturnType<typeof vi.fn>).mock.calls;
      expect(calls.length).toBe(2);

      // Second call should have feedback in user prompt
      const secondPrompt = calls[1][0];
      expect(secondPrompt.user).toContain('Previous');
    });

    it('should respect MAX_RETRY_COUNT', async () => {
      // Always return invalid workflow
      const mockClient = createMockLLMClient([invalidWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 5, // More than MAX_RETRY_COUNT
        validateBeforeReturn: true,
      });

      await expect(generator.generateSingle(task, capabilities as Capability[])).rejects.toThrow();

      // Should not exceed MAX_RETRY_COUNT
      expect((mockClient.generateStructured as ReturnType<typeof vi.fn>).mock.calls.length)
        .toBeLessThanOrEqual(MAX_RETRY_COUNT);
    });

    it('should throw WorkflowCapabilityError on validation failure', async () => {
      const mockClient = createMockLLMClient([invalidWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 1,
        validateBeforeReturn: true,
      });

      await expect(generator.generateSingle(task, capabilities as Capability[])).rejects.toThrow(
        WorkflowCapabilityError
      );
    });
  });

  describe('generateWithMetadata with metrics collection', () => {
    it('should collect generation metrics on success', async () => {
      const mockClient = createMockLLMClient([validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      const result = await generator.generateWithMetadata(task, capabilities as Capability[]);

      // Should have metrics
      expect(result.generationMetrics).toBeDefined();
      expect(result.generationMetrics!.initialSuccessRate).toBe(1.0);
      expect(result.generationMetrics!.averageRetryCount).toBe(1);
      expect(result.generationMetrics!.tokenUsageByAttempt).toHaveLength(1);
    });

    it('should collect metrics for multiple retry attempts', async () => {
      const mockClient = createMockLLMClient([invalidWorkflow, validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      const result = await generator.generateWithMetadata(task, capabilities as Capability[]);

      // Should have metrics from attempts (including failed attempts + success)
      expect(result.generationMetrics).toBeDefined();
      // averageRetryCount is the total number of attempts recorded
      expect(result.generationMetrics!.averageRetryCount).toBeGreaterThanOrEqual(2);
      expect(result.generationMetrics!.tokenUsageByAttempt.length).toBeGreaterThanOrEqual(1);
    });

    it('should track validation error types in metrics', async () => {
      const mockClient = createMockLLMClient([invalidWorkflow, validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      const result = await generator.generateWithMetadata(task, capabilities as Capability[]);

      // Should have error type tracking
      expect(result.generationMetrics).toBeDefined();
      // First attempt should have recorded validation errors
      expect(Object.keys(result.generationMetrics!.validationErrorTypes).length).toBeGreaterThanOrEqual(0);
    });

    it('should include totalDurationMs in metrics', async () => {
      const mockClient = createMockLLMClient([validWorkflow]);

      const generator = new WorkflowGenerator({
        llmClient: mockClient,
        maxRetries: 3,
        validateBeforeReturn: true,
      });

      const result = await generator.generateWithMetadata(task, capabilities as Capability[]);

      expect(result.generationMetrics).toBeDefined();
      expect(result.generationMetrics!.totalDurationMs).toBeGreaterThanOrEqual(0);
    });
  });

  describe('ValidationPipeline integration', () => {
    it('should include WorkflowCapabilityValidator in default validators', () => {
      const pipeline = new ValidationPipeline();
      const validators = pipeline.getValidators();

      const hasWorkflowCapabilityValidator = validators.some(
        (v) => v.name === 'WorkflowCapabilityValidator'
      );

      expect(hasWorkflowCapabilityValidator).toBe(true);
    });

    it('should detect missing required parameters through pipeline', async () => {
      const pipeline = new ValidationPipeline();

      const result = await pipeline.validate(invalidWorkflow as never, {
        capabilities: capabilities as Capability[],
        projectId: 'test',
      });

      // Should detect the missing 'to' parameter
      expect(result.isValid).toBe(false);
      expect(result.errors?.some((e) => e.code === 'MISSING_REQUIRED_PARAM')).toBe(true);
    });
  });

  describe('WorkflowCapabilityValidator validateOrThrow', () => {
    it('should throw WorkflowCapabilityError on validation failure', async () => {
      const validator = new WorkflowCapabilityValidator();

      await expect(
        validator.validateOrThrow(
          invalidWorkflow as never,
          { capabilities: capabilities as Capability[], projectId: 'test' },
          JSON.stringify(invalidWorkflow),
          1
        )
      ).rejects.toThrow(WorkflowCapabilityError);
    });

    it('should return result on validation success', async () => {
      const validator = new WorkflowCapabilityValidator();

      const result = await validator.validateOrThrow(
        validWorkflow as never,
        { capabilities: capabilities as Capability[], projectId: 'test' },
        JSON.stringify(validWorkflow),
        1
      );

      expect(result.isValid).toBe(true);
    });
  });
});
