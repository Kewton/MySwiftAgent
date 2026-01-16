/**
 * SecurityError - Security-related error handling
 *
 * Issue #363: Custom error class for security violations
 */

/**
 * Security error codes
 */
export enum SecurityErrorCode {
  SCRIPT_NOT_WHITELISTED = 'SCRIPT_NOT_WHITELISTED',
  SCRIPT_INTEGRITY_FAILED = 'SCRIPT_INTEGRITY_FAILED',
  FUNCTION_NOT_FOUND = 'FUNCTION_NOT_FOUND',
  EXECUTION_TIMEOUT = 'EXECUTION_TIMEOUT',
  MEMORY_LIMIT_EXCEEDED = 'MEMORY_LIMIT_EXCEEDED',
  PATH_TRAVERSAL_DETECTED = 'PATH_TRAVERSAL_DETECTED',
}

/**
 * SecurityError - Custom error for security violations
 */
export class SecurityError extends Error {
  public readonly code: SecurityErrorCode;
  public readonly context?: Record<string, unknown>;

  constructor(
    message: string,
    code: SecurityErrorCode,
    context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'SecurityError';
    this.code = code;
    this.context = context;

    // Ensure proper prototype chain for instanceof checks
    Object.setPrototypeOf(this, SecurityError.prototype);
  }
}

/**
 * Type guard for SecurityError
 */
export function isSecurityError(error: unknown): error is SecurityError {
  return error instanceof SecurityError;
}
