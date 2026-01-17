/**
 * WorkflowStorage - File-based workflow persistence
 *
 * Issue #370: Persist workflows to filesystem
 *
 * Features:
 * - Save workflows as JSON files
 * - Atomic write (tmp -> rename)
 * - Path validation for security
 * - Project-based organization
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
 * Storage configuration
 */
export interface WorkflowStorageConfig {
  baseDir?: string;
}

/**
 * Default base directory
 */
const DEFAULT_BASE_DIR = 'generated/workflows';

/**
 * WorkflowStorage - Persists workflows to filesystem
 */
export class WorkflowStorage {
  private readonly baseDir: string;
  private readonly pathValidator: PathValidator;

  constructor(config?: WorkflowStorageConfig) {
    this.baseDir = config?.baseDir ?? DEFAULT_BASE_DIR;
    this.pathValidator = new PathValidator();
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
   * @param projectId - Project identifier
   * @param workflowId - Workflow identifier
   * @param workflow - Workflow definition
   * @returns Save result
   */
  async save(
    projectId: string,
    workflowId: string,
    workflow: TaskFlowDefinition
  ): Promise<SaveResult> {
    // Validate paths
    try {
      this.pathValidator.validate(projectId);
      this.pathValidator.validate(workflowId);
    } catch (e) {
      if (e instanceof PathValidationError) {
        throw new WorkflowStorageError('save', e.message, e);
      }
      throw e;
    }

    const projectDir = path.join(this.baseDir, projectId);
    const filePath = path.join(projectDir, `${workflowId}.json`);
    const tmpPath = `${filePath}.tmp`;

    try {
      // Ensure directory exists
      await fs.mkdir(projectDir, { recursive: true });

      // Write to temp file first
      const content = JSON.stringify(workflow, null, 2);
      await fs.writeFile(tmpPath, content);

      // Atomic rename
      await fs.rename(tmpPath, filePath);

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

    const projectDir = path.join(this.baseDir, projectId);
    const workflows: Record<string, TaskFlowDefinition> = {};

    try {
      const files = await fs.readdir(projectDir);

      for (const file of files) {
        // Only process .json files (not .tmp or other files)
        if (typeof file === 'string' && file.endsWith('.json') && !file.endsWith('.tmp')) {
          const workflowId = file.replace('.json', '');
          const filePath = path.join(projectDir, file);

          try {
            const content = await fs.readFile(filePath, 'utf-8');
            workflows[workflowId] = JSON.parse(content) as TaskFlowDefinition;
          } catch {
            // Skip files that can't be parsed
          }
        }
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
}

/**
 * Factory function to create WorkflowStorage
 */
export function createWorkflowStorage(config?: WorkflowStorageConfig): WorkflowStorage {
  return new WorkflowStorage(config);
}
