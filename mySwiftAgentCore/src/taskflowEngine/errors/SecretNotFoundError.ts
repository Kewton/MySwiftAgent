/**
 * SecretNotFoundError - Unified error for missing secrets
 *
 * Issue #377: Unified secrets injection error handling
 */

/**
 * Context information for the error
 */
export interface SecretNotFoundContext {
  workflowId?: string;
  stepId?: string;
  nodeType?: string;
}

/**
 * SecretNotFoundError - Error thrown when a required secret is not found
 *
 * Provides detailed context about where the secret was needed.
 */
export class SecretNotFoundError extends Error {
  readonly code = 'SECRET_NOT_FOUND' as const;
  readonly secretKey: string;
  readonly workflowId?: string;
  readonly stepId?: string;
  readonly nodeType?: string;

  constructor(secretKey: string, context?: SecretNotFoundContext) {
    const message = SecretNotFoundError.buildMessage(secretKey, context);
    super(message);

    this.name = 'SecretNotFoundError';
    this.secretKey = secretKey;
    this.workflowId = context?.workflowId;
    this.stepId = context?.stepId;
    this.nodeType = context?.nodeType;

    // Maintains proper stack trace for where error was thrown (only in V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, SecretNotFoundError);
    }
  }

  /**
   * Build a descriptive error message
   */
  private static buildMessage(secretKey: string, context?: SecretNotFoundContext): string {
    let message = `Secret '${secretKey}' not found`;

    if (context?.workflowId) {
      message += ` in workflow '${context.workflowId}'`;
    }

    if (context?.stepId) {
      message += ` at step '${context.stepId}'`;
    }

    if (context?.nodeType) {
      message += ` (node type: ${context.nodeType})`;
    }

    return message;
  }

  /**
   * Serialize error to JSON for API responses
   */
  toJSON(): Record<string, unknown> {
    const result: Record<string, unknown> = {
      code: this.code,
      secretKey: this.secretKey,
      message: this.message,
    };

    if (this.workflowId !== undefined) {
      result.workflowId = this.workflowId;
    }

    if (this.stepId !== undefined) {
      result.stepId = this.stepId;
    }

    if (this.nodeType !== undefined) {
      result.nodeType = this.nodeType;
    }

    return result;
  }

  /**
   * Get the list of required secrets that were not found
   */
  getRequiredSecrets(): string[] {
    return [this.secretKey];
  }
}

/**
 * Type guard for SecretNotFoundError
 */
export function isSecretNotFoundError(error: unknown): error is SecretNotFoundError {
  return error instanceof SecretNotFoundError;
}
