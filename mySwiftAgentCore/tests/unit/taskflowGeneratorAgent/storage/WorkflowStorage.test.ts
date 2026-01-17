/**
 * WorkflowStorage Unit Tests
 *
 * Issue #370: Workflow persistence to filesystem
 * TDD Phase: Red - Write failing tests first
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import {
  WorkflowStorage,
  createWorkflowStorage,
  WorkflowStorageError,
  type WorkflowStorageConfig,
} from '../../../../src/taskflowGeneratorAgent/storage/WorkflowStorage.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

// Mock fs/promises
vi.mock('fs/promises');

describe('WorkflowStorage', () => {
  let storage: WorkflowStorage;
  const mockBaseDir = '/test/generated/workflows';

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

    // Default mock implementations
    vi.mocked(fs.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.writeFile).mockResolvedValue(undefined);
    vi.mocked(fs.rename).mockResolvedValue(undefined);
    vi.mocked(fs.readFile).mockResolvedValue(JSON.stringify(sampleWorkflow));
    vi.mocked(fs.readdir).mockResolvedValue([]);
    vi.mocked(fs.unlink).mockResolvedValue(undefined);
    vi.mocked(fs.access).mockResolvedValue(undefined);
    vi.mocked(fs.stat).mockResolvedValue({ isDirectory: () => true } as fs.FileHandle['stat'] extends (...args: infer A) => infer R ? Awaited<R> : never);

    storage = createWorkflowStorage({ baseDir: mockBaseDir });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('save', () => {
    it('should save workflow to correct path', async () => {
      const result = await storage.save('project1', 'workflow1', sampleWorkflow);

      expect(result.success).toBe(true);
      expect(result.filePath).toBe(path.join(mockBaseDir, 'project1', 'workflow1.json'));
    });

    it('should create directory if not exists', async () => {
      await storage.save('project1', 'workflow1', sampleWorkflow);

      expect(fs.mkdir).toHaveBeenCalledWith(
        path.join(mockBaseDir, 'project1'),
        { recursive: true }
      );
    });

    it('should use atomic write (tmp file then rename)', async () => {
      await storage.save('project1', 'workflow1', sampleWorkflow);

      const expectedTmpPath = path.join(mockBaseDir, 'project1', 'workflow1.json.tmp');
      const expectedFinalPath = path.join(mockBaseDir, 'project1', 'workflow1.json');

      expect(fs.writeFile).toHaveBeenCalledWith(expectedTmpPath, expect.any(String));
      expect(fs.rename).toHaveBeenCalledWith(expectedTmpPath, expectedFinalPath);
    });

    it('should validate projectId', async () => {
      await expect(storage.save('../attack', 'workflow1', sampleWorkflow))
        .rejects.toThrow(WorkflowStorageError);
    });

    it('should validate workflowId', async () => {
      await expect(storage.save('project1', '../attack', sampleWorkflow))
        .rejects.toThrow(WorkflowStorageError);
    });

    it('should return error result on write failure', async () => {
      vi.mocked(fs.writeFile).mockRejectedValue(new Error('Write failed'));

      const result = await storage.save('project1', 'workflow1', sampleWorkflow);

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('load', () => {
    it('should load workflow from file', async () => {
      const workflow = await storage.load('project1', 'workflow1');

      expect(workflow).toEqual(sampleWorkflow);
      expect(fs.readFile).toHaveBeenCalledWith(
        path.join(mockBaseDir, 'project1', 'workflow1.json'),
        'utf-8'
      );
    });

    it('should return undefined for non-existent file', async () => {
      vi.mocked(fs.readFile).mockRejectedValue({ code: 'ENOENT' });

      const workflow = await storage.load('project1', 'nonexistent');

      expect(workflow).toBeUndefined();
    });

    it('should validate projectId', async () => {
      await expect(storage.load('../attack', 'workflow1'))
        .rejects.toThrow(WorkflowStorageError);
    });

    it('should validate workflowId', async () => {
      await expect(storage.load('project1', '../attack'))
        .rejects.toThrow(WorkflowStorageError);
    });
  });

  describe('loadAll', () => {
    it('should load all workflows for a project', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        'workflow1.json',
        'workflow2.json',
      ] as unknown as fs.Dirent[]);
      vi.mocked(fs.readFile).mockResolvedValue(JSON.stringify(sampleWorkflow));

      const workflows = await storage.loadAll('project1');

      expect(Object.keys(workflows)).toHaveLength(2);
      expect(workflows['workflow1']).toEqual(sampleWorkflow);
      expect(workflows['workflow2']).toEqual(sampleWorkflow);
    });

    it('should skip non-json files', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        'workflow1.json',
        'readme.txt',
        'workflow2.json.tmp',
      ] as unknown as fs.Dirent[]);

      const workflows = await storage.loadAll('project1');

      expect(Object.keys(workflows)).toHaveLength(1);
    });

    it('should return empty object for non-existent project', async () => {
      vi.mocked(fs.readdir).mockRejectedValue({ code: 'ENOENT' });

      const workflows = await storage.loadAll('nonexistent');

      expect(workflows).toEqual({});
    });
  });

  describe('delete', () => {
    it('should delete workflow file', async () => {
      const result = await storage.delete('project1', 'workflow1');

      expect(result).toBe(true);
      expect(fs.unlink).toHaveBeenCalledWith(
        path.join(mockBaseDir, 'project1', 'workflow1.json')
      );
    });

    it('should return false for non-existent file', async () => {
      vi.mocked(fs.unlink).mockRejectedValue({ code: 'ENOENT' });

      const result = await storage.delete('project1', 'nonexistent');

      expect(result).toBe(false);
    });

    it('should validate projectId', async () => {
      await expect(storage.delete('../attack', 'workflow1'))
        .rejects.toThrow(WorkflowStorageError);
    });
  });

  describe('exists', () => {
    it('should return true for existing file', async () => {
      vi.mocked(fs.access).mockResolvedValue(undefined);

      const exists = await storage.exists('project1', 'workflow1');

      expect(exists).toBe(true);
    });

    it('should return false for non-existent file', async () => {
      vi.mocked(fs.access).mockRejectedValue({ code: 'ENOENT' });

      const exists = await storage.exists('project1', 'nonexistent');

      expect(exists).toBe(false);
    });
  });

  describe('getAllProjects', () => {
    it('should return all project directories', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        'project1',
        'project2',
      ] as unknown as fs.Dirent[]);

      const projects = await storage.getAllProjects();

      expect(projects).toContain('project1');
      expect(projects).toContain('project2');
    });

    it('should return empty array if base directory does not exist', async () => {
      vi.mocked(fs.readdir).mockRejectedValue({ code: 'ENOENT' });

      const projects = await storage.getAllProjects();

      expect(projects).toEqual([]);
    });
  });
});

describe('createWorkflowStorage factory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create a WorkflowStorage instance', () => {
    const storage = createWorkflowStorage({ baseDir: '/test' });
    expect(storage).toBeInstanceOf(WorkflowStorage);
  });

  it('should use default base directory if not specified', () => {
    const storage = createWorkflowStorage();
    expect(storage.getBaseDir()).toBe('generated/workflows');
  });
});
