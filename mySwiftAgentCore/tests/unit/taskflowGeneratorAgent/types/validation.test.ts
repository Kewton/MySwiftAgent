/**
 * Validation Types Unit Tests
 *
 * Issue #381: Extended validation types for error improvement
 */

import { describe, it, expect } from 'vitest';
import type {
  ErrorSuggestion,
  ValidationErrorContext,
  ComponentValidationError,
  SharedValidationCache,
  ValidationObserver,
  CircularReferenceInfo,
  PerformanceMetrics,
  ComponentValidationResult,
  EnhancedValidationContext,
  StepReference,
} from '../../../../../src/taskflowGeneratorAgent/types/validation.js';

describe('Validation Types', () => {
  describe('ErrorSuggestion', () => {
    it('should allow creating a valid ErrorSuggestion', () => {
      const suggestion: ErrorSuggestion = {
        message: 'Did you mean "result"?',
        availableOptions: ['result', 'status', 'data'],
        closestMatch: 'result',
        example: '$steps.step_001.result',
        documentationUrl: 'https://docs.example.com/fields',
      };

      expect(suggestion.message).toBe('Did you mean "result"?');
      expect(suggestion.availableOptions).toHaveLength(3);
      expect(suggestion.closestMatch).toBe('result');
    });

    it('should allow minimal ErrorSuggestion', () => {
      const suggestion: ErrorSuggestion = {
        message: 'Field not found',
      };

      expect(suggestion.message).toBe('Field not found');
      expect(suggestion.availableOptions).toBeUndefined();
    });
  });

  describe('ValidationErrorContext', () => {
    it('should allow creating a valid ValidationErrorContext', () => {
      const context: ValidationErrorContext = {
        sourceStep: 'step_001',
        targetStep: 'step_002',
        referencePath: '$steps.step_002.result',
        expectedType: 'string',
        actualType: 'undefined',
        circularPath: ['step_a', 'step_b', 'step_a'],
      };

      expect(context.sourceStep).toBe('step_001');
      expect(context.circularPath).toHaveLength(3);
    });

    it('should allow partial ValidationErrorContext', () => {
      const context: ValidationErrorContext = {
        sourceStep: 'step_001',
      };

      expect(context.sourceStep).toBe('step_001');
      expect(context.targetStep).toBeUndefined();
    });
  });

  describe('ComponentValidationError', () => {
    it('should extend ValidationError with additional fields', () => {
      const error: ComponentValidationError = {
        code: 'OUTPUT_FIELD_NOT_FOUND',
        message: 'Field "xyz" does not exist',
        path: 'steps.step_001.params',
        stepId: 'step_001',
        field: 'xyz',
        errorCode: 'OUTPUT_FIELD_NOT_FOUND',
        suggestion: {
          message: 'Did you mean "result"?',
          closestMatch: 'result',
        },
        context: {
          sourceStep: 'step_001',
          targetStep: 'step_002',
        },
      };

      expect(error.stepId).toBe('step_001');
      expect(error.suggestion?.closestMatch).toBe('result');
    });

    it('should support circular reference error code', () => {
      const error: ComponentValidationError = {
        code: 'CIRCULAR_REFERENCE_DETECTED',
        message: 'Circular reference detected',
        stepId: 'step_a',
        field: 'dependencies',
        errorCode: 'CIRCULAR_REFERENCE_DETECTED',
        context: {
          circularPath: ['step_a', 'step_b', 'step_a'],
        },
      };

      expect(error.errorCode).toBe('CIRCULAR_REFERENCE_DETECTED');
      expect(error.context?.circularPath).toBeDefined();
    });
  });

  describe('SharedValidationCache', () => {
    it('should have required cache maps', () => {
      const cache: SharedValidationCache = {
        capabilityMap: new Map(),
        stepMap: new Map(),
        responseSchemaMap: new Map(),
      };

      expect(cache.capabilityMap).toBeInstanceOf(Map);
      expect(cache.stepMap).toBeInstanceOf(Map);
      expect(cache.responseSchemaMap).toBeInstanceOf(Map);
    });
  });

  describe('ValidationObserver', () => {
    it('should define observer interface methods', () => {
      // Type check - ValidationObserver interface
      const observer: ValidationObserver = {
        onValidatorStart: (name: string) => {
          expect(typeof name).toBe('string');
        },
        onValidatorComplete: (name: string, result, durationMs: number) => {
          expect(typeof name).toBe('string');
          expect(typeof durationMs).toBe('number');
        },
        onError: (name: string, error: Error) => {
          expect(typeof name).toBe('string');
          expect(error).toBeInstanceOf(Error);
        },
      };

      // Test the observer
      observer.onValidatorStart('TestValidator');
      observer.onValidatorComplete('TestValidator', { isValid: true }, 100);
      observer.onError('TestValidator', new Error('test'));
    });
  });

  describe('CircularReferenceInfo', () => {
    it('should capture circular reference details', () => {
      const info: CircularReferenceInfo = {
        path: ['step_a', 'step_b', 'step_c', 'step_a'],
        severity: 'error',
        suggestion: 'Remove dependency from step_c to step_a',
      };

      expect(info.path).toHaveLength(4);
      expect(info.severity).toBe('error');
    });

    it('should support warning severity', () => {
      const info: CircularReferenceInfo = {
        path: ['a', 'b', 'a'],
        severity: 'warning',
        suggestion: 'Consider restructuring',
      };

      expect(info.severity).toBe('warning');
    });
  });

  describe('PerformanceMetrics', () => {
    it('should capture performance data', () => {
      const metrics: PerformanceMetrics = {
        totalDurationMs: 150,
        validatorMetrics: new Map([
          ['StepReferenceValidator', { durationMs: 50, errorsFound: 2 }],
          ['CircularReferenceValidator', { durationMs: 30, errorsFound: 0 }],
        ]),
        stepsAnalyzed: 10,
        referencesChecked: 25,
      };

      expect(metrics.totalDurationMs).toBe(150);
      expect(metrics.validatorMetrics.size).toBe(2);
      expect(metrics.stepsAnalyzed).toBe(10);
    });
  });

  describe('ComponentValidationResult', () => {
    it('should extend ValidationResult with component details', () => {
      const result: ComponentValidationResult = {
        isValid: false,
        errors: [
          {
            code: 'TEST',
            message: 'Test error',
            stepId: 'step_001',
            field: 'test',
            errorCode: 'OUTPUT_FIELD_NOT_FOUND',
          },
        ],
        warnings: [],
        componentErrors: new Map([
          [
            'step_001',
            [
              {
                code: 'TEST',
                message: 'Test error',
                stepId: 'step_001',
                field: 'test',
                errorCode: 'OUTPUT_FIELD_NOT_FOUND',
              },
            ],
          ],
        ]),
        circularReferences: [],
        performanceMetrics: {
          totalDurationMs: 100,
          validatorMetrics: new Map(),
          stepsAnalyzed: 5,
          referencesChecked: 10,
        },
      };

      expect(result.isValid).toBe(false);
      expect(result.componentErrors?.size).toBe(1);
      expect(result.performanceMetrics?.totalDurationMs).toBe(100);
    });
  });

  describe('EnhancedValidationContext', () => {
    it('should extend ValidationContext with additional options', () => {
      const context: EnhancedValidationContext = {
        capabilities: [],
        projectId: 'test-project',
        additionalContext: {
          enableTemplateValidation: true,
          enableSchemaCompatibilityCheck: true,
          enableCircularReferenceCheck: true,
          maxCircularDepth: 15,
          debugMode: true,
          verboseErrors: true,
          collectPerformanceMetrics: true,
        },
        sharedCache: {
          capabilityMap: new Map(),
          stepMap: new Map(),
          responseSchemaMap: new Map(),
        },
      };

      expect(context.additionalContext?.debugMode).toBe(true);
      expect(context.additionalContext?.maxCircularDepth).toBe(15);
      expect(context.sharedCache?.capabilityMap).toBeInstanceOf(Map);
    });
  });

  describe('StepReference', () => {
    it('should capture step reference details', () => {
      const ref: StepReference = {
        stepId: 'step_001',
        fieldName: 'result',
        fullPath: '$steps.step_001.result',
      };

      expect(ref.stepId).toBe('step_001');
      expect(ref.fieldName).toBe('result');
      expect(ref.fullPath).toBe('$steps.step_001.result');
    });
  });
});
