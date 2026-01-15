/**
 * ExecutionContext - Execution state management
 *
 * Manages the execution context for workflow runs, including
 * request tracking, state management, and lifecycle hooks.
 */

import type { WorkflowDefinition, StepResult } from '../types/workflow.types.js';

/**
 * Execution context state
 */
export interface ExecutionState {
  workflowId: string;
  requestId: string;
  startTime: Date;
  currentStep?: string;
  completedSteps: string[];
  stepResults: Map<string, StepResult>;
  variables: Map<string, unknown>;
  metadata: Map<string, unknown>;
}

/**
 * Execution context options
 */
export interface ExecutionContextOptions {
  requestId?: string;
  timeout?: number;
  metadata?: Record<string, unknown>;
}

/**
 * ExecutionContext class - manages execution state for workflows
 */
export class ExecutionContext {
  private state: ExecutionState;
  private readonly timeout: number;
  private startTime: Date;

  constructor(
    private readonly workflow: WorkflowDefinition,
    options: ExecutionContextOptions = {}
  ) {
    this.startTime = new Date();
    this.timeout = options.timeout ?? workflow.timeout ?? 300000; // Default 5 minutes

    this.state = {
      workflowId: workflow.id,
      requestId: options.requestId ?? this.generateRequestId(),
      startTime: this.startTime,
      completedSteps: [],
      stepResults: new Map(),
      variables: new Map(Object.entries(workflow.variables ?? {})),
      metadata: new Map(Object.entries(options.metadata ?? {})),
    };
  }

  /**
   * Get the current request ID
   */
  getRequestId(): string {
    return this.state.requestId;
  }

  /**
   * Get the workflow ID
   */
  getWorkflowId(): string {
    return this.state.workflowId;
  }

  /**
   * Get the workflow definition
   */
  getWorkflow(): WorkflowDefinition {
    return this.workflow;
  }

  /**
   * Set the current step being executed
   */
  setCurrentStep(stepId: string): void {
    this.state.currentStep = stepId;
  }

  /**
   * Get the current step ID
   */
  getCurrentStep(): string | undefined {
    return this.state.currentStep;
  }

  /**
   * Mark a step as completed
   */
  completeStep(stepId: string, result: StepResult): void {
    this.state.completedSteps.push(stepId);
    this.state.stepResults.set(stepId, result);
    if (this.state.currentStep === stepId) {
      this.state.currentStep = undefined;
    }
  }

  /**
   * Check if a step has been completed
   */
  isStepCompleted(stepId: string): boolean {
    return this.state.completedSteps.includes(stepId);
  }

  /**
   * Get the result of a completed step
   */
  getStepResult(stepId: string): StepResult | undefined {
    return this.state.stepResults.get(stepId);
  }

  /**
   * Get all step results
   */
  getAllStepResults(): StepResult[] {
    return Array.from(this.state.stepResults.values());
  }

  /**
   * Set a variable in the context
   */
  setVariable(key: string, value: unknown): void {
    this.state.variables.set(key, value);
  }

  /**
   * Get a variable from the context
   */
  getVariable(key: string): unknown {
    return this.state.variables.get(key);
  }

  /**
   * Get all variables
   */
  getAllVariables(): Record<string, unknown> {
    return Object.fromEntries(this.state.variables);
  }

  /**
   * Set metadata
   */
  setMetadata(key: string, value: unknown): void {
    this.state.metadata.set(key, value);
  }

  /**
   * Get metadata
   */
  getMetadata(key: string): unknown {
    return this.state.metadata.get(key);
  }

  /**
   * Check if the execution has timed out
   */
  isTimedOut(): boolean {
    return Date.now() - this.startTime.getTime() > this.timeout;
  }

  /**
   * Get remaining time in milliseconds
   */
  getRemainingTime(): number {
    const elapsed = Date.now() - this.startTime.getTime();
    return Math.max(0, this.timeout - elapsed);
  }

  /**
   * Get execution duration in milliseconds
   */
  getDuration(): number {
    return Date.now() - this.startTime.getTime();
  }

  /**
   * Create a snapshot of the current state
   */
  snapshot(): ExecutionState {
    return {
      ...this.state,
      stepResults: new Map(this.state.stepResults),
      variables: new Map(this.state.variables),
      metadata: new Map(this.state.metadata),
      completedSteps: [...this.state.completedSteps],
    };
  }

  /**
   * Generate a unique request ID
   */
  private generateRequestId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 10);
    return `req_${timestamp}_${random}`;
  }
}

/**
 * Factory function to create ExecutionContext
 */
export function createExecutionContext(
  workflow: WorkflowDefinition,
  options?: ExecutionContextOptions
): ExecutionContext {
  return new ExecutionContext(workflow, options);
}
