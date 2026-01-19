/**
 * WorkflowReloader Unit Tests
 *
 * Issue #375: Workflow hot reload functionality
 * Issue #378: Partial success model with status field
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WorkflowReloader } from '../../../../src/taskflowEngine/loader/WorkflowReloader.js';
import type { WorkflowLoader } from '../../../../src/taskflowEngine/loader/WorkflowLoader.js';
import type { WorkflowRegistry } from '../../../../src/taskflowEngine/registry/WorkflowRegistry.js';

describe('WorkflowReloader', () => {
  let reloader: WorkflowReloader;
  let mockLoader: WorkflowLoader;
  let mockRegistry: WorkflowRegistry;

  beforeEach(() => {
    mockLoader = {
      loadWorkflow: vi.fn(),
      loadWorkflowsForProject: vi.fn().mockResolvedValue([]),
      listProjects: vi.fn().mockResolvedValue([]),
      validateWorkflow: vi.fn(),
      getBasePath: vi.fn().mockReturnValue('/config/taskflow/projects'),
    } as unknown as WorkflowLoader;

    mockRegistry = {
      registerForProject: vi.fn(),
      getByProject: vi.fn().mockReturnValue([]),
      getWorkflow: vi.fn(),
      unregisterFromProject: vi.fn(),
      listProjects: vi.fn().mockReturnValue([]),
      clear: vi.fn(),
      getStats: vi.fn().mockReturnValue({ totalProjects: 0, totalWorkflows: 0, byProject: {} }),
    } as unknown as WorkflowRegistry;

    reloader = new WorkflowReloader(mockLoader, mockRegistry);
  });

  describe('constructor', () => {
    it('should create reloader instance', () => {
      expect(reloader).toBeInstanceOf(WorkflowReloader);
    });
  });

  describe('reloadWorkflow', () => {
    it('should reload a single workflow', async () => {
      const mockWorkflow = {
        id: 'wf-1',
        name: 'test_workflow',
        version: '1.0',
        inputSchema: { type: 'object', properties: {} },
        outputSchema: { type: 'object', properties: {} },
        steps: [],
        output: {},
      };

      vi.mocked(mockLoader.loadWorkflow).mockResolvedValue(mockWorkflow);

      const result = await reloader.reloadWorkflow(
        'project1',
        '/config/taskflow/projects/project1/workflows/test.json'
      );

      expect(result.success).toBe(true);
      expect(result.workflowName).toBe('test_workflow');
      expect(mockLoader.loadWorkflow).toHaveBeenCalledWith(
        '/config/taskflow/projects/project1/workflows/test.json'
      );
      expect(mockRegistry.registerForProject).toHaveBeenCalledWith('project1', mockWorkflow);
    });

    it('should handle reload failure', async () => {
      vi.mocked(mockLoader.loadWorkflow).mockRejectedValue(new Error('File not found'));

      const result = await reloader.reloadWorkflow('project1', '/nonexistent.json');

      expect(result.success).toBe(false);
      expect(result.error).toBe('File not found');
    });
  });

  describe('reloadProject', () => {
    it('should reload all workflows for a project', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
        {
          id: 'wf-2',
          name: 'workflow2',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);

      const result = await reloader.reloadProject('project1');

      expect(result.success).toBe(true);
      expect(result.reloadedCount).toBe(2);
      expect(result.workflowNames).toEqual(['workflow1', 'workflow2']);
      expect(mockRegistry.registerForProject).toHaveBeenCalledTimes(2);
    });

    it('should handle partial reload failure', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);
      vi.mocked(mockRegistry.registerForProject).mockImplementation(() => {
        throw new Error('Registration failed');
      });

      const result = await reloader.reloadProject('project1');

      expect(result.success).toBe(false);
      expect(result.errors?.length).toBeGreaterThan(0);
    });
  });

  describe('reloadAll', () => {
    it('should reload all projects', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue(['project1', 'project2']);
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ]);

      const result = await reloader.reloadAll();

      expect(result.success).toBe(true);
      expect(result.projectResults).toHaveLength(2);
      expect(mockRegistry.clear).toHaveBeenCalled();
    });

    it('should clear registry before reload', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue([]);

      await reloader.reloadAll();

      expect(mockRegistry.clear).toHaveBeenCalled();
    });
  });

  describe('getLastReloadTime', () => {
    it('should return last reload timestamp', async () => {
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([]);

      const beforeReload = Date.now();
      await reloader.reloadProject('project1');
      const afterReload = Date.now();

      const lastReload = reloader.getLastReloadTime('project1');

      expect(lastReload).toBeDefined();
      expect(lastReload!.getTime()).toBeGreaterThanOrEqual(beforeReload);
      expect(lastReload!.getTime()).toBeLessThanOrEqual(afterReload);
    });

    it('should return undefined for unreloaded project', () => {
      const lastReload = reloader.getLastReloadTime('nonexistent');

      expect(lastReload).toBeUndefined();
    });
  });
});

/**
 * Issue #378: Partial success model tests
 */
describe('WorkflowReloader - status field (Issue #378)', () => {
  let reloader: WorkflowReloader;
  let mockLoader: WorkflowLoader;
  let mockRegistry: WorkflowRegistry;

  beforeEach(() => {
    mockLoader = {
      loadWorkflow: vi.fn(),
      loadWorkflowsForProject: vi.fn().mockResolvedValue([]),
      listProjects: vi.fn().mockResolvedValue([]),
      validateWorkflow: vi.fn(),
      getBasePath: vi.fn().mockReturnValue('/config/taskflow/projects'),
    } as unknown as WorkflowLoader;

    mockRegistry = {
      registerForProject: vi.fn(),
      getByProject: vi.fn().mockReturnValue([]),
      getWorkflow: vi.fn(),
      unregisterFromProject: vi.fn(),
      listProjects: vi.fn().mockReturnValue([]),
      clear: vi.fn(),
      getStats: vi.fn().mockReturnValue({ totalProjects: 0, totalWorkflows: 0, byProject: {} }),
    } as unknown as WorkflowRegistry;

    reloader = new WorkflowReloader(mockLoader, mockRegistry);
  });

  describe('reloadProject - status', () => {
    it('should return status: success when all workflows reload successfully', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
        {
          id: 'wf-2',
          name: 'workflow2',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);

      const result = await reloader.reloadProject('project1');

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.reloadedCount).toBe(2);
      expect(result.failedCount).toBe(0);
    });

    it('should return status: success for empty project', async () => {
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([]);

      const result = await reloader.reloadProject('project1');

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.reloadedCount).toBe(0);
      expect(result.failedCount).toBe(0);
    });

    it('should return status: partial_success when some workflows fail', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
        {
          id: 'wf-2',
          name: 'workflow2',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);

      // First workflow succeeds, second fails
      let callCount = 0;
      vi.mocked(mockRegistry.registerForProject).mockImplementation(() => {
        callCount++;
        if (callCount === 2) {
          throw new Error('Registration failed');
        }
      });

      const result = await reloader.reloadProject('project1');

      expect(result.status).toBe('partial_success');
      expect(result.success).toBe(true); // success is status !== 'failed'
      expect(result.reloadedCount).toBe(1);
      expect(result.failedCount).toBe(1);
      expect(result.errors).toHaveLength(1);
    });

    it('should return status: failed when all workflows fail', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);
      vi.mocked(mockRegistry.registerForProject).mockImplementation(() => {
        throw new Error('Registration failed');
      });

      const result = await reloader.reloadProject('project1');

      expect(result.status).toBe('failed');
      expect(result.success).toBe(false);
      expect(result.reloadedCount).toBe(0);
      expect(result.failedCount).toBe(1);
    });

    it('should include failedCount in result', async () => {
      const mockWorkflows = [
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ];

      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue(mockWorkflows);

      const result = await reloader.reloadProject('project1');

      expect(result).toHaveProperty('failedCount');
      expect(typeof result.failedCount).toBe('number');
    });
  });

  describe('reloadAll - status', () => {
    it('should return status: success when all projects succeed', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue(['project1', 'project2']);
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ]);

      const result = await reloader.reloadAll();

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.projectResults).toHaveLength(2);
      expect(result.projectResults[0]?.status).toBe('success');
      expect(result.projectResults[1]?.status).toBe('success');
    });

    it('should return status: partial_success when some projects fail', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue(['project1', 'project2']);

      // First project loads successfully, second fails
      let projectCallCount = 0;
      vi.mocked(mockLoader.loadWorkflowsForProject).mockImplementation(() => {
        projectCallCount++;
        if (projectCallCount === 1) {
          return Promise.resolve([
            {
              id: 'wf-1',
              name: 'workflow1',
              version: '1.0',
              inputSchema: { type: 'object', properties: {} },
              outputSchema: { type: 'object', properties: {} },
              steps: [],
              output: {},
            },
          ]);
        }
        // Second project has a workflow that fails to register
        return Promise.resolve([
          {
            id: 'wf-2',
            name: 'workflow2',
            version: '1.0',
            inputSchema: { type: 'object', properties: {} },
            outputSchema: { type: 'object', properties: {} },
            steps: [],
            output: {},
          },
        ]);
      });

      // First workflow succeeds, second fails
      let registerCallCount = 0;
      vi.mocked(mockRegistry.registerForProject).mockImplementation(() => {
        registerCallCount++;
        if (registerCallCount === 2) {
          throw new Error('Registration failed');
        }
      });

      const result = await reloader.reloadAll();

      expect(result.status).toBe('partial_success');
      expect(result.success).toBe(true); // success is status !== 'failed'
    });

    it('should return status: failed when all projects fail', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue(['project1']);
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([
        {
          id: 'wf-1',
          name: 'workflow1',
          version: '1.0',
          inputSchema: { type: 'object', properties: {} },
          outputSchema: { type: 'object', properties: {} },
          steps: [],
          output: {},
        },
      ]);
      vi.mocked(mockRegistry.registerForProject).mockImplementation(() => {
        throw new Error('Registration failed');
      });

      const result = await reloader.reloadAll();

      expect(result.status).toBe('failed');
      expect(result.success).toBe(false);
    });

    it('should include status in each projectResult', async () => {
      vi.mocked(mockLoader.listProjects).mockResolvedValue(['project1']);
      vi.mocked(mockLoader.loadWorkflowsForProject).mockResolvedValue([]);

      const result = await reloader.reloadAll();

      expect(result.projectResults[0]).toHaveProperty('status');
      expect(result.projectResults[0]).toHaveProperty('failedCount');
    });
  });
});
