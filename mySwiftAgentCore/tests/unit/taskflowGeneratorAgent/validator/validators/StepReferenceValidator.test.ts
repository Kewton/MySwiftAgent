/**
 * StepReferenceValidator Unit Tests
 *
 * Issue #381: Step reference validation with improved error messages
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { StepReferenceValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/StepReferenceValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { EnhancedValidationContext } from '../../../../../src/taskflowGeneratorAgent/types/validation.js';
import type { CapabilityForPrompt } from '../../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('StepReferenceValidator', () => {
  let validator: StepReferenceValidator;

  beforeEach(() => {
    validator = new StepReferenceValidator();
  });

  const createContext = (
    capabilities: CapabilityForPrompt[] = []
  ): EnhancedValidationContext => ({
    capabilities: capabilities as any[],
    projectId: 'test-project',
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
      expect(validator.name).toBe('StepReferenceValidator');
    });
  });

  describe('valid references', () => {
    it('should pass for workflow without step references', async () => {
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
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should pass for valid step reference with known field', async () => {
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
  });

  describe('step existence validation', () => {
    it('should fail for reference to non-existent step', async () => {
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
      expect(result.errors).toHaveLength(1);
      expect(result.errors![0].code).toBe('STEP_REFERENCE_NOT_FOUND');
    });

    it('should include suggestion with closest match', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_001', type: 'transform', config: {}, params: {} },
          { id: 'step_002', type: 'transform', config: {}, params: {} },
          {
            id: 'step_003',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_01.result' }, // typo
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      const error = result.errors![0] as any;
      expect(error.suggestion).toBeDefined();
      expect(error.suggestion.closestMatch).toBe('step_001');
      expect(error.suggestion.availableOptions).toContain('step_001');
    });
  });

  describe('field existence validation', () => {
    it('should fail for reference to non-existent field', async () => {
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
            params: { input: '$steps.step_001.nonexistent' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext(capabilities));

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('OUTPUT_FIELD_NOT_FOUND');
    });

    it('should include available fields in error', async () => {
      const capabilities = [
        createCapability('google_search', ['result', 'status', 'data']),
      ];

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {},
          },
          {
            id: 'step_002',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_001.resul' }, // typo
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext(capabilities));

      expect(result.isValid).toBe(false);
      const error = result.errors![0] as any;
      expect(error.suggestion).toBeDefined();
      expect(error.suggestion.availableOptions).toContain('result');
      expect(error.suggestion.closestMatch).toBe('result');
    });
  });

  describe('warning for missing schema', () => {
    it('should warn when capability has no response schema', async () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'no_schema_capability',
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
            config: { capability_id: 'no_schema_capability' },
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

      // Should pass but with warnings
      expect(result.isValid).toBe(true);
      expect(result.warnings).toBeDefined();
      expect(result.warnings!.length).toBeGreaterThan(0);
    });
  });

  describe('error context', () => {
    it('should include detailed error context', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { input: '$steps.missing.field' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      const error = result.errors![0] as any;
      expect(error.context).toBeDefined();
      expect(error.context.sourceStep).toBe('step_001');
      expect(error.context.targetStep).toBe('missing');
      expect(error.context.referencePath).toBe('$steps.missing.field');
    });
  });

  describe('multiple errors', () => {
    it('should collect all errors from multiple steps', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { a: '$steps.missing1.field' },
          },
          {
            id: 'step_002',
            type: 'transform',
            config: {},
            params: { b: '$steps.missing2.field' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors!.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('shared cache usage', () => {
    it('should use shared cache when provided', async () => {
      const capabilities = [createCapability('google_search', ['result'])];

      const sharedCache = {
        capabilityMap: new Map([['google_search', capabilities[0]]]),
        stepMap: new Map(),
        responseSchemaMap: new Map([
          ['google_search', capabilities[0].responseSchema],
        ]),
      };

      const context: EnhancedValidationContext = {
        capabilities: capabilities as any[],
        projectId: 'test-project',
        sharedCache: sharedCache as any,
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(true);
    });
  });

  describe('nested references', () => {
    it('should detect references in nested config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              nested: {
                deep: {
                  value: '$steps.missing.field',
                },
              },
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
    });

    it('should detect references in arrays', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              items: ['$steps.missing.field'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
    });
  });
});
