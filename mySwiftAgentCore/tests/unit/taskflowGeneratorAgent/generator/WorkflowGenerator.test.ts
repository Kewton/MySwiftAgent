/**
 * WorkflowGenerator Unit Tests
 *
 * Issue #364: Core workflow generation logic
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { z } from 'zod';
import {
  WorkflowGenerator,
  createWorkflowGenerator,
  type WorkflowGeneratorConfig,
} from '../../../../src/taskflowGeneratorAgent/generator/WorkflowGenerator.js';
import type { LLMClient } from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type {
  TaskGenerationRequest,
  Capability,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';

// Mock LLM Client
const createMockLLMClient = (response?: string): LLMClient => {
  const defaultResponse = JSON.stringify({
    workflow_name: 'test_workflow_task_001',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: { input: { type: 'string' } } },
    output_schema: { type: 'object', properties: { result: { type: 'string' } } },
    steps: [
      {
        id: 'step_1',
        type: 'transform',
        config: {},
        params: { data: '$input' },
      },
    ],
    output: { result: '$steps.step_1.data' },
  });

  return {
    generate: vi.fn().mockResolvedValue({
      content: response ?? defaultResponse,
      model: 'test-model',
      usage: { promptTokens: 100, completionTokens: 50 },
      latencyMs: 500,
    }),
    generateStructured: vi.fn().mockResolvedValue({
      data: JSON.parse(response ?? defaultResponse),
      raw: {
        content: response ?? defaultResponse,
        model: 'test-model',
        usage: { promptTokens: 100, completionTokens: 50 },
        latencyMs: 500,
      },
    }),
    getProviderName: vi.fn().mockReturnValue('mock'),
    getConfig: vi.fn().mockReturnValue({ apiKey: 'test', defaultModel: 'test' }),
  };
};

describe('WorkflowGenerator', () => {
  let generator: WorkflowGenerator;
  let mockLLMClient: LLMClient;

  const task: TaskGenerationRequest = {
    task_id: 'task_001',
    name: 'Test Task',
    description: 'A test task description',
    interface: {
      input: { input: 'string' },
      output: { result: 'string' },
    },
  };

  const capabilities: Capability[] = [
    {
      id: 'user_api',
      name: 'User API',
      category: 'api',
      status: 'available',
    },
  ];

  beforeEach(() => {
    mockLLMClient = createMockLLMClient();
    generator = new WorkflowGenerator({
      llmClient: mockLLMClient,
      maxRetries: 3,
      validateBeforeReturn: true,
    });
  });

  describe('constructor', () => {
    it('should create with config', () => {
      expect(generator).toBeInstanceOf(WorkflowGenerator);
    });

    it('should use default config values', () => {
      const gen = new WorkflowGenerator({ llmClient: mockLLMClient });
      expect(gen).toBeInstanceOf(WorkflowGenerator);
    });
  });

  describe('generateSingle', () => {
    it('should generate workflow for task', async () => {
      const result = await generator.generateSingle(task, capabilities);

      expect(result.workflow_name).toBe('test_workflow_task_001');
      expect(result.steps).toHaveLength(1);
      expect(mockLLMClient.generateStructured).toHaveBeenCalled();
    });

    it('should build prompt with capabilities', async () => {
      await generator.generateSingle(task, capabilities);

      const call = (mockLLMClient.generateStructured as ReturnType<typeof vi.fn>).mock.calls[0];
      const prompt = call[0];

      expect(prompt.system).toContain('TaskFlow');
      expect(prompt.user).toContain('task_001');
      expect(prompt.user).toContain('Test Task');
    });

    it('should validate generated workflow', async () => {
      const result = await generator.generateSingle(task, capabilities);

      expect(result.workflow_name).toBeDefined();
      expect(result.steps).toBeDefined();
      expect(result.input_schema).toBeDefined();
      expect(result.output_schema).toBeDefined();
    });

    it('should retry on failure', async () => {
      const failingClient = createMockLLMClient();
      (failingClient.generateStructured as ReturnType<typeof vi.fn>)
        .mockRejectedValueOnce(new Error('First fail'))
        .mockRejectedValueOnce(new Error('Second fail'))
        .mockResolvedValueOnce({
          data: JSON.parse(JSON.stringify({
            workflow_name: 'test_workflow',
            input_schema: { type: 'object' },
            output_schema: { type: 'object' },
            steps: [{ id: 'step_1', type: 'transform', config: {}, params: {} }],
            output: {},
          })),
          raw: { content: '{}', model: 'test', usage: { promptTokens: 0, completionTokens: 0 }, latencyMs: 0 },
        });

      const retryGenerator = new WorkflowGenerator({
        llmClient: failingClient,
        maxRetries: 3,
        retryDelayMs: 10,
      });

      const result = await retryGenerator.generateSingle(task, capabilities);

      expect(result).toBeDefined();
      expect(failingClient.generateStructured).toHaveBeenCalledTimes(3);
    });

    it('should throw after max retries', async () => {
      const failingClient = createMockLLMClient();
      (failingClient.generateStructured as ReturnType<typeof vi.fn>)
        .mockRejectedValue(new Error('Always fail'));

      const retryGenerator = new WorkflowGenerator({
        llmClient: failingClient,
        maxRetries: 3,
        retryDelayMs: 10,
      });

      await expect(retryGenerator.generateSingle(task, capabilities)).rejects.toThrow();
    });
  });

});

describe('createWorkflowGenerator', () => {
  it('should create WorkflowGenerator instance', () => {
    const mockClient = createMockLLMClient();
    const generator = createWorkflowGenerator({ llmClient: mockClient });

    expect(generator).toBeInstanceOf(WorkflowGenerator);
  });
});
