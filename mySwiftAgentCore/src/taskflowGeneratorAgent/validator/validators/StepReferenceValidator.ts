/**
 * StepReferenceValidator - Validates step references in workflows
 *
 * Issue #381: Step reference validation with improved error messages
 *
 * Features:
 * - Validates $steps.xxx.yyy reference existence
 * - Validates field existence in capability response schema
 * - Provides suggestions using Levenshtein distance
 * - Uses shared cache for performance
 */

import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationResult, ValidationWarning, Capability, ResponseSchema } from '../../types/generator.js';
import type {
  EnhancedValidationContext,
  ComponentValidationError,
  StepReference,
  ComponentValidator,
} from '../../types/validation.js';
import { RegexPatternCache } from '../utils/RegexPatternCache.js';
import { SuggestionHelper } from '../utils/SuggestionHelper.js';

/**
 * StepReferenceValidator - Validates step references
 */
export class StepReferenceValidator implements ComponentValidator {
  readonly name = 'StepReferenceValidator';

  /**
   * Validate workflow step references
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: EnhancedValidationContext
  ): Promise<ValidationResult> {
    const errors: ComponentValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Use shared cache or build local maps
    const stepMap =
      context.sharedCache?.stepMap ?? this.buildStepMap(workflow.steps);
    const capabilityMap =
      context.sharedCache?.capabilityMap ?? this.buildCapabilityMap(context.capabilities);
    const regexCache = RegexPatternCache.getInstance();

    // Get available step IDs for suggestions
    const availableStepIds = Array.from(stepMap.keys());

    // Validate each step
    for (const step of workflow.steps) {
      const references = this.extractStepReferences(step, regexCache);

      for (const ref of references) {
        // Check step existence
        if (!stepMap.has(ref.stepId)) {
          errors.push(
            this.createStepNotFoundError(step.id, ref, availableStepIds)
          );
          continue;
        }

        // Check field existence
        const targetStep = stepMap.get(ref.stepId)!;
        const capabilityId = targetStep.config['capability_id'] as string | undefined;

        if (!capabilityId) {
          // Transform nodes don't have capability_id, skip field validation
          continue;
        }

        const capability = capabilityMap.get(capabilityId);

        if (!capability) {
          // Capability not found - this should be caught by CapabilityValidator
          continue;
        }

        // Get response schema from capability
        const responseSchema = this.getResponseSchema(capability);

        if (!responseSchema) {
          // No response schema - warn but don't fail
          warnings.push(this.createNoSchemaWarning(step.id, ref, capabilityId));
          continue;
        }

        const availableFields = this.getSchemaFieldNames(responseSchema);
        if (availableFields.length > 0 && !availableFields.includes(ref.fieldName)) {
          errors.push(
            this.createFieldNotFoundError(step.id, ref, capability.name, availableFields)
          );
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors: errors as any[],
      warnings,
    };
  }

  /**
   * Build step map from workflow steps
   */
  private buildStepMap(steps: TaskFlowStep[]): Map<string, TaskFlowStep> {
    return new Map(steps.map((s) => [s.id, s]));
  }

  /**
   * Build capability map from context
   */
  private buildCapabilityMap(capabilities: Capability[]): Map<string, Capability> {
    return new Map(capabilities.map((c) => [c.id, c]));
  }

  /**
   * Extract step references from a step using regex
   */
  private extractStepReferences(
    step: TaskFlowStep,
    regexCache: RegexPatternCache
  ): StepReference[] {
    const references: StepReference[] = [];
    const pattern = regexCache.getPattern('stepReference')!;
    const stepStr = JSON.stringify(step);

    let match;
    while ((match = pattern.exec(stepStr)) !== null) {
      references.push({
        stepId: match[1] ?? '',
        fieldName: match[2] ?? '',
        fullPath: match[0] ?? '',
      });
    }

    return references;
  }

  /**
   * Get response schema from capability (handles both Capability and CapabilityForPrompt)
   */
  private getResponseSchema(capability: any): ResponseSchema | undefined {
    return capability.responseSchema;
  }

  /**
   * Get field names from response schema
   */
  private getSchemaFieldNames(schema: ResponseSchema): string[] {
    if (schema.properties) {
      return Object.keys(schema.properties);
    }
    return [];
  }

  /**
   * Create error for step not found
   */
  private createStepNotFoundError(
    currentStepId: string,
    ref: StepReference,
    availableStepIds: string[]
  ): ComponentValidationError {
    const suggestion = SuggestionHelper.createStepNotFoundSuggestion(
      ref.stepId,
      availableStepIds
    );

    return {
      code: 'STEP_REFERENCE_NOT_FOUND',
      message: `Step "${ref.stepId}" referenced in step "${currentStepId}" does not exist`,
      path: `steps.${currentStepId}`,
      stepId: currentStepId,
      field: 'params',
      errorCode: 'STEP_REFERENCE_NOT_FOUND',
      suggestion,
      context: {
        sourceStep: currentStepId,
        targetStep: ref.stepId,
        referencePath: ref.fullPath,
      },
    };
  }

  /**
   * Create error for field not found
   */
  private createFieldNotFoundError(
    currentStepId: string,
    ref: StepReference,
    capabilityName: string,
    availableFields: string[]
  ): ComponentValidationError {
    const suggestion = SuggestionHelper.createFieldNotFoundSuggestion(
      ref.fieldName,
      availableFields,
      capabilityName
    );

    return {
      code: 'OUTPUT_FIELD_NOT_FOUND',
      message: `Field "${ref.fieldName}" does not exist in capability "${capabilityName}" output`,
      path: `steps.${currentStepId}.params`,
      stepId: currentStepId,
      field: ref.fieldName,
      errorCode: 'OUTPUT_FIELD_NOT_FOUND',
      suggestion,
      context: {
        sourceStep: currentStepId,
        targetStep: ref.stepId,
        referencePath: ref.fullPath,
        expectedType: 'defined field',
        actualType: 'undefined',
      },
    };
  }

  /**
   * Create warning for missing schema
   */
  private createNoSchemaWarning(
    _currentStepId: string,
    ref: StepReference,
    capabilityId: string
  ): ValidationWarning {
    return {
      code: 'NO_RESPONSE_SCHEMA',
      message: `Capability "${capabilityId}" has no response schema defined. Field "${ref.fieldName}" cannot be validated.`,
    };
  }
}
