/**
 * WorkflowLoader - Load workflows from filesystem
 *
 * Issue #363: Loads TaskFlow definitions from JSON files
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import type { TaskFlowDefinition } from '../types/TaskFlowDefinition.js';
import { TaskFlowDefinitionSchema } from '../types/TaskFlowDefinition.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';
import { TaskFlowDefinitionAdapter } from '../adapter/TaskFlowDefinitionAdapter.js';

/**
 * Workflow loader configuration
 */
export interface WorkflowLoaderConfig {
  basePath?: string;
}

/**
 * Validation result
 */
export interface WorkflowValidationResult {
  valid: boolean;
  errors: string[];
}

/**
 * Default base path for workflow files
 */
const DEFAULT_BASE_PATH = 'config/taskflow/projects';

/**
 * WorkflowLoader - Loads workflows from filesystem
 *
 * Features:
 * - Load individual workflow files
 * - Load all workflows for a project
 * - List available projects
 * - Validate workflow structure
 */
export class WorkflowLoader {
  private readonly basePath: string;

  constructor(config: WorkflowLoaderConfig = {}) {
    this.basePath = config.basePath ?? DEFAULT_BASE_PATH;
  }

  /**
   * Load a workflow from a specific file path and convert to internal format
   *
   * @param filePath - Absolute path to the workflow JSON file
   * @returns The loaded InternalWorkflowDefinition
   */
  async loadWorkflow(filePath: string): Promise<InternalWorkflowDefinition> {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const parsed = JSON.parse(content) as TaskFlowDefinition;

      const validation = this.validateWorkflow(parsed);
      if (!validation.valid) {
        throw new Error(`Invalid workflow: ${validation.errors.join(', ')}`);
      }

      // Convert TaskFlowDefinition to InternalWorkflowDefinition using adapter
      const internalWorkflow = TaskFlowDefinitionAdapter.toInternal(parsed);
      return internalWorkflow;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw new Error(`Failed to load workflow from ${filePath}: ${message}`);
    }
  }

  /**
   * Load all workflows for a specific project
   *
   * @param projectId - The project identifier
   * @returns Array of loaded workflows in internal format
   */
  async loadWorkflowsForProject(projectId: string): Promise<InternalWorkflowDefinition[]> {
    const projectPath = path.join(this.basePath, projectId, 'workflows');

    try {
      await fs.access(projectPath);
    } catch {
      return [];
    }

    const entries = await fs.readdir(projectPath, { withFileTypes: true });
    const workflows: InternalWorkflowDefinition[] = [];

    for (const entry of entries) {
      if (entry.isFile() && entry.name.endsWith('.json')) {
        try {
          const filePath = path.join(projectPath, entry.name);
          const workflow = await this.loadWorkflow(filePath);
          workflows.push(workflow);
        } catch (error) {
          // Log error but continue loading other workflows
          console.error(`Failed to load ${entry.name}:`, error);
        }
      }
    }

    return workflows;
  }

  /**
   * List available projects
   *
   * @returns Array of project identifiers
   */
  async listProjects(): Promise<string[]> {
    try {
      await fs.access(this.basePath);
    } catch {
      return [];
    }

    const entries = await fs.readdir(this.basePath, { withFileTypes: true });

    return entries
      .filter((entry) => entry.isDirectory())
      .map((entry) => entry.name);
  }

  /**
   * Validate a workflow definition
   *
   * @param workflow - The workflow to validate
   * @returns Validation result
   */
  validateWorkflow(workflow: TaskFlowDefinition): WorkflowValidationResult {
    const result = TaskFlowDefinitionSchema.safeParse(workflow);

    if (result.success) {
      return { valid: true, errors: [] };
    }

    const errors = result.error.errors.map(
      (e) => `${e.path.join('.')}: ${e.message}`
    );

    return { valid: false, errors };
  }

  /**
   * Get the base path for workflow files
   */
  getBasePath(): string {
    return this.basePath;
  }
}

/**
 * Factory function to create WorkflowLoader
 */
export function createWorkflowLoader(config?: WorkflowLoaderConfig): WorkflowLoader {
  return new WorkflowLoader(config);
}
