/**
 * ErrorHandler Unit Tests
 *
 * Issue #364: Error handling and recovery strategy
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ErrorHandler,
  createErrorHandler,
} from '../../../../src/taskflowGeneratorAgent/recovery/ErrorHandler.js';
import {
  ErrorType,
  RecoveryStrategy,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';
import {
  LLMApiError,
  LLMParseError,
  LLMValidationError,
  WorkflowValidationError,
} from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import { z } from 'zod';

describe('ErrorHandler', () => {
  let handler: ErrorHandler;

  beforeEach(() => {
    handler = new ErrorHandler();
  });

  describe('handle', () => {
    it('should handle LLMApiError with rate limit', async () => {
      const error = new LLMApiError('Rate limit exceeded', 'anthropic', 429);
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.task_id).toBe('task_001');
      expect(result.error_type).toBe(ErrorType.LLM_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_CURRENT);
    });

    it('should handle LLMApiError with server error', async () => {
      const error = new LLMApiError('Internal server error', 'openai', 500);
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.LLM_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_CURRENT);
    });

    it('should handle LLMApiError with auth error', async () => {
      const error = new LLMApiError('Unauthorized', 'anthropic', 401);
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.LLM_ERROR);
      expect(result.recoverable).toBe(false);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.MANUAL_INTERVENTION);
    });

    it('should handle LLMParseError', async () => {
      const error = new LLMParseError('Invalid JSON', 'raw content');
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.VALIDATION_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_WITH_FEEDBACK);
    });

    it('should handle LLMValidationError', async () => {
      const zodError = new z.ZodError([
        {
          code: 'invalid_type',
          expected: 'string',
          received: 'number',
          path: ['workflow_name'],
          message: 'Expected string, received number',
        },
      ]);
      const error = new LLMValidationError('Schema mismatch', 'raw', zodError);
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.VALIDATION_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_WITH_FEEDBACK);
      expect(result.details).toBeDefined();
    });

    it('should handle WorkflowValidationError (Issue #367)', async () => {
      const validationResult = {
        isValid: false,
        errors: [
          { code: 'SECURITY_001', message: 'Potential shell injection detected', path: 'steps[0].params.template' },
        ],
        warnings: [
          { code: 'WARN_001', message: 'Consider using more specific capability' },
        ],
      };
      const workflow = {
        workflow_name: 'test_workflow',
        description: 'Test workflow',
        steps: [],
      };
      const error = new WorkflowValidationError(
        'Validation failed: Potential shell injection detected',
        workflow,
        validationResult
      );
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.VALIDATION_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_WITH_FEEDBACK);
      expect(result.details).toBeDefined();
      expect(result.details?.['validationErrors']).toEqual(validationResult.errors);
      expect(result.details?.['validationWarnings']).toEqual(validationResult.warnings);
    });

    it('should handle timeout error', async () => {
      const error = new Error('Timeout exceeded');
      error.name = 'TimeoutError';
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.TIMEOUT_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_CURRENT);
    });

    it('should handle CapabilityNotFoundError', async () => {
      const error = new Error('Capability not found: weather_api');
      error.name = 'CapabilityNotFoundError';
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.CAPABILITY_NOT_FOUND);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.ROLLBACK_TO_ANALYSIS);
    });

    it('should handle RegistrationError', async () => {
      const error = new Error('Failed to register workflow');
      error.name = 'RegistrationError';
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.REGISTRATION_ERROR);
      expect(result.recoverable).toBe(true);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.RETRY_CURRENT);
    });

    it('should handle unknown error', async () => {
      const error = new Error('Unknown error');
      const context = { task_id: 'task_001' };

      const result = await handler.handle(error, context);

      expect(result.error_type).toBe(ErrorType.INTERNAL_ERROR);
      expect(result.recoverable).toBe(false);
      expect(result.recovery_suggestion).toBe(RecoveryStrategy.MANUAL_INTERVENTION);
    });
  });

  describe('isRecoverable', () => {
    it('should return true for rate limit errors', () => {
      const error = new LLMApiError('Rate limit', 'anthropic', 429);

      expect(handler.isRecoverable(error)).toBe(true);
    });

    it('should return false for auth errors', () => {
      const error = new LLMApiError('Unauthorized', 'anthropic', 401);

      expect(handler.isRecoverable(error)).toBe(false);
    });

    it('should return true for parse errors', () => {
      const error = new LLMParseError('Parse failed', 'content');

      expect(handler.isRecoverable(error)).toBe(true);
    });

    it('should return true for workflow validation errors (Issue #367)', () => {
      const error = new WorkflowValidationError(
        'Validation failed',
        { workflow_name: 'test' },
        { isValid: false, errors: [{ code: 'ERR', message: 'Error' }] }
      );

      expect(handler.isRecoverable(error)).toBe(true);
    });
  });

  describe('getRecoverySuggestion', () => {
    it('should suggest RETRY_CURRENT for transient errors', () => {
      const error = new LLMApiError('Rate limit', 'anthropic', 429);

      expect(handler.getRecoverySuggestion(error)).toBe(RecoveryStrategy.RETRY_CURRENT);
    });

    it('should suggest RETRY_WITH_FEEDBACK for validation errors', () => {
      const error = new LLMParseError('Parse failed', 'content');

      expect(handler.getRecoverySuggestion(error)).toBe(
        RecoveryStrategy.RETRY_WITH_FEEDBACK
      );
    });

    it('should suggest ROLLBACK_TO_ANALYSIS for capability errors', () => {
      const error = new Error('Capability not found');
      error.name = 'CapabilityNotFoundError';

      expect(handler.getRecoverySuggestion(error)).toBe(
        RecoveryStrategy.ROLLBACK_TO_ANALYSIS
      );
    });

    it('should suggest RETRY_WITH_FEEDBACK for workflow validation errors (Issue #367)', () => {
      const error = new WorkflowValidationError(
        'Validation failed',
        { workflow_name: 'test' },
        { isValid: false, errors: [{ code: 'ERR', message: 'Error' }] }
      );

      expect(handler.getRecoverySuggestion(error)).toBe(
        RecoveryStrategy.RETRY_WITH_FEEDBACK
      );
    });
  });
});

describe('createErrorHandler', () => {
  it('should create ErrorHandler instance', () => {
    const handler = createErrorHandler();

    expect(handler).toBeInstanceOf(ErrorHandler);
  });
});
