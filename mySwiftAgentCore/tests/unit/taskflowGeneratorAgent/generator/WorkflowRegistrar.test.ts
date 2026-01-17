/**
 * WorkflowRegistrar Unit Tests
 *
 * Issue #370: Integration with WorkflowStorage
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
        sampleWorkflow
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
        sampleWorkflow
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

      await registrar.initialize();

      expect(registry.listProjects()).toHaveLength(0);
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

  it('should skip initialize when no storage', async () => {
    await registrar.initialize();

    expect(mockLogger.debug).toHaveBeenCalledWith(
      'No storage configured, skipping initialization'
    );
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
