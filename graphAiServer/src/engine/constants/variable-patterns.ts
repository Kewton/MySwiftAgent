/**
 * TaskFlow V2 Variable Pattern Definitions
 *
 * Issue #352: Centralized variable pattern definitions for GraphAiServer.
 * Aligned with expertAgent/variable_patterns.py for consistency.
 *
 * This module provides:
 * - TASKFLOW_VARIABLE_PATTERN: Regex for variable references
 * - isValidTaskflowVariable(): Validate variable reference syntax
 * - extractVariableReference(): Extract variable from URL with trailing path
 *
 * Variable Reference Format:
 * - ${inputs.field} - Workflow input parameters
 * - ${step_id.output.field} - Previous step output
 * - ${env.VAR_NAME} - Environment variable
 * - ${secrets.KEY} - MyVault secret
 *
 * @module engine/constants/variable-patterns
 * @see Issue #352
 */

// ============================================================
// Pattern Definition
// ============================================================

/**
 * TaskFlow V2 variable reference pattern
 *
 * Pattern breakdown:
 *   \$\{                           - Literal ${
 *   [a-zA-Z_][a-zA-Z0-9_-]*        - Identifier (starts with letter/underscore, allows hyphen)
 *   (?:\.[a-zA-Z_][a-zA-Z0-9_-]*)* - Optional dot-separated nested identifiers
 *   \}                             - Literal }
 *
 * Matches:
 * - ${inputs.query}
 * - ${step_001.output}
 * - ${step-001.output.data.name}
 * - ${secrets.API_KEY}
 * - ${env.BASE_URL}
 *
 * Does NOT match:
 * - ${123invalid} - starts with number
 * - ${.invalid} - starts with dot
 * - ${} - empty
 * - ${invalid.} - ends with dot
 */
export const TASKFLOW_VARIABLE_PATTERN = /^\$\{[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*\}$/;

/**
 * Pattern to extract variable reference from the beginning of a string
 * Useful for URLs like "${inputs.url}/api/v1/endpoint"
 */
export const TASKFLOW_VARIABLE_EXTRACT_PATTERN = /^\$\{[^}]+\}/;

// ============================================================
// Validation Functions
// ============================================================

/**
 * Check if a string is a valid TaskFlow variable reference
 *
 * @param str - String to validate (must be exactly the variable, e.g., "${inputs.url}")
 * @returns true if the string is a valid variable reference
 *
 * @example
 * isValidTaskflowVariable("${inputs.url}") // true
 * isValidTaskflowVariable("${step_001.output.data}") // true
 * isValidTaskflowVariable("${123invalid}") // false
 * isValidTaskflowVariable("${inputs.url}/path") // false (has trailing path)
 */
export function isValidTaskflowVariable(str: string): boolean {
  return TASKFLOW_VARIABLE_PATTERN.test(str);
}

/**
 * Extract the variable reference from a string that may have trailing content
 * Returns null if no valid variable reference is found at the start
 *
 * @param str - String that may contain a variable reference at the start
 * @returns The variable reference or null
 *
 * @example
 * extractVariableReference("${inputs.url}/api/v1") // "${inputs.url}"
 * extractVariableReference("${env.BASE_URL}?query=1") // "${env.BASE_URL}"
 * extractVariableReference("https://example.com") // null
 */
export function extractVariableReference(str: string): string | null {
  const match = str.match(TASKFLOW_VARIABLE_EXTRACT_PATTERN);
  return match ? match[0] : null;
}

/**
 * Check if a URL starts with a valid TaskFlow variable reference
 * Supports trailing paths like "${inputs.url}/api/v1/endpoint"
 *
 * @param url - URL string to validate
 * @returns true if the URL starts with a valid variable reference
 *
 * @example
 * startsWithValidVariable("${inputs.url}") // true
 * startsWithValidVariable("${inputs.url}/api/v1") // true
 * startsWithValidVariable("${step_001.output.api_url}?query=1") // true
 * startsWithValidVariable("${123invalid}/path") // false
 * startsWithValidVariable("https://example.com") // false
 */
export function startsWithValidVariable(url: string): boolean {
  if (!url.startsWith('${')) {
    return false;
  }

  const varRef = extractVariableReference(url);
  if (!varRef) {
    return false;
  }

  return isValidTaskflowVariable(varRef);
}

// ============================================================
// Error Message Templates
// ============================================================

/**
 * Error message for invalid URL with helpful examples
 * Issue #352 SF-2: Improved error messages
 */
export const URL_VALIDATION_ERROR_MESSAGE =
  'URL must use HTTPS protocol or start with a TaskFlow variable reference. ' +
  'Valid variable formats: ${inputs.field}, ${step_id.output.field}, ${env.VAR}, ${secrets.KEY}. ' +
  'Example: ${inputs.base_url}/api/v1/endpoint';

/**
 * Short error message for Zod schema
 */
export const URL_VALIDATION_SHORT_MESSAGE =
  'URL must use HTTPS protocol or be a TaskFlow variable reference ' +
  '(${inputs.*}, ${step_id.output.*}, ${env.*}, ${secrets.*})';
