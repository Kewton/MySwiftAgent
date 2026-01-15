/**
 * TaskFlow Engine - Workflow execution engine
 *
 * This module provides the core workflow execution engine for TaskFlow.
 * It handles workflow parsing, step execution, and result aggregation.
 *
 * @module taskflowEngine
 */

import type {
  WorkflowDefinition,
  WorkflowExecutionResult,
  StepResult,
  StepError,
  RecoveryAction,
  ExecutionStatus,
} from '../shared/types/workflow.types.js';
import {
  createExecutionContext,
  type ExecutionContextOptions,
} from '../shared/context/ExecutionContext.js';
import {
  ValidationCoordinator,
  createValidationCoordinator,
} from '../shared/context/ValidationCoordinator.js';

/**
 * TaskFlow Engine configuration
 */
export interface TaskFlowEngineConfig {
  maxConcurrentSteps?: number;
  defaultTimeout?: number;
  enableRecovery?: boolean;
}

/**
 * TaskFlow Engine class - executes workflows
 */
export class TaskFlowEngine {
  private readonly config: TaskFlowEngineConfig;
  private readonly validator: ValidationCoordinator;

  constructor(config: TaskFlowEngineConfig = {}) {
    this.config = {
      maxConcurrentSteps: config.maxConcurrentSteps ?? 5,
      defaultTimeout: config.defaultTimeout ?? 300000,
      enableRecovery: config.enableRecovery ?? true,
    };
    this.validator = createValidationCoordinator();
  }

  /**
   * Execute a workflow definition
   *
   * @param workflow - The workflow definition to execute
   * @param options - Execution options
   * @returns WorkflowExecutionResult with status and results
   */
  async execute(
    workflow: WorkflowDefinition,
    options?: ExecutionContextOptions
  ): Promise<WorkflowExecutionResult> {
    const startTime = new Date();

    // Validate workflow
    const validationResult = this.validator.validateWorkflow(workflow);
    if (!validationResult.valid) {
      return this.createFailedResult(
        workflow,
        startTime,
        validationResult.errors.map((e) => ({
          stepId: 'validation',
          stepName: 'Workflow Validation',
          errorCode: 'VALIDATION_ERROR',
          errorMessage: e.message,
          timestamp: new Date(),
          recoverable: false,
          context: { field: e.field, value: e.value },
        }))
      );
    }

    // Create execution context
    const context = createExecutionContext(workflow, {
      ...options,
      timeout: options?.timeout ?? this.config.defaultTimeout,
    });

    const stepResults: StepResult[] = [];
    const errors: StepError[] = [];
    const recoveryActions: RecoveryAction[] = [];

    // Execute steps (stub implementation)
    for (const step of workflow.steps) {
      const stepStartTime = new Date();

      // Check for timeout
      if (context.isTimedOut()) {
        errors.push({
          stepId: step.id,
          stepName: step.name,
          errorCode: 'TIMEOUT',
          errorMessage: 'Workflow execution timed out',
          timestamp: new Date(),
          recoverable: false,
        });
        break;
      }

      // Stub step execution
      const stepResult: StepResult = {
        stepId: step.id,
        stepName: step.name,
        status: 'success',
        output: { message: 'Step executed (stub)' },
        startTime: stepStartTime,
        endTime: new Date(),
        durationMs: Date.now() - stepStartTime.getTime(),
      };

      stepResults.push(stepResult);
      context.completeStep(step.id, stepResult);
    }

    // Determine overall status
    const status = this.determineStatus(stepResults, errors);
    const endTime = new Date();

    return {
      workflowId: workflow.id,
      workflowName: workflow.name,
      status,
      stepResults,
      errors,
      recoveryActions,
      startTime,
      endTime,
      durationMs: endTime.getTime() - startTime.getTime(),
      metadata: {
        requestId: context.getRequestId(),
      },
    };
  }

  /**
   * Determine overall execution status from results
   */
  private determineStatus(stepResults: StepResult[], errors: StepError[]): ExecutionStatus {
    if (errors.length > 0 && stepResults.every((r) => r.status === 'failed')) {
      return 'failed';
    }

    if (errors.length > 0 || stepResults.some((r) => r.status === 'failed')) {
      return 'partial_success';
    }

    return 'success';
  }

  /**
   * Create a failed result for validation errors
   */
  private createFailedResult(
    workflow: WorkflowDefinition,
    startTime: Date,
    errors: StepError[]
  ): WorkflowExecutionResult {
    const endTime = new Date();
    return {
      workflowId: workflow.id,
      workflowName: workflow.name,
      status: 'failed',
      stepResults: [],
      errors,
      recoveryActions: [],
      startTime,
      endTime,
      durationMs: endTime.getTime() - startTime.getTime(),
    };
  }
}

/**
 * Factory function to create TaskFlowEngine
 */
export function createTaskFlowEngine(config?: TaskFlowEngineConfig): TaskFlowEngine {
  return new TaskFlowEngine(config);
}

// Types are exported via their interface definitions above
