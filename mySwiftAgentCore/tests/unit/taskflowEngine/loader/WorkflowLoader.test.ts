/**
 * WorkflowLoader Unit Tests
 *
 * Issue #363: Workflow loading from filesystem
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  WorkflowLoader,
  createWorkflowLoader,
  type WorkflowLoaderConfig,
} from '../../../../src/taskflowEngine/loader/WorkflowLoader.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

// Mock fs module
vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
  readdir: vi.fn(),
  access: vi.fn(),
}));

vi.mock('path', async () => {
  const actual = await vi.importActual('path');
  return actual;
});

describe('WorkflowLoader', () => {
  let loader: WorkflowLoader;
  let mockFs: {
    readFile: ReturnType<typeof vi.fn>;
    readdir: ReturnType<typeof vi.fn>;
    access: ReturnType<typeof vi.fn>;
  };

  const sampleTaskFlow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [],
    output: {},
  };

  beforeEach(async () => {
    const fs = await import('fs/promises');
    mockFs = {
      readFile: fs.readFile as ReturnType<typeof vi.fn>,
      readdir: fs.readdir as ReturnType<typeof vi.fn>,
      access: fs.access as ReturnType<typeof vi.fn>,
    };

    loader = new WorkflowLoader();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('loadWorkflow', () => {
    it('should load a workflow from file', async () => {
      mockFs.readFile.mockResolvedValue(JSON.stringify(sampleTaskFlow));

      const workflow = await loader.loadWorkflow('/path/to/workflow.json');

      expect(workflow).toBeDefined();
      // After adapter conversion, uses InternalWorkflowDefinition.name instead of TaskFlowDefinition.workflow_name
      expect(workflow.name).toBe('test_workflow');
    });

    it('should throw error for invalid JSON', async () => {
      mockFs.readFile.mockResolvedValue('invalid json');

      await expect(loader.loadWorkflow('/path/to/invalid.json')).rejects.toThrow();
    });

    it('should throw error for non-existent file', async () => {
      mockFs.readFile.mockRejectedValue(new Error('ENOENT: no such file'));

      await expect(loader.loadWorkflow('/path/to/nonexistent.json')).rejects.toThrow(
        'Failed to load workflow'
      );
    });
  });

  describe('loadWorkflowsForProject', () => {
    it('should load all workflows for a project', async () => {
      const workflow1: TaskFlowDefinition = {
        ...sampleTaskFlow,
        workflow_name: 'workflow_1',
      };
      const workflow2: TaskFlowDefinition = {
        ...sampleTaskFlow,
        workflow_name: 'workflow_2',
      };

      mockFs.access.mockResolvedValue(undefined);
      mockFs.readdir.mockResolvedValue([
        { name: 'workflow_1.json', isFile: () => true },
        { name: 'workflow_2.json', isFile: () => true },
        { name: 'readme.md', isFile: () => true },
      ]);
      mockFs.readFile
        .mockResolvedValueOnce(JSON.stringify(workflow1))
        .mockResolvedValueOnce(JSON.stringify(workflow2));

      const workflows = await loader.loadWorkflowsForProject('test_project');

      expect(workflows).toHaveLength(2);
      // After adapter conversion, uses InternalWorkflowDefinition.name
      expect(workflows.map(w => w.name)).toContain('workflow_1');
      expect(workflows.map(w => w.name)).toContain('workflow_2');
    });

    it('should return empty array for non-existent project directory', async () => {
      mockFs.access.mockRejectedValue(new Error('ENOENT'));

      const workflows = await loader.loadWorkflowsForProject('non_existent');

      expect(workflows).toEqual([]);
    });

    it('should skip non-JSON files', async () => {
      mockFs.access.mockResolvedValue(undefined);
      mockFs.readdir.mockResolvedValue([
        { name: 'workflow.json', isFile: () => true },
        { name: 'readme.txt', isFile: () => true },
        { name: 'subdir', isFile: () => false },
      ]);
      mockFs.readFile.mockResolvedValue(JSON.stringify(sampleTaskFlow));

      const workflows = await loader.loadWorkflowsForProject('test_project');

      expect(workflows).toHaveLength(1);
      expect(mockFs.readFile).toHaveBeenCalledTimes(1);
    });
  });

  describe('listProjects', () => {
    it('should list available projects', async () => {
      mockFs.access.mockResolvedValue(undefined);
      mockFs.readdir.mockResolvedValue([
        { name: 'project_a', isDirectory: () => true },
        { name: 'project_b', isDirectory: () => true },
        { name: 'config.json', isDirectory: () => false },
      ]);

      const projects = await loader.listProjects();

      expect(projects).toContain('project_a');
      expect(projects).toContain('project_b');
      expect(projects).not.toContain('config.json');
    });

    it('should return empty array if base directory does not exist', async () => {
      mockFs.access.mockRejectedValue(new Error('ENOENT'));

      const projects = await loader.listProjects();

      expect(projects).toEqual([]);
    });
  });

  describe('configuration', () => {
    it('should use custom base path', async () => {
      const customConfig: WorkflowLoaderConfig = {
        basePath: '/custom/path',
      };
      const customLoader = new WorkflowLoader(customConfig);

      mockFs.access.mockResolvedValue(undefined);
      mockFs.readdir.mockResolvedValue([]);

      await customLoader.listProjects();

      // Verify the custom path is used
      expect(mockFs.access).toHaveBeenCalledWith('/custom/path');
    });
  });

  describe('validateWorkflow', () => {
    it('should validate a valid workflow', () => {
      const result = loader.validateWorkflow(sampleTaskFlow);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect missing required fields', () => {
      const invalidWorkflow = {
        workflow_name: 'incomplete',
      } as TaskFlowDefinition;

      const result = loader.validateWorkflow(invalidWorkflow);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });
});

describe('createWorkflowLoader factory', () => {
  it('should create a WorkflowLoader instance', () => {
    const loader = createWorkflowLoader();
    expect(loader).toBeInstanceOf(WorkflowLoader);
  });

  it('should create loader with custom config', () => {
    const loader = createWorkflowLoader({ basePath: '/custom/path' });
    expect(loader).toBeInstanceOf(WorkflowLoader);
  });
});
