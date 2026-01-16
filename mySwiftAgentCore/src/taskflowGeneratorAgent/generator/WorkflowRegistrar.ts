/**
 * WorkflowRegistrar - taskflowEngine integration
 *
 * Issue #364: Register generated workflows in taskflowEngine
 */

import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';
import type { WorkflowRegistry } from '../../taskflowEngine/registry/WorkflowRegistry.js';
import type { InternalWorkflowDefinition } from '../../taskflowEngine/types/InternalWorkflowDefinition.js';

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
  defaultProject?: string;
}

/**
 * WorkflowRegistrar - Registers workflows in taskflowEngine
 *
 * Features:
 * - Register workflow in WorkflowRegistry
 * - Project-based organization
 * - Error handling for registration failures
 */
export class WorkflowRegistrar {
  private readonly registry: WorkflowRegistry;
  private readonly defaultProject: string;

  constructor(config: WorkflowRegistrarConfig) {
    this.registry = config.registry;
    this.defaultProject = config.defaultProject ?? 'default';
  }

  /**
   * Register a workflow
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

    try {
      // Convert TaskFlowDefinition to InternalWorkflowDefinition
      const internalWorkflow: InternalWorkflowDefinition = {
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

      // Register with taskflowEngine registry
      this.registry.registerForProject(project, internalWorkflow);

      return {
        success: true,
        workflowId: workflow.workflow_name,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

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

    for (const [taskId, workflow] of Object.entries(workflows)) {
      results[taskId] = await this.register(workflow, projectId);
    }

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

    try {
      return this.registry.unregisterFromProject(project, workflowName);
    } catch {
      return false;
    }
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
