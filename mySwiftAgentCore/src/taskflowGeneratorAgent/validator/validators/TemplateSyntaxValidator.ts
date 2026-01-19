/**
 * TemplateSyntaxValidator - Validates template syntax in workflows
 *
 * Issue #381: Template syntax validation for {{expression}} and $.steps.xxx patterns
 *
 * Features:
 * - Validates mustache {{}} syntax
 * - Validates JSON path $. syntax
 * - Validates mixed templates {{$.expression}}
 * - Special handling for transform nodes
 */

import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationResult } from '../../types/generator.js';
import type {
  EnhancedValidationContext,
  ComponentValidationError,
  ComponentValidator,
} from '../../types/validation.js';
import { RegexPatternCache } from '../utils/RegexPatternCache.js';
import { SuggestionHelper, type TemplateSyntaxErrorType } from '../utils/SuggestionHelper.js';

/**
 * TemplateSyntaxValidator - Validates template syntax
 */
export class TemplateSyntaxValidator implements ComponentValidator {
  readonly name = 'TemplateSyntaxValidator';

  /**
   * Validate workflow template syntax
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: EnhancedValidationContext
  ): Promise<ValidationResult> {
    // Check if template validation is enabled
    if (context.additionalContext?.enableTemplateValidation === false) {
      return { isValid: true, errors: [], warnings: [] };
    }

    const errors: ComponentValidationError[] = [];
    const regexCache = RegexPatternCache.getInstance();

    for (const step of workflow.steps) {
      const stepErrors = this.validateStep(step, regexCache);
      errors.push(...stepErrors);
    }

    return {
      isValid: errors.length === 0,
      errors: errors as any[],
      warnings: [],
    };
  }

  /**
   * Validate a single step
   */
  private validateStep(
    step: TaskFlowStep,
    regexCache: RegexPatternCache
  ): ComponentValidationError[] {
    const errors: ComponentValidationError[] = [];

    // Extract all string values from step config and params
    const strings = this.extractStrings(step);

    for (const { value, path } of strings) {
      const templateErrors = this.validateTemplate(value, step.id, path, regexCache);
      errors.push(...templateErrors);
    }

    return errors;
  }

  /**
   * Extract all string values from step with their paths
   */
  private extractStrings(
    step: TaskFlowStep
  ): Array<{ value: string; path: string }> {
    const results: Array<{ value: string; path: string }> = [];

    // Extract from config
    this.extractStringsFromObject(step.config, `steps.${step.id}.config`, results);

    // Extract from params
    this.extractStringsFromObject(step.params, `steps.${step.id}.params`, results);

    return results;
  }

  /**
   * Recursively extract strings from an object
   */
  private extractStringsFromObject(
    obj: unknown,
    basePath: string,
    results: Array<{ value: string; path: string }>
  ): void {
    if (typeof obj === 'string') {
      results.push({ value: obj, path: basePath });
    } else if (Array.isArray(obj)) {
      obj.forEach((item, index) => {
        this.extractStringsFromObject(item, `${basePath}[${index}]`, results);
      });
    } else if (obj && typeof obj === 'object') {
      for (const [key, value] of Object.entries(obj)) {
        this.extractStringsFromObject(value, `${basePath}.${key}`, results);
      }
    }
  }

  /**
   * Validate template syntax in a string value
   */
  private validateTemplate(
    value: string,
    stepId: string,
    path: string,
    regexCache: RegexPatternCache
  ): ComponentValidationError[] {
    const errors: ComponentValidationError[] = [];

    // Check for unclosed mustache
    if (this.hasUnclosedMustache(value, regexCache)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'UNCLOSED_MUSTACHE')
      );
    }

    // Check for unmatched closing braces
    if (this.hasUnmatchedClosing(value)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'UNMATCHED_CLOSING')
      );
    }

    // Check for empty mustache
    const emptyPattern = regexCache.getPattern('emptyMustache')!;
    if (emptyPattern.test(value)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'EMPTY_EXPRESSION')
      );
    }

    // Check for nested mustache
    const nestedPattern = regexCache.getPattern('nestedMustache')!;
    if (nestedPattern.test(value)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'NESTED_EXPRESSION')
      );
    }

    // Check for invalid JSON path
    const invalidPathPattern = regexCache.getPattern('invalidJsonPath')!;
    if (invalidPathPattern.test(value)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'INVALID_JSON_PATH')
      );
    }

    // Check for incomplete step reference
    if (this.hasIncompleteStepRef(value)) {
      errors.push(
        this.createSyntaxError(stepId, path, value, 'INCOMPLETE_REFERENCE')
      );
    }

    return errors;
  }

  /**
   * Check for unclosed mustache templates
   */
  private hasUnclosedMustache(value: string, regexCache: RegexPatternCache): boolean {
    // Count opening and closing braces
    const openCount = (value.match(/\{\{/g) || []).length;
    const closeCount = (value.match(/\}\}/g) || []).length;

    if (openCount !== closeCount) {
      return true;
    }

    // Also check for {{ without following }}
    const unclosedPattern = regexCache.getPattern('unclosedMustache');
    if (unclosedPattern) {
      return unclosedPattern.test(value);
    }

    return false;
  }

  /**
   * Check for unmatched closing braces
   */
  private hasUnmatchedClosing(value: string): boolean {
    // Simple approach: scan for }} that don't have corresponding {{
    let depth = 0;
    for (let i = 0; i < value.length - 1; i++) {
      if (value[i] === '{' && value[i + 1] === '{') {
        depth++;
        i++;
      } else if (value[i] === '}' && value[i + 1] === '}') {
        if (depth === 0) {
          return true; // Unmatched closing
        }
        depth--;
        i++;
      }
    }
    return false;
  }

  /**
   * Check for incomplete step reference
   */
  private hasIncompleteStepRef(value: string): boolean {
    // Skip if there's a valid step reference
    const validRefPattern = /\$steps\.[a-zA-Z_][a-zA-Z0-9_-]*\.[a-zA-Z_][a-zA-Z0-9_]*/;
    if (validRefPattern.test(value)) {
      return false;
    }

    // Check if $steps. exists but no valid reference
    if (/\$steps\./.test(value)) {
      return !validRefPattern.test(value);
    }

    return false;
  }

  /**
   * Create syntax error
   */
  private createSyntaxError(
    stepId: string,
    path: string,
    value: string,
    errorType: TemplateSyntaxErrorType
  ): ComponentValidationError {
    const suggestion = SuggestionHelper.createTemplateSyntaxSuggestion(value, errorType);

    return {
      code: 'TEMPLATE_SYNTAX_ERROR',
      message: `Template syntax error in step "${stepId}": ${suggestion.message}`,
      path,
      stepId,
      field: path.split('.').pop() || 'template',
      errorCode: 'TEMPLATE_SYNTAX_ERROR',
      suggestion,
      context: {
        sourceStep: stepId,
        referencePath: value,
      },
    };
  }
}
