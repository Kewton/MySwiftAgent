/**
 * Error Types - Custom error classes for taskflowGeneratorAgent
 *
 * Issue #374: WorkflowCapabilityError for feedback loop support
 */

import type { ValidationResult } from './generator.js';

/**
 * WorkflowCapabilityError - Specialized error for capability validation failures
 *
 * This error type supports the feedback loop mechanism:
 * 1. Contains detailed validation results
 * 2. Stores the raw LLM output for feedback
 * 3. Tracks attempt number for retry management
 * 4. Provides formatted feedback summary for LLM
 *
 * Note: This is different from LLMValidationError in LLMClient.ts which is
 * for Zod schema validation. This error is for capability-aware validation.
 */
export class WorkflowCapabilityError extends Error {
  readonly name = 'WorkflowCapabilityError';

  constructor(
    message: string,
    public readonly validationResult: ValidationResult,
    public readonly rawContent: string,
    public readonly attempt: number
  ) {
    super(message);
  }

  /**
   * Generate feedback summary for LLM prompt
   *
   * Creates a structured summary of validation errors
   * that can be included in the feedback prompt
   */
  toFeedbackSummary(): string {
    const errors = this.validationResult.errors ?? [];
    const lines: string[] = [
      `## Previous generation had the following issues (attempt ${this.attempt}):`,
      '',
    ];

    for (const error of errors) {
      lines.push(`### Error: ${error.code}`);
      lines.push(`- Path: ${error.path ?? 'N/A'}`);
      lines.push(`- Issue: ${error.message}`);
      lines.push('');
    }

    lines.push('## Please fix the above errors and regenerate the workflow.');

    return lines.join('\n');
  }
}

// Re-export for backward compatibility - alias to the new name
export { WorkflowCapabilityError as LLMValidationError };

/**
 * CapabilityValidationError - Detailed error for capability validation
 *
 * Extends ValidationError with capability-specific context
 */
export interface CapabilityValidationError {
  code: string;
  message: string;
  step: string;
  capability?: string;
  parameter?: string;
  expected?: string;
  actual?: string;
  suggestion?: string;
}

/**
 * CapabilityValidationWarning - Warning for non-critical issues
 */
export interface CapabilityValidationWarning {
  code: string;
  message: string;
  step: string;
  parameter?: string;
}

/**
 * CapabilityValidationResult - Result from WorkflowCapabilityValidator
 */
export interface CapabilityValidationResult {
  valid: boolean;
  errors: CapabilityValidationError[];
  warnings: CapabilityValidationWarning[];
}
