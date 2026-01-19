/**
 * OutputMappingValidator Unit Tests
 *
 * Issue #375: Validates output mapping references against responseSchema
 */

import { describe, it, expect } from 'vitest';
import { OutputMappingValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/OutputMappingValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('OutputMappingValidator', () => {
  const validator = new OutputMappingValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('OutputMappingValidator');
    });
  });

  describe('output mapping validation', () => {
    it('should pass when output mapping matches output_schema', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string', description: 'Result' },
            count: { type: 'number', description: 'Count' },
          },
        },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mapping: { data: '$.input' } },
            params: {},
          },
        ],
        output: {
          result: '$steps.step1.data',
          count: '$steps.step1.count',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should fail when output mapping references non-existent output_schema field', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string', description: 'Result' },
          },
        },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {
          result: '$steps.step1.data',
          nonExistentField: '$steps.step1.other', // This field is not in output_schema
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'OUTPUT_MAPPING_EXTRA_FIELD')).toBe(true);
    });

    it('should fail when output_schema required field is missing from output mapping', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string', description: 'Result' },
            count: { type: 'number', description: 'Count' },
          },
          required: ['result', 'count'],
        },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {
          result: '$steps.step1.data',
          // 'count' is missing but required
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'OUTPUT_MAPPING_MISSING_REQUIRED')).toBe(true);
    });

    it('should warn when output_schema optional field is missing from output mapping', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string', description: 'Result' },
            optionalField: { type: 'string', description: 'Optional' },
          },
          required: ['result'],
        },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {
          result: '$steps.step1.data',
          // 'optionalField' is missing but optional
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
      expect(result.warnings?.some((w) => w.code === 'OUTPUT_MAPPING_MISSING_OPTIONAL')).toBe(
        true
      );
    });

    it('should pass when output_schema has no properties (flexible schema)', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
        },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {
          anyField: '$steps.step1.data',
        },
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('responseSchema compatibility validation', () => {
    it('should pass when step output references match capability responseSchema', async () => {
      const context: ValidationContext = {
        capabilities: [
          {
            id: 'api_weather',
            name: 'Weather API',
            category: 'api',
            status: 'available',
            responseSchema: {
              type: 'object',
              properties: {
                temperature: { type: 'number' },
                humidity: { type: 'number' },
              },
            },
          },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            temp: { type: 'number', description: 'Temperature' },
          },
        },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: { capability_id: 'api_weather' },
            params: {},
          },
        ],
        output: {
          temp: '$steps.get_weather.temperature', // temperature exists in responseSchema
        },
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });

    it('should warn when step output references non-existent responseSchema field', async () => {
      const context: ValidationContext = {
        capabilities: [
          {
            id: 'api_weather',
            name: 'Weather API',
            category: 'api',
            status: 'available',
            responseSchema: {
              type: 'object',
              properties: {
                temperature: { type: 'number' },
              },
            },
          },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string' },
          },
        },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: { capability_id: 'api_weather' },
            params: {},
          },
        ],
        output: {
          result: '$steps.get_weather.nonExistentField', // This field is not in responseSchema
        },
      };

      const result = await validator.validate(workflow, context);

      expect(result.warnings?.some((w) => w.code === 'RESPONSE_SCHEMA_FIELD_UNKNOWN')).toBe(true);
    });
  });
});
