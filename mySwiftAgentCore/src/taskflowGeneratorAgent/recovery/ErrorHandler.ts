/**
 * ErrorHandler - Error handling and recovery strategy
 *
 * Issue #364: Structured error handling with recovery suggestions
 */

import {
  ErrorType,
  RecoveryStrategy,
  type TaskError,
} from '../types/generator.js';
import {
  LLMApiError,
  LLMParseError,
  LLMValidationError,
} from '../llm/LLMClient.js';

/**
 * Error Context - Additional information about the error
 */
export interface ErrorContext {
  task_id: string;
  attempt?: number;
  maxAttempts?: number;
  additionalInfo?: Record<string, unknown>;
}

/**
 * ErrorHandler - Handles errors and provides recovery suggestions
 *
 * Error Type to Recovery Strategy Mapping:
 * - LLM Rate Limit -> RETRY_CURRENT (with backoff)
 * - LLM Timeout -> RETRY_CURRENT
 * - LLM Server Error -> RETRY_CURRENT
 * - LLM Auth Error -> MANUAL_INTERVENTION
 * - Parse Error -> RETRY_WITH_FEEDBACK
 * - Validation Error -> RETRY_WITH_FEEDBACK
 * - Capability Not Found -> ROLLBACK_TO_ANALYSIS
 * - Registration Error -> RETRY_CURRENT
 * - Unknown Error -> MANUAL_INTERVENTION
 */
export class ErrorHandler {
  /**
   * Handle error and return structured TaskError
   *
   * @param error - The error to handle
   * @param context - Error context
   * @returns TaskError with recovery suggestion
   */
  async handle(error: Error, context: ErrorContext): Promise<TaskError> {
    const errorType = this.classifyError(error);
    const recoverable = this.isRecoverable(error);
    const recoverySuggestion = this.getRecoverySuggestion(error);
    const details = this.extractDetails(error);

    return {
      task_id: context.task_id,
      error_type: errorType,
      message: error.message,
      recoverable,
      recovery_suggestion: recoverySuggestion,
      details: {
        ...details,
        attempt: context.attempt,
        maxAttempts: context.maxAttempts,
        ...context.additionalInfo,
      },
    };
  }

  /**
   * Classify error into ErrorType
   */
  classifyError(error: Error): ErrorType {
    if (error instanceof LLMApiError) {
      return ErrorType.LLM_ERROR;
    }

    if (error instanceof LLMParseError || error instanceof LLMValidationError) {
      return ErrorType.VALIDATION_ERROR;
    }

    if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
      return ErrorType.TIMEOUT_ERROR;
    }

    if (error.name === 'CapabilityNotFoundError' || error.message.includes('Capability not found')) {
      return ErrorType.CAPABILITY_NOT_FOUND;
    }

    if (error.name === 'RegistrationError' || error.message.includes('register')) {
      return ErrorType.REGISTRATION_ERROR;
    }

    return ErrorType.INTERNAL_ERROR;
  }

  /**
   * Determine if error is recoverable
   */
  isRecoverable(error: Error): boolean {
    if (error instanceof LLMApiError) {
      // Auth errors are not recoverable
      if (error.statusCode === 401 || error.statusCode === 403) {
        return false;
      }
      // Rate limits and server errors are recoverable
      return true;
    }

    if (error instanceof LLMParseError || error instanceof LLMValidationError) {
      return true;
    }

    if (error.name === 'TimeoutError') {
      return true;
    }

    if (error.name === 'CapabilityNotFoundError') {
      return true;
    }

    if (error.name === 'RegistrationError') {
      return true;
    }

    return false;
  }

  /**
   * Get recovery suggestion based on error type
   */
  getRecoverySuggestion(error: Error): RecoveryStrategy {
    if (error instanceof LLMApiError) {
      // Auth errors need manual intervention
      if (error.statusCode === 401 || error.statusCode === 403) {
        return RecoveryStrategy.MANUAL_INTERVENTION;
      }
      // Rate limits and server errors can be retried
      return RecoveryStrategy.RETRY_CURRENT;
    }

    if (error instanceof LLMParseError || error instanceof LLMValidationError) {
      return RecoveryStrategy.RETRY_WITH_FEEDBACK;
    }

    if (error.name === 'TimeoutError') {
      return RecoveryStrategy.RETRY_CURRENT;
    }

    if (error.name === 'CapabilityNotFoundError') {
      return RecoveryStrategy.ROLLBACK_TO_ANALYSIS;
    }

    if (error.name === 'RegistrationError') {
      return RecoveryStrategy.RETRY_CURRENT;
    }

    return RecoveryStrategy.MANUAL_INTERVENTION;
  }

  /**
   * Extract additional details from error
   */
  private extractDetails(error: Error): Record<string, unknown> {
    const details: Record<string, unknown> = {
      errorName: error.name,
    };

    if (error instanceof LLMApiError) {
      details['provider'] = error.provider;
      details['statusCode'] = error.statusCode;
    }

    if (error instanceof LLMParseError) {
      details['rawContent'] = error.rawContent.substring(0, 500); // Truncate for safety
    }

    if (error instanceof LLMValidationError) {
      details['validationErrors'] = error.zodError.errors;
      details['rawContent'] = error.rawContent.substring(0, 500);
    }

    return details;
  }
}

/**
 * Factory function
 */
export function createErrorHandler(): ErrorHandler {
  return new ErrorHandler();
}
