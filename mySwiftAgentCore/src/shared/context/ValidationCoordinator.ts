/**
 * ValidationCoordinator - Validation coordination for workflows
 *
 * Coordinates validation across workflow execution, including
 * input validation, schema validation, and security checks.
 */

import { z } from 'zod';
import type { WorkflowDefinition, WorkflowStep } from '../types/workflow.types.js';
import type { ValidationError, FieldError } from '../types/error.types.js';
import { ErrorCodes } from '../types/error.types.js';

/**
 * Validation rule definition
 */
export interface ValidationRule {
  name: string;
  validate: (value: unknown, context?: ValidationContext) => ValidationResult;
}

/**
 * Validation context
 */
export interface ValidationContext {
  workflow?: WorkflowDefinition;
  step?: WorkflowStep;
  variables?: Record<string, unknown>;
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean;
  errors: FieldError[];
}

/**
 * ValidationCoordinator class - coordinates validation operations
 */
export class ValidationCoordinator {
  private readonly rules: Map<string, ValidationRule>;

  constructor() {
    this.rules = new Map();
    this.registerDefaultRules();
  }

  /**
   * Register a validation rule
   */
  registerRule(rule: ValidationRule): void {
    this.rules.set(rule.name, rule);
  }

  /**
   * Validate a workflow definition
   */
  validateWorkflow(workflow: WorkflowDefinition): ValidationResult {
    const errors: FieldError[] = [];

    // Validate workflow ID
    if (!workflow.id || workflow.id.trim() === '') {
      errors.push({
        field: 'id',
        message: 'Workflow ID is required',
      });
    }

    // Validate workflow name
    if (!workflow.name || workflow.name.trim() === '') {
      errors.push({
        field: 'name',
        message: 'Workflow name is required',
      });
    }

    // Validate version format
    if (workflow.version && !this.isValidVersion(workflow.version)) {
      errors.push({
        field: 'version',
        message: 'Invalid version format (expected semver)',
        value: workflow.version,
      });
    }

    // Validate steps
    if (!workflow.steps || workflow.steps.length === 0) {
      errors.push({
        field: 'steps',
        message: 'Workflow must have at least one step',
      });
    } else {
      // Validate each step
      for (let i = 0; i < workflow.steps.length; i++) {
        const step = workflow.steps[i];
        if (step) {
          const stepErrors = this.validateStep(step, i);
          errors.push(...stepErrors);
        }
      }

      // Validate step dependencies
      const dependencyErrors = this.validateStepDependencies(workflow.steps);
      errors.push(...dependencyErrors);
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Validate a workflow step
   */
  validateStep(step: WorkflowStep, index: number): FieldError[] {
    const errors: FieldError[] = [];
    const prefix = `steps[${index}]`;

    if (!step.id || step.id.trim() === '') {
      errors.push({
        field: `${prefix}.id`,
        message: 'Step ID is required',
      });
    }

    if (!step.name || step.name.trim() === '') {
      errors.push({
        field: `${prefix}.name`,
        message: 'Step name is required',
      });
    }

    if (!step.type || step.type.trim() === '') {
      errors.push({
        field: `${prefix}.type`,
        message: 'Step type is required',
      });
    }

    return errors;
  }

  /**
   * Validate step dependencies
   */
  validateStepDependencies(steps: WorkflowStep[]): FieldError[] {
    const errors: FieldError[] = [];
    const stepIds = new Set(steps.map((s) => s.id));

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      if (step?.dependsOn) {
        for (const depId of step.dependsOn) {
          if (!stepIds.has(depId)) {
            errors.push({
              field: `steps[${i}].dependsOn`,
              message: `Dependency '${depId}' not found`,
              value: depId,
            });
          }
        }
      }
    }

    // Check for circular dependencies
    const circularErrors = this.detectCircularDependencies(steps);
    errors.push(...circularErrors);

    return errors;
  }

  /**
   * Validate input against a Zod schema
   */
  validateWithSchema<T>(
    schema: z.ZodSchema<T>,
    input: unknown,
    fieldPrefix?: string
  ): ValidationResult {
    const result = schema.safeParse(input);

    if (result.success) {
      return { valid: true, errors: [] };
    }

    const errors: FieldError[] = result.error.errors.map((err) => ({
      field: fieldPrefix ? `${fieldPrefix}.${err.path.join('.')}` : err.path.join('.'),
      message: err.message,
      constraint: err.code,
    }));

    return { valid: false, errors };
  }

  /**
   * Convert validation result to CoreError
   */
  toValidationError(result: ValidationResult, message?: string): ValidationError | null {
    if (result.valid) {
      return null;
    }

    return {
      code: ErrorCodes.VAL_INVALID_INPUT,
      message: message ?? 'Validation failed',
      category: 'validation',
      severity: 'medium',
      timestamp: new Date(),
      fieldErrors: result.errors,
    };
  }

  /**
   * Register default validation rules
   */
  private registerDefaultRules(): void {
    this.registerRule({
      name: 'required',
      validate: (value: unknown): ValidationResult => {
        if (value === null || value === undefined || value === '') {
          return {
            valid: false,
            errors: [{ field: '', message: 'Value is required' }],
          };
        }
        return { valid: true, errors: [] };
      },
    });

    this.registerRule({
      name: 'nonEmptyString',
      validate: (value: unknown): ValidationResult => {
        if (typeof value !== 'string' || value.trim() === '') {
          return {
            valid: false,
            errors: [{ field: '', message: 'Value must be a non-empty string' }],
          };
        }
        return { valid: true, errors: [] };
      },
    });
  }

  /**
   * Check if a version string is valid semver
   */
  private isValidVersion(version: string): boolean {
    const semverPattern = /^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$/;
    return semverPattern.test(version);
  }

  /**
   * Detect circular dependencies in steps
   */
  private detectCircularDependencies(steps: WorkflowStep[]): FieldError[] {
    const errors: FieldError[] = [];
    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const stepMap = new Map<string, WorkflowStep>();
    for (const step of steps) {
      stepMap.set(step.id, step);
    }

    const dfs = (stepId: string, path: string[]): boolean => {
      if (recursionStack.has(stepId)) {
        const cycle = [...path, stepId].join(' -> ');
        errors.push({
          field: 'steps',
          message: `Circular dependency detected: ${cycle}`,
          value: stepId,
        });
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
          if (dfs(depId, [...path, stepId])) {
            return true;
          }
        }
      }

      recursionStack.delete(stepId);
      return false;
    };

    for (const step of steps) {
      if (!visited.has(step.id)) {
        dfs(step.id, []);
      }
    }

    return errors;
  }
}

/**
 * Factory function to create ValidationCoordinator
 */
export function createValidationCoordinator(): ValidationCoordinator {
  return new ValidationCoordinator();
}
