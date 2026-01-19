/**
 * ComponentIntegrityValidator - Composite validator for component integrity
 *
 * Issue #381: Composite pattern implementation for component integrity validation
 *
 * Features:
 * - Aggregates multiple sub-validators
 * - Shared cache initialization for performance
 * - ValidationObserver integration for debug mode
 * - Performance metrics collection
 */

import type { TaskFlowDefinition } from '../../taskflowEngine/types/TaskFlowDefinition.js';
import type {
  ValidationWarning,
  Capability,
  ResponseSchema,
} from '../types/generator.js';
import type {
  EnhancedValidationContext,
  ComponentValidationError,
  SharedValidationCache,
  ComponentValidationResult,
  ComponentValidator,
  ValidationObserver,
} from '../types/validation.js';
import type { Validator } from './ValidationPipeline.js';
import { StepReferenceValidator } from './validators/StepReferenceValidator.js';
import { TemplateSyntaxValidator } from './validators/TemplateSyntaxValidator.js';
import { CircularReferenceValidator } from './validators/CircularReferenceValidator.js';

/**
 * ComponentIntegrityValidator - Composite validator
 */
export class ComponentIntegrityValidator implements Validator {
  readonly name = 'ComponentIntegrityValidator';
  private readonly validators: ComponentValidator[];
  private observer?: ValidationObserver;

  constructor() {
    this.validators = [
      new StepReferenceValidator(),
      new TemplateSyntaxValidator(),
      new CircularReferenceValidator(),
    ];
  }

  /**
   * Validate workflow using all sub-validators
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: EnhancedValidationContext
  ): Promise<ComponentValidationResult> {
    const allErrors: ComponentValidationError[] = [];
    const allWarnings: ValidationWarning[] = [];
    const startTime = Date.now();
    const validatorMetrics = new Map<string, { durationMs: number; errorsFound: number }>();

    // Initialize shared cache
    const sharedCache = this.initializeSharedCache(workflow, context);
    const enhancedContext: EnhancedValidationContext = {
      ...context,
      sharedCache,
    };

    // Get observer from context
    this.observer = context.additionalContext?.validationObserver;

    // Run each sub-validator
    for (const validator of this.validators) {
      const validatorStartTime = Date.now();
      this.observer?.onValidatorStart(validator.name);

      try {
        const result = await validator.validate(workflow, enhancedContext);

        if (result.errors) {
          allErrors.push(...(result.errors as ComponentValidationError[]));
        }
        if (result.warnings) {
          allWarnings.push(...result.warnings);
        }

        const durationMs = Date.now() - validatorStartTime;
        validatorMetrics.set(validator.name, {
          durationMs,
          errorsFound: result.errors?.length ?? 0,
        });

        this.observer?.onValidatorComplete(validator.name, result, durationMs);
      } catch (error) {
        this.observer?.onError(validator.name, error as Error);
        throw error;
      }
    }

    // Build result
    const result: ComponentValidationResult = {
      isValid: allErrors.length === 0,
      errors: allErrors as any[],
      warnings: allWarnings,
    };

    // Add performance metrics if requested
    if (context.additionalContext?.collectPerformanceMetrics) {
      result.performanceMetrics = {
        totalDurationMs: Date.now() - startTime,
        validatorMetrics,
        stepsAnalyzed: workflow.steps.length,
        referencesChecked: this.countReferences(workflow),
      };
    }

    return result;
  }

  /**
   * Initialize shared cache for sub-validators
   */
  private initializeSharedCache(
    workflow: TaskFlowDefinition,
    context: EnhancedValidationContext
  ): SharedValidationCache {
    const capabilityMap = new Map<string, Capability>();
    const responseSchemaMap = new Map<string, ResponseSchema>();

    for (const capability of context.capabilities) {
      capabilityMap.set(capability.id, capability);
      if ((capability as any).responseSchema) {
        responseSchemaMap.set(capability.id, (capability as any).responseSchema);
      }
    }

    return {
      capabilityMap,
      stepMap: new Map(workflow.steps.map((s) => [s.id, s])),
      responseSchemaMap,
    };
  }

  /**
   * Count total references in workflow (for metrics)
   */
  private countReferences(workflow: TaskFlowDefinition): number {
    let count = 0;
    const pattern = /\$steps\.[a-zA-Z_][a-zA-Z0-9_-]*\.[a-zA-Z_][a-zA-Z0-9_]*/g;

    for (const step of workflow.steps) {
      const stepStr = JSON.stringify(step);
      const matches = stepStr.match(pattern);
      if (matches) {
        count += matches.length;
      }
    }

    return count;
  }

  /**
   * Get list of sub-validators
   */
  getValidators(): ComponentValidator[] {
    return [...this.validators];
  }
}

/**
 * Factory function
 */
export function createComponentIntegrityValidator(): ComponentIntegrityValidator {
  return new ComponentIntegrityValidator();
}
