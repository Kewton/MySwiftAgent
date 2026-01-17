/**
 * WorkflowStorage - File-based workflow persistence
 *
 * Issue #370: Persist workflows to filesystem
 * Issue #373: Add taskId directory structure and cache mechanism
 *
 * Features:
 * - Save workflows as JSON files
 * - Atomic write (tmp -> rename)
 * - Path validation for security
 * - Project-based organization
 * - Task-based subdirectory structure (optional)
 * - In-memory cache with TTL
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import { PathValidator, PathValidationError } from '../../utils/validation/PathValidator.js';
import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Storage error
 */
export class WorkflowStorageError extends Error {
  readonly operation: string;
  readonly cause?: Error;

  constructor(operation: string, message: string, cause?: Error) {
    super(`WorkflowStorage.${operation}: ${message}`);
    this.name = 'WorkflowStorageError';
    this.operation = operation;
    this.cause = cause;
  }
}

/**
 * Save result
 */
export interface SaveResult {
  success: boolean;
  filePath?: string;
  error?: string;
}

/**
 * Cache entry for loadAll results
 */
interface CacheEntry {
  data: Record<string, TaskFlowDefinition>;
  timestamp: number;
  expiresAt: number;
}

/**
 * Cache configuration
 */
export interface WorkflowCacheConfig {
  ttlMs: number;        // default: 300000 (5 minutes)
  maxEntries: number;   // default: 100
}

/**
 * Storage configuration
 */
export interface WorkflowStorageConfig {
  baseDir?: string;
  cache?: WorkflowCacheConfig;
}

/**
 * Default base directory
 */
const DEFAULT_BASE_DIR = 'generated/workflows';

/**
 * Default cache config - exported for documentation purposes
 * Used as reference when cache config is provided
 */
export const DEFAULT_CACHE_CONFIG: WorkflowCacheConfig = {
  ttlMs: 300000,    // 5 minutes
  maxEntries: 100,
};

/**
 * WorkflowStorage - Persists workflows to filesystem
 */
export class WorkflowStorage {
  private readonly baseDir: string;
  private readonly pathValidator: PathValidator;
  private readonly cacheConfig?: WorkflowCacheConfig;
  private readonly cache: Map<string, CacheEntry> = new Map();

  constructor(config?: WorkflowStorageConfig) {
    this.baseDir = config?.baseDir ?? DEFAULT_BASE_DIR;
    this.pathValidator = new PathValidator();
    this.cacheConfig = config?.cache;
  }

  /**
   * Get base directory
   */
  getBaseDir(): string {
    return this.baseDir;
  }

  /**
   * Save workflow to file
   *
   * Issue #373: Added taskId parameter for nested directory structure
   *
   * @param projectId - Project identifier
   * @param workflowId - Workflow identifier
   * @param workflow - Workflow definition
   * @param taskId - Optional task identifier for nested directory
   * @returns Save result
   */
  async save(
    projectId: string,
    workflowId: string,
    workflow: TaskFlowDefinition,
    taskId?: string
  ): Promise<SaveResult> {
    // Validate paths
    try {
      this.pathValidator.validate(projectId);
      this.pathValidator.validate(workflowId);
      if (taskId) {
        this.pathValidator.validate(taskId);
      }
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('save', e.message, e);
      }
      throw e;
    }

    // Build directory path based on taskId presence
    const targetDir = taskId
      ? path.join(this.baseDir, projectId, taskId)
      : path.join(this.baseDir, projectId);
    const filePath = path.join(targetDir, `${workflowId}.json`);
    const tmpPath = `${filePath}.tmp`;

    try {
      // Ensure directory exists
      await fs.mkdir(targetDir, { recursive: true });

      // Write to temp file first
      const content = JSON.stringify(workflow, null, 2);
      await fs.writeFile(tmpPath, content);

      // Atomic rename
      await fs.rename(tmpPath, filePath);

      // Invalidate cache for this project
      this.invalidateCache(projectId);

      return {
        success: true,
        filePath,
      };
    } catch (e) {
      const error = e instanceof Error ? e : new Error(String(e));
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Load workflow from file
   *
   * @param projectId - Project identifier
   * @param workflowId - Workflow identifier
   * @returns Workflow definition or undefined if not found
   */
  async load(
    projectId: string,
    workflowId: string
  ): Promise<TaskFlowDefinition | undefined> {
    // Validate paths
    try {
      this.pathValidator.validate(projectId);
      this.pathValidator.validate(workflowId);
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('load', e.message, e);
      }
      throw e;
    }

    const filePath = path.join(this.baseDir, projectId, `${workflowId}.json`);

    try {
      const content = await fs.readFile(filePath, 'utf-8');
      return JSON.parse(content) as TaskFlowDefinition;
    } catch (e) {
      if (this.isNotFoundError(e)) {
        return undefined;
      }
      throw e;
    }
  }

  /**
   * Load all workflows for a project
   *
   * Issue #373: Support recursive directory reading for task subdirectories
   * Issue #373: Implement cache mechanism
   *
   * @param projectId - Project identifier
   * @returns Map of workflowId to workflow definition
   */
  async loadAll(projectId: string): Promise<Record<string, TaskFlowDefinition>> {
    // Validate path
    try {
      this.pathValidator.validate(projectId);
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('loadAll', e.message, e);
      }
      throw e;
    }

    // Check cache if enabled
    if (this.cacheConfig) {
      const cached = this.getFromCache(projectId);
      if (cached) {
        return cached;
      }
    }

    const projectDir = path.join(this.baseDir, projectId);
    const workflows: Record<string, TaskFlowDefinition> = {};

    try {
      const entries = await fs.readdir(projectDir);

      for (const entry of entries) {
        if (typeof entry !== 'string') continue;

        const entryPath = path.join(projectDir, entry);

        // Check if it's a directory (task subdirectory)
        try {
          const stat = await fs.stat(entryPath);
          if (stat.isDirectory()) {
            // Load workflows from task subdirectory
            const subWorkflows = await this.loadWorkflowsFromDir(entryPath);
            Object.assign(workflows, subWorkflows);
          } else if (entry.endsWith('.json') && !entry.endsWith('.tmp')) {
            // Load workflow from flat structure
            const workflowId = entry.replace('.json', '');
            try {
              const content = await fs.readFile(entryPath, 'utf-8');
              workflows[workflowId] = JSON.parse(content) as TaskFlowDefinition;
            } catch {
              // Skip files that can't be parsed
            }
          }
        } catch {
          // Skip entries that can't be accessed
        }
      }

      // Cache the result if enabled
      if (this.cacheConfig) {
        this.setCache(projectId, workflows);
      }

      return workflows;
    } catch (e) {
      if (this.isNotFoundError(e)) {
        return {};
      }
      throw e;
    }
  }

  /**
   * Load workflows from a directory
   */
  private async loadWorkflowsFromDir(dirPath: string): Promise<Record<string, TaskFlowDefinition>> {
    const workflows: Record<string, TaskFlowDefinition> = {};

    try {
      const files = await fs.readdir(dirPath);

      for (const file of files) {
        if (typeof file === 'string' && file.endsWith('.json') && !file.endsWith('.tmp')) {
          const workflowId = file.replace('.json', '');
          const filePath = path.join(dirPath, file);

          try {
            const content = await fs.readFile(filePath, 'utf-8');
            workflows[workflowId] = JSON.parse(content) as TaskFlowDefinition;
          } catch {
            // Skip files that can't be parsed
          }
        }
      }
    } catch {
      // Return empty if directory can't be read
    }

    return workflows;
  }

  /**
   * Delete workflow file
   *
   * @param projectId - Project identifier
   * @param workflowId - Workflow identifier
   * @returns true if deleted, false if not found
   */
  async delete(projectId: string, workflowId: string): Promise<boolean> {
    // Validate paths
    try {
      this.pathValidator.validate(projectId);
      this.pathValidator.validate(workflowId);
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('delete', e.message, e);
      }
      throw e;
    }

    const filePath = path.join(this.baseDir, projectId, `${workflowId}.json`);

    try {
      await fs.unlink(filePath);
      // Invalidate cache for this project
      this.invalidateCache(projectId);
      return true;
    } catch (e) {
      if (this.isNotFoundError(e)) {
        return false;
      }
      throw e;
    }
  }

  /**
   * Check if workflow exists
   *
   * @param projectId - Project identifier
   * @param workflowId - Workflow identifier
   * @returns true if exists
   */
  async exists(projectId: string, workflowId: string): Promise<boolean> {
    // Validate paths
    try {
      this.pathValidator.validate(projectId);
      this.pathValidator.validate(workflowId);
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('exists', e.message, e);
      }
      throw e;
    }

    const filePath = path.join(this.baseDir, projectId, `${workflowId}.json`);

    try {
      await fs.access(filePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get all project IDs
   *
   * @returns Array of project identifiers
   */
  async getAllProjects(): Promise<string[]> {
    try {
      const entries = await fs.readdir(this.baseDir);
      return entries.filter((entry) => typeof entry === 'string') as string[];
    } catch (e) {
      if (this.isNotFoundError(e)) {
        return [];
      }
      throw e;
    }
  }

  /**
   * Check if error is a "not found" error
   */
  private isNotFoundError(e: unknown): boolean {
    return (
      e !== null &&
      typeof e === 'object' &&
      'code' in e &&
      e.code === 'ENOENT'
    );
  }

  /**
   * Get data from cache if valid
   */
  private getFromCache(projectId: string): Record<string, TaskFlowDefinition> | null {
    const entry = this.cache.get(projectId);
    if (!entry) return null;

    const now = Date.now();
    if (now >= entry.expiresAt) {
      // Cache expired
      this.cache.delete(projectId);
      return null;
    }

    return entry.data;
  }

  /**
   * Set data in cache
   */
  private setCache(projectId: string, data: Record<string, TaskFlowDefinition>): void {
    if (!this.cacheConfig) return;

    // Enforce max entries (LRU-like: remove oldest entries)
    while (this.cache.size >= this.cacheConfig.maxEntries) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey) {
        this.cache.delete(oldestKey);
      }
    }

    const now = Date.now();
    this.cache.set(projectId, {
      data,
      timestamp: now,
      expiresAt: now + this.cacheConfig.ttlMs,
    });
  }

  /**
   * Invalidate cache for a project
   */
  private invalidateCache(projectId: string): void {
    this.cache.delete(projectId);
  }
}

/**
 * Factory function to create WorkflowStorage
 */
export function createWorkflowStorage(config?: WorkflowStorageConfig): WorkflowStorage {
  return new WorkflowStorage(config);
}
