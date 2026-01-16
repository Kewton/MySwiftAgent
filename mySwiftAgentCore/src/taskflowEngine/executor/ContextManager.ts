/**
 * ContextManager - Workflow execution context management
 *
 * Issue #363: Manages context during workflow execution
 */

import type { ExecutionContext } from '../nodes/BaseNode.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';

/**
 * Context manager configuration
 */
export interface ContextManagerConfig {
  secrets?: Record<string, string>;
  variables?: Record<string, unknown>;
}

/**
 * ContextManager - Manages execution context
 *
 * Features:
 * - Variable resolution
 * - Step result storage
 * - Secret management
 */
export class ContextManager {
  private readonly workflowId: string;
  private readonly stepResults: Map<string, unknown>;
  private readonly variables: Map<string, unknown>;
  private readonly secrets: Record<string, string>;

  constructor(
    workflow: InternalWorkflowDefinition,
    config: ContextManagerConfig = {}
  ) {
    this.workflowId = workflow.id;
    this.stepResults = new Map();
    this.variables = new Map(Object.entries(workflow.variables || {}));
    this.secrets = config.secrets || {};

    // Add initial variables from config
    if (config.variables) {
      for (const [key, value] of Object.entries(config.variables)) {
        this.variables.set(key, value);
      }
    }
  }

  /**
   * Get execution context for a step
   */
  getContext(): ExecutionContext {
    return {
      workflowId: this.workflowId,
      stepResults: Object.fromEntries(this.stepResults),
      variables: Object.fromEntries(this.variables),
      secrets: this.secrets,
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
   * Handles ${stepId.output} and ${input.field} patterns
   */
  resolveValue(value: unknown, inputs: Record<string, unknown>): unknown {
    if (typeof value !== 'string') {
      return value;
    }

    // Check for ${...} pattern
    const match = value.match(/^\$\{(.+)\}$/);
    if (!match) {
      return value;
    }

    const path = match[1]!;
    return this.resolvePath(path, inputs);
  }

  /**
   * Resolve a path reference
   */
  private resolvePath(path: string, inputs: Record<string, unknown>): unknown {
    const parts = path.split('.');

    if (parts.length === 0) {
      return undefined;
    }

    const root = parts[0]!;
    const rest = parts.slice(1);

    let value: unknown;

    if (root === 'input') {
      value = inputs;
    } else {
      // Try step results
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
