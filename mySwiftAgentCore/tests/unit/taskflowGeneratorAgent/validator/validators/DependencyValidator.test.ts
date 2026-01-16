/**
 * DependencyValidator Unit Tests
 *
 * Issue #364: Dependency validation tests
 */

import { describe, it, expect } from 'vitest';
import { DependencyValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/DependencyValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('DependencyValidator', () => {
  const validator = new DependencyValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('DependencyValidator');
    });
  });

  describe('valid dependencies', () => {
    it('should pass for workflow without dependencies', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
          { id: 'step_two', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should pass for valid step references', async () => {
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

    it('should pass for valid output references', async () => {
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

  describe('duplicate step IDs', () => {
    it('should fail for duplicate step IDs', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'DUPLICATE_STEP_ID')).toBe(true);
    });
  });

  describe('invalid step references', () => {
    it('should fail for reference to non-existent step', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {},
            params: { input: '$steps.nonexistent.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_STEP_REFERENCE')).toBe(true);
    });

    it('should fail for forward reference (referencing later step)', async () => {
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
      expect(result.errors.some((e) => e.code === 'FORWARD_REFERENCE')).toBe(true);
    });
  });

  describe('invalid output references', () => {
    it('should fail for output referencing non-existent step', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_one', type: 'transform', config: {}, params: {} },
        ],
        output: {
          result: '$steps.nonexistent.result',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'INVALID_OUTPUT_REFERENCE')).toBe(true);
    });
  });

  describe('nested references', () => {
    it('should detect references in nested config objects', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              nested: {
                deep: {
                  value: '$steps.nonexistent.result',
                },
              },
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should detect references in arrays', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              items: ['$steps.nonexistent.result'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });
  });
});
