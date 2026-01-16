/**
 * WorkflowExecutor - Main workflow execution engine
 *
 * Issue #363: Executes TaskFlow workflows
 */

import type { InternalWorkflowDefinition, InternalWorkflowStep } from '../types/InternalWorkflowDefinition.js';
import type { NodeRegistry, NodeConfig } from '../nodes/BaseNode.js';
import { ContextManager, type ContextManagerConfig } from './ContextManager.js';
import { ParallelExecutionManager } from './ParallelExecutionManager.js';
import type { ExecutionStatus, StepResult, StepError, WorkflowExecutionResult } from '../../shared/types/workflow.types.js';

/**
 * Workflow executor configuration
 */
export interface WorkflowExecutorConfig {
  nodeRegistry: NodeRegistry;
  parallelManager?: ParallelExecutionManager;
  defaultTimeout?: number;
}

/**
 * Execution options
 */
export interface ExecutionOptions {
  inputs?: Record<string, unknown>;
  secrets?: Record<string, string>;
  variables?: Record<string, unknown>;
  timeout?: number;
}

/**
 * WorkflowExecutor - Executes workflows
 *
 * Features:
 * - Sequential and parallel step execution
 * - Dependency resolution
 * - Error handling with partial success
 * - Context management
 */
export class WorkflowExecutor {
  private readonly config: WorkflowExecutorConfig;
  private readonly parallelManager: ParallelExecutionManager;

  constructor(config: WorkflowExecutorConfig) {
    this.config = config;
    this.parallelManager = config.parallelManager || new ParallelExecutionManager();
  }

  /**
   * Execute a workflow
   */
  async execute(
    workflow: InternalWorkflowDefinition,
    options: ExecutionOptions = {}
  ): Promise<WorkflowExecutionResult> {
    const startTime = new Date();
    const stepResults: StepResult[] = [];
    const errors: StepError[] = [];
    const inputs = options.inputs || {};

    // Create context manager
    const contextConfig: ContextManagerConfig = {
      secrets: options.secrets,
      variables: options.variables,
    };
    const contextManager = new ContextManager(workflow, contextConfig);

    // Store inputs in context
    contextManager.setVariable('input', inputs);

    // Determine execution order based on dependencies
    const executionOrder = this.resolveExecutionOrder(workflow.steps);

    // Execute steps
    for (const step of executionOrder) {
      const stepStartTime = new Date();

      try {
        // Check if dependencies are satisfied
        const canExecute = this.checkDependencies(step, contextManager);
        if (!canExecute) {
          const error: StepError = {
            stepId: step.id,
            stepName: step.name,
            errorCode: 'DEPENDENCY_FAILED',
            errorMessage: `Dependencies not satisfied for step ${step.id}`,
            timestamp: new Date(),
            recoverable: false,
          };
          errors.push(error);
          stepResults.push(this.createFailedStepResult(step, stepStartTime, error));
          continue;
        }

        // Resolve parameters
        const resolvedParams = this.resolveParams(step.params, inputs, contextManager);

        // Get node executor
        const executor = this.config.nodeRegistry.get(step.type);
        if (!executor) {
          const error: StepError = {
            stepId: step.id,
            stepName: step.name,
            errorCode: 'UNKNOWN_NODE_TYPE',
            errorMessage: `Unknown node type: ${step.type}`,
            timestamp: new Date(),
            recoverable: false,
          };
          errors.push(error);
          stepResults.push(this.createFailedStepResult(step, stepStartTime, error));
          continue;
        }

        // Build node config
        const nodeConfig: NodeConfig = {
          nodeId: step.id,
          type: step.type,
          config: step.config,
        };

        // Execute with parallel manager for resource control
        const result = await this.parallelManager.execute(
          workflow.id,
          step.type,
          async () => executor.execute(nodeConfig, resolvedParams, contextManager.getContext())
        );

        const stepEndTime = new Date();

        if (result.success) {
          // Store result in context
          contextManager.setStepResult(step.id, result.output);

          stepResults.push({
            stepId: step.id,
            stepName: step.name,
            status: 'success',
            output: result.output,
            startTime: stepStartTime,
            endTime: stepEndTime,
            durationMs: stepEndTime.getTime() - stepStartTime.getTime(),
          });
        } else {
          const error: StepError = {
            stepId: step.id,
            stepName: step.name,
            errorCode: result.error?.code || 'EXECUTION_ERROR',
            errorMessage: result.error?.message || 'Unknown error',
            timestamp: new Date(),
            recoverable: true,
            context: result.error?.details as Record<string, unknown>,
          };
          errors.push(error);
          stepResults.push(this.createFailedStepResult(step, stepStartTime, error));
        }
      } catch (error) {
        const stepError: StepError = {
          stepId: step.id,
          stepName: step.name,
          errorCode: 'UNEXPECTED_ERROR',
          errorMessage: error instanceof Error ? error.message : 'Unknown error',
          timestamp: new Date(),
          recoverable: false,
        };
        errors.push(stepError);
        stepResults.push(this.createFailedStepResult(step, stepStartTime, stepError));
      }
    }

    // Build output
    const output = contextManager.buildOutput(workflow.outputMapping, inputs);

    // Determine overall status
    const status = this.determineStatus(stepResults, errors);
    const endTime = new Date();

    // Cleanup
    this.parallelManager.cleanup(workflow.id);

    return {
      workflowId: workflow.id,
      workflowName: workflow.name,
      status,
      stepResults,
      errors,
      recoveryActions: [],
      startTime,
      endTime,
      durationMs: endTime.getTime() - startTime.getTime(),
      metadata: {
        output,
        inputs,
      },
    };
  }

  /**
   * Resolve execution order based on dependencies
   */
  private resolveExecutionOrder(steps: InternalWorkflowStep[]): InternalWorkflowStep[] {
    const resolved: InternalWorkflowStep[] = [];
    const remaining = [...steps];
    const resolvedIds = new Set<string>();

    while (remaining.length > 0) {
      const readyIndex = remaining.findIndex((step) =>
        !step.dependsOn || step.dependsOn.every((dep) => resolvedIds.has(dep))
      );

      if (readyIndex === -1) {
        // Circular dependency or missing step
        // Add remaining in order
        resolved.push(...remaining);
        break;
      }

      const step = remaining.splice(readyIndex, 1)[0]!;
      resolved.push(step);
      resolvedIds.add(step.id);
    }

    return resolved;
  }

  /**
   * Check if step dependencies are satisfied
   */
  private checkDependencies(
    step: InternalWorkflowStep,
    contextManager: ContextManager
  ): boolean {
    if (!step.dependsOn || step.dependsOn.length === 0) {
      return true;
    }

    return step.dependsOn.every((depId) => contextManager.hasStepResult(depId));
  }

  /**
   * Resolve parameter references
   */
  private resolveParams(
    params: Record<string, unknown>,
    inputs: Record<string, unknown>,
    contextManager: ContextManager
  ): Record<string, unknown> {
    const resolved: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(params)) {
      resolved[key] = contextManager.resolveValue(value, inputs);
    }

    return resolved;
  }

  /**
   * Create failed step result
   */
  private createFailedStepResult(
    step: InternalWorkflowStep,
    startTime: Date,
    error: StepError
  ): StepResult {
    const endTime = new Date();
    return {
      stepId: step.id,
      stepName: step.name,
      status: 'failed',
      error,
      startTime,
      endTime,
      durationMs: endTime.getTime() - startTime.getTime(),
    };
  }

  /**
   * Determine overall status
   */
  private determineStatus(stepResults: StepResult[], errors: StepError[]): ExecutionStatus {
    if (errors.length === 0 && stepResults.every((r) => r.status === 'success')) {
      return 'success';
    }

    if (stepResults.every((r) => r.status === 'failed')) {
      return 'failed';
    }

    return 'partial_success';
  }
}

/**
 * Factory function
 */
export function createWorkflowExecutor(config: WorkflowExecutorConfig): WorkflowExecutor {
  return new WorkflowExecutor(config);
}
