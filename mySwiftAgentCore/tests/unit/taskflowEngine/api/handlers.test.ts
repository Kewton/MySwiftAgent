/**
 * API Handlers Unit Tests
 *
 * Issue #363: REST API handlers for TaskFlow
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  createExecuteHandler,
  createListWorkflowsHandler,
  createGetWorkflowHandler,
  createStatsHandler,
  type HandlerDependencies,
} from '../../../../src/taskflowEngine/api/handlers.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

// Mock Hono context
function createMockContext(body?: unknown, query?: Record<string, string>, params?: Record<string, string>) {
  return {
    req: {
      json: vi.fn().mockResolvedValue(body),
      query: vi.fn().mockImplementation((key: string) => query?.[key]),
      param: vi.fn().mockImplementation((key: string) => params?.[key]),
    },
    json: vi.fn().mockImplementation((data, status) => ({ data, status })),
  };
}

describe('createExecuteHandler', () => {
  let deps: HandlerDependencies;
  let mockWorkflow: InternalWorkflowDefinition;

  beforeEach(() => {
    vi.clearAllMocks();

    mockWorkflow = {
      id: 'wf_test',
      name: 'test_workflow',
      version: '1.0.0',
      steps: [],
      outputMapping: {},
    };

    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn().mockReturnValue(mockWorkflow),
        getByProject: vi.fn(),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn(),
      },
      executor: {
        execute: vi.fn().mockResolvedValue({
          workflowId: 'wf_test',
          workflowName: 'test_workflow',
          status: 'success',
          stepResults: [],
          errors: [],
          recoveryActions: [],
          startTime: new Date(),
          endTime: new Date(),
          durationMs: 100,
          metadata: { output: { result: 'data' } },
        }),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn().mockReturnValue({ valid: true, errors: [] }),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should execute workflow and return result', async () => {
    const handler = createExecuteHandler(deps);
    const ctx = createMockContext({
      project: 'test_project',
      workflow: 'test_workflow',
      inputs: { key: 'value' },
    });

    await handler(ctx as any);

    expect(deps.registry.getWorkflow).toHaveBeenCalledWith('test_project', 'test_workflow');
    expect(deps.executor.execute).toHaveBeenCalled();
    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 'success',
      })
    );
  });

  it('should return 404 when workflow not found', async () => {
    vi.mocked(deps.registry.getWorkflow).mockReturnValue(undefined);

    const handler = createExecuteHandler(deps);
    const ctx = createMockContext({
      project: 'test_project',
      workflow: 'unknown_workflow',
      inputs: {},
    });

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('not found'),
      }),
      404
    );
  });

  it('should return 400 when input validation fails', async () => {
    vi.mocked(deps.validator.validateInputs).mockReturnValue({
      valid: false,
      errors: [{ path: 'name', message: 'name is required', code: 'REQUIRED' }],
    });

    const handler = createExecuteHandler(deps);
    const ctx = createMockContext({
      project: 'test_project',
      workflow: 'test_workflow',
      inputs: { invalid: 'data' },
    });

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: 'Input validation failed',
      }),
      400
    );
  });

  it('should return 400 when request body is missing fields', async () => {
    const handler = createExecuteHandler(deps);
    const ctx = createMockContext({
      // Missing project and workflow
    });

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('required'),
      }),
      400
    );
  });
});

describe('createListWorkflowsHandler', () => {
  let deps: HandlerDependencies;

  beforeEach(() => {
    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn(),
        getByProject: vi.fn().mockReturnValue([
          {
            id: 'wf_1',
            name: 'workflow_1',
            version: '1.0.0',
            steps: [{ id: 's1', name: 'S1', type: 'transform', config: {}, params: {} }],
            outputMapping: {},
          },
          {
            id: 'wf_2',
            name: 'workflow_2',
            version: '2.0.0',
            steps: [],
            outputMapping: {},
          },
        ]),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn(),
      },
      executor: {
        execute: vi.fn(),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn(),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should return list of workflows for project', async () => {
    const handler = createListWorkflowsHandler(deps);
    const ctx = createMockContext(undefined, { project: 'test_project' });

    await handler(ctx as any);

    expect(deps.registry.getByProject).toHaveBeenCalledWith('test_project');
    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        workflows: expect.arrayContaining([
          expect.objectContaining({ name: 'workflow_1' }),
          expect.objectContaining({ name: 'workflow_2' }),
        ]),
      })
    );
  });

  it('should return empty list when no workflows exist', async () => {
    vi.mocked(deps.registry.getByProject).mockReturnValue([]);

    const handler = createListWorkflowsHandler(deps);
    const ctx = createMockContext(undefined, { project: 'empty_project' });

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith({ workflows: [] });
  });

  it('should return 400 when project is not specified', async () => {
    const handler = createListWorkflowsHandler(deps);
    const ctx = createMockContext(undefined, {});

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('required'),
      }),
      400
    );
  });
});

describe('createGetWorkflowHandler', () => {
  let deps: HandlerDependencies;

  beforeEach(() => {
    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn().mockReturnValue({
          id: 'wf_test',
          name: 'test_workflow',
          version: '1.0.0',
          steps: [
            { id: 'step_1', name: 'Step 1', type: 'transform', config: {}, params: {} },
          ],
          outputMapping: {},
        }),
        getByProject: vi.fn(),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn(),
      },
      executor: {
        execute: vi.fn(),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn(),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should return workflow details', async () => {
    const handler = createGetWorkflowHandler(deps);
    const ctx = createMockContext(
      undefined,
      { project: 'test_project' },
      { name: 'test_workflow' }
    );

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        workflow_name: 'test_workflow',
        version: '1.0.0',
      })
    );
  });

  it('should return 404 when workflow not found', async () => {
    vi.mocked(deps.registry.getWorkflow).mockReturnValue(undefined);

    const handler = createGetWorkflowHandler(deps);
    const ctx = createMockContext(
      undefined,
      { project: 'test_project' },
      { name: 'unknown_workflow' }
    );

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('not found'),
      }),
      404
    );
  });
});

describe('createStatsHandler', () => {
  let deps: HandlerDependencies;

  beforeEach(() => {
    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn(),
        getByProject: vi.fn(),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn().mockReturnValue({
          totalWorkflows: 10,
          totalProjects: 3,
          workflowsByProject: {
            project_a: 5,
            project_b: 3,
            project_c: 2,
          },
        }),
      },
      executor: {
        execute: vi.fn(),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn(),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should return registry statistics', async () => {
    const handler = createStatsHandler(deps);
    const ctx = createMockContext();

    await handler(ctx as any);

    expect(ctx.json).toHaveBeenCalledWith({
      totalWorkflows: 10,
      totalProjects: 3,
      workflowsByProject: expect.any(Object),
    });
  });
});
