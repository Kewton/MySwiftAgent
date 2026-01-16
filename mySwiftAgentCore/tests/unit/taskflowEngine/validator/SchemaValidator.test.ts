/**
 * SchemaValidator Unit Tests
 *
 * Issue #363: JSON Schema validation for workflows
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  SchemaValidator,
  createSchemaValidator,
} from '../../../../src/taskflowEngine/validator/SchemaValidator.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('SchemaValidator', () => {
  let validator: SchemaValidator;

  beforeEach(() => {
    validator = new SchemaValidator();
  });

  describe('validateTaskFlow', () => {
    it('should validate a minimal valid workflow', () => {
      // The TaskFlowDefinitionSchema expects full structure
      const workflow = {
        workflow_name: 'Test Workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_1',
            type: 'transform',
            config: { template: '{}' },
            params: {},
          },
        ],
        output: {},
      };

      const result = validator.validateTaskFlow(workflow);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject workflow without workflow_name', () => {
      const workflow = {
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [],
        output: {},
      };

      const result = validator.validateTaskFlow(workflow);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should reject workflow without required fields', () => {
      const workflow = {
        workflow_name: 'Test',
        steps: [],
      };

      const result = validator.validateTaskFlow(workflow);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('validateInternal', () => {
    it('should validate a valid internal workflow', () => {
      const workflow = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: { template: '{}' },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      const result = validator.validateInternal(workflow);

      expect(result.valid).toBe(true);
    });
  });

  describe('validateInputs', () => {
    it('should validate input against schema', () => {
      const workflow = {
        name: 'Test',
        version: '1.0.0',
        input_schema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            age: { type: 'number' },
          },
          required: ['name'],
        },
        steps: [],
      };
      const input = { name: 'Alice', age: 30 };

      const result = validator.validateInputs(workflow, input);

      expect(result.valid).toBe(true);
    });

    it('should detect missing required fields', () => {
      const workflow = {
        name: 'Test',
        version: '1.0.0',
        input_schema: {
          type: 'object',
          properties: {
            name: { type: 'string' },
          },
          required: ['name'],
        },
        steps: [],
      };
      const input = {};

      const result = validator.validateInputs(workflow, input);

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.message.includes('name'))).toBe(true);
    });

    it('should detect type mismatches', () => {
      const workflow = {
        name: 'Test',
        version: '1.0.0',
        input_schema: {
          type: 'object',
          properties: {
            count: { type: 'number' },
          },
        },
        steps: [],
      };
      const input = { count: 'not a number' };

      const result = validator.validateInputs(workflow, input);

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.code === 'TYPE_MISMATCH')).toBe(true);
    });

    it('should pass when no schema provided', () => {
      const workflow = {
        name: 'Test',
        version: '1.0.0',
        steps: [],
      };

      const result = validator.validateInputs(workflow, { any: 'data' });

      expect(result.valid).toBe(true);
    });
  });

  describe('validateDependencies', () => {
    it('should detect missing dependencies', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['non_existent_step'],
          },
        ],
        outputMapping: {},
      };

      const result = validator.validateDependencies(workflow);

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.code === 'DEPENDENCY_NOT_FOUND')).toBe(true);
    });

    it('should detect circular dependencies', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_2'],
          },
          {
            id: 'step_2',
            name: 'Step 2',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_1'],
          },
        ],
        outputMapping: {},
      };

      const result = validator.validateDependencies(workflow);

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.code === 'CIRCULAR_DEPENDENCY')).toBe(true);
    });

    it('should pass for valid dependencies', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step 1',
            type: 'transform',
            config: {},
            params: {},
          },
          {
            id: 'step_2',
            name: 'Step 2',
            type: 'transform',
            config: {},
            params: {},
            dependsOn: ['step_1'],
          },
        ],
        outputMapping: {},
      };

      const result = validator.validateDependencies(workflow);

      expect(result.valid).toBe(true);
    });
  });
});

describe('createSchemaValidator factory', () => {
  it('should create a SchemaValidator instance', () => {
    const validator = createSchemaValidator();
    expect(validator).toBeInstanceOf(SchemaValidator);
  });
});
