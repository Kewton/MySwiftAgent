/**
 * Error Messages for TaskFlow Engine
 *
 * This module provides LLM-friendly error messages with:
 * - Clear problem descriptions
 * - Suggested fixes
 * - Error codes for categorization
 *
 * Designed for use in LLM retry loops where the error message
 * should guide the LLM to fix the workflow definition.
 *
 * @module engine/validator/error-messages
 * @see Issue #348
 */

// ============================================================
// Error Code Categories
// ============================================================

/** Error severity levels */
export type ErrorSeverity = 'error' | 'warning' | 'info';

/** Error categories for retry logic */
export enum ErrorCategory {
  /** Schema validation errors - fix the definition structure */
  SCHEMA = 'SCHEMA',
  /** Type errors - fix data types */
  TYPE = 'TYPE',
  /** Security errors - cannot be fixed by LLM */
  SECURITY = 'SECURITY',
  /** Runtime errors - may need definition changes */
  RUNTIME = 'RUNTIME',
  /** API errors - external service issues */
  API = 'API',
  /** Timeout errors - may need config changes */
  TIMEOUT = 'TIMEOUT',
}

/** Whether an error is retryable by modifying the definition */
export const RETRYABLE_CATEGORIES = new Set([
  ErrorCategory.SCHEMA,
  ErrorCategory.TYPE,
  ErrorCategory.RUNTIME,
]);

// ============================================================
// Error Messages with Suggestions
// ============================================================

/** Error message template */
export interface ErrorMessage {
  code: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  message: string;
  suggestion: string;
  example?: string;
}

/** Error messages catalog */
export const ERROR_MESSAGES: Record<string, ErrorMessage> = {
  // Schema Errors
  MISSING_WORKFLOW_NAME: {
    code: 'SCHEMA_001',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Workflow definition is missing required field: workflow_name',
    suggestion: 'Add a "workflow_name" field with a valid identifier (letters, numbers, underscores, hyphens)',
    example: '"workflow_name": "my_workflow"',
  },

  MISSING_INPUT_SCHEMA: {
    code: 'SCHEMA_002',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Workflow definition is missing required field: input_schema',
    suggestion: 'Add an "input_schema" object defining the expected input fields and their types',
    example: '"input_schema": { "user_id": "string", "count": "number" }',
  },

  MISSING_OUTPUT_SCHEMA: {
    code: 'SCHEMA_003',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Workflow definition is missing required field: output_schema',
    suggestion: 'Add an "output_schema" object defining the expected output fields and their types',
    example: '"output_schema": { "result": "string", "success": "boolean" }',
  },

  MISSING_STEPS: {
    code: 'SCHEMA_004',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Workflow definition is missing required field: steps',
    suggestion: 'Add a "steps" array with at least one step definition',
    example: '"steps": [{ "id": "step1", "type": "api_rest", "config": {...} }]',
  },

  MISSING_OUTPUT_MAPPING: {
    code: 'SCHEMA_005',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Workflow definition is missing required field: output',
    suggestion: 'Add an "output" object mapping output schema fields to node output references',
    example: '"output": { "result": "${step1.output.data}" }',
  },

  INVALID_STEP_ID: {
    code: 'SCHEMA_006',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Step ID must start with a letter or underscore and contain only alphanumeric characters and underscores',
    suggestion: 'Rename the step ID to match the pattern: [a-zA-Z_][a-zA-Z0-9_]*',
    example: '"id": "fetch_user_data"',
  },

  DUPLICATE_STEP_ID: {
    code: 'SCHEMA_007',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Duplicate step ID found. Each step must have a unique ID.',
    suggestion: 'Rename one of the duplicate step IDs to be unique',
  },

  INVALID_STEP_TYPE: {
    code: 'SCHEMA_008',
    category: ErrorCategory.SCHEMA,
    severity: 'error',
    message: 'Invalid step type. Must be one of: api_rest, code_js, transform, parallel',
    suggestion: 'Use a valid step type based on what the step should do',
    example: '"type": "api_rest" for HTTP requests, "transform" for data manipulation',
  },

  // Type Errors
  INVALID_SIMPLE_TYPE: {
    code: 'TYPE_001',
    category: ErrorCategory.TYPE,
    severity: 'error',
    message: 'Invalid type in schema. Must be: string, number, boolean, array, object, or null',
    suggestion: 'Use one of the supported simple types in your schema definitions',
    example: '"field_name": "string"',
  },

  TYPE_MISMATCH: {
    code: 'TYPE_002',
    category: ErrorCategory.TYPE,
    severity: 'error',
    message: 'Input/output type does not match the schema',
    suggestion: 'Ensure the data type matches what is declared in the schema',
  },

  // Security Errors
  HTTP_NOT_ALLOWED: {
    code: 'SEC_001',
    category: ErrorCategory.SECURITY,
    severity: 'error',
    message: 'HTTP protocol is not allowed. HTTPS is required for all external API calls.',
    suggestion: 'Change the URL to use https:// instead of http://',
    example: '"url": "https://api.example.com/endpoint"',
  },

  PRIVATE_IP_BLOCKED: {
    code: 'SEC_002',
    category: ErrorCategory.SECURITY,
    severity: 'error',
    message: 'Private IP addresses are blocked for security reasons (SSRF protection)',
    suggestion: 'Use a public API endpoint. Private IPs (127.x.x.x, 10.x.x.x, 192.168.x.x) are not allowed.',
  },

  METADATA_ENDPOINT_BLOCKED: {
    code: 'SEC_003',
    category: ErrorCategory.SECURITY,
    severity: 'error',
    message: 'Cloud metadata endpoints are blocked for security reasons',
    suggestion: 'This endpoint cannot be accessed. Use a different API endpoint.',
  },

  DOMAIN_NOT_WHITELISTED: {
    code: 'SEC_004',
    category: ErrorCategory.SECURITY,
    severity: 'error',
    message: 'Domain is not in the allowed domains list',
    suggestion: 'Contact the administrator to add this domain to the whitelist',
  },

  PATH_TRAVERSAL: {
    code: 'SEC_005',
    category: ErrorCategory.SECURITY,
    severity: 'error',
    message: 'Path traversal characters (..) are not allowed in file paths',
    suggestion: 'Use a direct path without ".." components',
  },

  // Runtime Errors
  NODE_NOT_FOUND: {
    code: 'RUNTIME_001',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'Referenced node not found in workflow',
    suggestion: 'Check that the node ID in the reference matches an existing step ID',
    example: 'If referencing ${fetch_user.output.name}, ensure there is a step with id "fetch_user"',
  },

  MISSING_REQUIRED_INPUT: {
    code: 'RUNTIME_002',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'Required input field is missing',
    suggestion: 'Ensure all fields declared in input_schema are provided in the inputs',
  },

  VARIABLE_RESOLUTION_FAILED: {
    code: 'RUNTIME_003',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'Failed to resolve variable reference',
    suggestion: 'Check the variable reference syntax: ${source.path.to.field}',
    example: '${inputs.user_id}, ${fetch_user.output.name}, ${env.API_KEY}, ${secrets.TOKEN}',
  },

  TEMPLATE_ERROR: {
    code: 'RUNTIME_004',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'Handlebars template execution failed',
    suggestion: 'Check the template syntax. Use {{field}} for variables and {{#if condition}}...{{/if}} for conditionals',
  },

  SCRIPT_NOT_FOUND: {
    code: 'RUNTIME_005',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'JavaScript file not found',
    suggestion: 'Ensure the script file exists in the scripts directory',
  },

  FUNCTION_NOT_FOUND: {
    code: 'RUNTIME_006',
    category: ErrorCategory.RUNTIME,
    severity: 'error',
    message: 'JavaScript function not found in script',
    suggestion: 'Ensure the function is exported from the script file',
    example: 'module.exports = { myFunction: (params) => {...} }',
  },

  // API Errors
  API_REQUEST_FAILED: {
    code: 'API_001',
    category: ErrorCategory.API,
    severity: 'error',
    message: 'API request failed',
    suggestion: 'Check the URL, headers, and request body. Verify the API is accessible.',
  },

  API_UNAUTHORIZED: {
    code: 'API_002',
    category: ErrorCategory.API,
    severity: 'error',
    message: 'API returned 401 Unauthorized',
    suggestion: 'Check the Authorization header or API key. Use ${secrets.KEY} for sensitive credentials.',
  },

  API_NOT_FOUND: {
    code: 'API_003',
    category: ErrorCategory.API,
    severity: 'error',
    message: 'API returned 404 Not Found',
    suggestion: 'Check the URL path. The resource may not exist or the URL may be incorrect.',
  },

  // Timeout Errors
  REQUEST_TIMEOUT: {
    code: 'TIMEOUT_001',
    category: ErrorCategory.TIMEOUT,
    severity: 'error',
    message: 'HTTP request timed out',
    suggestion: 'Increase timeout_ms in the step config, or check if the API is responding slowly',
    example: '"timeout_ms": 60000',
  },

  SCRIPT_TIMEOUT: {
    code: 'TIMEOUT_002',
    category: ErrorCategory.TIMEOUT,
    severity: 'error',
    message: 'JavaScript execution timed out',
    suggestion: 'Optimize the script to run faster. Maximum execution time is 5 seconds.',
  },

  WORKFLOW_TIMEOUT: {
    code: 'TIMEOUT_003',
    category: ErrorCategory.TIMEOUT,
    severity: 'error',
    message: 'Workflow execution timed out',
    suggestion: 'The workflow took too long to complete. Consider splitting into smaller workflows or reducing parallel steps.',
  },
};

// ============================================================
// Helper Functions
// ============================================================

/**
 * Get an error message by code
 * @param code - Error code (e.g., 'MISSING_WORKFLOW_NAME')
 * @returns Error message template or undefined
 */
export function getErrorMessage(code: string): ErrorMessage | undefined {
  return ERROR_MESSAGES[code];
}

/**
 * Format an error with context for LLM consumption
 * @param code - Error code
 * @param context - Additional context (field name, value, etc.)
 * @returns Formatted error string
 */
export function formatErrorForLLM(
  code: string,
  context?: Record<string, unknown>
): string {
  const template = ERROR_MESSAGES[code];

  if (!template) {
    return `Unknown error: ${code}`;
  }

  let message = `[${template.code}] ${template.message}`;

  if (context) {
    message += '\n\nContext:';
    for (const [key, value] of Object.entries(context)) {
      message += `\n  ${key}: ${JSON.stringify(value)}`;
    }
  }

  message += `\n\nSuggestion: ${template.suggestion}`;

  if (template.example) {
    message += `\n\nExample: ${template.example}`;
  }

  return message;
}

/**
 * Check if an error is retryable by modifying the workflow
 * @param code - Error code
 * @returns true if the error can be fixed by changing the workflow
 */
export function isRetryableError(code: string): boolean {
  const template = ERROR_MESSAGES[code];
  if (!template) {
    return false;
  }
  return RETRYABLE_CATEGORIES.has(template.category);
}

/**
 * Get all error messages for a category
 * @param category - Error category
 * @returns Array of error messages in that category
 */
export function getErrorsByCategory(category: ErrorCategory): ErrorMessage[] {
  return Object.values(ERROR_MESSAGES).filter((e) => e.category === category);
}
