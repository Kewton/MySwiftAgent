/**
 * WorkflowReloader - Hot reload functionality for workflows
 *
 * Issue #375: Provides workflow reloading capabilities
 * Issue #378: Added status field for partial success model
 */

import type { WorkflowLoader } from './WorkflowLoader.js';
import type { WorkflowRegistry } from '../registry/WorkflowRegistry.js';
import { type RegistrationStatus, determineStatus } from '../../taskflowGeneratorAgent/types/registration.js';

/**
 * Single workflow reload result
 */
export interface WorkflowReloadResult {
  success: boolean;
  workflowName?: string;
  error?: string;
}

/**
 * Project reload result
 *
 * Issue #378: Added status field for partial success model
 */
export interface ProjectReloadResult {
  /** 3-state status: 'success' | 'partial_success' | 'failed' */
  status: RegistrationStatus;
  /** Backward-compatible success flag (status !== 'failed') */
  success: boolean;
  /** Number of successfully reloaded workflows */
  reloadedCount: number;
  /** Number of failed workflow reloads */
  failedCount: number;
  /** Names of successfully reloaded workflows */
  workflowNames?: string[];
  /** Error messages for failed reloads */
  errors?: string[];
}

/**
 * Full reload result
 *
 * Issue #378: Added status field for partial success model
 */
export interface FullReloadResult {
  /** 3-state status: 'success' | 'partial_success' | 'failed' */
  status: RegistrationStatus;
  /** Backward-compatible success flag (status !== 'failed') */
  success: boolean;
  /** Results for each project */
  projectResults: ProjectReloadResult[];
}

/**
 * WorkflowReloader - Handles workflow hot reloading
 *
 * Features:
 * - Reload single workflow
 * - Reload all workflows for a project
 * - Reload all projects
 * - Track reload timestamps
 */
export class WorkflowReloader {
  private readonly loader: WorkflowLoader;
  private readonly registry: WorkflowRegistry;
  private readonly reloadTimestamps: Map<string, Date>;

  constructor(loader: WorkflowLoader, registry: WorkflowRegistry) {
    this.loader = loader;
    this.registry = registry;
    this.reloadTimestamps = new Map();
  }

  /**
   * Reload a single workflow file
   */
  async reloadWorkflow(projectId: string, filePath: string): Promise<WorkflowReloadResult> {
    try {
      const workflow = await this.loader.loadWorkflow(filePath);

      this.registry.registerForProject(projectId, workflow);
      this.reloadTimestamps.set(projectId, new Date());

      return {
        success: true,
        workflowName: workflow.name,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Reload all workflows for a project
   *
   * Issue #378: Returns status field with proper partial success handling
   */
  async reloadProject(projectId: string): Promise<ProjectReloadResult> {
    const workflowNames: string[] = [];
    const errors: string[] = [];

    try {
      const workflows = await this.loader.loadWorkflowsForProject(projectId);
      const total = workflows.length;

      for (const workflow of workflows) {
        try {
          this.registry.registerForProject(projectId, workflow);
          workflowNames.push(workflow.name);
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Unknown error';
          errors.push(`Failed to register ${workflow.name}: ${message}`);
        }
      }

      this.reloadTimestamps.set(projectId, new Date());

      const succeeded = workflowNames.length;
      const failed = errors.length;
      const status = determineStatus(succeeded, failed, total);

      return {
        status,
        success: status !== 'failed',
        reloadedCount: succeeded,
        failedCount: failed,
        workflowNames,
        errors: errors.length > 0 ? errors : undefined,
      };
    } catch (error) {
      return {
        status: 'failed',
        success: false,
        reloadedCount: workflowNames.length,
        failedCount: 1,
        workflowNames,
        errors: [error instanceof Error ? error.message : 'Unknown error'],
      };
    }
  }

  /**
   * Reload all projects
   *
   * Issue #378: Returns status field with proper partial success handling
   */
  async reloadAll(): Promise<FullReloadResult> {
    // Clear registry before full reload
    this.registry.clear();

    const projectResults: ProjectReloadResult[] = [];

    try {
      const projects = await this.loader.listProjects();

      for (const projectId of projects) {
        const result = await this.reloadProject(projectId);
        projectResults.push(result);
      }

      // Calculate aggregate status from project results
      const successCount = projectResults.filter((r) => r.status === 'success').length;
      const failedCount = projectResults.filter((r) => r.status === 'failed').length;
      const total = projectResults.length;

      const status = determineStatus(successCount, failedCount, total);

      return {
        status,
        success: status !== 'failed',
        projectResults,
      };
    } catch {
      return {
        status: 'failed',
        success: false,
        projectResults,
      };
    }
  }

  /**
   * Get last reload timestamp for a project
   */
  getLastReloadTime(projectId: string): Date | undefined {
    return this.reloadTimestamps.get(projectId);
  }
}

/**
 * Factory function
 */
export function createWorkflowReloader(
  loader: WorkflowLoader,
  registry: WorkflowRegistry
): WorkflowReloader {
  return new WorkflowReloader(loader, registry);
}
