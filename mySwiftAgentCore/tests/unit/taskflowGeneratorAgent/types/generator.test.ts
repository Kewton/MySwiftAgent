/**
 * Generator Types Unit Tests
 *
 * Issue #364: Type definitions for taskflowGeneratorAgent
 * Tests types according to OpenAPI specification: docs/spec/api/taskflow-generator-api.yaml
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  RecoveryStrategy,
  ErrorType,
  RecoveryStrategySchema,
  ErrorTypeSchema,
  TaskGenerationRequestSchema,
  BatchGenerationRequestSchema,
  BatchGenerationResponseSchema,
  TaskErrorSchema,
  TraceContextSchema,
  CapabilitySchema,
  GenerationOptionsSchema,
  ValidationResultSchema,
  WorkflowGenerationResultSchema,
  type TaskGenerationRequest,
  type BatchGenerationRequest,
  type BatchGenerationResponse,
  type TaskError,
  type TraceContext,
  type Capability,
  type GenerationOptions,
  type ValidationResult,
  type WorkflowGenerationResult,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('Generator Types', () => {
  describe('RecoveryStrategy enum', () => {
    it('should have all required values from OpenAPI spec', () => {
      expect(RecoveryStrategy.RETRY_CURRENT).toBe('RETRY_CURRENT');
      expect(RecoveryStrategy.RETRY_WITH_FEEDBACK).toBe('RETRY_WITH_FEEDBACK');
      expect(RecoveryStrategy.ROLLBACK_TO_ANALYSIS).toBe('ROLLBACK_TO_ANALYSIS');
      expect(RecoveryStrategy.UPDATE_CAPABILITIES).toBe('UPDATE_CAPABILITIES');
      expect(RecoveryStrategy.MANUAL_INTERVENTION).toBe('MANUAL_INTERVENTION');
    });

    it('should validate valid RecoveryStrategy values', () => {
      expect(RecoveryStrategySchema.safeParse('RETRY_CURRENT').success).toBe(true);
      expect(RecoveryStrategySchema.safeParse('RETRY_WITH_FEEDBACK').success).toBe(true);
      expect(RecoveryStrategySchema.safeParse('ROLLBACK_TO_ANALYSIS').success).toBe(true);
      expect(RecoveryStrategySchema.safeParse('UPDATE_CAPABILITIES').success).toBe(true);
      expect(RecoveryStrategySchema.safeParse('MANUAL_INTERVENTION').success).toBe(true);
    });

    it('should reject invalid RecoveryStrategy values', () => {
      expect(RecoveryStrategySchema.safeParse('INVALID').success).toBe(false);
      expect(RecoveryStrategySchema.safeParse('').success).toBe(false);
      expect(RecoveryStrategySchema.safeParse(123).success).toBe(false);
    });
  });

  describe('ErrorType enum', () => {
    it('should have all required values from OpenAPI spec', () => {
      expect(ErrorType.VALIDATION_ERROR).toBe('VALIDATION_ERROR');
      expect(ErrorType.LLM_ERROR).toBe('LLM_ERROR');
      expect(ErrorType.TIMEOUT_ERROR).toBe('TIMEOUT_ERROR');
      expect(ErrorType.REGISTRATION_ERROR).toBe('REGISTRATION_ERROR');
      expect(ErrorType.CAPABILITY_NOT_FOUND).toBe('CAPABILITY_NOT_FOUND');
      expect(ErrorType.INTERNAL_ERROR).toBe('INTERNAL_ERROR');
    });

    it('should validate valid ErrorType values', () => {
      expect(ErrorTypeSchema.safeParse('VALIDATION_ERROR').success).toBe(true);
      expect(ErrorTypeSchema.safeParse('LLM_ERROR').success).toBe(true);
      expect(ErrorTypeSchema.safeParse('TIMEOUT_ERROR').success).toBe(true);
    });

    it('should reject invalid ErrorType values', () => {
      expect(ErrorTypeSchema.safeParse('INVALID').success).toBe(false);
    });
  });

  describe('TaskGenerationRequest', () => {
    it('should validate a complete request', () => {
      const request: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Test Task',
        description: 'A test task description',
        interface: {
          input: { user_id: 'string' },
          output: { result: 'string' },
        },
      };

      const result = TaskGenerationRequestSchema.safeParse(request);
      expect(result.success).toBe(true);
    });

    it('should validate request with optional fields', () => {
      const request: TaskGenerationRequest = {
        task_id: 'task_001',
        task_master_id: 'tm_001',
        name: 'Test Task',
        description: 'A test task description',
        dependencies: ['task_000'],
        interface: {
          input: { user_id: 'string' },
          output: { result: 'string' },
        },
      };

      const result = TaskGenerationRequestSchema.safeParse(request);
      expect(result.success).toBe(true);
    });

    it('should reject request without required fields', () => {
      const invalidRequest = {
        task_id: 'task_001',
        // missing name, description, interface
      };

      const result = TaskGenerationRequestSchema.safeParse(invalidRequest);
      expect(result.success).toBe(false);
    });
  });

  describe('Capability', () => {
    it('should validate a complete capability', () => {
      const capability: Capability = {
        id: 'user_api',
        name: 'User API',
        description: 'User information API',
        category: 'api',
        status: 'available',
        parameters: [
          { name: 'user_id', type: 'string', required: true },
        ],
      };

      const result = CapabilitySchema.safeParse(capability);
      expect(result.success).toBe(true);
    });

    it('should validate all category types', () => {
      const categories = ['api', 'llm', 'transform', 'utility'] as const;

      for (const category of categories) {
        const capability: Capability = {
          id: 'test',
          name: 'Test',
          category,
          status: 'available',
        };
        const result = CapabilitySchema.safeParse(capability);
        expect(result.success).toBe(true);
      }
    });

    it('should validate all status types', () => {
      const statuses = ['available', 'unavailable', 'deprecated'] as const;

      for (const status of statuses) {
        const capability: Capability = {
          id: 'test',
          name: 'Test',
          category: 'api',
          status,
        };
        const result = CapabilitySchema.safeParse(capability);
        expect(result.success).toBe(true);
      }
    });
  });

  describe('TraceContext', () => {
    it('should validate a complete trace context', () => {
      const context: TraceContext = {
        trace_id: 'trace_001',
        parent_span_id: 'span_001',
        user_id: 'user_001',
        session_id: 'session_001',
        metadata: { key: 'value' },
      };

      const result = TraceContextSchema.safeParse(context);
      expect(result.success).toBe(true);
    });

    it('should validate trace context with only optional fields', () => {
      const context: TraceContext = {};

      const result = TraceContextSchema.safeParse(context);
      expect(result.success).toBe(true);
    });
  });

  describe('GenerationOptions', () => {
    it('should validate options with defaults', () => {
      const options: GenerationOptions = {};

      const result = GenerationOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should validate options with all fields', () => {
      const options: GenerationOptions = {
        max_concurrency: 5,
        timeout_per_task_ms: 30000,
        validate_before_register: true,
        max_retries: 3,
      };

      const result = GenerationOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should reject invalid max_concurrency', () => {
      const options = {
        max_concurrency: 0, // minimum is 1
      };

      const result = GenerationOptionsSchema.safeParse(options);
      expect(result.success).toBe(false);
    });

    it('should reject max_concurrency over limit', () => {
      const options = {
        max_concurrency: 21, // maximum is 20
      };

      const result = GenerationOptionsSchema.safeParse(options);
      expect(result.success).toBe(false);
    });
  });

  describe('BatchGenerationRequest', () => {
    it('should validate a complete batch request', () => {
      const request: BatchGenerationRequest = {
        tasks: [
          {
            task_id: 'task_001',
            name: 'Test Task',
            description: 'A test task',
            interface: { input: {}, output: {} },
          },
        ],
        capabilities: [
          {
            id: 'api_1',
            name: 'API 1',
            category: 'api',
            status: 'available',
          },
        ],
        project_id: 'test_project',
      };

      const result = BatchGenerationRequestSchema.safeParse(request);
      expect(result.success).toBe(true);
    });

    it('should validate batch request with optional fields', () => {
      const request: BatchGenerationRequest = {
        tasks: [],
        capabilities: [],
        project_id: 'test_project',
        options: {
          max_concurrency: 3,
        },
        trace_context: {
          trace_id: 'trace_001',
        },
      };

      const result = BatchGenerationRequestSchema.safeParse(request);
      expect(result.success).toBe(true);
    });
  });

  describe('TaskError', () => {
    it('should validate a task error', () => {
      const error: TaskError = {
        task_id: 'task_001',
        error_type: ErrorType.VALIDATION_ERROR,
        message: 'Validation failed',
        recoverable: true,
        recovery_suggestion: RecoveryStrategy.RETRY_CURRENT,
      };

      const result = TaskErrorSchema.safeParse(error);
      expect(result.success).toBe(true);
    });

    it('should validate task error without recovery suggestion', () => {
      const error: TaskError = {
        task_id: 'task_001',
        error_type: ErrorType.INTERNAL_ERROR,
        message: 'Internal error',
        recoverable: false,
      };

      const result = TaskErrorSchema.safeParse(error);
      expect(result.success).toBe(true);
    });

    it('should validate task error with details', () => {
      const error: TaskError = {
        task_id: 'task_001',
        error_type: ErrorType.LLM_ERROR,
        message: 'Rate limit exceeded',
        recoverable: true,
        recovery_suggestion: RecoveryStrategy.RETRY_CURRENT,
        details: {
          retry_after: 60,
          rate_limit_remaining: 0,
        },
      };

      const result = TaskErrorSchema.safeParse(error);
      expect(result.success).toBe(true);
    });
  });

  describe('ValidationResult', () => {
    it('should validate a successful validation result', () => {
      const validationResult: ValidationResult = {
        isValid: true,
        errors: [],
        warnings: [],
      };

      const result = ValidationResultSchema.safeParse(validationResult);
      expect(result.success).toBe(true);
    });

    it('should validate a failed validation result', () => {
      const validationResult: ValidationResult = {
        isValid: false,
        errors: [
          {
            code: 'INVALID_STEP',
            message: 'Step reference not found',
            path: 'steps[0].params.depends_on',
          },
        ],
        warnings: [
          {
            code: 'DEPRECATED_PARAM',
            message: 'Parameter is deprecated',
          },
        ],
      };

      const result = ValidationResultSchema.safeParse(validationResult);
      expect(result.success).toBe(true);
    });
  });

  describe('WorkflowGenerationResult', () => {
    it('should validate a successful generation result', () => {
      const genResult: WorkflowGenerationResult = {
        workflow_name: 'test_workflow',
        registered: true,
        workflow_id: 'wf_001',
        validation_result: {
          isValid: true,
          errors: [],
          warnings: [],
        },
      };

      const result = WorkflowGenerationResultSchema.safeParse(genResult);
      expect(result.success).toBe(true);
    });

    it('should validate a minimal generation result', () => {
      const genResult: WorkflowGenerationResult = {
        workflow_name: 'test_workflow',
        registered: false,
      };

      const result = WorkflowGenerationResultSchema.safeParse(genResult);
      expect(result.success).toBe(true);
    });
  });

  describe('BatchGenerationResponse', () => {
    it('should validate a successful response', () => {
      const response: BatchGenerationResponse = {
        success: true,
        workflows: {
          task_001: {
            workflow_name: 'task_001_workflow',
            registered: true,
            workflow_id: 'wf_001',
          },
        },
        failed_tasks: [],
        trace_url: 'https://langfuse.example.com/trace/123',
      };

      const result = BatchGenerationResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });

    it('should validate a partial success response', () => {
      const response: BatchGenerationResponse = {
        success: false,
        workflows: {
          task_001: {
            workflow_name: 'task_001_workflow',
            registered: true,
          },
        },
        failed_tasks: [
          {
            task_id: 'task_002',
            error_type: ErrorType.VALIDATION_ERROR,
            message: 'Validation failed',
            recoverable: true,
            recovery_suggestion: RecoveryStrategy.RETRY_CURRENT,
          },
        ],
      };

      const result = BatchGenerationResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });
  });
});
