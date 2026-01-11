/**
 * Workflow Validator - Main Entry Point
 *
 * Orchestrates multi-level validation of workflow definitions:
 * - Level 1: Schema validation (Zod)
 * - Level 2: Semantic validation (variable references, etc.)
 * - Level 3: Runtime validation (URL reachability, etc.)
 *
 * Features:
 * - Dependency injection for testability
 * - Path traversal protection for file validation
 * - Agent feedback generation for LLM auto-fix
 *
 * @module engine/validator/workflow-validator
 * @see Issue #348
 */

import * as path from 'path';
import type {
  ValidationResult,
  ValidationIssue,
  AgentSummary,
  BatchValidationResult,
} from './types.js';
import { ZodSchemaValidator } from './zod-schema-validator.js';
import { SemanticValidator } from './semantic-validator.js';
import { RuntimeValidator } from './runtime-validator.js';

// ============================================================
// Types
// ============================================================

/**
 * Validation options
 */
export interface ValidatorOptions {
  /** Validation level (1=schema, 2=semantic, 3=runtime) */
  level?: 1 | 2 | 3;
  /** Treat warnings as errors */
  strict?: boolean;
  /** Check URL reachability (Level 3 only) */
  checkUrls?: boolean;
  /** Timeout for runtime checks in milliseconds */
  timeout_ms?: number;
  /** Include agent feedback in result */
  includeAgentFeedback?: boolean;
}

/**
 * Dependencies for WorkflowValidator (for DI)
 */
export interface ValidatorDependencies {
  schemaValidator?: ZodSchemaValidator;
  semanticValidator?: SemanticValidator;
  runtimeValidator?: RuntimeValidator;
}

// ============================================================
// Workflow Validator
// ============================================================

/**
 * Main workflow validator class.
 *
 * Provides comprehensive validation of workflow definitions
 * with support for multiple validation levels and agent feedback.
 *
 * @example
 * ```typescript
 * const validator = new WorkflowValidator();
 *
 * // Validate a workflow definition
 * const result = await validator.validate(definition);
 * if (!result.valid) {
 *   console.log(result.issues);
 * }
 *
 * // Validate with agent feedback
 * const resultWithFeedback = await validator.validate(definition, {
 *   includeAgentFeedback: true,
 * });
 * console.log(resultWithFeedback.agentSummary);
 * ```
 */
export class WorkflowValidator {
  private schemaValidator: ZodSchemaValidator;
  private semanticValidator: SemanticValidator;
  private runtimeValidator: RuntimeValidator;

  /** Allowed base paths for file validation (path traversal protection) */
  private allowedBasePaths: string[];

  /**
   * Create a new WorkflowValidator
   * @param deps - Optional dependencies for testing
   * @param allowedBasePaths - Allowed directories for file validation
   */
  constructor(deps: ValidatorDependencies = {}, allowedBasePaths?: string[]) {
    this.schemaValidator = deps.schemaValidator || new ZodSchemaValidator();
    this.semanticValidator = deps.semanticValidator || new SemanticValidator();
    this.runtimeValidator = deps.runtimeValidator || new RuntimeValidator();

    // Default to config/taskflow for security
    this.allowedBasePaths = allowedBasePaths || [
      path.resolve(process.cwd(), 'config/taskflow'),
    ];
  }

  /**
   * Validate a workflow definition
   * @param definition - Workflow definition object
   * @param options - Validation options
   * @returns Validation result
   */
  async validate(
    definition: unknown,
    options: ValidatorOptions = {}
  ): Promise<ValidationResult> {
    const startTime = Date.now();
    const level = options.level || 2;
    const issues: ValidationIssue[] = [];

    // Level 1: Schema Validation (always run)
    const schemaResult = this.schemaValidator.validate(definition);
    issues.push(...schemaResult.issues);

    // Only proceed to higher levels if schema validation passes
    if (schemaResult.valid && level >= 2) {
      // Level 2: Semantic Validation
      const semanticResult = this.semanticValidator.validate(definition);
      issues.push(...semanticResult.issues);

      // Only proceed to level 3 if semantic validation passes
      if (semanticResult.valid && level >= 3 && options.checkUrls) {
        // Level 3: Runtime Validation
        const runtimeResult = await this.runtimeValidator.validate(definition, {
          timeout_ms: options.timeout_ms || 5000,
          checkUrls: options.checkUrls,
        });
        issues.push(...runtimeResult.issues);
      }
    }

    // Calculate summary
    const errors = issues.filter((i) => i.severity === 'error').length;
    const warnings = issues.filter((i) => i.severity === 'warning').length;
    const infos = issues.filter((i) => i.severity === 'info').length;

    // Determine validity
    const valid = options.strict
      ? errors === 0 && warnings === 0
      : errors === 0;

    // Generate agent summary if requested
    const agentSummary = options.includeAgentFeedback
      ? this.generateAgentSummary(issues)
      : undefined;

    return {
      valid,
      issues,
      summary: { errors, warnings, infos },
      metadata: {
        duration_ms: Date.now() - startTime,
        level,
      },
      agentSummary,
    };
  }

  /**
   * Validate a workflow from a file
   * @param filePath - Path to the workflow JSON file
   * @param options - Validation options
   * @returns Validation result
   */
  async validateFile(
    filePath: string,
    options?: ValidatorOptions
  ): Promise<ValidationResult> {
    // Path traversal protection
    if (!this.isPathAllowed(filePath)) {
      return {
        valid: false,
        issues: [
          {
            severity: 'error',
            code: 'PATH_NOT_ALLOWED',
            message: `File path is outside allowed directories: ${filePath}`,
            agentFeedback: {
              targetPath: 'file_path',
              category: 'constraint',
              currentValue: filePath,
              expectedFormat: `Path must be within: ${this.allowedBasePaths.join(', ')}`,
            },
          },
        ],
        summary: { errors: 1, warnings: 0, infos: 0 },
        metadata: { file: filePath, duration_ms: 0, level: 1 },
      };
    }

    // Read and parse file
    try {
      const fs = await import('fs/promises');
      const content = await fs.readFile(filePath, 'utf-8');
      let definition: unknown;

      try {
        definition = JSON.parse(content);
      } catch (e) {
        const error = e as Error;
        return {
          valid: false,
          issues: [
            {
              severity: 'error',
              code: 'INVALID_JSON',
              message: `Invalid JSON: ${error.message}`,
              agentFeedback: {
                targetPath: 'root',
                category: 'schema',
                expectedFormat: 'Valid JSON object with workflow_name, steps, output',
                fixExample: '{"workflow_name": "example", "input_schema": {}, "output_schema": {}, "steps": [], "output": {}}',
              },
            },
          ],
          summary: { errors: 1, warnings: 0, infos: 0 },
          metadata: { file: filePath, duration_ms: 0, level: 1 },
        };
      }

      // Validate the definition
      const result = await this.validate(definition, options);

      // Add file info to metadata
      return {
        ...result,
        metadata: {
          ...result.metadata,
          file: filePath,
          duration_ms: result.metadata?.duration_ms || 0,
          level: result.metadata?.level || 1,
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return {
        valid: false,
        issues: [
          {
            severity: 'error',
            code: 'FILE_READ_ERROR',
            message: `Failed to read file: ${message}`,
          },
        ],
        summary: { errors: 1, warnings: 0, infos: 0 },
        metadata: { file: filePath, duration_ms: 0, level: 1 },
      };
    }
  }

  /**
   * Validate all JSON files in a directory
   * @param dirPath - Directory path
   * @param options - Validation options
   * @returns Batch validation result
   */
  async validateDirectory(
    dirPath: string,
    options?: ValidatorOptions
  ): Promise<BatchValidationResult> {
    const fs = await import('fs/promises');

    const files = await fs.readdir(dirPath);
    const jsonFiles = files.filter((f) => f.endsWith('.json'));

    const results = new Map<string, ValidationResult>();
    let validCount = 0;
    let totalErrors = 0;
    let totalWarnings = 0;

    for (const file of jsonFiles) {
      const filePath = path.join(dirPath, file);
      const result = await this.validateFile(filePath, options);

      results.set(file, result);

      if (result.valid) validCount++;
      totalErrors += result.summary.errors;
      totalWarnings += result.summary.warnings;
    }

    return {
      results,
      summary: {
        total_files: jsonFiles.length,
        valid_files: validCount,
        invalid_files: jsonFiles.length - validCount,
        total_errors: totalErrors,
        total_warnings: totalWarnings,
      },
    };
  }

  /**
   * Check if a file path is within allowed directories
   * @param filePath - File path to check
   * @returns true if path is allowed
   */
  private isPathAllowed(filePath: string): boolean {
    const resolvedPath = path.resolve(filePath);

    return this.allowedBasePaths.some((basePath) => {
      const resolvedBase = path.resolve(basePath);
      return (
        resolvedPath.startsWith(resolvedBase + path.sep) ||
        resolvedPath === resolvedBase
      );
    });
  }

  /**
   * Generate agent summary from validation issues
   * @param issues - Validation issues
   * @returns Agent summary or undefined if no errors
   */
  private generateAgentSummary(
    issues: ValidationIssue[]
  ): AgentSummary | undefined {
    const errorIssues = issues.filter((i) => i.severity === 'error');

    if (errorIssues.length === 0) {
      return undefined;
    }

    const fixRequired: string[] = [];
    const suggestedFixes: Record<string, unknown> = {};
    const regenerationHints: string[] = [];

    for (const issue of errorIssues) {
      // Build fix required list
      fixRequired.push(
        `[${issue.code}] ${issue.path || 'root'}: ${issue.message}`
      );

      // Extract suggested fixes from agent feedback
      if (issue.agentFeedback?.fixExample) {
        try {
          const fix = JSON.parse(issue.agentFeedback.fixExample);
          if (issue.path) {
            suggestedFixes[issue.path] = fix;
          }
        } catch {
          // fixExample is not JSON, skip
        }
      }

      // Generate regeneration hints
      if (issue.agentFeedback) {
        const fb = issue.agentFeedback;

        if (fb.allowedValues && fb.allowedValues.length > 0) {
          regenerationHints.push(
            `${fb.targetPath}: Use one of [${fb.allowedValues.join(', ')}]`
          );
        } else if (fb.expectedFormat) {
          regenerationHints.push(
            `${fb.targetPath}: Expected format is "${fb.expectedFormat}"`
          );
        }
      }
    }

    return {
      fixRequired,
      suggestedFixes:
        Object.keys(suggestedFixes).length > 0 ? suggestedFixes : undefined,
      regenerationHints:
        regenerationHints.length > 0 ? regenerationHints : undefined,
    };
  }
}

// ============================================================
// Exported Instance
// ============================================================

/**
 * Default workflow validator instance
 */
export const workflowValidator = new WorkflowValidator();
