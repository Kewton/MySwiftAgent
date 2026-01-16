/**
 * SchemaValidator Unit Tests
 *
 * Issue #364: Schema validation tests
 */

import { describe, it, expect } from 'vitest';
import { SchemaValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/SchemaValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('SchemaValidator', () => {
  const validator = new SchemaValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('SchemaValidator');
    });
  });

  describe('valid workflows', () => {
    it('should pass for minimal valid workflow', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: {
          type: 'object',
          properties: {},
        },
        output_schema: {
          type: 'object',
          properties: {},
        },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should pass for workflow with multiple steps', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'multi_step_workflow',
        input_schema: {
          type: 'object',
          properties: {
            data: { type: 'string' },
          },
        },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string' },
          },
        },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: {},
          },
          {
            id: 'step_b',
            type: 'llm',
            config: { model: 'claude-sonnet-4-20250514' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('workflow_name validation', () => {
    it('should fail for non-snake_case workflow_name', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'TestWorkflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_WORKFLOW_NAME_FORMAT')).toBe(true);
    });

    it('should fail for workflow_name starting with number', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: '123_workflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for workflow_name with hyphen', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test-workflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });
  });

  describe('steps validation', () => {
    it('should fail for empty steps array', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'empty_steps',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'EMPTY_STEPS')).toBe(true);
    });

    it('should fail for step ID with uppercase', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'StepOne', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_STEP_ID_FORMAT')).toBe(true);
    });

    it('should fail for step ID starting with number', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: '1_step', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });
  });

  describe('Zod schema validation', () => {
    it('should fail for missing required fields', async () => {
      const workflow = {
        workflow_name: 'test_workflow',
        // Missing version, input_schema, steps, output
      } as unknown as TaskFlowDefinition;

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should fail for invalid step type', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        output_schema: { type: 'object', properties: {} },
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'invalid_type' as any, config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });
  });
});
