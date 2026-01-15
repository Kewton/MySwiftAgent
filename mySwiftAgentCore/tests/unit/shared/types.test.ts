/**
 * Type Definitions Unit Tests
 *
 * Tests for Zod schemas and type utilities
 */

import { describe, it, expect } from 'vitest';
import {
  StepErrorSchema,
  RecoveryActionSchema,
  StepResultSchema,
  WorkflowExecutionResultSchema,
  CapabilitySchema,
  CapabilityInvocationRequestSchema,
  CoreErrorSchema,
  FieldErrorSchema,
  ErrorCodes,
  createCoreError,
  createHttpErrorResponse,
} from '../../../src/shared/types/index.js';

describe('Workflow Types - Zod Schemas', () => {
  describe('StepErrorSchema', () => {
    it('should validate a valid StepError', () => {
      const data = {
        stepId: 'step_1',
        stepName: 'Test Step',
        errorCode: 'ERR_001',
        errorMessage: 'Something went wrong',
        timestamp: new Date(),
        recoverable: true,
      };

      const result = StepErrorSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should include optional context', () => {
      const data = {
        stepId: 'step_1',
        stepName: 'Test Step',
        errorCode: 'ERR_001',
        errorMessage: 'Something went wrong',
        timestamp: new Date(),
        recoverable: false,
        context: { key: 'value' },
      };

      const result = StepErrorSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });

  describe('RecoveryActionSchema', () => {
    it('should validate retry action', () => {
      const data = {
        type: 'retry',
        stepId: 'step_1',
        maxRetries: 3,
        reason: 'Transient failure',
      };

      const result = RecoveryActionSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should validate skip action', () => {
      const data = {
        type: 'skip',
        stepId: 'step_1',
        reason: 'Non-critical step',
      };

      const result = RecoveryActionSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should validate fallback action with value', () => {
      const data = {
        type: 'fallback',
        stepId: 'step_1',
        fallbackValue: { default: 'value' },
        reason: 'Using default value',
      };

      const result = RecoveryActionSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should reject invalid type', () => {
      const data = {
        type: 'invalid_type',
        stepId: 'step_1',
        reason: 'Test',
      };

      const result = RecoveryActionSchema.safeParse(data);
      expect(result.success).toBe(false);
    });
  });

  describe('StepResultSchema', () => {
    it('should validate successful step result', () => {
      const data = {
        stepId: 'step_1',
        stepName: 'Test Step',
        status: 'success',
        output: { result: 'done' },
        startTime: new Date(),
        endTime: new Date(),
        durationMs: 100,
      };

      const result = StepResultSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should validate failed step result with error', () => {
      const data = {
        stepId: 'step_1',
        stepName: 'Test Step',
        status: 'failed',
        error: {
          stepId: 'step_1',
          stepName: 'Test Step',
          errorCode: 'ERR_001',
          errorMessage: 'Failed',
          timestamp: new Date(),
          recoverable: false,
        },
        startTime: new Date(),
        endTime: new Date(),
        durationMs: 50,
      };

      const result = StepResultSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should validate partial_success status', () => {
      const data = {
        stepId: 'step_1',
        stepName: 'Test Step',
        status: 'partial_success',
        startTime: new Date(),
        endTime: new Date(),
        durationMs: 200,
      };

      const result = StepResultSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });

  describe('WorkflowExecutionResultSchema', () => {
    it('should validate complete workflow result', () => {
      const data = {
        workflowId: 'wf_001',
        workflowName: 'Test Workflow',
        status: 'success',
        stepResults: [],
        errors: [],
        recoveryActions: [],
        startTime: new Date(),
        endTime: new Date(),
        durationMs: 500,
      };

      const result = WorkflowExecutionResultSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });
});

describe('Capability Types - Zod Schemas', () => {
  describe('CapabilitySchema', () => {
    it('should validate a valid capability', () => {
      const data = {
        id: 'cap_001',
        name: 'Test Capability',
        description: 'A test capability',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [
          {
            name: 'input',
            type: 'string',
            required: true,
            description: 'Input parameter',
          },
        ],
        returnType: 'object',
      };

      const result = CapabilitySchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should validate capability with optional fields', () => {
      const data = {
        id: 'cap_001',
        name: 'Test Capability',
        description: 'A test capability',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
        tags: ['test', 'example'],
        metadata: { author: 'test' },
      };

      const result = CapabilitySchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should reject invalid status', () => {
      const data = {
        id: 'cap_001',
        name: 'Test Capability',
        description: 'A test capability',
        version: '1.0.0',
        status: 'invalid_status',
        category: 'test',
        parameters: [],
        returnType: 'string',
      };

      const result = CapabilitySchema.safeParse(data);
      expect(result.success).toBe(false);
    });
  });

  describe('CapabilityInvocationRequestSchema', () => {
    it('should validate invocation request', () => {
      const data = {
        capabilityId: 'cap_001',
        parameters: { input: 'test' },
      };

      const result = CapabilityInvocationRequestSchema.safeParse(data);
      expect(result.success).toBe(true);
    });

    it('should include optional fields', () => {
      const data = {
        capabilityId: 'cap_001',
        parameters: { input: 'test' },
        context: { userId: '123' },
        timeout: 5000,
      };

      const result = CapabilityInvocationRequestSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });
});

describe('Error Types', () => {
  describe('FieldErrorSchema', () => {
    it('should validate field error', () => {
      const data = {
        field: 'email',
        message: 'Invalid email format',
        value: 'not-an-email',
        constraint: 'email',
      };

      const result = FieldErrorSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });

  describe('CoreErrorSchema', () => {
    it('should validate core error', () => {
      const data = {
        code: 'VAL_INVALID_INPUT',
        message: 'Validation failed',
        category: 'validation',
        severity: 'medium',
        timestamp: new Date(),
      };

      const result = CoreErrorSchema.safeParse(data);
      expect(result.success).toBe(true);
    });
  });

  describe('ErrorCodes', () => {
    it('should have validation error codes', () => {
      expect(ErrorCodes.VAL_INVALID_INPUT).toBe('VAL_INVALID_INPUT');
      expect(ErrorCodes.VAL_MISSING_REQUIRED).toBe('VAL_MISSING_REQUIRED');
    });

    it('should have authentication error codes', () => {
      expect(ErrorCodes.AUTH_MISSING_TOKEN).toBe('AUTH_MISSING_TOKEN');
      expect(ErrorCodes.AUTH_INVALID_TOKEN).toBe('AUTH_INVALID_TOKEN');
    });

    it('should have execution error codes', () => {
      expect(ErrorCodes.EXEC_WORKFLOW_FAILED).toBe('EXEC_WORKFLOW_FAILED');
      expect(ErrorCodes.EXEC_TIMEOUT).toBe('EXEC_TIMEOUT');
    });
  });

  describe('createCoreError', () => {
    it('should create CoreError with all fields', () => {
      const error = createCoreError(
        ErrorCodes.VAL_INVALID_INPUT,
        'Test error',
        'validation',
        'medium',
        { field: 'test' }
      );

      expect(error.code).toBe('VAL_INVALID_INPUT');
      expect(error.message).toBe('Test error');
      expect(error.category).toBe('validation');
      expect(error.severity).toBe('medium');
      expect(error.details?.field).toBe('test');
      expect(error.timestamp).toBeInstanceOf(Date);
    });
  });

  describe('createHttpErrorResponse', () => {
    it('should create HTTP error response', () => {
      const coreError = createCoreError(
        ErrorCodes.AUTH_INVALID_TOKEN,
        'Invalid token',
        'authentication',
        'high'
      );

      const response = createHttpErrorResponse(coreError, 'req_123');

      expect(response.error.code).toBe('AUTH_INVALID_TOKEN');
      expect(response.error.message).toBe('Invalid token');
      expect(response.error.requestId).toBe('req_123');
      expect(response.timestamp).toBeDefined();
    });
  });
});
