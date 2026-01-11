/**
 * Type Definitions for Workflow Validator
 *
 * Defines all types used by the validation system including:
 * - Validation severity levels
 * - Agent feedback for LLM-driven auto-fix
 * - Validation issues and results
 * - Batch validation results
 *
 * @module engine/validator/types
 * @see Issue #348
 */

// ============================================================
// Basic Types
// ============================================================

/**
 * Severity level for validation issues
 */
export type ValidationSeverity = 'error' | 'warning' | 'info';

// ============================================================
// Agent Feedback Types
// ============================================================

/**
 * Feedback category for agent-driven fixes
 */
export type AgentFeedbackCategory = 'schema' | 'reference' | 'type' | 'constraint';

/**
 * Feedback information for workflow generation agents (LLMs).
 * Provides detailed hints for automatic correction of validation errors.
 *
 * @example
 * ```typescript
 * const feedback: AgentFeedback = {
 *   targetPath: 'steps[0].config.url',
 *   category: 'schema',
 *   currentValue: 'http://api.example.com',
 *   expectedFormat: 'URL must use HTTPS protocol',
 *   fixExample: '"https://api.example.com/v1/users"',
 * };
 * ```
 */
export interface AgentFeedback {
  /** JSON path to the problematic field */
  targetPath: string;

  /** Category of the validation issue */
  category: AgentFeedbackCategory;

  /** Current (invalid) value */
  currentValue?: unknown;

  /** Expected format or value description */
  expectedFormat?: string;

  /** List of allowed values (for enums/fixed sets) */
  allowedValues?: string[];

  /** Example of a correct value (JSON string) */
  fixExample?: string;

  /** URL to relevant documentation */
  docUrl?: string;
}

// ============================================================
// Validation Issue Types
// ============================================================

/**
 * Individual validation issue found during validation.
 *
 * Includes human-readable messages and machine-readable feedback
 * for automated correction by LLM agents.
 */
export interface ValidationIssue {
  /** Issue severity */
  severity: ValidationSeverity;

  /** Error code for programmatic handling */
  code: string;

  /** Human-readable error message */
  message: string;

  /** JSON path to the issue location */
  path?: string;

  /** Line number in source file (if applicable) */
  line?: number;

  /** Human-readable fix suggestion */
  suggestion?: string;

  /** Machine-readable feedback for LLM agents */
  agentFeedback?: AgentFeedback;
}

// ============================================================
// Validation Result Types
// ============================================================

/**
 * Agent summary for LLM-driven auto-correction.
 * Formatted for easy inclusion in LLM prompts.
 */
export interface AgentSummary {
  /** List of required fixes in human-readable format */
  fixRequired: string[];

  /** JSON patch-style suggested fixes (path -> value) */
  suggestedFixes?: Record<string, unknown>;

  /** Hints for regenerating the workflow */
  regenerationHints?: string[];
}

/**
 * Validation metadata
 */
export interface ValidationMetadata {
  /** Source file path (if validating a file) */
  file?: string;

  /** Validation duration in milliseconds */
  duration_ms: number;

  /** Validation level used (1=schema, 2=semantic, 3=runtime) */
  level: 1 | 2 | 3;
}

/**
 * Summary of validation issues
 */
export interface ValidationSummary {
  /** Number of error-level issues */
  errors: number;

  /** Number of warning-level issues */
  warnings: number;

  /** Number of info-level issues */
  infos: number;
}

/**
 * Result of workflow validation.
 *
 * Contains all validation issues found, summary statistics,
 * and optional agent feedback for automated correction.
 */
export interface ValidationResult {
  /** Whether the workflow passed validation */
  valid: boolean;

  /** List of validation issues */
  issues: ValidationIssue[];

  /** Summary of issue counts by severity */
  summary: ValidationSummary;

  /** Validation metadata */
  metadata?: ValidationMetadata;

  /** Agent summary for LLM-driven auto-correction */
  agentSummary?: AgentSummary;
}

// ============================================================
// Batch Validation Types
// ============================================================

/**
 * Summary for batch validation
 */
export interface BatchValidationSummary {
  /** Total number of files validated */
  total_files: number;

  /** Number of valid files */
  valid_files: number;

  /** Number of invalid files */
  invalid_files: number;

  /** Total number of errors across all files */
  total_errors: number;

  /** Total number of warnings across all files */
  total_warnings: number;
}

/**
 * Result of batch validation (multiple files).
 */
export interface BatchValidationResult {
  /** Validation results keyed by file name */
  results: Map<string, ValidationResult>;

  /** Summary across all files */
  summary: BatchValidationSummary;
}

// ============================================================
// Validator Interface Types
// ============================================================

/**
 * Common interface for validation layer implementations
 */
export interface ValidatorLayer {
  /**
   * Validate a workflow definition
   * @param definition - Workflow definition object
   * @returns Validation result
   */
  validate(definition: unknown): ValidationResult;
}

/**
 * Interface for async validation layers (e.g., runtime checks)
 */
export interface AsyncValidatorLayer {
  /**
   * Validate a workflow definition asynchronously
   * @param definition - Workflow definition object
   * @param options - Validation options
   * @returns Validation result
   */
  validate(
    definition: unknown,
    options?: { timeout_ms?: number }
  ): Promise<ValidationResult>;
}
