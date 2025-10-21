// src/types/workflow.ts

/**
 * Request body for workflow registration endpoint
 */
export interface WorkflowRegisterRequest {
  /**
   * Workflow name (will be used as filename: {workflow_name}.yml)
   * Must be a valid filename (alphanumeric, underscores, hyphens)
   */
  workflow_name: string;

  /**
   * YAML content of the GraphAI workflow
   * Must be valid YAML syntax
   */
  yaml_content: string;

  /**
   * Optional: Overwrite existing file if it exists
   * Default: false
   */
  overwrite?: boolean;
}

/**
 * Response from workflow registration endpoint
 */
export interface WorkflowRegisterResponse {
  /**
   * Registration status
   * - "success": Workflow registered successfully
   * - "error": Workflow registration failed
   */
  status: "success" | "error";

  /**
   * Absolute path to the saved workflow file
   * Only present on success
   */
  file_path?: string;

  /**
   * Workflow name (without .yml extension)
   * Only present on success
   */
  workflow_name?: string;

  /**
   * Error message if registration failed
   * Only present on error
   */
  error_message?: string;

  /**
   * Detailed validation errors
   * Only present if YAML validation failed
   */
  validation_errors?: WorkflowValidationError[];
}

/**
 * Validation error details
 */
export interface WorkflowValidationError {
  /**
   * Error type
   * - "yaml_syntax": YAML parsing error
   * - "schema": Schema validation error
   * - "file_system": File system error
   */
  type: "yaml_syntax" | "schema" | "file_system";

  /**
   * Error message
   */
  message: string;

  /**
   * Line number where error occurred (for YAML syntax errors)
   */
  line?: number;

  /**
   * Column number where error occurred (for YAML syntax errors)
   */
  column?: number;
}
