/**
 * ValidationPipeline - Multi-stage validation for generated workflows
 *
 * Issue #364: Validation pipeline with multiple validators
 * Issue #375: Added OutputMappingValidator and NodeConfigValidator
 * Issue #380: Added ResponseSchemaValidator for capability response schema validation
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
// Issue #375: OutputMappingValidator and NodeConfigValidator
import { OutputMappingValidator } from './validators/OutputMappingValidator.js';
import { NodeConfigValidator } from './validators/NodeConfigValidator.js';
// Issue #374: WorkflowCapabilityValidator for enhanced capability validation
import { WorkflowCapabilityValidator } from './WorkflowCapabilityValidator.js';
// Issue #380: ResponseSchemaValidator for capability response schema validation
import { ResponseSchemaValidator } from './validators/ResponseSchemaValidator.js';

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
   *
   * Issue #374: Added WorkflowCapabilityValidator for enhanced capability validation
   * Issue #375: Added OutputMappingValidator and NodeConfigValidator
   * Issue #380: Added ResponseSchemaValidator for capability response schema validation
   */
  private createDefaultValidators(): Validator[] {
    // Use real validators (Issue #364 integration fix)
    // Issue #374: Added WorkflowCapabilityValidator for enhanced parameter validation
    // Issue #375: Added OutputMappingValidator and NodeConfigValidator
    // Issue #380: Added ResponseSchemaValidator for capability response schema validation
    return [
      new SchemaValidator(),
      new DependencyValidator(),
      new VariableValidator(),
      new CapabilityValidator(),
      new SecurityValidator(),
      new OutputMappingValidator(), // Issue #375: Output mapping validation
      new NodeConfigValidator(), // Issue #375: Node config validation
      new WorkflowCapabilityValidator(), // Issue #374: Enhanced capability validation
      new ResponseSchemaValidator(), // Issue #380: Response schema validation
    ];
  }
}

/**
 * Factory function
 */
export function createValidationPipeline(validators?: Validator[]): ValidationPipeline {
  return new ValidationPipeline(validators);
}
