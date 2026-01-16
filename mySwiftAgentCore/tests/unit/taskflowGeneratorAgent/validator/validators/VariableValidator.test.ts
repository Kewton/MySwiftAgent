/**
 * VariableValidator Unit Tests
 *
 * Issue #364: Variable reference validation tests
 */

import { describe, it, expect } from 'vitest';
import { VariableValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/VariableValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('VariableValidator', () => {
  const validator = new VariableValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('VariableValidator');
    });
  });

  describe('valid variable references', () => {
    it('should pass for valid $input references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: {
          type: 'object',
          properties: {
            user_id: { type: 'string' },
            data: { type: 'object' },
          },
        },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {},
            params: { userId: '$input.user_id' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should pass for valid $steps references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
          {
            id: 'step_two',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_one.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('invalid $input references', () => {
    it('should fail for reference to undefined input field', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: {
          type: 'object',
          properties: {
            user_id: { type: 'string' },
          },
        },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {},
            params: { data: '$input.nonexistent_field' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_INPUT_REFERENCE')).toBe(true);
    });
  });

  describe('invalid $steps references', () => {
    it('should fail for reference to non-preceding step', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_two.result' },
          },
          { id: 'step_two', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_STEP_REFERENCE')).toBe(true);
    });
  });

  describe('$env references', () => {
    it('should add warning for $env references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'api_rest',
            config: {},
            params: { apiKey: '$env.API_KEY' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true); // Warnings don't fail validation
      expect(result.warnings?.some((w) => w.code === 'ENV_REFERENCE')).toBe(true);
    });
  });

  describe('output references', () => {
    it('should validate output $input references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: {
          type: 'object',
          properties: {
            data: { type: 'string' },
          },
        },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {
          input_data: '$input.data',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail for invalid $input reference in output', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {
          result: '$input.nonexistent',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should validate output $steps references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {
          result: '$steps.step_one.result',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('nested references', () => {
    it('should validate references in nested objects', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: {
          type: 'object',
          properties: {
            data: { type: 'string' },
          },
        },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              nested: {
                deep: {
                  value: '$input.data',
                },
              },
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should validate references in arrays', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: {
          type: 'object',
          properties: {
            items: { type: 'array' },
          },
        },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              items: ['$input.items'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });
});
