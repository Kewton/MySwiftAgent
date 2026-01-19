/**
 * Error Types Unit Tests
 *
 * Issue #374: LLMValidationError for feedback loop support
 */

import { describe, it, expect } from 'vitest';
import {
  WorkflowCapabilityError,
  LLMValidationError,
  type CapabilityValidationError,
  type CapabilityValidationWarning,
  type CapabilityValidationResult,
} from '../../../../src/taskflowGeneratorAgent/types/errors.js';
import type { ValidationResult } from '../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('WorkflowCapabilityError', () => {
  it('should be the same class as LLMValidationError alias', () => {
    expect(WorkflowCapabilityError).toBe(LLMValidationError);
  });
});

describe('WorkflowCapabilityError (alias: LLMValidationError)', () => {
  const mockValidationResult: ValidationResult = {
    isValid: false,
    errors: [
      {
        code: 'MISSING_REQUIRED_PARAM',
        message: "Required parameter 'queries' is missing",
        path: 'steps[0].params.body.queries',
      },
      {
        code: 'PARAM_TYPE_MISMATCH',
        message: "Parameter 'num' should be number, got string",
        path: 'steps[0].params.body.num',
      },
    ],
    warnings: [
      {
        code: 'UNKNOWN_PARAM',
        message: "Unknown parameter 'query' for capability 'google_search'",
      },
    ],
  };

  const rawContent = JSON.stringify({
    workflow_name: 'test_workflow',
    steps: [
      {
        id: 'search_step',
        type: 'api_rest',
        config: { capability_id: 'google_search' },
        params: { body: { query: 'test' } },
      },
    ],
  });

  describe('constructor', () => {
    it('should create error with all properties', () => {
      const error = new WorkflowCapabilityError(
        'Validation failed',
        mockValidationResult,
        rawContent,
        1
      );

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(WorkflowCapabilityError);
      expect(error.name).toBe('WorkflowCapabilityError');
      expect(error.message).toBe('Validation failed');
      expect(error.validationResult).toBe(mockValidationResult);
      expect(error.rawContent).toBe(rawContent);
      expect(error.attempt).toBe(1);
    });

    it('should preserve error stack trace', () => {
      const error = new WorkflowCapabilityError(
        'Test error',
        mockValidationResult,
        rawContent,
        2
      );

      expect(error.stack).toBeDefined();
      expect(error.stack).toContain('WorkflowCapabilityError');
    });
  });

  describe('toFeedbackSummary', () => {
    it('should generate formatted feedback summary', () => {
      const error = new WorkflowCapabilityError(
        'Validation failed',
        mockValidationResult,
        rawContent,
        1
      );

      const summary = error.toFeedbackSummary();

      expect(summary).toContain('attempt 1');
      expect(summary).toContain('MISSING_REQUIRED_PARAM');
      expect(summary).toContain('PARAM_TYPE_MISMATCH');
      expect(summary).toContain("Required parameter 'queries' is missing");
    });

    it('should include all errors in summary', () => {
      const error = new WorkflowCapabilityError(
        'Validation failed',
        mockValidationResult,
        rawContent,
        2
      );

      const summary = error.toFeedbackSummary();
      const errorMatches = summary.match(/### Error:/g);

      expect(errorMatches).toHaveLength(2);
    });

    it('should handle empty errors array', () => {
      const emptyResult: ValidationResult = {
        isValid: false,
        errors: [],
        warnings: [],
      };

      const error = new WorkflowCapabilityError(
        'Validation failed',
        emptyResult,
        rawContent,
        1
      );

      const summary = error.toFeedbackSummary();

      expect(summary).toContain('attempt 1');
      expect(summary).toContain('Please fix');
    });

    it('should include attempt number in summary', () => {
      for (let attempt = 1; attempt <= 3; attempt++) {
        const error = new WorkflowCapabilityError(
          'Validation failed',
          mockValidationResult,
          rawContent,
          attempt
        );

        const summary = error.toFeedbackSummary();
        expect(summary).toContain(`attempt ${attempt}`);
      }
    });

    it('should include error paths when available', () => {
      const error = new WorkflowCapabilityError(
        'Validation failed',
        mockValidationResult,
        rawContent,
        1
      );

      const summary = error.toFeedbackSummary();

      expect(summary).toContain('steps[0].params.body.queries');
    });

    it('should handle errors without paths', () => {
      const resultWithoutPaths: ValidationResult = {
        isValid: false,
        errors: [
          {
            code: 'GENERAL_ERROR',
            message: 'Something went wrong',
          },
        ],
      };

      const error = new WorkflowCapabilityError(
        'Validation failed',
        resultWithoutPaths,
        rawContent,
        1
      );

      const summary = error.toFeedbackSummary();

      expect(summary).toContain('GENERAL_ERROR');
      expect(summary).toContain('N/A');
    });
  });
});

describe('CapabilityValidationError type', () => {
  it('should define all required fields', () => {
    const error: CapabilityValidationError = {
      code: 'MISSING_REQUIRED_PARAM',
      message: "Required parameter 'queries' is missing",
      step: 'search_step',
      capability: 'google_search',
      parameter: 'queries',
      suggestion: "Add 'queries' to params.body",
    };

    expect(error.code).toBe('MISSING_REQUIRED_PARAM');
    expect(error.message).toBeDefined();
    expect(error.step).toBe('search_step');
    expect(error.capability).toBe('google_search');
    expect(error.parameter).toBe('queries');
    expect(error.suggestion).toBeDefined();
  });

  it('should allow optional fields', () => {
    const minimalError: CapabilityValidationError = {
      code: 'ERROR',
      message: 'Error message',
      step: 'step_1',
    };

    expect(minimalError.capability).toBeUndefined();
    expect(minimalError.parameter).toBeUndefined();
    expect(minimalError.expected).toBeUndefined();
    expect(minimalError.actual).toBeUndefined();
    expect(minimalError.suggestion).toBeUndefined();
  });

  it('should support type mismatch fields', () => {
    const typeMismatchError: CapabilityValidationError = {
      code: 'PARAM_TYPE_MISMATCH',
      message: "Parameter 'num' should be number, got string",
      step: 'search_step',
      capability: 'google_search',
      parameter: 'num',
      expected: 'number',
      actual: 'string',
    };

    expect(typeMismatchError.expected).toBe('number');
    expect(typeMismatchError.actual).toBe('string');
  });
});

describe('CapabilityValidationWarning type', () => {
  it('should define warning fields', () => {
    const warning: CapabilityValidationWarning = {
      code: 'UNKNOWN_PARAM',
      message: "Unknown parameter 'query'",
      step: 'search_step',
      parameter: 'query',
    };

    expect(warning.code).toBe('UNKNOWN_PARAM');
    expect(warning.message).toBeDefined();
    expect(warning.step).toBe('search_step');
    expect(warning.parameter).toBe('query');
  });

  it('should allow minimal warning', () => {
    const minimalWarning: CapabilityValidationWarning = {
      code: 'WARNING',
      message: 'Warning message',
      step: 'step_1',
    };

    expect(minimalWarning.parameter).toBeUndefined();
  });
});

describe('CapabilityValidationResult type', () => {
  it('should combine errors and warnings', () => {
    const result: CapabilityValidationResult = {
      valid: false,
      errors: [
        {
          code: 'ERROR',
          message: 'Error',
          step: 'step_1',
        },
      ],
      warnings: [
        {
          code: 'WARNING',
          message: 'Warning',
          step: 'step_1',
        },
      ],
    };

    expect(result.valid).toBe(false);
    expect(result.errors).toHaveLength(1);
    expect(result.warnings).toHaveLength(1);
  });

  it('should support valid result with empty arrays', () => {
    const validResult: CapabilityValidationResult = {
      valid: true,
      errors: [],
      warnings: [],
    };

    expect(validResult.valid).toBe(true);
    expect(validResult.errors).toHaveLength(0);
    expect(validResult.warnings).toHaveLength(0);
  });
});
