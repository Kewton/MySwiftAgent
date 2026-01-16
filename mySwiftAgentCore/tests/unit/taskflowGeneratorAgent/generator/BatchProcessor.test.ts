/**
 * BatchProcessor Unit Tests
 *
 * Issue #364: Parallel batch generation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  BatchProcessor,
  createBatchProcessor,
  type BatchProcessorConfig,
} from '../../../../src/taskflowGeneratorAgent/generator/BatchProcessor.js';
import type { WorkflowGenerator } from '../../../../src/taskflowGeneratorAgent/generator/WorkflowGenerator.js';
import type {
  TaskGenerationRequest,
  Capability,
  BatchGenerationRequest,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

// Mock WorkflowGenerator
const createMockGenerator = (
  shouldFail: Set<string> = new Set()
): WorkflowGenerator => {
  return {
    generateSingle: vi.fn().mockImplementation(
      (task: TaskGenerationRequest): Promise<TaskFlowDefinition> => {
        if (shouldFail.has(task.task_id)) {
          return Promise.reject(new Error(`Failed for ${task.task_id}`));
        }
        return Promise.resolve({
          workflow_name: `workflow_${task.task_id}`,
          input_schema: { type: 'object' },
          output_schema: { type: 'object' },
          steps: [{ id: 'step_1', type: 'transform', config: {}, params: {} }],
          output: {},
        } as TaskFlowDefinition);
      }
    ),
    generateWithMetadata: vi.fn(),
  } as unknown as WorkflowGenerator;
};

describe('BatchProcessor', () => {
  let processor: BatchProcessor;
  let mockGenerator: WorkflowGenerator;

  const capabilities: Capability[] = [
    { id: 'api_1', name: 'API 1', category: 'api', status: 'available' },
  ];

  const createTasks = (count: number): TaskGenerationRequest[] =>
    Array.from({ length: count }, (_, i) => ({
      task_id: `task_${i + 1}`,
      name: `Task ${i + 1}`,
      description: `Description ${i + 1}`,
      interface: { input: {}, output: {} },
    }));

  beforeEach(() => {
    mockGenerator = createMockGenerator();
    processor = new BatchProcessor({
      generator: mockGenerator,
      maxConcurrency: 3,
      timeoutPerTaskMs: 30000,
    });
  });

  describe('constructor', () => {
    it('should create with config', () => {
      expect(processor).toBeInstanceOf(BatchProcessor);
    });

    it('should use default config values', () => {
      const proc = new BatchProcessor({ generator: mockGenerator });
      expect(proc).toBeInstanceOf(BatchProcessor);
    });
  });

  describe('processBatch', () => {
    it('should process all tasks successfully', async () => {
      const tasks = createTasks(3);

      const result = await processor.processBatch({
        tasks,
        capabilities,
        project_id: 'test_project',
      });

      expect(result.success).toBe(true);
      expect(Object.keys(result.workflows)).toHaveLength(3);
      expect(result.failed_tasks).toHaveLength(0);
    });

    it('should handle partial failures', async () => {
      const failingGenerator = createMockGenerator(new Set(['task_2']));
      const failingProcessor = new BatchProcessor({
        generator: failingGenerator,
        maxConcurrency: 3,
      });

      const tasks = createTasks(3);

      const result = await failingProcessor.processBatch({
        tasks,
        capabilities,
        project_id: 'test_project',
      });

      expect(result.success).toBe(false);
      expect(Object.keys(result.workflows)).toHaveLength(2);
      expect(result.failed_tasks).toHaveLength(1);
      expect(result.failed_tasks[0].task_id).toBe('task_2');
    });

    it('should respect max concurrency', async () => {
      const concurrencyTracker: number[] = [];
      let currentConcurrency = 0;

      const trackingGenerator = {
        generateSingle: vi.fn().mockImplementation(async (task: TaskGenerationRequest) => {
          currentConcurrency++;
          concurrencyTracker.push(currentConcurrency);

          // Simulate work
          await new Promise((resolve) => setTimeout(resolve, 50));

          currentConcurrency--;

          return {
            workflow_name: `workflow_${task.task_id}`,
            input_schema: { type: 'object' },
            output_schema: { type: 'object' },
            steps: [{ id: 'step_1', type: 'transform', config: {}, params: {} }],
            output: {},
          } as TaskFlowDefinition;
        }),
      } as unknown as WorkflowGenerator;

      const limitedProcessor = new BatchProcessor({
        generator: trackingGenerator,
        maxConcurrency: 2,
      });

      const tasks = createTasks(5);

      await limitedProcessor.processBatch({
        tasks,
        capabilities,
        project_id: 'test_project',
      });

      // Check that concurrency never exceeded limit
      const maxObservedConcurrency = Math.max(...concurrencyTracker);
      expect(maxObservedConcurrency).toBeLessThanOrEqual(2);
    });

    it('should use options from request', async () => {
      const customProcessor = new BatchProcessor({
        generator: mockGenerator,
        maxConcurrency: 5, // Default
      });

      const tasks = createTasks(3);
      const request: BatchGenerationRequest = {
        tasks,
        capabilities,
        project_id: 'test_project',
        options: {
          max_concurrency: 1, // Override
        },
      };

      const result = await customProcessor.processBatch(request);

      expect(result.success).toBe(true);
      expect(Object.keys(result.workflows)).toHaveLength(3);
    });

    it('should include task errors with recovery suggestions', async () => {
      const failingGenerator = createMockGenerator(new Set(['task_1']));
      const failingProcessor = new BatchProcessor({
        generator: failingGenerator,
      });

      const tasks = createTasks(2);

      const result = await failingProcessor.processBatch({
        tasks,
        capabilities,
        project_id: 'test_project',
      });

      expect(result.failed_tasks[0]).toMatchObject({
        task_id: 'task_1',
        error_type: expect.any(String),
        message: expect.any(String),
        recoverable: expect.any(Boolean),
      });
    });

    it('should handle empty task list', async () => {
      const result = await processor.processBatch({
        tasks: [],
        capabilities,
        project_id: 'test_project',
      });

      expect(result.success).toBe(true);
      expect(Object.keys(result.workflows)).toHaveLength(0);
      expect(result.failed_tasks).toHaveLength(0);
    });
  });

  describe('parallel execution', () => {
    it('should execute tasks in parallel', async () => {
      const startTimes: number[] = [];
      const endTimes: number[] = [];

      const timingGenerator = {
        generateSingle: vi.fn().mockImplementation(async () => {
          startTimes.push(Date.now());
          await new Promise((resolve) => setTimeout(resolve, 100));
          endTimes.push(Date.now());

          return {
            workflow_name: 'test',
            input_schema: { type: 'object' },
            output_schema: { type: 'object' },
            steps: [],
            output: {},
          } as TaskFlowDefinition;
        }),
      } as unknown as WorkflowGenerator;

      const parallelProcessor = new BatchProcessor({
        generator: timingGenerator,
        maxConcurrency: 3,
      });

      const tasks = createTasks(3);

      const overallStart = Date.now();
      await parallelProcessor.processBatch({
        tasks,
        capabilities,
        project_id: 'test',
      });
      const overallEnd = Date.now();

      // If truly parallel, total time should be ~100ms, not ~300ms
      expect(overallEnd - overallStart).toBeLessThan(250);
    });
  });
});

describe('createBatchProcessor', () => {
  it('should create BatchProcessor instance', () => {
    const mockGenerator = createMockGenerator();
    const processor = createBatchProcessor({ generator: mockGenerator });

    expect(processor).toBeInstanceOf(BatchProcessor);
  });
});
