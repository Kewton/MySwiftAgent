/**
 * WorkflowCapabilityValidator - Capability-aware workflow validation
 *
 * Issue #374: Validates workflow steps against capability definitions
 * - Required parameter checking
 * - Type validation
 * - Constraint validation (min, max, enum)
 * - Defensive validation (warns when capability parameters are undefined)
 */

import type { Validator, ValidationContext } from './ValidationPipeline.js';
import type {
  ValidationResult,
  ValidationError,
  ValidationWarning,
  CapabilityForPrompt,
  CapabilityParameter,
} from '../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../taskflowEngine/types/TaskFlowDefinition.js';
// Issue #374: Import WorkflowCapabilityError for feedback loop support
import { WorkflowCapabilityError } from '../types/errors.js';

/**
 * WorkflowCapabilityValidator - Validates workflow against capability definitions
 *
 * Validation checks:
 * 1. Required parameters are provided
 * 2. Parameter types match specification
 * 3. Parameter values are within constraints
 * 4. Unknown parameters generate warnings
 *
 * Issue #374: Supports throwing WorkflowCapabilityError for feedback loop
 */
export class WorkflowCapabilityValidator implements Validator {
  readonly name = 'WorkflowCapabilityValidator';

  /**
   * Standard validate method - returns ValidationResult
   *
   * Used by ValidationPipeline for aggregated validation
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    return this.validateWorkflow(workflow, context);
  }

  /**
   * Validate and throw on failure - for feedback loop support
   *
   * Issue #374: Throws WorkflowCapabilityError with detailed information
   * for the feedback prompt to correct validation issues
   *
   * @param workflow - Workflow to validate
   * @param context - Validation context
   * @param rawContent - Raw LLM output for feedback
   * @param attempt - Current attempt number
   * @throws WorkflowCapabilityError if validation fails
   */
  async validateOrThrow(
    workflow: TaskFlowDefinition,
    context: ValidationContext,
    rawContent: string,
    attempt: number
  ): Promise<ValidationResult> {
    const result = await this.validateWorkflow(workflow, context);

    if (!result.isValid) {
      const errorMessages = result.errors
        ?.map((e) => e.message)
        .join('; ');
      throw new WorkflowCapabilityError(
        `Capability validation failed: ${errorMessages}`,
        result,
        rawContent,
        attempt
      );
    }

    return result;
  }

  /**
   * Internal validation logic
   */
  private async validateWorkflow(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Build capability lookup from context
    const capabilityMap = new Map<string, CapabilityForPrompt>(
      (context.capabilities as CapabilityForPrompt[]).map((c) => [c.id, c])
    );

    // Validate each step
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (!step) continue;

      // Only validate api_rest steps with capability_id
      if (step.type === 'api_rest') {
        const capabilityId = step.config['capability_id'] as string | undefined;
        if (capabilityId) {
          const capability = capabilityMap.get(capabilityId);
          if (capability) {
            this.validateStep(step, i, capability, errors, warnings);
          }
          // Note: missing capability is handled by CapabilityValidator
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Validate a single step against capability definition
   *
   * Issue #374: Added defensive validation to warn when capability parameters
   * are undefined, which indicates incomplete capability data.
   */
  private validateStep(
    step: TaskFlowStep,
    stepIndex: number,
    capability: CapabilityForPrompt,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const params = capability.parameters ?? [];
    const stepParams = this.extractStepParams(step);

    // Issue #374: Defensive validation - warn when capability parameters are undefined
    // This catches cases where capability enrichment failed or capabilities were not
    // loaded from YAML files properly
    if (
      (!capability.parameters || capability.parameters.length === 0) &&
      Object.keys(stepParams).length > 0
    ) {
      warnings.push({
        code: 'CAPABILITY_PARAMS_UNDEFINED',
        message: `Step "${step.id}": Capability "${capability.id}" has no parameter definitions. ` +
          `Step provides ${Object.keys(stepParams).length} parameter(s) that cannot be validated. ` +
          `Ensure capability YAML file defines parameters.`,
      });
      // Skip further validation since we have no parameter definitions
      return;
    }

    // 1. Check required parameters
    this.validateRequiredParams(step, stepIndex, params, stepParams, errors);

    // 2. Check parameter types
    this.validateParamTypes(step, stepIndex, params, stepParams, errors);

    // 3. Check parameter constraints
    this.validateParamConstraints(step, stepIndex, params, stepParams, errors);

    // 4. Warn about unknown parameters
    this.warnUnknownParams(step, stepIndex, params, stepParams, warnings);
  }

  /**
   * Extract parameters from step
   * Handles both params.body and direct params
   */
  private extractStepParams(step: TaskFlowStep): Record<string, unknown> {
    const params = step.params ?? {};

    // If params.body exists, use it (common pattern for api_rest)
    if (params.body && typeof params.body === 'object') {
      return params.body as Record<string, unknown>;
    }

    return params;
  }

  /**
   * Validate that all required parameters are provided
   */
  private validateRequiredParams(
    step: TaskFlowStep,
    stepIndex: number,
    params: CapabilityParameter[],
    stepParams: Record<string, unknown>,
    errors: ValidationError[]
  ): void {
    for (const param of params) {
      if (param.required && !(param.name in stepParams)) {
        errors.push({
          code: 'MISSING_REQUIRED_PARAM',
          message: `Step "${step.id}": Required parameter '${param.name}' is missing for capability`,
          path: `steps[${stepIndex}].params.body.${param.name}`,
        });
      }
    }
  }

  /**
   * Validate parameter types match specification
   */
  private validateParamTypes(
    step: TaskFlowStep,
    stepIndex: number,
    params: CapabilityParameter[],
    stepParams: Record<string, unknown>,
    errors: ValidationError[]
  ): void {
    for (const param of params) {
      if (!(param.name in stepParams)) continue;

      const value = stepParams[param.name];

      // Skip dynamic references (e.g., $input.field, $steps.step.field)
      if (typeof value === 'string' && value.startsWith('$')) {
        continue;
      }

      const actualType = this.getValueType(value);
      if (actualType !== param.type) {
        errors.push({
          code: 'PARAM_TYPE_MISMATCH',
          message: `Step "${step.id}": Parameter '${param.name}' should be ${param.type}, got ${actualType}`,
          path: `steps[${stepIndex}].params.body.${param.name}`,
        });
      }
    }
  }

  /**
   * Get the type of a value as a string
   */
  private getValueType(value: unknown): string {
    if (value === null) return 'null';
    if (Array.isArray(value)) return 'array';
    return typeof value;
  }

  /**
   * Validate parameter values against constraints
   */
  private validateParamConstraints(
    step: TaskFlowStep,
    stepIndex: number,
    params: CapabilityParameter[],
    stepParams: Record<string, unknown>,
    errors: ValidationError[]
  ): void {
    for (const param of params) {
      if (!(param.name in stepParams)) continue;
      if (!param.validation) continue;

      const value = stepParams[param.name];

      // Skip dynamic references
      if (typeof value === 'string' && value.startsWith('$')) {
        continue;
      }

      // Check min constraint
      if (param.validation.min !== undefined && typeof value === 'number') {
        if (value < param.validation.min) {
          errors.push({
            code: 'PARAM_BELOW_MIN',
            message: `Step "${step.id}": Parameter '${param.name}' value ${value} is below minimum ${param.validation.min}`,
            path: `steps[${stepIndex}].params.body.${param.name}`,
          });
        }
      }

      // Check max constraint
      if (param.validation.max !== undefined && typeof value === 'number') {
        if (value > param.validation.max) {
          errors.push({
            code: 'PARAM_ABOVE_MAX',
            message: `Step "${step.id}": Parameter '${param.name}' value ${value} is above maximum ${param.validation.max}`,
            path: `steps[${stepIndex}].params.body.${param.name}`,
          });
        }
      }

      // Check enum constraint
      if (param.validation.enum !== undefined) {
        if (!param.validation.enum.includes(value)) {
          errors.push({
            code: 'PARAM_NOT_IN_ENUM',
            message: `Step "${step.id}": Parameter '${param.name}' value '${value}' is not in allowed values [${param.validation.enum.join(', ')}]`,
            path: `steps[${stepIndex}].params.body.${param.name}`,
          });
        }
      }
    }
  }

  /**
   * Warn about unknown parameters
   */
  private warnUnknownParams(
    step: TaskFlowStep,
    stepIndex: number,
    params: CapabilityParameter[],
    stepParams: Record<string, unknown>,
    warnings: ValidationWarning[]
  ): void {
    const knownParamNames = new Set(params.map(p => p.name));

    for (const paramName of Object.keys(stepParams)) {
      if (!knownParamNames.has(paramName)) {
        warnings.push({
          code: 'UNKNOWN_PARAM',
          message: `Step "${step.id}": Unknown parameter '${paramName}' in steps[${stepIndex}]`,
        });
      }
    }
  }
}

/**
 * Factory function
 */
export function createWorkflowCapabilityValidator(): WorkflowCapabilityValidator {
  return new WorkflowCapabilityValidator();
}
