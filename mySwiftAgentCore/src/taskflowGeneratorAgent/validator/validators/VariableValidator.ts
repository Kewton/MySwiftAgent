/**
 * VariableValidator - Validates variable references in workflow
 *
 * Issue #364: Variable reference validation
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * VariableValidator - Validates variable references
 *
 * Checks:
 * - $input.xxx references match input_schema
 * - $steps.xxx.yyy references are valid
 * - $env.XXX references are noted as warnings
 */
export class VariableValidator implements Validator {
  readonly name = 'VariableValidator';

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    const inputFields = this.extractInputFields(workflow);
    // stepOutputs is reserved for future use (output field validation)
    void this.buildStepOutputMap(workflow.steps);

    // Validate each step
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (!step) continue;

      // Get preceding steps for this step
      const precedingSteps = workflow.steps.slice(0, i).map((s) => s.id);

      // Validate variable references in step
      this.validateStepReferences(
        step,
        i,
        inputFields,
        new Set(precedingSteps),
        errors,
        warnings
      );
    }

    // Validate output references
    this.validateOutputReferences(
      workflow,
      inputFields,
      new Set(workflow.steps.map((s) => s.id)),
      errors,
      warnings
    );

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Extract input field names from input_schema
   */
  private extractInputFields(workflow: TaskFlowDefinition): Set<string> {
    const fields = new Set<string>();

    if (workflow.input_schema?.properties) {
      for (const field of Object.keys(workflow.input_schema.properties)) {
        fields.add(field);
      }
    }

    return fields;
  }

  /**
   * Build map of step IDs to their potential outputs
   */
  private buildStepOutputMap(steps: TaskFlowStep[]): Map<string, Set<string>> {
    const map = new Map<string, Set<string>>();

    for (const step of steps) {
      // We don't know exact outputs, so we just track step existence
      map.set(step.id, new Set(['*'])); // Wildcard for any output
    }

    return map;
  }

  /**
   * Validate variable references in a step
   */
  private validateStepReferences(
    step: TaskFlowStep,
    stepIndex: number,
    inputFields: Set<string>,
    precedingSteps: Set<string>,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check params
    this.validateObject(
      step.params,
      `steps[${stepIndex}].params`,
      inputFields,
      precedingSteps,
      errors,
      warnings
    );

    // Check config
    this.validateObject(
      step.config,
      `steps[${stepIndex}].config`,
      inputFields,
      precedingSteps,
      errors,
      warnings
    );
  }

  /**
   * Validate variable references in an object
   */
  private validateObject(
    obj: unknown,
    path: string,
    inputFields: Set<string>,
    precedingSteps: Set<string>,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    if (typeof obj === 'string') {
      this.validateString(obj, path, inputFields, precedingSteps, errors, warnings);
    } else if (Array.isArray(obj)) {
      for (let i = 0; i < obj.length; i++) {
        this.validateObject(obj[i], `${path}[${i}]`, inputFields, precedingSteps, errors, warnings);
      }
    } else if (obj && typeof obj === 'object') {
      for (const [key, value] of Object.entries(obj)) {
        this.validateObject(value, `${path}.${key}`, inputFields, precedingSteps, errors, warnings);
      }
    }
  }

  /**
   * Validate variable references in a string
   */
  private validateString(
    str: string,
    path: string,
    inputFields: Set<string>,
    precedingSteps: Set<string>,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check $input references
    const inputPattern = /\$input\.([a-zA-Z_][a-zA-Z0-9_]*)/g;
    let match;

    while ((match = inputPattern.exec(str)) !== null) {
      const field = match[1];
      if (field && !inputFields.has(field)) {
        errors.push({
          code: 'INVALID_INPUT_REFERENCE',
          message: `Reference "$input.${field}" points to undefined input field`,
          path,
        });
      }
    }

    // Check $steps references
    const stepsPattern = /\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)/g;

    while ((match = stepsPattern.exec(str)) !== null) {
      const stepId = match[1];
      if (stepId && !precedingSteps.has(stepId)) {
        errors.push({
          code: 'INVALID_STEP_REFERENCE',
          message: `Reference "$steps.${stepId}" points to non-preceding step`,
          path,
        });
      }
    }

    // Check $env references (warnings only)
    const envPattern = /\$env\.([A-Z_][A-Z0-9_]*)/g;

    while ((match = envPattern.exec(str)) !== null) {
      const envVar = match[1];
      warnings.push({
        code: 'ENV_REFERENCE',
        message: `Environment variable reference "$env.${envVar}" found at ${path}`,
      });
    }
  }

  /**
   * Validate output references
   */
  private validateOutputReferences(
    workflow: TaskFlowDefinition,
    inputFields: Set<string>,
    allSteps: Set<string>,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    for (const [key, value] of Object.entries(workflow.output ?? {})) {
      this.validateString(
        value,
        `output.${key}`,
        inputFields,
        allSteps,
        errors,
        warnings
      );
    }
  }
}
