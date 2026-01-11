/**
 * Tests for Conditional Executor
 *
 * @module tests/unit/engine/executor/conditional-executor
 * @see Issue #348
 */

import {
  executeConditional,
  MAX_NESTING_DEPTH,
  type ConditionalExecutionResult,
  type ConditionalBlock,
} from '../../../../src/engine/executor/conditional-executor.js';
import { ContextManager } from '../../../../src/engine/context/context-manager.js';
import { BaseNode } from '../../../../src/nodes/base-node.js';

// Mock node for testing
class MockNode extends BaseNode {
  private mockOutput: unknown;
  private shouldFail: boolean;

  constructor(id: string, mockOutput: unknown = { result: 'success' }, shouldFail: boolean = false) {
    super({
      id,
      type: 'transform',
      config: { mode: 'template', template: '' },
    });
    this.mockOutput = mockOutput;
    this.shouldFail = shouldFail;
  }

  protected async executeInternal(
    _params: Record<string, unknown>,
    _context: ContextManager
  ): Promise<unknown> {
    if (this.shouldFail) {
      throw new Error('Mock error');
    }
    return this.mockOutput;
  }
}

describe('Conditional Executor', () => {
  let context: ContextManager;
  let nodes: Map<string, BaseNode>;

  beforeEach(() => {
    context = new ContextManager({ userId: 'user123' });
    nodes = new Map();

    // Set up initial output for condition evaluation
    context.setOutput('check_status', { status: 'active' });
    context.setOutput('count', { value: 150 });
  });

  describe('executeConditional', () => {
    it('should execute then branch when condition is true', async () => {
      const thenNode = new MockNode('then_action', { message: 'then executed' });
      nodes.set('then_action', thenNode);

      const block: ConditionalBlock = {
        type: 'conditional',
        condition: "${check_status.output.status} == 'active'",
        then: [{ id: 'then_action', type: 'transform', config: { mode: 'template' } }],
        else: [],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.conditionResult).toBe(true);
      expect(result.branchTaken).toBe('then');
      expect(result.allSucceeded).toBe(true);
      expect(result.logs).toHaveLength(1);
      expect(result.logs[0].nodeId).toBe('then_action');
    });

    it('should execute else branch when condition is false', async () => {
      const elseNode = new MockNode('else_action', { message: 'else executed' });
      nodes.set('else_action', elseNode);

      const block: ConditionalBlock = {
        type: 'conditional',
        condition: "${check_status.output.status} == 'inactive'",
        then: [{ id: 'then_action', type: 'transform', config: { mode: 'template' } }],
        else: [{ id: 'else_action', type: 'transform', config: { mode: 'template' } }],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.conditionResult).toBe(false);
      expect(result.branchTaken).toBe('else');
      expect(result.allSucceeded).toBe(true);
      expect(result.logs).toHaveLength(1);
      expect(result.logs[0].nodeId).toBe('else_action');
    });

    it('should return none branch when condition is false and no else', async () => {
      const block: ConditionalBlock = {
        type: 'conditional',
        condition: "${check_status.output.status} == 'inactive'",
        then: [{ id: 'then_action', type: 'transform', config: { mode: 'template' } }],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.conditionResult).toBe(false);
      expect(result.branchTaken).toBe('none');
      expect(result.logs).toHaveLength(0);
    });

    it('should handle numeric comparison', async () => {
      const thenNode = new MockNode('high_count', { message: 'count is high' });
      nodes.set('high_count', thenNode);

      const block: ConditionalBlock = {
        type: 'conditional',
        condition: '${count.output.value} > 100',
        then: [{ id: 'high_count', type: 'transform', config: { mode: 'template' } }],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.conditionResult).toBe(true);
      expect(result.branchTaken).toBe('then');
    });

    it('should handle node failures in branch', async () => {
      const failingNode = new MockNode('failing_action', {}, true);
      nodes.set('failing_action', failingNode);

      const block: ConditionalBlock = {
        type: 'conditional',
        condition: "${check_status.output.status} == 'active'",
        then: [{ id: 'failing_action', type: 'transform', config: { mode: 'template' } }],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.conditionResult).toBe(true);
      expect(result.allSucceeded).toBe(false);
      expect(result.failedNodeIds).toContain('failing_action');
    });

    it('should handle multiple steps in a branch', async () => {
      const node1 = new MockNode('step1', { value: 1 });
      const node2 = new MockNode('step2', { value: 2 });
      nodes.set('step1', node1);
      nodes.set('step2', node2);

      const block: ConditionalBlock = {
        type: 'conditional',
        condition: "${check_status.output.status} == 'active'",
        then: [
          { id: 'step1', type: 'transform', config: { mode: 'template' } },
          { id: 'step2', type: 'transform', config: { mode: 'template' } },
        ],
      };

      const result = await executeConditional(block, nodes, context);

      expect(result.allSucceeded).toBe(true);
      expect(result.logs).toHaveLength(2);
    });

    describe('nesting depth limit', () => {
      it('should enforce MAX_NESTING_DEPTH limit', async () => {
        // Build deeply nested conditional block
        let deepBlock: ConditionalBlock = {
          type: 'conditional',
          condition: "${check_status.output.status} == 'active'",
          then: [{ id: 'deep_action', type: 'transform', config: { mode: 'template' } }],
        };

        // Nest beyond limit
        for (let i = 0; i < MAX_NESTING_DEPTH + 2; i++) {
          deepBlock = {
            type: 'conditional',
            condition: "${check_status.output.status} == 'active'",
            then: [deepBlock as any],
          };
        }

        const result = await executeConditional(deepBlock, nodes, context);

        // Should fail due to depth limit
        expect(result.allSucceeded).toBe(false);
        expect(result.failedNodeIds).toContain('__conditional__');
      });

      it('should allow nesting within limit', async () => {
        const innerNode = new MockNode('inner_action', { result: 'inner' });
        nodes.set('inner_action', innerNode);

        // Create nested conditional within limit
        const innerBlock: ConditionalBlock = {
          type: 'conditional',
          condition: "${check_status.output.status} == 'active'",
          then: [{ id: 'inner_action', type: 'transform', config: { mode: 'template' } }],
        };

        const outerBlock: ConditionalBlock = {
          type: 'conditional',
          condition: "${check_status.output.status} == 'active'",
          then: [innerBlock as any],
        };

        const result = await executeConditional(outerBlock, nodes, context);

        expect(result.allSucceeded).toBe(true);
        expect(result.logs).toHaveLength(1);
        expect(result.logs[0].nodeId).toBe('inner_action');
      });
    });

    describe('parallel steps within conditional', () => {
      it('should handle parallel blocks within then branch', async () => {
        const parallelNode1 = new MockNode('parallel1', { p: 1 });
        const parallelNode2 = new MockNode('parallel2', { p: 2 });
        nodes.set('parallel1', parallelNode1);
        nodes.set('parallel2', parallelNode2);

        const block: ConditionalBlock = {
          type: 'conditional',
          condition: "${check_status.output.status} == 'active'",
          then: [
            {
              type: 'parallel',
              steps: [
                { id: 'parallel1', type: 'transform', config: { mode: 'template' } },
                { id: 'parallel2', type: 'transform', config: { mode: 'template' } },
              ],
            },
          ],
        };

        const result = await executeConditional(block, nodes, context);

        expect(result.allSucceeded).toBe(true);
        expect(result.logs).toHaveLength(2);
      });
    });
  });

  describe('MAX_NESTING_DEPTH constant', () => {
    it('should be exported and equal to 10', () => {
      expect(MAX_NESTING_DEPTH).toBe(10);
    });
  });
});
