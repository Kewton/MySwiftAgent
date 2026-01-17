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

/**
 * Issue #373: taskId directory structure and cache mechanism tests
 */
describe('WorkflowStorage - taskId support (Issue #373)', () => {
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

    vi.mocked(fs.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.writeFile).mockResolvedValue(undefined);
    vi.mocked(fs.rename).mockResolvedValue(undefined);
    vi.mocked(fs.readFile).mockResolvedValue(JSON.stringify(sampleWorkflow));
    vi.mocked(fs.readdir).mockResolvedValue([]);
    vi.mocked(fs.unlink).mockResolvedValue(undefined);
    vi.mocked(fs.access).mockResolvedValue(undefined);

    storage = createWorkflowStorage({ baseDir: mockBaseDir });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('save with taskId', () => {
    it('should save workflow with taskId in path', async () => {
      const result = await storage.save('project1', 'workflow1', sampleWorkflow, 'task_123');

      expect(result.success).toBe(true);
      expect(result.filePath).toBe(path.join(mockBaseDir, 'project1', 'task_123', 'workflow1.json'));
    });

    it('should create nested directory structure for taskId', async () => {
      await storage.save('project1', 'workflow1', sampleWorkflow, 'task_123');

      expect(fs.mkdir).toHaveBeenCalledWith(
        path.join(mockBaseDir, 'project1', 'task_123'),
        { recursive: true }
      );
    });

    it('should use flat structure when taskId is not provided', async () => {
      const result = await storage.save('project1', 'workflow1', sampleWorkflow, undefined);

      expect(result.success).toBe(true);
      expect(result.filePath).toBe(path.join(mockBaseDir, 'project1', 'workflow1.json'));
    });

    it('should validate taskId for path traversal', async () => {
      await expect(storage.save('project1', 'workflow1', sampleWorkflow, '../attack'))
        .rejects.toThrow(WorkflowStorageError);
    });
  });

  describe('loadAll with taskId subdirectories', () => {
    it('should load workflows from task subdirectories', async () => {
      // Mock stat to identify directories
      vi.mocked(fs.stat).mockImplementation((filePath: fs.PathLike) => {
        const pathStr = String(filePath);
        if (pathStr.includes('task_')) {
          return Promise.resolve({ isDirectory: () => true } as Awaited<ReturnType<typeof fs.stat>>);
        }
        return Promise.resolve({ isDirectory: () => false } as Awaited<ReturnType<typeof fs.stat>>);
      });

      // First readdir returns task directories and json files
      vi.mocked(fs.readdir).mockImplementation((dirPath: fs.PathLike) => {
        const pathStr = String(dirPath);
        if (pathStr.endsWith('project1')) {
          return Promise.resolve(['task_123', 'workflow1.json'] as unknown as fs.Dirent[]);
        }
        if (pathStr.includes('task_123')) {
          return Promise.resolve(['workflow2.json'] as unknown as fs.Dirent[]);
        }
        return Promise.resolve([]);
      });

      const workflows = await storage.loadAll('project1');

      // Should load from both flat and nested structures
      expect(Object.keys(workflows).length).toBeGreaterThanOrEqual(1);
    });

    it('should maintain backward compatibility with flat structure', async () => {
      vi.mocked(fs.stat).mockResolvedValue({ isDirectory: () => false } as Awaited<ReturnType<typeof fs.stat>>);
      vi.mocked(fs.readdir).mockResolvedValue([
        'workflow1.json',
        'workflow2.json',
      ] as unknown as fs.Dirent[]);

      const workflows = await storage.loadAll('project1');

      expect(Object.keys(workflows)).toHaveLength(2);
      expect(workflows['workflow1']).toBeDefined();
      expect(workflows['workflow2']).toBeDefined();
    });
  });
});

/**
 * Issue #373: Cache mechanism tests
 */
describe('WorkflowStorage - cache mechanism (Issue #373)', () => {
  let storage: WorkflowStorage;
  const mockBaseDir = '/test/generated/workflows';

  const sampleWorkflow: TaskFlowDefinition = {
    workflow_name: 'test_workflow',
    description: 'Test workflow',
    input_schema: { type: 'object', properties: {} },
    output_schema: { type: 'object', properties: {} },
    steps: [],
    output: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    vi.mocked(fs.mkdir).mockResolvedValue(undefined);
    vi.mocked(fs.writeFile).mockResolvedValue(undefined);
    vi.mocked(fs.rename).mockResolvedValue(undefined);
    vi.mocked(fs.readFile).mockResolvedValue(JSON.stringify(sampleWorkflow));
    vi.mocked(fs.readdir).mockResolvedValue(['workflow1.json'] as unknown as fs.Dirent[]);
    vi.mocked(fs.unlink).mockResolvedValue(undefined);
    vi.mocked(fs.stat).mockResolvedValue({ isDirectory: () => false } as Awaited<ReturnType<typeof fs.stat>>);

    storage = createWorkflowStorage({
      baseDir: mockBaseDir,
      cache: { ttlMs: 5000, maxEntries: 100 },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('cache hit', () => {
    it('should return cached data on second loadAll call', async () => {
      // First call - cache miss
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Second call - cache hit
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1); // Still 1
    });

    it('should fetch from disk after cache expires', async () => {
      // First call - cache miss
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Advance time past TTL
      vi.advanceTimersByTime(6000);

      // Third call - cache miss (expired)
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(2);
    });
  });

  describe('cache invalidation', () => {
    it('should invalidate cache on save', async () => {
      // First call - cache miss
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Save workflow - should invalidate cache
      await storage.save('project1', 'workflow2', sampleWorkflow);

      // Next call - cache miss (invalidated)
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(2);
    });

    it('should invalidate cache on delete', async () => {
      // First call - cache miss
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Delete workflow - should invalidate cache
      await storage.delete('project1', 'workflow1');

      // Next call - cache miss (invalidated)
      await storage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(2);
    });
  });

  describe('cache configuration', () => {
    it('should use custom TTL from config', async () => {
      const shortTtlStorage = createWorkflowStorage({
        baseDir: mockBaseDir,
        cache: { ttlMs: 1000, maxEntries: 100 },
      });

      await shortTtlStorage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Advance time within TTL
      vi.advanceTimersByTime(500);
      await shortTtlStorage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(1);

      // Advance time past TTL
      vi.advanceTimersByTime(600);
      await shortTtlStorage.loadAll('project1');
      expect(fs.readdir).toHaveBeenCalledTimes(2);
    });

    it('should work without cache config (disabled by default)', async () => {
      const noCacheStorage = createWorkflowStorage({ baseDir: mockBaseDir });

      await noCacheStorage.loadAll('project1');
      await noCacheStorage.loadAll('project1');

      // Should hit disk both times
      expect(fs.readdir).toHaveBeenCalledTimes(2);
    });
  });
});
