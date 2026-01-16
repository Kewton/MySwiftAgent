/**
 * SchemaValidator - TaskFlow schema validation
 *
 * Issue #363: Validates TaskFlow definitions against schema
 */

import { z } from 'zod';
import type { TaskFlowDefinition } from '../types/TaskFlowDefinition.js';
import { TaskFlowDefinitionSchema } from '../types/TaskFlowDefinition.js';
import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';
import { InternalWorkflowDefinitionSchema } from '../types/InternalWorkflowDefinition.js';

/**
 * Validation result
 */
export interface SchemaValidationResult {
  valid: boolean;
  errors: SchemaValidationError[];
}

/**
 * Validation error
 */
export interface SchemaValidationError {
  path: string;
  message: string;
  code: string;
}

/**
 * SchemaValidator - Validates TaskFlow definitions
 *
 * Features:
 * - Validates external TaskFlowDefinition
 * - Validates internal InternalWorkflowDefinition
 * - Provides detailed error information
 */
export class SchemaValidator {
  /**
   * Validate TaskFlowDefinition (external format)
   */
  validateTaskFlow(workflow: unknown): SchemaValidationResult {
    return this.validate(workflow, TaskFlowDefinitionSchema);
  }

  /**
   * Validate InternalWorkflowDefinition (internal format)
   */
  validateInternal(workflow: unknown): SchemaValidationResult {
    return this.validate(workflow, InternalWorkflowDefinitionSchema);
  }

  /**
   * Validate inputs against workflow input schema
   */
  validateInputs(
    workflow: TaskFlowDefinition | InternalWorkflowDefinition,
    inputs: unknown
  ): SchemaValidationResult {
    const inputSchema = 'input_schema' in workflow
      ? workflow.input_schema
      : workflow.inputSchema;

    if (!inputSchema || !inputSchema.properties) {
      return { valid: true, errors: [] };
    }

    const errors: SchemaValidationError[] = [];

    // Check required fields
    const required = inputSchema.required || [];
    for (const field of required) {
      if (!inputs || typeof inputs !== 'object' || !(field in inputs)) {
        errors.push({
          path: field,
          message: `Required field '${field}' is missing`,
          code: 'REQUIRED_FIELD_MISSING',
        });
      }
    }

    // Validate types (basic)
    if (inputs && typeof inputs === 'object' && inputSchema.properties) {
      for (const [field, schema] of Object.entries(inputSchema.properties)) {
        const value = (inputs as Record<string, unknown>)[field];
        if (value !== undefined) {
          const typeError = this.validateType(value, schema.type);
          if (typeError) {
            errors.push({
              path: field,
              message: typeError,
              code: 'TYPE_MISMATCH',
            });
          }
        }
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Validate step dependencies
   */
  validateDependencies(
    workflow: InternalWorkflowDefinition
  ): SchemaValidationResult {
    const errors: SchemaValidationError[] = [];
    const stepIds = new Set(workflow.steps.map((s) => s.id));

    for (const step of workflow.steps) {
      if (step.dependsOn) {
        for (const depId of step.dependsOn) {
          if (!stepIds.has(depId)) {
            errors.push({
              path: `steps.${step.id}.dependsOn`,
              message: `Dependency '${depId}' not found`,
              code: 'DEPENDENCY_NOT_FOUND',
            });
          }
        }
      }
    }

    // Check for circular dependencies
    const circularError = this.detectCircularDependencies(workflow.steps);
    if (circularError) {
      errors.push(circularError);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Perform generic validation with a Zod schema
   */
  private validate(data: unknown, schema: z.ZodType): SchemaValidationResult {
    const result = schema.safeParse(data);

    if (result.success) {
      return { valid: true, errors: [] };
    }

    const errors: SchemaValidationError[] = result.error.errors.map((e) => ({
      path: e.path.join('.'),
      message: e.message,
      code: e.code,
    }));

    return { valid: false, errors };
  }

  /**
   * Validate type (basic)
   */
  private validateType(value: unknown, expectedType: string): string | null {
    const actualType = typeof value;

    switch (expectedType) {
      case 'string':
        if (actualType !== 'string') {
          return `Expected string, got ${actualType}`;
        }
        break;
      case 'number':
      case 'integer':
        if (actualType !== 'number') {
          return `Expected number, got ${actualType}`;
        }
        break;
      case 'boolean':
        if (actualType !== 'boolean') {
          return `Expected boolean, got ${actualType}`;
        }
        break;
      case 'array':
        if (!Array.isArray(value)) {
          return `Expected array, got ${actualType}`;
        }
        break;
      case 'object':
        if (actualType !== 'object' || Array.isArray(value)) {
          return `Expected object, got ${actualType}`;
        }
        break;
    }

    return null;
  }

  /**
   * Detect circular dependencies
   */
  private detectCircularDependencies(
    steps: InternalWorkflowDefinition['steps']
  ): SchemaValidationError | null {
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const stepMap = new Map(steps.map((s) => [s.id, s]));

    const hasCycle = (stepId: string): boolean => {
      if (recursionStack.has(stepId)) {
        return true;
      }
      if (visited.has(stepId)) {
        return false;
      }

      visited.add(stepId);
      recursionStack.add(stepId);

      const step = stepMap.get(stepId);
      if (step?.dependsOn) {
        for (const depId of step.dependsOn) {
          if (hasCycle(depId)) {
            return true;
          }
        }
      }

      recursionStack.delete(stepId);
      return false;
    };

    for (const step of steps) {
      if (hasCycle(step.id)) {
        return {
          path: 'steps',
          message: 'Circular dependency detected',
          code: 'CIRCULAR_DEPENDENCY',
        };
      }
    }

    return null;
  }
}

/**
 * Factory function
 */
export function createSchemaValidator(): SchemaValidator {
  return new SchemaValidator();
}
