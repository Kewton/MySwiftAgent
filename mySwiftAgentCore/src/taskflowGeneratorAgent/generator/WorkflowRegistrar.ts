/**
 * WorkflowRegistrar - taskflowEngine integration with persistence
 *
 * Issue #364: Register generated workflows in taskflowEngine
 * Issue #370: Add persistence and logging
 */

import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';
import type { WorkflowRegistry } from '../../taskflowEngine/registry/WorkflowRegistry.js';
import type { InternalWorkflowDefinition } from '../../taskflowEngine/types/InternalWorkflowDefinition.js';
import type { WorkflowStorage } from '../storage/WorkflowStorage.js';
import { Logger, createLogger } from '../../utils/logger/Logger.js';

/**
 * Registration Result
 */
export interface RegistrationResult {
  success: boolean;
  workflowId?: string;
  filePath?: string;
  error?: string;
}

/**
 * Registrar Configuration
 */
export interface WorkflowRegistrarConfig {
  registry: WorkflowRegistry;
  storage?: WorkflowStorage;
  logger?: Logger;
  defaultProject?: string;
}

/**
 * WorkflowRegistrar - Registers workflows in taskflowEngine with persistence
 *
 * Features:
 * - Register workflow in WorkflowRegistry
 * - Persist workflow to filesystem via WorkflowStorage
 * - Project-based organization
 * - Structured logging
 * - Initialize from persisted storage
 */
export class WorkflowRegistrar {
  private readonly registry: WorkflowRegistry;
  private readonly storage?: WorkflowStorage;
  private readonly logger: Logger;
  private readonly defaultProject: string;

  constructor(config: WorkflowRegistrarConfig) {
    this.registry = config.registry;
    this.storage = config.storage;
    this.logger = config.logger ?? createLogger({ name: 'WorkflowRegistrar' });
    this.defaultProject = config.defaultProject ?? 'default';
  }

  /**
   * Initialize registrar by loading workflows from storage
   *
   * Issue #370: Restore workflows from filesystem on startup
   */
  async initialize(): Promise<void> {
    if (!this.storage) {
      this.logger.debug('No storage configured, skipping initialization');
      return;
    }

    this.logger.info('Initializing WorkflowRegistrar from storage');

    try {
      const projects = await this.storage.getAllProjects();
      let totalRestored = 0;

      for (const projectId of projects) {
        const workflows = await this.storage.loadAll(projectId);
        const workflowCount = Object.keys(workflows).length;

        for (const [workflowId, workflow] of Object.entries(workflows)) {
          try {
            const internalWorkflow = this.toInternalWorkflow(workflow);
            this.registry.registerForProject(projectId, internalWorkflow);
            totalRestored++;

            this.logger.debug('Restored workflow', {
              projectId,
              workflowId,
            });
          } catch (e) {
            this.logger.warn('Failed to restore workflow', {
              projectId,
              workflowId,
              error: e instanceof Error ? e.message : String(e),
            });
          }
        }

        this.logger.info('Restored workflows for project', {
          projectId,
          count: workflowCount,
        });
      }

      this.logger.info('WorkflowRegistrar initialization complete', {
        projectCount: projects.length,
        totalWorkflows: totalRestored,
      });
    } catch (e) {
      this.logger.error('Failed to initialize from storage', {
        error: e instanceof Error ? e.message : String(e),
      });
    }
  }

  /**
   * Register a workflow
   *
   * Issue #370: Also persist to filesystem
   *
   * @param workflow - TaskFlow definition to register
   * @param projectId - Project identifier (optional)
   * @returns Registration result
   */
  async register(
    workflow: TaskFlowDefinition,
    projectId?: string
  ): Promise<RegistrationResult> {
    const project = projectId ?? this.defaultProject;
    const workflowName = workflow.workflow_name;

    this.logger.info('Registering workflow', {
      projectId: project,
      workflowName,
    });

    try {
      // Convert TaskFlowDefinition to InternalWorkflowDefinition
      const internalWorkflow = this.toInternalWorkflow(workflow);

      // Register with taskflowEngine registry (memory)
      this.registry.registerForProject(project, internalWorkflow);

      this.logger.debug('Registered workflow to memory', {
        projectId: project,
        workflowId: internalWorkflow.id,
      });

      // Persist to storage if available
      let filePath: string | undefined;
      let storageError: string | undefined;

      if (this.storage) {
        const saveResult = await this.storage.save(project, workflowName, workflow);

        if (saveResult.success) {
          filePath = saveResult.filePath;
          this.logger.info('Persisted workflow to storage', {
            projectId: project,
            workflowName,
            filePath,
          });
        } else {
          storageError = saveResult.error;
          this.logger.warn('Failed to persist workflow to storage', {
            projectId: project,
            workflowName,
            error: storageError,
          });
        }
      }

      // If storage failed, return with error but still registered to memory
      if (storageError) {
        return {
          success: false,
          workflowId: workflowName,
          error: storageError,
        };
      }

      return {
        success: true,
        workflowId: workflowName,
        filePath,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      this.logger.error('Failed to register workflow', {
        projectId: project,
        workflowName,
        error: errorMessage,
      });

      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Register multiple workflows
   *
   * @param workflows - Map of task_id to workflow
   * @param projectId - Project identifier (optional)
   * @returns Map of task_id to registration result
   */
  async registerBatch(
    workflows: Record<string, TaskFlowDefinition>,
    projectId?: string
  ): Promise<Record<string, RegistrationResult>> {
    const results: Record<string, RegistrationResult> = {};

    this.logger.info('Registering batch of workflows', {
      projectId: projectId ?? this.defaultProject,
      count: Object.keys(workflows).length,
    });

    for (const [taskId, workflow] of Object.entries(workflows)) {
      results[taskId] = await this.register(workflow, projectId);
    }

    const successCount = Object.values(results).filter((r) => r.success).length;
    this.logger.info('Batch registration complete', {
      total: Object.keys(workflows).length,
      success: successCount,
      failed: Object.keys(workflows).length - successCount,
    });

    return results;
  }

  /**
   * Check if workflow exists
   *
   * @param workflowName - Workflow name
   * @param projectId - Project identifier (optional)
   * @returns True if workflow exists
   */
  exists(workflowName: string, projectId?: string): boolean {
    const project = projectId ?? this.defaultProject;

    try {
      const workflow = this.registry.getWorkflow(project, workflowName);
      return !!workflow;
    } catch {
      return false;
    }
  }

  /**
   * Unregister a workflow
   *
   * @param workflowName - Workflow name
   * @param projectId - Project identifier (optional)
   * @returns True if unregistered successfully
   */
  unregister(workflowName: string, projectId?: string): boolean {
    const project = projectId ?? this.defaultProject;

    this.logger.info('Unregistering workflow', {
      projectId: project,
      workflowName,
    });

    try {
      return this.registry.unregisterFromProject(project, workflowName);
    } catch {
      return false;
    }
  }

  /**
   * Convert TaskFlowDefinition to InternalWorkflowDefinition
   */
  private toInternalWorkflow(workflow: TaskFlowDefinition): InternalWorkflowDefinition {
    return {
      id: `wf_${Date.now()}_${workflow.workflow_name}`,
      name: workflow.workflow_name,
      version: '1.0.0',
      steps: workflow.steps.map((step) => ({
        id: step.id,
        name: step.id,
        type: step.type,
        config: step.config as Record<string, unknown>,
        params: step.params as Record<string, unknown>,
      })),
      inputSchema: workflow.input_schema,
      outputSchema: workflow.output_schema,
      outputMapping: workflow.output,
    };
  }
}

/**
 * Factory function
 */
export function createWorkflowRegistrar(
  config: WorkflowRegistrarConfig
): WorkflowRegistrar {
  return new WorkflowRegistrar(config);
}
