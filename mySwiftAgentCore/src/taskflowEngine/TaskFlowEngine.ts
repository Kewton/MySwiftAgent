/**
 * TaskFlowEngine - High-level facade for TaskFlow execution
 *
 * Issue #363: Main entry point for executing workflows
 */

import type { WorkflowDefinition, WorkflowExecutionResult } from '../shared/types/workflow.types.js';
import { createDefaultNodeRegistry } from './nodes/index.js';
import { WorkflowExecutor } from './executor/WorkflowExecutor.js';
import type { NodeRegistry } from './nodes/BaseNode.js';
import type { InternalWorkflowDefinition } from './types/InternalWorkflowDefinition.js';
import type { NodeType } from './types/TaskFlowDefinition.js';

/**
 * TaskFlowEngine configuration
 */
export interface TaskFlowEngineConfig {
  /** Maximum concurrent steps */
  maxConcurrentSteps?: number;
  /** Default timeout in milliseconds */
  defaultTimeout?: number;
  /** Enable recovery mode */
  enableRecovery?: boolean;
  /** Custom node registry */
  nodeRegistry?: NodeRegistry;
}

/**
 * Execution options
 */
export interface TaskFlowExecutionOptions {
  /** Custom request ID */
  requestId?: string;
  /** Override timeout */
  timeout?: number;
  /** Input variables */
  inputs?: Record<string, unknown>;
  /** Secrets for execution */
  secrets?: Record<string, string>;
}

/**
 * TaskFlowEngine - Main workflow execution facade
 *
 * Provides a simplified interface for executing TaskFlow workflows.
 * Wraps the underlying WorkflowExecutor with sensible defaults.
 */
export class TaskFlowEngine {
  private readonly config: Required<TaskFlowEngineConfig>;
  private readonly executor: WorkflowExecutor;

  constructor(config: TaskFlowEngineConfig = {}) {
    this.config = {
      maxConcurrentSteps: config.maxConcurrentSteps ?? 5,
      defaultTimeout: config.defaultTimeout ?? 30000,
      enableRecovery: config.enableRecovery ?? true,
      nodeRegistry: config.nodeRegistry ?? createDefaultNodeRegistry(),
    };

    this.executor = new WorkflowExecutor({
      nodeRegistry: this.config.nodeRegistry,
      defaultTimeout: this.config.defaultTimeout,
    });
  }

  /**
   * Execute a workflow
   *
   * @param workflow - Workflow definition to execute
   * @param options - Execution options
   * @returns Execution result
   */
  async execute(
    workflow: WorkflowDefinition,
    options: TaskFlowExecutionOptions = {}
  ): Promise<WorkflowExecutionResult> {
    const startTime = new Date();

    // Validate workflow
    const validationErrors = this.validateWorkflow(workflow);
    if (validationErrors.length > 0) {
      return {
        workflowId: workflow.id,
        workflowName: workflow.name,
        status: 'failed',
        stepResults: [],
        errors: validationErrors.map((msg) => ({
          stepId: 'validation',
          stepName: 'Workflow Validation',
          errorCode: 'VALIDATION_ERROR',
          errorMessage: msg,
          timestamp: new Date(),
          recoverable: false,
        })),
        recoveryActions: [],
        startTime,
        endTime: new Date(),
        durationMs: 0,
        metadata: { requestId: options.requestId },
      };
    }

    // Convert WorkflowDefinition to InternalWorkflowDefinition
    const internalWorkflow: InternalWorkflowDefinition = {
      id: workflow.id,
      name: workflow.name,
      version: workflow.version,
      steps: workflow.steps.map((step) => ({
        id: step.id,
        name: step.name || step.id,
        type: (step.type || 'action') as NodeType,
        config: step.config || {},
        params: {},
        dependsOn: step.dependsOn,
      })),
      inputSchema: { type: 'object' },
      outputSchema: { type: 'object' },
      outputMapping: {},
    };

    // Execute
    const result = await this.executor.execute(internalWorkflow, {
      inputs: options.inputs,
      secrets: options.secrets,
      timeout: options.timeout ?? this.config.defaultTimeout,
    });

    // Add request ID to metadata
    if (options.requestId) {
      result.metadata = {
        ...result.metadata,
        requestId: options.requestId,
      };
    }

    return result;
  }

  /**
   * Validate a workflow definition
   */
  private validateWorkflow(workflow: WorkflowDefinition): string[] {
    const errors: string[] = [];

    if (!workflow.id) {
      errors.push('Workflow ID is required');
    }

    if (!workflow.name) {
      errors.push('Workflow name is required');
    }

    if (!workflow.steps || workflow.steps.length === 0) {
      errors.push('Workflow must have at least one step');
    }

    return errors;
  }

  /**
   * Get engine configuration
   */
  getConfig(): Readonly<Required<TaskFlowEngineConfig>> {
    return { ...this.config };
  }
}

/**
 * Factory function to create TaskFlowEngine
 *
 * @param config - Engine configuration
 * @returns TaskFlowEngine instance
 */
export function createTaskFlowEngine(config?: TaskFlowEngineConfig): TaskFlowEngine {
  return new TaskFlowEngine(config);
}
