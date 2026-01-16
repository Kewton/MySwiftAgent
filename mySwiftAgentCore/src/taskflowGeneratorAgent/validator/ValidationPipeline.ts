/**
 * ValidationPipeline - Multi-stage validation for generated workflows
 *
 * Issue #364: Validation pipeline with multiple validators
 */

import type {
  ValidationResult,
  ValidationError,
  ValidationWarning,
  Capability,
} from '../types/generator.js';
import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';

// Import real validators
import { SchemaValidator } from './validators/SchemaValidator.js';
import { DependencyValidator } from './validators/DependencyValidator.js';
import { VariableValidator } from './validators/VariableValidator.js';
import { CapabilityValidator } from './validators/CapabilityValidator.js';
import { SecurityValidator } from './validators/SecurityValidator.js';

/**
 * Validation Context - Additional info for validators
 */
export interface ValidationContext {
  capabilities: Capability[];
  projectId: string;
  additionalContext?: Record<string, unknown>;
}

/**
 * Validator Interface - All validators must implement this
 */
export interface Validator {
  readonly name: string;
  validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult>;
}

/**
 * ValidationPipeline - Runs multiple validators sequentially
 *
 * Features:
 * - Multiple validator stages
 * - Error and warning aggregation
 * - Validator management (add/remove)
 * - Fail-fast option (future)
 */
export class ValidationPipeline {
  private validators: Validator[];

  constructor(validators?: Validator[]) {
    this.validators = validators ?? this.createDefaultValidators();
  }

  /**
   * Validate workflow through all validators
   *
   * @param workflow - Workflow to validate
   * @param context - Validation context
   * @returns Aggregated validation result
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const allErrors: ValidationError[] = [];
    const allWarnings: ValidationWarning[] = [];

    for (const validator of this.validators) {
      const result = await validator.validate(workflow, context);

      if (result.errors) {
        allErrors.push(...result.errors);
      }

      if (result.warnings) {
        allWarnings.push(...result.warnings);
      }
    }

    return {
      isValid: allErrors.length === 0,
      errors: allErrors,
      warnings: allWarnings,
    };
  }

  /**
   * Add validator to pipeline
   */
  addValidator(validator: Validator): void {
    this.validators.push(validator);
  }

  /**
   * Remove validator by name
   */
  removeValidator(name: string): void {
    this.validators = this.validators.filter((v) => v.name !== name);
  }

  /**
   * Get all validators
   */
  getValidators(): Validator[] {
    return [...this.validators];
  }

  /**
   * Create default validators
   */
  private createDefaultValidators(): Validator[] {
    // Use real validators (Issue #364 integration fix)
    return [
      new SchemaValidator(),
      new DependencyValidator(),
      new VariableValidator(),
      new CapabilityValidator(),
      new SecurityValidator(),
    ];
  }
}

/**
 * Factory function
 */
export function createValidationPipeline(validators?: Validator[]): ValidationPipeline {
  return new ValidationPipeline(validators);
}
