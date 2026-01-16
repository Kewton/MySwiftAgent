/**
 * ParallelExecutionManager Unit Tests
 *
 * Issue #363: Parallel execution resource management
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  ParallelExecutionManager,
  createParallelExecutionManager,
  type ParallelExecutionConfig,
} from '../../../../src/taskflowEngine/executor/ParallelExecutionManager.js';

describe('ParallelExecutionManager', () => {
  let manager: ParallelExecutionManager;

  beforeEach(() => {
    manager = new ParallelExecutionManager();
  });

  describe('constructor', () => {
    it('should create with default config', () => {
      const m = new ParallelExecutionManager();
      const metrics = m.getMetrics();

      expect(metrics.activeGlobal).toBe(0);
      expect(metrics.queuedTasks).toBe(0);
    });

    it('should create with custom config', () => {
      const config: ParallelExecutionConfig = {
        globalMaxConcurrency: 10,
        workflowMaxConcurrency: 3,
        nodeTypeLimits: {
          api_rest: 5,
          code_js: 2,
          llm: 1,
          transform: 10,
          parallel: 5,
        },
        queueTimeoutMs: 5000,
      };

      const m = new ParallelExecutionManager(config);
      expect(m.getMetrics().activeGlobal).toBe(0);
    });
  });

  describe('execute', () => {
    it('should execute a simple task', async () => {
      const result = await manager.execute('wf_1', 'transform', async () => {
        return 42;
      });

      expect(result).toBe(42);
    });

    it('should track metrics during execution', async () => {
      let metricsSnapshot: ReturnType<typeof manager.getMetrics> | null = null;

      await manager.execute('wf_1', 'transform', async () => {
        metricsSnapshot = manager.getMetrics();
        return 'done';
      });

      expect(metricsSnapshot?.activeGlobal).toBe(1);

      // After completion
      const finalMetrics = manager.getMetrics();
      expect(finalMetrics.activeGlobal).toBe(0);
      expect(finalMetrics.completedTasks).toBe(1);
    });

    it('should track failed tasks', async () => {
      try {
        await manager.execute('wf_1', 'transform', async () => {
          throw new Error('Task failed');
        });
      } catch {
        // Expected
      }

      const metrics = manager.getMetrics();
      expect(metrics.failedTasks).toBe(1);
    });

    it('should respect global concurrency limit', async () => {
      const config: ParallelExecutionConfig = {
        globalMaxConcurrency: 2,
        workflowMaxConcurrency: 10,
        nodeTypeLimits: {
          api_rest: 10,
          code_js: 10,
          llm: 10,
          transform: 10,
          parallel: 10,
        },
        queueTimeoutMs: 30000,
      };

      const m = new ParallelExecutionManager(config);
      const executionOrder: number[] = [];
      let maxConcurrent = 0;

      const tasks = Array(5)
        .fill(null)
        .map((_, i) =>
          m.execute('wf_1', 'transform', async () => {
            const current = m.getMetrics().activeGlobal;
            maxConcurrent = Math.max(maxConcurrent, current);
            await new Promise((resolve) => setTimeout(resolve, 50));
            executionOrder.push(i);
            return i;
          })
        );

      await Promise.all(tasks);

      expect(maxConcurrent).toBeLessThanOrEqual(2);
      expect(executionOrder).toHaveLength(5);
    });

    it('should respect node type limits', async () => {
      const config: ParallelExecutionConfig = {
        globalMaxConcurrency: 100,
        workflowMaxConcurrency: 100,
        nodeTypeLimits: {
          api_rest: 10,
          code_js: 10,
          llm: 1, // Only 1 concurrent LLM
          transform: 10,
          parallel: 10,
        },
        queueTimeoutMs: 30000,
      };

      const m = new ParallelExecutionManager(config);
      let maxLlmConcurrent = 0;

      const tasks = Array(3)
        .fill(null)
        .map(() =>
          m.execute('wf_1', 'llm', async () => {
            const current = m.getMetrics().activeByNodeType.get('llm') || 0;
            maxLlmConcurrent = Math.max(maxLlmConcurrent, current);
            await new Promise((resolve) => setTimeout(resolve, 50));
            return 'done';
          })
        );

      await Promise.all(tasks);

      expect(maxLlmConcurrent).toBe(1);
    });
  });

  describe('executeParallelBlock', () => {
    it('should execute multiple tasks in parallel', async () => {
      const tasks = [
        { nodeType: 'transform' as const, task: async () => 1 },
        { nodeType: 'transform' as const, task: async () => 2 },
        { nodeType: 'transform' as const, task: async () => 3 },
      ];

      const results = await manager.executeParallelBlock('wf_1', tasks);

      expect(results).toHaveLength(3);
      expect(results.every((r) => r.status === 'fulfilled')).toBe(true);
      expect(results.map((r) => r.value)).toEqual([1, 2, 3]);
    });

    it('should handle mixed success and failure', async () => {
      const tasks = [
        { nodeType: 'transform' as const, task: async () => 'success' },
        {
          nodeType: 'transform' as const,
          task: async () => {
            throw new Error('failed');
          },
        },
        { nodeType: 'transform' as const, task: async () => 'also success' },
      ];

      const results = await manager.executeParallelBlock('wf_1', tasks);

      expect(results).toHaveLength(3);
      expect(results[0]?.status).toBe('fulfilled');
      expect(results[1]?.status).toBe('rejected');
      expect(results[2]?.status).toBe('fulfilled');
    });

    it('should return error reason for failed tasks', async () => {
      const tasks = [
        {
          nodeType: 'transform' as const,
          task: async () => {
            throw new Error('Test error');
          },
        },
      ];

      const results = await manager.executeParallelBlock('wf_1', tasks);

      expect(results[0]?.status).toBe('rejected');
      expect(results[0]?.reason?.message).toBe('Test error');
    });
  });

  describe('getMetrics', () => {
    it('should return current metrics', () => {
      const metrics = manager.getMetrics();

      expect(metrics).toHaveProperty('activeGlobal');
      expect(metrics).toHaveProperty('activeByWorkflow');
      expect(metrics).toHaveProperty('activeByNodeType');
      expect(metrics).toHaveProperty('queuedTasks');
      expect(metrics).toHaveProperty('completedTasks');
      expect(metrics).toHaveProperty('failedTasks');
    });

    it('should track by workflow', async () => {
      await manager.execute('wf_1', 'transform', async () => 'a');
      await manager.execute('wf_2', 'transform', async () => 'b');

      const metrics = manager.getMetrics();
      expect(metrics.completedTasks).toBe(2);
    });
  });

  describe('cleanup', () => {
    it('should cleanup workflow resources', async () => {
      await manager.execute('wf_1', 'transform', async () => 'done');

      manager.cleanup('wf_1');

      const metrics = manager.getMetrics();
      expect(metrics.activeByWorkflow.has('wf_1')).toBe(false);
    });

    it('should be safe to cleanup non-existent workflow', () => {
      expect(() => manager.cleanup('non_existent')).not.toThrow();
    });
  });
});

describe('createParallelExecutionManager factory', () => {
  it('should create a ParallelExecutionManager instance', () => {
    const manager = createParallelExecutionManager();
    expect(manager).toBeInstanceOf(ParallelExecutionManager);
  });

  it('should create with custom config', () => {
    const config: ParallelExecutionConfig = {
      globalMaxConcurrency: 5,
      workflowMaxConcurrency: 2,
      nodeTypeLimits: {
        api_rest: 3,
        code_js: 2,
        llm: 1,
        transform: 5,
        parallel: 5,
      },
      queueTimeoutMs: 10000,
    };

    const manager = createParallelExecutionManager(config);
    expect(manager).toBeInstanceOf(ParallelExecutionManager);
  });
});
