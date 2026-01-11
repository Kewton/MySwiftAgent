/**
 * Zod Schema Validator for Workflow Definitions
 *
 * Performs Level 1 validation using Zod schemas.
 * Converts Zod errors to our unified ValidationResult format.
 *
 * @module engine/validator/zod-schema-validator
 * @see Issue #348
 */

import { z } from 'zod';
import {
  WorkflowDefinitionSchema,
  zodErrorToValidationErrors,
} from '../schemas/workflow-schema.js';
import type {
  ValidationResult,
  ValidationIssue,
  ValidatorLayer,
} from './types.js';

// ============================================================
// Zod Schema Validator
// ============================================================

/**
 * Validates workflow definitions using Zod schemas.
 *
 * Provides Level 1 (schema) validation:
 * - Required fields present
 * - Field types correct
 * - Enum values valid
 * - HTTPS URL requirements
 */
export class ZodSchemaValidator implements ValidatorLayer {
  /**
   * Validate a workflow definition against Zod schema
   * @param definition - Workflow definition object
   * @returns Validation result with converted issues
   */
  validate(definition: unknown): ValidationResult {
    const result = WorkflowDefinitionSchema.safeParse(definition);

    if (result.success) {
      return {
        valid: true,
        issues: [],
        summary: { errors: 0, warnings: 0, infos: 0 },
      };
    }

    // Convert Zod errors to ValidationIssues
    const issues = this.convertZodErrors(result.error);

    return {
      valid: false,
      issues,
      summary: {
        errors: issues.filter((i) => i.severity === 'error').length,
        warnings: issues.filter((i) => i.severity === 'warning').length,
        infos: issues.filter((i) => i.severity === 'info').length,
      },
    };
  }

  /**
   * Convert Zod error to our ValidationIssue format
   */
  private convertZodErrors(zodError: z.ZodError): ValidationIssue[] {
    return zodError.errors.map((err) => {
      const path = err.path.join('.');

      return {
        severity: 'error' as const,
        code: `SCHEMA_${err.code.toUpperCase()}`,
        message: err.message,
        path: path || 'root',
        suggestion: this.getSuggestionForError(err),
        agentFeedback: this.getAgentFeedback(err),
      };
    });
  }

  /**
   * Generate human-readable suggestion for Zod error
   */
  private getSuggestionForError(err: z.ZodIssue): string {
    switch (err.code) {
      case 'invalid_type':
        return `Expected ${err.expected}, got ${err.received}`;
      case 'invalid_enum_value':
        return `Valid values: ${(err as z.ZodInvalidEnumValueIssue).options.join(', ')}`;
      case 'too_small':
        return `Value is too small (minimum: ${(err as z.ZodTooSmallIssue).minimum})`;
      case 'too_big':
        return `Value is too big (maximum: ${(err as z.ZodTooBigIssue).maximum})`;
      case 'custom':
        return err.message;
      default:
        return 'Check the field value and format';
    }
  }

  /**
   * Generate agent feedback for Zod error
   */
  private getAgentFeedback(
    err: z.ZodIssue
  ): ValidationIssue['agentFeedback'] {
    const path = err.path.join('.');

    switch (err.code) {
      case 'invalid_type':
        return {
          targetPath: path || 'root',
          category: 'type',
          currentValue: (err as z.ZodInvalidTypeIssue).received,
          expectedFormat: String((err as z.ZodInvalidTypeIssue).expected),
        };

      case 'invalid_enum_value':
        const enumIssue = err as z.ZodInvalidEnumValueIssue;
        return {
          targetPath: path || 'root',
          category: 'schema',
          currentValue: enumIssue.received,
          allowedValues: enumIssue.options.map(String),
          fixExample: `"${enumIssue.options[0]}"`,
        };

      case 'custom':
        return {
          targetPath: path || 'root',
          category: 'constraint',
          expectedFormat: err.message,
        };

      default:
        return {
          targetPath: path || 'root',
          category: 'schema',
          expectedFormat: err.message,
        };
    }
  }
}

// ============================================================
// Exported Instance
// ============================================================

/**
 * Default Zod schema validator instance
 */
export const zodSchemaValidator = new ZodSchemaValidator();
