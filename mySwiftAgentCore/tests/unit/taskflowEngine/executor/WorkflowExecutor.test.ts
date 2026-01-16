/**
 * WorkflowExecutor Unit Tests
 *
 * Issue #363: Main workflow execution engine
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  WorkflowExecutor,
  createWorkflowExecutor,
} from '../../../../src/taskflowEngine/executor/WorkflowExecutor.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';
import type { NodeRegistry, NodeExecutor } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

describe('WorkflowExecutor', () => {
  let executor: WorkflowExecutor;
  let mockNodeRegistry: NodeRegistry;
  let mockTransformExecutor: NodeExecutor;
  let mockApiRestExecutor: NodeExecutor;

  beforeEach(() => {
    vi.clearAllMocks();

    mockTransformExecutor = {
      type: 'transform',
      validate: vi.fn().mockReturnValue({ valid: true }),
      execute: vi.fn().mockResolvedValue({
        success: true,
        output: { result: 'transformed' },
      }),
    };

    mockApiRestExecutor = {
      type: 'api_rest',
      validate: vi.fn().mockReturnValue({ valid: true }),
      execute: vi.fn().mockResolvedValue({
        success: true,
        output: { status: 200, data: {} },
      }),
    };

    mockNodeRegistry = {
      get: vi.fn().mockImplementation((type: string) => {
        if (type === 'transform') return mockTransformExecutor;
        if (type === 'api_rest') return mockApiRestExecutor;
        return undefined;
      }),
      register: vi.fn(),
      has: vi.fn(),
      getAll: vi.fn(),
    };

    executor = new WorkflowExecutor({
      nodeRegistry: mockNodeRegistry,
    });
  });

  describe('execute', () => {
    it('should execute a simple workflow', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: { template: '{}' },
            params: {},
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('success');
      expect(result.workflowId).toBe('wf_test');
      expect(result.stepResults).toHaveLength(1);
      expect(result.stepResults[0].status).toBe('success');
    });

    it('should handle step execution failure', async () => {
      vi.mocked(mockApiRestExecutor.execute).mockResolvedValue({
        success: false,
        output: null,
        error: { code: 'HTTP_ERROR', message: 'Request failed' },
      });

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'API Call',
            type: 'api_rest',
            config: { url: 'http://example.com' },
            params: {},
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('failed');
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].stepId).toBe('step_1');
    });

    it('should resolve step dependencies', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: { template: '{"data": "initial"}' },
            params: {},
          },
          {
            id: 'step_2',
            name: 'Step 2',
            type: 'transform',
            config: { template: '{"prev": "{{prev}}"}' },
            params: {},
            dependsOn: ['step_1'],
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('success');
      expect(mockTransformExecutor.execute).toHaveBeenCalledTimes(2);
    });

    it('should handle unknown node type', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Unknown Step',
            type: 'unknown_type',
            config: {},
            params: {},
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('failed');
      expect(result.errors[0].errorCode).toBe('UNKNOWN_NODE_TYPE');
    });

    it('should support partial success mode', async () => {
      vi.mocked(mockApiRestExecutor.execute).mockResolvedValue({
        success: false,
        output: null,
        error: { code: 'HTTP_ERROR', message: 'Failed' },
      });

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Transform',
            type: 'transform',
            config: { template: '{"ok": true}' },
            params: {},
          },
          {
            id: 'step_2',
            name: 'API Call',
            type: 'api_rest',
            config: { url: 'http://fail.com' },
            params: {},
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('partial_success');
      expect(result.stepResults.filter((r) => r.status === 'success')).toHaveLength(1);
      expect(result.errors).toHaveLength(1);
    });

    it('should pass inputs to execution', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: { template: '{}' },
            params: { value: '${input.key}' },
          },
        ],
        outputMapping: {},
      };

      await executor.execute(workflow, { inputs: { key: 'testValue' } });

      expect(mockTransformExecutor.execute).toHaveBeenCalled();
    });

    it('should collect execution metrics', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: { template: '{}' },
            params: {},
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.durationMs).toBeGreaterThanOrEqual(0);
      expect(result.startTime).toBeDefined();
      expect(result.endTime).toBeDefined();
    });

    it('should handle steps with failed dependencies', async () => {
      vi.mocked(mockApiRestExecutor.execute).mockResolvedValue({
        success: false,
        output: null,
        error: { code: 'HTTP_ERROR', message: 'Failed' },
      });

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'API Call',
            type: 'api_rest',
            config: { url: 'http://fail.com' },
            params: {},
          },
          {
            id: 'step_2',
            name: 'Dependent Step',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_1'],
          },
        ],
        outputMapping: {},
      };

      const result = await executor.execute(workflow);

      expect(result.status).toBe('failed');
      // step_2 should fail because step_1 failed
      expect(result.errors.some((e) => e.stepId === 'step_2')).toBe(true);
    });
  });

  describe('execution order', () => {
    it('should execute steps in dependency order', async () => {
      const executionOrder: string[] = [];

      vi.mocked(mockTransformExecutor.execute).mockImplementation(async (config) => {
        executionOrder.push(config.nodeId);
        return { success: true, output: {} };
      });

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_c',
            name: 'Step C',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_b'],
          },
          {
            id: 'step_a',
            name: 'Step A',
            type: 'transform',
            config: {},
            params: {},
          },
          {
            id: 'step_b',
            name: 'Step B',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_a'],
          },
        ],
        outputMapping: {},
      };

      await executor.execute(workflow);

      expect(executionOrder).toEqual(['step_a', 'step_b', 'step_c']);
    });
  });
});

describe('createWorkflowExecutor factory', () => {
  it('should create a WorkflowExecutor instance', () => {
    const mockRegistry: NodeRegistry = {
      get: vi.fn(),
      register: vi.fn(),
      has: vi.fn(),
      getAll: vi.fn(),
    };

    const executor = createWorkflowExecutor({ nodeRegistry: mockRegistry });

    expect(executor).toBeInstanceOf(WorkflowExecutor);
  });
});
