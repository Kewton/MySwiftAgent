/**
 * Unit Tests for Sequential and Parallel Executors
 *
 * @module tests/unit/engine/test-executors
 * @see Issue #348
 */

import { executeSequential, executeSingleNode } from '../../../src/engine/executor/sequential-executor';
import { executeParallel, executeParallelWithLimit } from '../../../src/engine/executor/parallel-executor';
import { ContextManager } from '../../../src/engine/context/context-manager';
import { TransformNode } from '../../../src/nodes/transform-node';
import type { TransformStep } from '../../../src/types/taskflow';

describe('Sequential Executor', () => {
  let context: ContextManager;
  let nodes: Map<string, TransformNode>;

  beforeEach(() => {
    context = new ContextManager({ value: 'test' });
    nodes = new Map();
  });

  function createTestNode(id: string, template: string): TransformNode {
    const step: TransformStep = {
      id,
      type: 'transform',
      config: {
        mode: 'template',
        template,
      },
      params: {
        value: '${inputs.value}',
      },
    };
    return new TransformNode(step);
  }

  describe('executeSequential', () => {
    it('should execute nodes in order', async () => {
      const node1 = createTestNode('step1', 'Step 1: {{value}}');
      const node2 = createTestNode('step2', 'Step 2: {{value}}');

      nodes.set('step1', node1);
      nodes.set('step2', node2);

      const result = await executeSequential(['step1', 'step2'], nodes, context);

      expect(result.allSucceeded).toBe(true);
      expect(result.logs.length).toBe(2);
      expect(result.logs[0].nodeId).toBe('step1');
      expect(result.logs[1].nodeId).toBe('step2');
    });

    it('should continue after node failure', async () => {
      const node1 = createTestNode('step1', 'OK');

      // Create a node that will fail (missing template)
      const failingStep: TransformStep = {
        id: 'step2',
        type: 'transform',
        config: {
          mode: 'template',
          // No template provided - will fail
        },
        params: {},
      };
      const node2 = new TransformNode(failingStep);

      const node3 = createTestNode('step3', 'After failure');

      nodes.set('step1', node1);
      nodes.set('step2', node2);
      nodes.set('step3', node3);

      const result = await executeSequential(['step1', 'step2', 'step3'], nodes, context);

      expect(result.allSucceeded).toBe(false);
      expect(result.failedNodeIds).toContain('step2');
      expect(result.logs.length).toBe(3);
    });

    it('should handle missing node gracefully', async () => {
      const node1 = createTestNode('step1', 'OK');
      nodes.set('step1', node1);

      const result = await executeSequential(['step1', 'missing_node'], nodes, context);

      // Should complete with 1 log (missing node is skipped)
      expect(result.logs.length).toBe(1);
    });

    it('should store outputs in context', async () => {
      const node1 = createTestNode('step1', 'Output: test');
      nodes.set('step1', node1);

      await executeSequential(['step1'], nodes, context);

      const output = context.getOutput('step1');
      expect(output).toEqual({ result: 'Output: test' });
    });
  });

  describe('executeSingleNode', () => {
    it('should execute a single node', async () => {
      const node = createTestNode('single', 'Single: {{value}}');
      const result = await executeSingleNode(node, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'Single: test' });
    });

    it('should handle node failure', async () => {
      const step: TransformStep = {
        id: 'failing',
        type: 'transform',
        config: {
          mode: 'template',
          // No template
        },
        params: {},
      };
      const node = new TransformNode(step);

      const result = await executeSingleNode(node, context);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });
});

describe('Parallel Executor', () => {
  let context: ContextManager;
  let nodes: Map<string, TransformNode>;

  beforeEach(() => {
    context = new ContextManager({ value: 'parallel' });
    nodes = new Map();
  });

  function createTestNode(id: string, template: string, delay: number = 0): TransformNode {
    // For testing, we use a simple sync template
    const step: TransformStep = {
      id,
      type: 'transform',
      config: {
        mode: 'template',
        template,
      },
      params: {
        value: '${inputs.value}',
      },
    };
    return new TransformNode(step);
  }

  describe('executeParallel', () => {
    it('should execute all nodes in parallel', async () => {
      const node1 = createTestNode('parallel1', 'P1: {{value}}');
      const node2 = createTestNode('parallel2', 'P2: {{value}}');
      const node3 = createTestNode('parallel3', 'P3: {{value}}');

      nodes.set('parallel1', node1);
      nodes.set('parallel2', node2);
      nodes.set('parallel3', node3);

      const result = await executeParallel(
        ['parallel1', 'parallel2', 'parallel3'],
        nodes,
        context
      );

      expect(result.allSucceeded).toBe(true);
      expect(result.logs.length).toBe(3);
      expect(result.results.size).toBe(3);
    });

    it('should continue if some nodes fail', async () => {
      const node1 = createTestNode('ok1', 'OK');

      const failingStep: TransformStep = {
        id: 'fail',
        type: 'transform',
        config: { mode: 'template' }, // Missing template
        params: {},
      };
      const node2 = new TransformNode(failingStep);

      const node3 = createTestNode('ok2', 'OK');

      nodes.set('ok1', node1);
      nodes.set('fail', node2);
      nodes.set('ok2', node3);

      const result = await executeParallel(['ok1', 'fail', 'ok2'], nodes, context);

      expect(result.allSucceeded).toBe(false);
      expect(result.failedNodeIds).toContain('fail');
      expect(result.logs.length).toBe(3);
    });

    it('should handle all nodes failing', async () => {
      const failingStep1: TransformStep = {
        id: 'fail1',
        type: 'transform',
        config: { mode: 'template' },
        params: {},
      };
      const failingStep2: TransformStep = {
        id: 'fail2',
        type: 'transform',
        config: { mode: 'template' },
        params: {},
      };

      nodes.set('fail1', new TransformNode(failingStep1));
      nodes.set('fail2', new TransformNode(failingStep2));

      const result = await executeParallel(['fail1', 'fail2'], nodes, context);

      expect(result.allSucceeded).toBe(false);
      expect(result.failedNodeIds.length).toBe(2);
    });

    it('should store all outputs in context', async () => {
      const node1 = createTestNode('p1', 'Output 1');
      const node2 = createTestNode('p2', 'Output 2');

      nodes.set('p1', node1);
      nodes.set('p2', node2);

      await executeParallel(['p1', 'p2'], nodes, context);

      expect(context.getOutput('p1')).toEqual({ result: 'Output 1' });
      expect(context.getOutput('p2')).toEqual({ result: 'Output 2' });
    });
  });

  describe('executeParallelWithLimit', () => {
    it('should execute with concurrency limit', async () => {
      // Create 5 nodes
      for (let i = 1; i <= 5; i++) {
        nodes.set(`node${i}`, createTestNode(`node${i}`, `Node ${i}`));
      }

      const nodeIds = ['node1', 'node2', 'node3', 'node4', 'node5'];
      const result = await executeParallelWithLimit(nodeIds, nodes, context, 2);

      expect(result.allSucceeded).toBe(true);
      expect(result.logs.length).toBe(5);
    });

    it('should not batch when under limit', async () => {
      nodes.set('n1', createTestNode('n1', 'N1'));
      nodes.set('n2', createTestNode('n2', 'N2'));

      const result = await executeParallelWithLimit(['n1', 'n2'], nodes, context, 10);

      expect(result.allSucceeded).toBe(true);
      expect(result.logs.length).toBe(2);
    });
  });
});

describe('Executor Integration', () => {
  it('should allow sequential access to parallel results', async () => {
    const context = new ContextManager({ prefix: 'Test' });
    const nodes = new Map<string, TransformNode>();

    // Parallel step 1
    const step1: TransformStep = {
      id: 'parallel_a',
      type: 'transform',
      config: { mode: 'template', template: 'A: {{prefix}}' },
      params: { prefix: '${inputs.prefix}' },
    };
    nodes.set('parallel_a', new TransformNode(step1));

    const step2: TransformStep = {
      id: 'parallel_b',
      type: 'transform',
      config: { mode: 'template', template: 'B: {{prefix}}' },
      params: { prefix: '${inputs.prefix}' },
    };
    nodes.set('parallel_b', new TransformNode(step2));

    // Execute parallel
    await executeParallel(['parallel_a', 'parallel_b'], nodes, context);

    // Now sequential step can access parallel results
    const step3: TransformStep = {
      id: 'combine',
      type: 'transform',
      config: { mode: 'template', template: '{{a}} + {{b}}' },
      params: {
        a: '${parallel_a.output.result}',
        b: '${parallel_b.output.result}',
      },
    };
    nodes.set('combine', new TransformNode(step3));

    const result = await executeSequential(['combine'], nodes, context);

    expect(result.allSucceeded).toBe(true);
    expect(context.getOutput('combine')).toEqual({
      result: 'A: Test + B: Test',
    });
  });
});
