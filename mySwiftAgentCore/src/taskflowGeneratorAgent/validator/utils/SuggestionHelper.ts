/**
 * SuggestionHelper - Error message improvement utilities
 *
 * Issue #381: Levenshtein distance calculation and suggestion generation
 *
 * Features:
 * - Levenshtein distance for fuzzy matching
 * - Closest match finder for typo suggestions
 * - Detailed error suggestions with examples
 */

import type { ErrorSuggestion } from '../../types/validation.js';

/**
 * Template syntax error types
 */
export type TemplateSyntaxErrorType =
  | 'UNCLOSED_MUSTACHE'
  | 'UNMATCHED_CLOSING'
  | 'EMPTY_EXPRESSION'
  | 'NESTED_EXPRESSION'
  | 'INVALID_JSON_PATH'
  | 'INCOMPLETE_REFERENCE';

/**
 * SuggestionHelper - Utility class for generating error suggestions
 */
export class SuggestionHelper {
  /**
   * Calculate Levenshtein distance between two strings
   *
   * @param a - First string
   * @param b - Second string
   * @returns Edit distance between the strings
   */
  static levenshteinDistance(a: string, b: string): number {
    const matrix: number[][] = [];

    // Initialize first column
    for (let i = 0; i <= b.length; i++) {
      matrix[i] = [i];
    }

    // Initialize first row
    const firstRow = matrix[0];
    if (firstRow) {
      for (let j = 0; j <= a.length; j++) {
        firstRow[j] = j;
      }
    }

    // Fill in the rest of the matrix
    for (let i = 1; i <= b.length; i++) {
      for (let j = 1; j <= a.length; j++) {
        const prevRow = matrix[i - 1];
        const currRow = matrix[i];
        if (!prevRow || !currRow) continue;

        if (b.charAt(i - 1) === a.charAt(j - 1)) {
          currRow[j] = prevRow[j - 1] ?? 0;
        } else {
          currRow[j] = Math.min(
            (prevRow[j - 1] ?? 0) + 1, // substitution
            (currRow[j - 1] ?? 0) + 1, // insertion
            (prevRow[j] ?? 0) + 1 // deletion
          );
        }
      }
    }

    return matrix[b.length]?.[a.length] ?? 0;
  }

  /**
   * Find the closest match from a list of candidates
   *
   * @param input - Input string to match
   * @param candidates - List of candidate strings
   * @param maxDistance - Maximum Levenshtein distance to consider (default: 3)
   * @returns Closest matching candidate or undefined
   */
  static findClosestMatch(
    input: string,
    candidates: string[],
    maxDistance: number = 3
  ): string | undefined {
    if (candidates.length === 0) {
      return undefined;
    }

    let closest: string | undefined;
    let minDistance = Infinity;

    const inputLower = input.toLowerCase();

    for (const candidate of candidates) {
      const distance = this.levenshteinDistance(inputLower, candidate.toLowerCase());
      if (distance < minDistance && distance <= maxDistance) {
        minDistance = distance;
        closest = candidate;
      }
    }

    return closest;
  }

  /**
   * Create suggestion for field not found error
   *
   * @param fieldName - The field name that was not found
   * @param availableFields - List of available field names
   * @param capabilityName - Name of the capability
   * @returns ErrorSuggestion with helpful information
   */
  static createFieldNotFoundSuggestion(
    fieldName: string,
    availableFields: string[],
    capabilityName: string
  ): ErrorSuggestion {
    const closestMatch = this.findClosestMatch(fieldName, availableFields);

    return {
      message: closestMatch
        ? `Did you mean "${closestMatch}"?`
        : `Field "${fieldName}" is not available in capability "${capabilityName}"`,
      availableOptions: availableFields,
      closestMatch: closestMatch,
      example:
        availableFields.length > 0
          ? `$steps.step_id.${availableFields[0]}`
          : undefined,
    };
  }

  /**
   * Create suggestion for step not found error
   *
   * @param stepId - The step ID that was not found
   * @param availableSteps - List of available step IDs
   * @returns ErrorSuggestion with helpful information
   */
  static createStepNotFoundSuggestion(
    stepId: string,
    availableSteps: string[]
  ): ErrorSuggestion {
    const closestMatch = this.findClosestMatch(stepId, availableSteps);

    return {
      message: closestMatch
        ? `Did you mean "${closestMatch}"?`
        : `Step "${stepId}" does not exist in the workflow`,
      availableOptions: availableSteps,
      closestMatch: closestMatch,
      example:
        availableSteps.length > 0 ? `$steps.${availableSteps[0]}.output` : undefined,
    };
  }

  /**
   * Create suggestion for template syntax errors
   *
   * @param template - The template string with error
   * @param errorType - Type of syntax error
   * @returns ErrorSuggestion with helpful information
   */
  static createTemplateSyntaxSuggestion(
    template: string,
    errorType: TemplateSyntaxErrorType
  ): ErrorSuggestion {
    const suggestions: Record<TemplateSyntaxErrorType, ErrorSuggestion> = {
      UNCLOSED_MUSTACHE: {
        message: 'Template has unclosed mustache expression. Add closing "}}".',
        example: '{{$.steps.step_id.field}}',
      },
      UNMATCHED_CLOSING: {
        message:
          'Template has unmatched closing braces "}}". Ensure each "}}" has a matching "{{".',
        example: '{{expression}}',
      },
      EMPTY_EXPRESSION: {
        message: 'Template has empty mustache expression "{{}}". Add an expression.',
        example: '{{$.steps.step_id.result}}',
      },
      NESTED_EXPRESSION: {
        message:
          'Template has nested mustache expressions "{{{{". Use single level nesting.',
        example: '{{$.steps.step_id.result}}',
      },
      INVALID_JSON_PATH: {
        message:
          'Invalid JSON path prefix. Use $.steps, $.input, or $.env for path expressions.',
        example: '$.steps.step_id.result or $.input.field or $.env.VAR_NAME',
        availableOptions: ['$.steps', '$.input', '$.env'],
      },
      INCOMPLETE_REFERENCE: {
        message:
          'Step reference is incomplete. Include both step ID and field name.',
        example: '$steps.step_id.field_name',
      },
    };

    return (
      suggestions[errorType] || {
        message: `Template syntax error in: ${template}`,
        example: '{{$.steps.step_id.result}}',
      }
    );
  }

  /**
   * Create suggestion for circular reference error
   *
   * @param circularPath - The path of the circular reference
   * @returns ErrorSuggestion with helpful information
   */
  static createCircularReferenceSuggestion(circularPath: string[]): ErrorSuggestion {
    const pathStr = circularPath.join(' -> ');
    const cycleLength = circularPath.length - 1;

    return {
      message: `Break the circular dependency by removing one of the references in the chain: ${pathStr}`,
      availableOptions: circularPath.slice(0, -1), // Exclude the repeated step
      example:
        cycleLength >= 2
          ? `Consider using a transform step to break the dependency between "${circularPath[0]}" and "${circularPath[1]}"`
          : `Remove the self-reference in step "${circularPath[0]}"`,
    };
  }
}
