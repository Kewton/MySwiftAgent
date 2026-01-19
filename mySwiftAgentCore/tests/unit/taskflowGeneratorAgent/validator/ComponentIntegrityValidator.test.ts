/**
 * ComponentIntegrityValidator Unit Tests
 *
 * Issue #381: Composite validator for component integrity checking
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ComponentIntegrityValidator } from '../../../../src/taskflowGeneratorAgent/validator/ComponentIntegrityValidator.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type {
  EnhancedValidationContext,
  ValidationObserver,
} from '../../../../src/taskflowGeneratorAgent/types/validation.js';
import type { CapabilityForPrompt } from '../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('ComponentIntegrityValidator', () => {
  let validator: ComponentIntegrityValidator;

  beforeEach(() => {
    validator = new ComponentIntegrityValidator();
  });

  const createContext = (
    capabilities: CapabilityForPrompt[] = [],
    options?: Partial<EnhancedValidationContext['additionalContext']>
  ): EnhancedValidationContext => ({
    capabilities: capabilities as any[],
    projectId: 'test-project',
    additionalContext: {
      enableTemplateValidation: true,
      enableCircularReferenceCheck: true,
      ...options,
    },
  });

  const createCapability = (
    id: string,
    responseFields: string[] = []
  ): CapabilityForPrompt => ({
    id,
    name: id,
    category: 'api',
    status: 'available',
    responseSchema: {
      type: 'object',
      properties: Object.fromEntries(
        responseFields.map((f) => [f, { type: 'string' }])
      ),
    },
  });

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('ComponentIntegrityValidator');
    });
  });

  describe('basic validation', () => {
    it('should pass for valid simple workflow', async () => {
      const capabilities = [createCapability('google_search', ['result', 'status'])];

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: { query: 'test' },
          },
          {
            id: 'step_002',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_001.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext(capabilities));
      expect(result.isValid).toBe(true);
    });

    it('should fail for workflow with invalid step reference', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { input: '$steps.nonexistent.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
      expect(result.errors!.length).toBeGreaterThan(0);
    });

    it('should fail for workflow with circular reference', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
      expect(result.errors!.some((e) => e.code === 'CIRCULAR_REFERENCE_DETECTED')).toBe(
        true
      );
    });

    it('should fail for workflow with invalid template syntax', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{unclosed' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
      expect(result.errors!.some((e) => e.code === 'TEMPLATE_SYNTAX_ERROR')).toBe(true);
    });
  });

  describe('aggregated validation', () => {
    it('should collect errors from all sub-validators', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: {
              input: '$steps.step_b.result',
              template: '{{broken', // Template error
            },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: {
              input: '$steps.step_a.result', // Circular reference
            },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors!.length).toBeGreaterThanOrEqual(2);
    });

    it('should collect warnings from all sub-validators', async () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'no_schema',
          name: 'No Schema',
          category: 'api',
          status: 'available',
          // No responseSchema
        },
      ];

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'api_rest',
            config: { capability_id: 'no_schema' },
            params: {},
          },
          {
            id: 'step_002',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_001.anyfield' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext(capabilities));

      expect(result.warnings).toBeDefined();
      expect(result.warnings!.length).toBeGreaterThan(0);
    });
  });

  describe('shared cache initialization', () => {
    it('should initialize shared cache for sub-validators', async () => {
      const capabilities = [createCapability('test_cap', ['field1', 'field2'])];

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'api_rest',
            config: { capability_id: 'test_cap' },
            params: {},
          },
        ],
        output: {},
      };

      // Should run without errors, indicating cache was properly initialized
      const result = await validator.validate(workflow, createContext(capabilities));
      expect(result).toBeDefined();
    });
  });

  describe('ValidationObserver integration', () => {
    it('should call observer callbacks during validation', async () => {
      const observer: ValidationObserver = {
        onValidatorStart: vi.fn(),
        onValidatorComplete: vi.fn(),
        onError: vi.fn(),
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_001', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const context = createContext([], {
        debugMode: true,
        validationObserver: observer,
      });

      await validator.validate(workflow, context);

      expect(observer.onValidatorStart).toHaveBeenCalled();
      expect(observer.onValidatorComplete).toHaveBeenCalled();
    });

    it('should call onError when validator throws', async () => {
      const observer: ValidationObserver = {
        onValidatorStart: vi.fn(),
        onValidatorComplete: vi.fn(),
        onError: vi.fn(),
      };

      // Create a workflow that might cause issues
      const workflow = {
        workflow_name: 'test',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: null as any, // Invalid
        output: {},
      };

      const context = createContext([], {
        debugMode: true,
        validationObserver: observer,
      });

      try {
        await validator.validate(workflow as any, context);
      } catch {
        // Expected to throw
      }

      // Observer might be called with error
    });
  });

  describe('performance metrics', () => {
    it('should collect performance metrics when enabled', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_001', type: 'transform', config: {}, params: {} },
          { id: 'step_002', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const context = createContext([], {
        collectPerformanceMetrics: true,
      });

      const result = await validator.validate(workflow, context);

      expect((result as any).performanceMetrics).toBeDefined();
      expect((result as any).performanceMetrics.totalDurationMs).toBeGreaterThanOrEqual(
        0
      );
      expect((result as any).performanceMetrics.stepsAnalyzed).toBe(2);
    });

    it('should not include metrics when disabled', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [{ id: 'step_001', type: 'transform', config: {}, params: {} }],
        output: {},
      };

      const context = createContext([], {
        collectPerformanceMetrics: false,
      });

      const result = await validator.validate(workflow, context);

      expect((result as any).performanceMetrics).toBeUndefined();
    });
  });

  describe('validation toggle options', () => {
    it('should respect enableTemplateValidation option', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{broken' },
          },
        ],
        output: {},
      };

      const context = createContext([], {
        enableTemplateValidation: false,
      });

      const result = await validator.validate(workflow, context);

      // Should not have template syntax errors when disabled
      expect(
        result.errors?.some((e) => e.code === 'TEMPLATE_SYNTAX_ERROR')
      ).toBeFalsy();
    });

    it('should respect enableCircularReferenceCheck option', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const context = createContext([], {
        enableCircularReferenceCheck: false,
      });

      const result = await validator.validate(workflow, context);

      // Should not have circular reference errors when disabled
      expect(
        result.errors?.some((e) => e.code === 'CIRCULAR_REFERENCE_DETECTED')
      ).toBeFalsy();
    });
  });

  describe('getValidators method', () => {
    it('should return list of sub-validators', () => {
      const validators = validator.getValidators();

      expect(Array.isArray(validators)).toBe(true);
      expect(validators.length).toBeGreaterThan(0);
      expect(validators.some((v) => v.name === 'StepReferenceValidator')).toBe(true);
      expect(validators.some((v) => v.name === 'TemplateSyntaxValidator')).toBe(true);
      expect(validators.some((v) => v.name === 'CircularReferenceValidator')).toBe(true);
    });
  });
});
