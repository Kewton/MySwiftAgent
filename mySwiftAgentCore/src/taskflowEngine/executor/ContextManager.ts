/**
 * ContextManager - Workflow execution context management
 *
 * Issue #363: Manages context during workflow execution
 * Issue #372: Extended to support CapabilityExecutor
 */

import type { ExecutionContext, ICapabilityExecutor } from '../nodes/BaseNode.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';

/**
 * Context manager configuration
 */
export interface ContextManagerConfig {
  secrets?: Record<string, string>;
  variables?: Record<string, unknown>;
  /** Issue #372: CapabilityExecutor for capability_id based API execution */
  capabilityExecutor?: ICapabilityExecutor;
}

/**
 * ContextManager - Manages execution context
 *
 * Features:
 * - Variable resolution
 * - Step result storage
 * - Secret management
 * - Issue #372: CapabilityExecutor support
 */
export class ContextManager {
  private readonly workflowId: string;
  private readonly stepResults: Map<string, unknown>;
  private readonly variables: Map<string, unknown>;
  private readonly secrets: Record<string, string>;
  private readonly capabilityExecutor?: ICapabilityExecutor;

  constructor(
    workflow: InternalWorkflowDefinition,
    config: ContextManagerConfig = {}
  ) {
    this.workflowId = workflow.id;
    this.stepResults = new Map();
    this.variables = new Map(Object.entries(workflow.variables || {}));
    this.secrets = config.secrets || {};
    this.capabilityExecutor = config.capabilityExecutor;

    // Add initial variables from config
    if (config.variables) {
      for (const [key, value] of Object.entries(config.variables)) {
        this.variables.set(key, value);
      }
    }
  }

  /**
   * Get execution context for a step
   * Issue #372: Now includes capabilityExecutor if configured
   */
  getContext(): ExecutionContext {
    return {
      workflowId: this.workflowId,
      stepResults: Object.fromEntries(this.stepResults),
      variables: Object.fromEntries(this.variables),
      secrets: this.secrets,
      capabilityExecutor: this.capabilityExecutor,
    };
  }

  /**
   * Store step result
   */
  setStepResult(stepId: string, result: unknown): void {
    this.stepResults.set(stepId, result);
  }

  /**
   * Get step result
   */
  getStepResult(stepId: string): unknown {
    return this.stepResults.get(stepId);
  }

  /**
   * Check if step has result
   */
  hasStepResult(stepId: string): boolean {
    return this.stepResults.has(stepId);
  }

  /**
   * Set variable
   */
  setVariable(key: string, value: unknown): void {
    this.variables.set(key, value);
  }

  /**
   * Get variable
   */
  getVariable(key: string): unknown {
    return this.variables.get(key);
  }

  /**
   * Resolve variable references in a value
   * Issue #372: Handles both ${stepId.output} and $stepId.output patterns
   * Also recursively resolves values in arrays and objects
   */
  resolveValue(value: unknown, inputs: Record<string, unknown>): unknown {
    // Handle arrays recursively
    if (Array.isArray(value)) {
      return value.map((item) => this.resolveValue(item, inputs));
    }

    // Handle objects recursively (but not null)
    if (value !== null && typeof value === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(value)) {
        result[key] = this.resolveValue(val, inputs);
      }
      return result;
    }

    if (typeof value !== 'string') {
      return value;
    }

    // Check for ${...} pattern
    const match1 = value.match(/^\$\{(.+)\}$/);
    if (match1) {
      const path = match1[1]!;
      return this.resolvePath(path, inputs);
    }

    // Issue #372: Check for $xxx.yyy pattern (without curly braces)
    const match2 = value.match(/^\$(\w+(?:\.\w+)*)$/);
    if (match2) {
      const path = match2[1]!;
      return this.resolvePath(path, inputs);
    }

    return value;
  }

  /**
   * Resolve a path reference
   *
   * Supports the following path formats:
   * - $input.field - Access input fields
   * - $steps.stepId.field - Access step results (graphAiServer format)
   * - $stepId.field - Access step results directly
   * - $variable - Access variables
   */
  private resolvePath(path: string, inputs: Record<string, unknown>): unknown {
    const parts = path.split('.');

    if (parts.length === 0) {
      return undefined;
    }

    const root = parts[0]!;
    let rest = parts.slice(1);

    let value: unknown;

    if (root === 'input') {
      value = inputs;
    } else if (root === 'steps') {
      // Issue #372: Handle $steps.stepId.field format (graphAiServer compatible)
      // Extract stepId from rest and use it to get step result
      if (rest.length === 0) {
        return undefined;
      }
      const stepId = rest[0]!;
      rest = rest.slice(1);
      value = this.stepResults.get(stepId);
    } else {
      // Try step results directly (e.g., $stepId.field)
      value = this.stepResults.get(root);
      if (value === undefined) {
        // Try variables
        value = this.variables.get(root);
      }
    }

    // Navigate nested path
    for (const part of rest) {
      if (value === null || value === undefined) {
        return undefined;
      }
      if (typeof value === 'object') {
        value = (value as Record<string, unknown>)[part];
      } else {
        return undefined;
      }
    }

    return value;
  }

  /**
   * Build output from mapping
   */
  buildOutput(
    outputMapping: Record<string, string>,
    inputs: Record<string, unknown>
  ): Record<string, unknown> {
    const result: Record<string, unknown> = {};

    for (const [key, valueRef] of Object.entries(outputMapping)) {
      result[key] = this.resolveValue(valueRef, inputs);
    }

    return result;
  }

  /**
   * Get workflow ID
   */
  getWorkflowId(): string {
    return this.workflowId;
  }

  /**
   * Get all step results
   */
  getAllStepResults(): Record<string, unknown> {
    return Object.fromEntries(this.stepResults);
  }
}

/**
 * Factory function
 */
export function createContextManager(
  workflow: InternalWorkflowDefinition,
  config?: ContextManagerConfig
): ContextManager {
  return new ContextManager(workflow, config);
}
