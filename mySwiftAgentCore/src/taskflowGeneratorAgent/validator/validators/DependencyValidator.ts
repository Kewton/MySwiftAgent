/**
 * DependencyValidator - Validates step dependencies in workflow
 *
 * Issue #364: Dependency and ordering validation
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * DependencyValidator - Validates step dependencies
 *
 * Checks:
 * - No duplicate step IDs
 * - Step references point to existing steps
 * - No circular dependencies
 * - Proper step ordering
 */
export class DependencyValidator implements Validator {
  readonly name = 'DependencyValidator';

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    const steps = workflow.steps ?? [];
    const stepIds = new Set<string>();
    const stepOrder: string[] = [];

    // Check for duplicate step IDs
    for (const step of steps) {
      if (stepIds.has(step.id)) {
        errors.push({
          code: 'DUPLICATE_STEP_ID',
          message: `Duplicate step ID: "${step.id}"`,
          path: `steps`,
        });
      }
      stepIds.add(step.id);
      stepOrder.push(step.id);
    }

    // Check variable references for forward dependencies
    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      if (!step) continue;

      const referencedSteps = this.extractStepReferences(step);

      for (const refId of referencedSteps) {
        // Check if referenced step exists
        if (!stepIds.has(refId)) {
          errors.push({
            code: 'INVALID_STEP_REFERENCE',
            message: `Step "${step.id}" references non-existent step "${refId}"`,
            path: `steps[${i}]`,
          });
          continue;
        }

        // Check if referenced step comes before current step
        const refIndex = stepOrder.indexOf(refId);
        if (refIndex >= i) {
          errors.push({
            code: 'FORWARD_REFERENCE',
            message: `Step "${step.id}" references step "${refId}" which is defined later`,
            path: `steps[${i}]`,
          });
        }
      }
    }

    // Check output references
    for (const [key, value] of Object.entries(workflow.output ?? {})) {
      const referencedSteps = this.extractStepReferencesFromString(value);
      for (const refId of referencedSteps) {
        if (!stepIds.has(refId)) {
          errors.push({
            code: 'INVALID_OUTPUT_REFERENCE',
            message: `Output "${key}" references non-existent step "${refId}"`,
            path: `output.${key}`,
          });
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
   * Extract step IDs referenced in a step's params and config
   */
  private extractStepReferences(step: TaskFlowStep): Set<string> {
    const references = new Set<string>();

    // Check params
    this.findReferencesInObject(step.params, references);

    // Check config
    this.findReferencesInObject(step.config, references);

    return references;
  }

  /**
   * Find $steps.xxx references in an object
   */
  private findReferencesInObject(obj: unknown, references: Set<string>): void {
    if (typeof obj === 'string') {
      const refs = this.extractStepReferencesFromString(obj);
      for (const ref of refs) {
        references.add(ref);
      }
    } else if (Array.isArray(obj)) {
      for (const item of obj) {
        this.findReferencesInObject(item, references);
      }
    } else if (obj && typeof obj === 'object') {
      for (const value of Object.values(obj)) {
        this.findReferencesInObject(value, references);
      }
    }
  }

  /**
   * Extract step IDs from $steps.xxx.yyy pattern
   */
  private extractStepReferencesFromString(str: string): string[] {
    const pattern = /\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)/g;
    const matches: string[] = [];
    let match;

    while ((match = pattern.exec(str)) !== null) {
      if (match[1]) {
        matches.push(match[1]);
      }
    }

    return matches;
  }
}
