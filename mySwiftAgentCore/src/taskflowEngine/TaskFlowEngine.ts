/**
 * TaskFlowEngine - High-level facade for TaskFlow execution
 *
 * Issue #363: Main entry point for executing workflows
 * Issue #372: Extended to support CapabilityExecutor for capability_id based API execution
 */

import type { WorkflowDefinition, WorkflowExecutionResult } from '../shared/types/workflow.types.js';
import { createDefaultNodeRegistry } from './nodes/index.js';
import { WorkflowExecutor } from './executor/WorkflowExecutor.js';
import type { NodeRegistry, ICapabilityExecutor } from './nodes/BaseNode.js';
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
  /** Issue #372: CapabilityExecutor for capability_id based API execution */
  capabilityExecutor?: ICapabilityExecutor;
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
 * Required config type with capabilityExecutor as optional
 */
type ResolvedTaskFlowEngineConfig = Required<Omit<TaskFlowEngineConfig, 'capabilityExecutor'>> & {
  capabilityExecutor?: ICapabilityExecutor;
};

/**
 * TaskFlowEngine - Main workflow execution facade
 *
 * Provides a simplified interface for executing TaskFlow workflows.
 * Wraps the underlying WorkflowExecutor with sensible defaults.
 * Issue #372: Supports CapabilityExecutor for capability_id based API execution
 */
export class TaskFlowEngine {
  private readonly config: ResolvedTaskFlowEngineConfig;
  private readonly executor: WorkflowExecutor;

  constructor(config: TaskFlowEngineConfig = {}) {
    this.config = {
      maxConcurrentSteps: config.maxConcurrentSteps ?? 5,
      defaultTimeout: config.defaultTimeout ?? 30000,
      enableRecovery: config.enableRecovery ?? true,
      nodeRegistry: config.nodeRegistry ?? createDefaultNodeRegistry(),
      capabilityExecutor: config.capabilityExecutor,
    };

    this.executor = new WorkflowExecutor({
      nodeRegistry: this.config.nodeRegistry,
      defaultTimeout: this.config.defaultTimeout,
      capabilityExecutor: this.config.capabilityExecutor,
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
    // Issue #372: Check if workflow is already InternalWorkflowDefinition (has inputSchema)
    // If so, use it directly to preserve params
    const isInternalWorkflow = 'inputSchema' in workflow && 'outputMapping' in workflow;

    const internalWorkflow: InternalWorkflowDefinition = isInternalWorkflow
      ? (workflow as unknown as InternalWorkflowDefinition)
      : {
          id: workflow.id,
          name: workflow.name,
          version: workflow.version,
          steps: workflow.steps.map((step) => ({
            id: step.id,
            name: step.name || step.id,
            type: (step.type || 'action') as NodeType,
            config: step.config || {},
            // Issue #372: Preserve params if they exist (for InternalWorkflowStep)
            params: ('params' in step ? step.params : {}) as Record<string, unknown>,
            dependsOn: step.dependsOn,
          })),
          inputSchema: { type: 'object' },
          outputSchema: { type: 'object' },
          // Issue #372: Convert output field to outputMapping for result extraction
          outputMapping: workflow.output || {},
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
   * Issue #372: Returns ResolvedTaskFlowEngineConfig (capabilityExecutor is optional)
   */
  getConfig(): Readonly<ResolvedTaskFlowEngineConfig> {
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
