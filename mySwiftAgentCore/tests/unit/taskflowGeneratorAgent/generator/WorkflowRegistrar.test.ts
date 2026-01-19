/**
 * WorkflowRegistrar Unit Tests
 *
 * Issue #370: Integration with WorkflowStorage
 * Issue #378: Partial success model and registerDetailed()
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  WorkflowRegistrar,
  createWorkflowRegistrar,
} from '../../../../src/taskflowGeneratorAgent/generator/WorkflowRegistrar.js';
import { WorkflowRegistry } from '../../../../src/taskflowEngine/registry/WorkflowRegistry.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { Logger } from '../../../../src/utils/logger/Logger.js';
import type { WorkflowStorage, SaveResult } from '../../../../src/taskflowGeneratorAgent/storage/WorkflowStorage.js';
import type { DetailedRegistrationResult, BatchRegistrationSummary } from '../../../../src/taskflowGeneratorAgent/types/registration.js';

describe('WorkflowRegistrar', () => {
  let registrar: WorkflowRegistrar;
  let registry: WorkflowRegistry;
  let mockStorage: WorkflowStorage;
  let mockLogger: Logger;

  const sampleWorkflow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [
      {
        id: 'step_1',
        type: 'api_rest',
        config: { method: 'GET', url: 'https://api.example.com' },
        params: {},
      },
    ],
    output: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();

    registry = new WorkflowRegistry();

    // Create mock storage with proper spy functions
    mockStorage = {
      save: vi.fn().mockResolvedValue({ success: true, filePath: '/test/path.json' } as SaveResult),
      load: vi.fn().mockResolvedValue(undefined),
      loadAll: vi.fn().mockResolvedValue({}),
      exists: vi.fn().mockResolvedValue(false),
      getAllProjects: vi.fn().mockResolvedValue([]),
      delete: vi.fn().mockResolvedValue(true),
      getBaseDir: vi.fn().mockReturnValue('generated/workflows'),
    } as unknown as WorkflowStorage;

    // Create mock logger
    mockLogger = {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
      child: vi.fn().mockReturnThis(),
      getLevel: vi.fn().mockReturnValue('debug'),
    } as unknown as Logger;

    registrar = createWorkflowRegistrar({
      registry,
      storage: mockStorage,
      logger: mockLogger,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('register', () => {
    it('should register workflow to registry', async () => {
      const result = await registrar.register(sampleWorkflow, 'project1');

      expect(result.success).toBe(true);
      const workflows = registry.getByProject('project1');
      expect(workflows).toHaveLength(1);
    });

    it('should save workflow to storage', async () => {
      await registrar.register(sampleWorkflow, 'project1');

      expect(mockStorage.save).toHaveBeenCalledWith(
        'project1',
        'test_workflow',
        sampleWorkflow,
        undefined
      );
    });

    it('should return filePath in result', async () => {
      const result = await registrar.register(sampleWorkflow, 'project1');

      expect(result.success).toBe(true);
      expect(result.filePath).toBe('/test/path.json');
    });

    it('should log registration process', async () => {
      await registrar.register(sampleWorkflow, 'project1');

      expect(mockLogger.info).toHaveBeenCalled();
    });

    it('should use default project if not specified', async () => {
      const result = await registrar.register(sampleWorkflow);

      expect(result.success).toBe(true);
      expect(mockStorage.save).toHaveBeenCalledWith(
        'default',
        'test_workflow',
        sampleWorkflow,
        undefined
      );
    });

    it('should return error if storage fails', async () => {
      vi.mocked(mockStorage.save).mockResolvedValue({
        success: false,
        error: 'Storage error',
      });

      const result = await registrar.register(sampleWorkflow, 'project1');

      expect(result.success).toBe(false);
      expect(result.error).toBe('Storage error');
    });

    it('should still register to memory even if storage fails', async () => {
      vi.mocked(mockStorage.save).mockResolvedValue({
        success: false,
        error: 'Storage error',
      });

      await registrar.register(sampleWorkflow, 'project1');

      const workflows = registry.getByProject('project1');
      expect(workflows).toHaveLength(1);
    });
  });

  describe('registerBatch', () => {
    const workflows: Record<string, TaskFlowDefinition> = {
      task1: { ...sampleWorkflow, workflow_name: 'workflow1' },
      task2: { ...sampleWorkflow, workflow_name: 'workflow2' },
    };

    it('should register multiple workflows', async () => {
      const results = await registrar.registerBatch(workflows, 'project1');

      expect(results['task1']?.success).toBe(true);
      expect(results['task2']?.success).toBe(true);
    });

    it('should save all workflows to storage', async () => {
      await registrar.registerBatch(workflows, 'project1');

      expect(mockStorage.save).toHaveBeenCalledTimes(2);
    });
  });

  describe('initialize', () => {
    it('should load all workflows from storage on initialize', async () => {
      const storedWorkflow: TaskFlowDefinition = {
        ...sampleWorkflow,
        workflow_name: 'stored_workflow',
      };

      vi.mocked(mockStorage.getAllProjects).mockResolvedValue(['project1', 'project2']);
      vi.mocked(mockStorage.loadAll).mockResolvedValue({
        stored_workflow: storedWorkflow,
      });

      await registrar.initialize();

      expect(mockStorage.getAllProjects).toHaveBeenCalled();
      expect(mockStorage.loadAll).toHaveBeenCalledWith('project1');
      expect(mockStorage.loadAll).toHaveBeenCalledWith('project2');
    });

    it('should register loaded workflows to memory cache', async () => {
      const storedWorkflow: TaskFlowDefinition = {
        ...sampleWorkflow,
        workflow_name: 'stored_workflow',
      };

      vi.mocked(mockStorage.getAllProjects).mockResolvedValue(['project1']);
      vi.mocked(mockStorage.loadAll).mockResolvedValue({
        stored_workflow: storedWorkflow,
      });

      await registrar.initialize();

      const workflows = registry.getByProject('project1');
      expect(workflows).toHaveLength(1);
      expect(workflows[0]?.name).toBe('stored_workflow');
    });

    it('should log restoration process', async () => {
      vi.mocked(mockStorage.getAllProjects).mockResolvedValue(['project1']);
      vi.mocked(mockStorage.loadAll).mockResolvedValue({});

      await registrar.initialize();

      expect(mockLogger.info).toHaveBeenCalled();
    });

    it('should handle empty storage gracefully', async () => {
      vi.mocked(mockStorage.getAllProjects).mockResolvedValue([]);

      // Issue #378: initialize() no longer throws even with empty storage
      // It may still load from config directory, so we just verify no error
      await expect(registrar.initialize()).resolves.not.toThrow();
    });
  });

  describe('exists', () => {
    it('should check memory registry', async () => {
      await registrar.register(sampleWorkflow, 'project1');

      expect(registrar.exists('test_workflow', 'project1')).toBe(true);
    });

    it('should return false for non-existent workflow', () => {
      expect(registrar.exists('nonexistent', 'project1')).toBe(false);
    });
  });

  describe('unregister', () => {
    it('should remove workflow from registry', async () => {
      await registrar.register(sampleWorkflow, 'project1');

      const result = registrar.unregister('test_workflow', 'project1');

      expect(result).toBe(true);
      expect(registry.getByProject('project1')).toHaveLength(0);
    });
  });
});

describe('WorkflowRegistrar without storage', () => {
  let registrar: WorkflowRegistrar;
  let registry: WorkflowRegistry;
  let mockLogger: Logger;

  const sampleWorkflow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [],
    output: {},
  };

  beforeEach(() => {
    registry = new WorkflowRegistry();
    mockLogger = {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
      child: vi.fn().mockReturnThis(),
      getLevel: vi.fn().mockReturnValue('debug'),
    } as unknown as Logger;

    registrar = createWorkflowRegistrar({
      registry,
      logger: mockLogger,
      // No storage
    });
  });

  it('should register workflow to memory only', async () => {
    const result = await registrar.register(sampleWorkflow, 'project1');

    expect(result.success).toBe(true);
    expect(result.filePath).toBeUndefined();
  });

  it('should initialize even without storage (Issue #378)', async () => {
    await registrar.initialize();

    // Issue #378: initialize() now always runs, trying config directory first
    expect(mockLogger.info).toHaveBeenCalledWith('Initializing WorkflowRegistrar');
  });
});

describe('createWorkflowRegistrar factory', () => {
  it('should create a WorkflowRegistrar instance', () => {
    const registry = new WorkflowRegistry();
    const registrar = createWorkflowRegistrar({ registry });

    expect(registrar).toBeInstanceOf(WorkflowRegistrar);
  });

  it('should work without logger and storage', async () => {
    const registry = new WorkflowRegistry();
    const registrar = createWorkflowRegistrar({ registry });

    expect(registrar).toBeInstanceOf(WorkflowRegistrar);

    // Should not throw
    const workflow: TaskFlowDefinition = {
      workflow_name: 'test',
      description: 'test',
      input_schema: { type: 'object', properties: {} },
      output_schema: { type: 'object', properties: {} },
      steps: [],
      output: {},
    };
    const result = await registrar.register(workflow);
    expect(result.success).toBe(true);
  });
});

/**
 * Issue #373: taskId propagation tests
 */
describe('WorkflowRegistrar - taskId support (Issue #373)', () => {
  let registrar: WorkflowRegistrar;
  let registry: WorkflowRegistry;
  let mockStorage: WorkflowStorage;
  let mockLogger: Logger;

  const sampleWorkflow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [
      {
        id: 'step_1',
        type: 'api_rest',
        config: { method: 'GET', url: 'https://api.example.com' },
        params: {},
      },
    ],
    output: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();

    registry = new WorkflowRegistry();

    mockStorage = {
      save: vi.fn().mockResolvedValue({ success: true, filePath: '/test/path.json' } as SaveResult),
      load: vi.fn().mockResolvedValue(undefined),
      loadAll: vi.fn().mockResolvedValue({}),
      exists: vi.fn().mockResolvedValue(false),
      getAllProjects: vi.fn().mockResolvedValue([]),
      delete: vi.fn().mockResolvedValue(true),
      getBaseDir: vi.fn().mockReturnValue('generated/workflows'),
    } as unknown as WorkflowStorage;

    mockLogger = {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
      child: vi.fn().mockReturnThis(),
      getLevel: vi.fn().mockReturnValue('debug'),
    } as unknown as Logger;

    registrar = createWorkflowRegistrar({
      registry,
      storage: mockStorage,
      logger: mockLogger,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('register with taskId', () => {
    it('should pass taskId to storage save', async () => {
      await registrar.register(sampleWorkflow, 'project1', 'task_123');

      expect(mockStorage.save).toHaveBeenCalledWith(
        'project1',
        'test_workflow',
        sampleWorkflow,
        'task_123'
      );
    });

    it('should work without taskId (backward compatible)', async () => {
      await registrar.register(sampleWorkflow, 'project1');

      expect(mockStorage.save).toHaveBeenCalledWith(
        'project1',
        'test_workflow',
        sampleWorkflow,
        undefined
      );
    });

    it('should include taskId in log context', async () => {
      await registrar.register(sampleWorkflow, 'project1', 'task_123');

      expect(mockLogger.info).toHaveBeenCalledWith(
        'Registering workflow',
        expect.objectContaining({
          projectId: 'project1',
          workflowName: 'test_workflow',
          taskId: 'task_123',
        })
      );
    });
  });

  describe('registerBatch with taskId', () => {
    const workflows: Record<string, TaskFlowDefinition> = {
      task_1: { ...sampleWorkflow, workflow_name: 'workflow1' },
      task_2: { ...sampleWorkflow, workflow_name: 'workflow2' },
    };

    it('should pass taskId (key) to each register call', async () => {
      await registrar.registerBatch(workflows, 'project1');

      // Each workflow should be registered with its task_id as the taskId
      expect(mockStorage.save).toHaveBeenCalledWith(
        'project1',
        'workflow1',
        workflows['task_1'],
        'task_1'
      );
      expect(mockStorage.save).toHaveBeenCalledWith(
        'project1',
        'workflow2',
        workflows['task_2'],
        'task_2'
      );
    });
  });
});

/**
 * Issue #378: Partial success model tests
 */
describe('WorkflowRegistrar - registerDetailed (Issue #378)', () => {
  let registrar: WorkflowRegistrar;
  let registry: WorkflowRegistry;
  let mockStorage: WorkflowStorage;
  let mockLogger: Logger;

  const sampleWorkflow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [
      {
        id: 'step_1',
        type: 'api_rest',
        config: { method: 'GET', url: 'https://api.example.com' },
        params: {},
      },
    ],
    output: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();

    registry = new WorkflowRegistry();

    mockStorage = {
      save: vi.fn().mockResolvedValue({ success: true, filePath: '/test/path.json' } as SaveResult),
      load: vi.fn().mockResolvedValue(undefined),
      loadAll: vi.fn().mockResolvedValue({}),
      exists: vi.fn().mockResolvedValue(false),
      getAllProjects: vi.fn().mockResolvedValue([]),
      delete: vi.fn().mockResolvedValue(true),
      getBaseDir: vi.fn().mockReturnValue('generated/workflows'),
    } as unknown as WorkflowStorage;

    mockLogger = {
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
      child: vi.fn().mockReturnThis(),
      getLevel: vi.fn().mockReturnValue('debug'),
    } as unknown as Logger;

    registrar = createWorkflowRegistrar({
      registry,
      storage: mockStorage,
      logger: mockLogger,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('registerDetailed - status: success', () => {
    it('should return status: success when both memory and storage succeed', async () => {
      const result = await registrar.registerDetailed(sampleWorkflow, 'project1');

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.memoryRegistered).toBe(true);
      expect(result.storagePersisted).toBe(true);
      expect(result.workflowId).toBe('test_workflow');
      expect(result.filePath).toBe('/test/path.json');
    });

    it('should return status: success without storage configured', async () => {
      const registrarNoStorage = createWorkflowRegistrar({
        registry,
        logger: mockLogger,
        // No storage
      });

      const result = await registrarNoStorage.registerDetailed(sampleWorkflow, 'project1');

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.memoryRegistered).toBe(true);
      expect(result.storagePersisted).toBe(true); // true when no storage is configured
    });
  });

  describe('registerDetailed - status: partial_success', () => {
    it('should return status: partial_success when memory succeeds but storage fails', async () => {
      vi.mocked(mockStorage.save).mockResolvedValue({
        success: false,
        error: 'Disk full',
      });

      const result = await registrar.registerDetailed(sampleWorkflow, 'project1');

      expect(result.status).toBe('partial_success');
      expect(result.success).toBe(true); // success is status !== 'failed'
      expect(result.memoryRegistered).toBe(true);
      expect(result.storagePersisted).toBe(false);
      expect(result.storageError).toBe('Disk full');

      // Verify workflow is in memory
      const workflows = registry.getByProject('project1');
      expect(workflows).toHaveLength(1);
    });
  });

  describe('registerDetailed - status: failed', () => {
    it('should return status: failed when memory registration throws', async () => {
      // Create a registry that throws on register
      const throwingRegistry = {
        registerForProject: vi.fn().mockImplementation(() => {
          throw new Error('Memory allocation failed');
        }),
        getByProject: vi.fn().mockReturnValue([]),
        getWorkflow: vi.fn(),
        unregisterFromProject: vi.fn(),
        listProjects: vi.fn().mockReturnValue([]),
        clear: vi.fn(),
        getStats: vi.fn().mockReturnValue({ totalProjects: 0, totalWorkflows: 0, byProject: {} }),
      } as unknown as WorkflowRegistry;

      const registrarWithThrowingRegistry = createWorkflowRegistrar({
        registry: throwingRegistry,
        storage: mockStorage,
        logger: mockLogger,
      });

      const result = await registrarWithThrowingRegistry.registerDetailed(sampleWorkflow, 'project1');

      expect(result.status).toBe('failed');
      expect(result.success).toBe(false);
      expect(result.memoryRegistered).toBe(false);
      expect(result.storagePersisted).toBe(false);
      expect(result.error).toBe('Memory allocation failed');
    });
  });

  describe('registerBatchDetailed', () => {
    const workflows: Record<string, TaskFlowDefinition> = {
      task_1: { ...sampleWorkflow, workflow_name: 'workflow1' },
      task_2: { ...sampleWorkflow, workflow_name: 'workflow2' },
      task_3: { ...sampleWorkflow, workflow_name: 'workflow3' },
    };

    it('should return status: success when all workflows succeed', async () => {
      const result = await registrar.registerBatchDetailed(workflows, 'project1');

      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.total).toBe(3);
      expect(result.succeeded).toBe(3);
      expect(result.partialSuccess).toBe(0);
      expect(result.failed).toBe(0);
    });

    it('should return status: success when storage fails but memory succeeds', async () => {
      // Make second save fail (but memory registration still succeeds)
      vi.mocked(mockStorage.save)
        .mockResolvedValueOnce({ success: true, filePath: '/path1.json' })
        .mockResolvedValueOnce({ success: false, error: 'Storage error' })
        .mockResolvedValueOnce({ success: true, filePath: '/path3.json' });

      const result = await registrar.registerBatchDetailed(workflows, 'project1');

      // Note: Even with storage failure, if memory succeeds, batch is considered successful
      // because workflows are available for execution
      expect(result.status).toBe('success');
      expect(result.success).toBe(true);
      expect(result.total).toBe(3);
      expect(result.succeeded).toBe(2);
      expect(result.partialSuccess).toBe(1);
      expect(result.failed).toBe(0);
    });

    it('should return status: partial_success when some memory registrations fail', async () => {
      // Create a registry that fails on one registration
      const partialFailRegistry = {
        registerForProject: vi.fn().mockImplementation((_project, workflow) => {
          if (workflow.name === 'workflow2') {
            throw new Error('Memory allocation failed');
          }
        }),
        getByProject: vi.fn().mockReturnValue([]),
        getWorkflow: vi.fn(),
        unregisterFromProject: vi.fn(),
        listProjects: vi.fn().mockReturnValue([]),
        clear: vi.fn(),
        getStats: vi.fn().mockReturnValue({ totalProjects: 0, totalWorkflows: 0, byProject: {} }),
      } as unknown as WorkflowRegistry;

      const registrarWithPartialFail = createWorkflowRegistrar({
        registry: partialFailRegistry,
        storage: mockStorage,
        logger: mockLogger,
      });

      const result = await registrarWithPartialFail.registerBatchDetailed(workflows, 'project1');

      expect(result.status).toBe('partial_success');
      expect(result.success).toBe(true);
      expect(result.total).toBe(3);
      expect(result.succeeded).toBe(2);
      expect(result.failed).toBe(1);
    });

    it('should return individual results for each workflow', async () => {
      const result = await registrar.registerBatchDetailed(workflows, 'project1');

      expect(result.results['task_1']).toBeDefined();
      expect(result.results['task_2']).toBeDefined();
      expect(result.results['task_3']).toBeDefined();
      expect(result.results['task_1']?.status).toBe('success');
    });
  });
});
