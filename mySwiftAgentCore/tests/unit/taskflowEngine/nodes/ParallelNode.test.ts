/**
 * ParallelNode Unit Tests
 *
 * Issue #363: Parallel step execution node
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  ParallelNodeExecutor,
  createParallelNodeExecutor,
} from '../../../../src/taskflowEngine/nodes/ParallelNode.js';
import type { NodeConfig, ExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

describe('ParallelNodeExecutor', () => {
  let executor: ParallelNodeExecutor;
  let context: ExecutionContext;

  beforeEach(() => {
    executor = new ParallelNodeExecutor();
    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {},
    };
  });

  describe('type', () => {
    it('should have type parallel', () => {
      expect(executor.type).toBe('parallel');
    });
  });

  describe('validate', () => {
    it('should validate config with steps array', () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a', 'step_b', 'step_c'],
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should require steps array', () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {},
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('steps array is required');
    });

    it('should reject empty steps array', () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: [],
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('steps array must not be empty');
    });

    it('should validate maxConcurrency if provided', () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a'],
          maxConcurrency: 5,
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should reject invalid maxConcurrency', () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a'],
          maxConcurrency: 0,
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('maxConcurrency must be a positive integer');
    });
  });

  describe('execute', () => {
    it('should return step metadata for parallel execution', async () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a', 'step_b', 'step_c'],
          maxConcurrency: 2,
        },
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(result.output).toMatchObject({
        type: 'parallel_execution',
        steps: ['step_a', 'step_b', 'step_c'],
        maxConcurrency: 2,
        status: 'pending',
      });
    });

    it('should use default maxConcurrency when not specified', async () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a', 'step_b'],
        },
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(result.output).toMatchObject({
        maxConcurrency: undefined,
      });
    });

    it('should handle missing configuration', async () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {},
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('PARALLEL_ERROR');
    });

    it('should include workflow context in output', async () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a'],
        },
      };
      context.workflowId = 'wf_custom';

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(result.output).toMatchObject({
        workflowId: 'wf_custom',
      });
    });

    it('should support failFast option', async () => {
      const config: NodeConfig = {
        nodeId: 'parallel_1',
        type: 'parallel',
        config: {
          steps: ['step_a', 'step_b'],
          failFast: true,
        },
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(result.output).toMatchObject({
        failFast: true,
      });
    });
  });
});

describe('createParallelNodeExecutor factory', () => {
  it('should create a ParallelNodeExecutor instance', () => {
    const executor = createParallelNodeExecutor();
    expect(executor).toBeInstanceOf(ParallelNodeExecutor);
  });
});
