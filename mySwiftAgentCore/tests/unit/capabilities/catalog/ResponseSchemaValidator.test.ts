/**
 * ResponseSchemaValidator Unit Tests
 *
 * Issue #380: Response Schema validation using ajv
 * Tests for JSON Schema Draft-07 compliance and validation logic
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ResponseSchemaValidator,
  createResponseSchemaValidator,
} from '../../../../src/taskflowGeneratorAgent/validator/validators/ResponseSchemaValidator.js';
import type { ValidationContext } from '../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

describe('ResponseSchemaValidator', () => {
  let validator: ResponseSchemaValidator;

  beforeEach(() => {
    validator = new ResponseSchemaValidator();
  });

  describe('constructor and factory', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('ResponseSchemaValidator');
    });

    it('should create validator via factory function', () => {
      const created = createResponseSchemaValidator();
      expect(created).toBeInstanceOf(ResponseSchemaValidator);
    });
  });

  describe('validateSchema', () => {
    it('should validate a valid JSON Schema Draft-07', () => {
      const schema = {
        type: 'object',
        properties: {
          name: { type: 'string' },
          age: { type: 'integer', minimum: 0 },
        },
        required: ['name'],
      };

      const result = validator.validateSchema(schema);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect invalid schema with wrong type', () => {
      const schema = {
        type: 'invalid_type', // Invalid type
        properties: {},
      };

      const result = validator.validateSchema(schema);
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should validate schema with nested objects', () => {
      const schema = {
        type: 'object',
        properties: {
          user: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              email: { type: 'string', format: 'email' },
            },
          },
        },
      };

      const result = validator.validateSchema(schema);
      expect(result.isValid).toBe(true);
    });

    it('should validate schema with arrays', () => {
      const schema = {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string' },
            link: { type: 'string', format: 'uri' },
          },
        },
      };

      const result = validator.validateSchema(schema);
      expect(result.isValid).toBe(true);
    });

    it('should handle empty schema', () => {
      const schema = {};

      const result = validator.validateSchema(schema);
      expect(result.isValid).toBe(true);
    });
  });

  describe('validateData', () => {
    it('should validate data against schema', () => {
      const schema = {
        type: 'object',
        properties: {
          name: { type: 'string' },
          age: { type: 'integer' },
        },
        required: ['name'],
      };

      const data = {
        name: 'John',
        age: 30,
      };

      const result = validator.validateData(data, schema);
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect missing required field', () => {
      const schema = {
        type: 'object',
        properties: {
          name: { type: 'string' },
          age: { type: 'integer' },
        },
        required: ['name'],
      };

      const data = {
        age: 30,
        // name is missing
      };

      const result = validator.validateData(data, schema);
      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.message.includes('name') || e.message.includes('required'))).toBe(true);
    });

    it('should detect type mismatch', () => {
      const schema = {
        type: 'object',
        properties: {
          age: { type: 'integer' },
        },
      };

      const data = {
        age: 'not a number',
      };

      const result = validator.validateData(data, schema);
      expect(result.isValid).toBe(false);
    });

    it('should validate email format', () => {
      const schema = {
        type: 'object',
        properties: {
          email: { type: 'string', format: 'email' },
        },
      };

      const validData = { email: 'test@example.com' };
      const invalidData = { email: 'not-an-email' };

      expect(validator.validateData(validData, schema).isValid).toBe(true);
      expect(validator.validateData(invalidData, schema).isValid).toBe(false);
    });

    it('should validate URI format', () => {
      const schema = {
        type: 'object',
        properties: {
          url: { type: 'string', format: 'uri' },
        },
      };

      const validData = { url: 'https://example.com/path' };
      const invalidData = { url: 'not-a-url' };

      expect(validator.validateData(validData, schema).isValid).toBe(true);
      expect(validator.validateData(invalidData, schema).isValid).toBe(false);
    });

    it('should validate date-time format', () => {
      const schema = {
        type: 'object',
        properties: {
          timestamp: { type: 'string', format: 'date-time' },
        },
      };

      const validData = { timestamp: '2024-01-15T10:30:00Z' };
      const invalidData = { timestamp: '2024-01-15' };

      expect(validator.validateData(validData, schema).isValid).toBe(true);
      expect(validator.validateData(invalidData, schema).isValid).toBe(false);
    });

    it('should validate minimum and maximum constraints', () => {
      const schema = {
        type: 'object',
        properties: {
          value: { type: 'integer', minimum: 1, maximum: 100 },
        },
      };

      expect(validator.validateData({ value: 50 }, schema).isValid).toBe(true);
      expect(validator.validateData({ value: 0 }, schema).isValid).toBe(false);
      expect(validator.validateData({ value: 101 }, schema).isValid).toBe(false);
    });

    it('should validate pattern constraint', () => {
      const schema = {
        type: 'object',
        properties: {
          code: { type: 'string', pattern: '^[A-Z]{3}$' },
        },
      };

      expect(validator.validateData({ code: 'ABC' }, schema).isValid).toBe(true);
      expect(validator.validateData({ code: 'abc' }, schema).isValid).toBe(false);
      expect(validator.validateData({ code: 'ABCD' }, schema).isValid).toBe(false);
    });

    it('should validate array items', () => {
      const schema = {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id: { type: 'integer' },
            name: { type: 'string' },
          },
          required: ['id'],
        },
      };

      const validData = [
        { id: 1, name: 'Item 1' },
        { id: 2, name: 'Item 2' },
      ];

      const invalidData = [
        { id: 1, name: 'Item 1' },
        { name: 'Missing ID' }, // Missing required id
      ];

      expect(validator.validateData(validData, schema).isValid).toBe(true);
      expect(validator.validateData(invalidData, schema).isValid).toBe(false);
    });
  });

  describe('validate (Validator interface)', () => {
    it('should pass when workflow has no api_rest steps', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(true);
    });

    it('should pass when capability has valid responseSchema', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'search',
            type: 'api_rest',
            config: {
              capability_id: 'google_search',
            },
            params: {},
          },
        ],
        output: {},
      };

      const context: ValidationContext = {
        capabilities: [
          {
            id: 'google_search',
            name: 'Google Search',
            status: 'available',
            responseSchema: {
              type: 'object',
              properties: {
                results: { type: 'array' },
              },
            },
          },
        ],
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(true);
    });

    it('should add warning when capability has no responseSchema', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {
              capability_id: 'legacy_api',
            },
            params: {},
          },
        ],
        output: {},
      };

      const context: ValidationContext = {
        capabilities: [
          {
            id: 'legacy_api',
            name: 'Legacy API',
            status: 'available',
            // No responseSchema
          },
        ],
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(true);
      expect(result.warnings?.some((w) => w.code === 'MISSING_RESPONSE_SCHEMA')).toBe(true);
    });

    it('should fail when capability has invalid responseSchema', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {
              capability_id: 'broken_api',
            },
            params: {},
          },
        ],
        output: {},
      };

      const context: ValidationContext = {
        capabilities: [
          {
            id: 'broken_api',
            name: 'Broken API',
            status: 'available',
            responseSchema: {
              type: 'invalid_type', // Invalid JSON Schema type
            },
          },
        ],
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(false);
      expect(result.errors?.some((e) => e.code === 'INVALID_RESPONSE_SCHEMA')).toBe(true);
    });
  });

  describe('convertToJsonSchema', () => {
    it('should convert YAML-style schema to JSON Schema', () => {
      const yamlSchema = {
        search_results: {
          type: 'array',
          description: 'Search results',
          items: {
            type: 'object',
            properties: {
              title: { type: 'string', description: 'Title' },
            },
          },
        },
        count: {
          type: 'integer',
          description: 'Count',
        },
      };

      const jsonSchema = validator.convertToJsonSchema(yamlSchema);

      expect(jsonSchema.type).toBe('object');
      expect(jsonSchema.properties).toBeDefined();
      expect(jsonSchema.properties?.search_results?.type).toBe('array');
      expect(jsonSchema.properties?.count?.type).toBe('integer');
    });

    it('should handle nested object schemas', () => {
      const yamlSchema = {
        user: {
          type: 'object',
          properties: {
            name: { type: 'string' },
            address: {
              type: 'object',
              properties: {
                city: { type: 'string' },
              },
            },
          },
        },
      };

      const jsonSchema = validator.convertToJsonSchema(yamlSchema);

      expect(jsonSchema.type).toBe('object');
      expect(jsonSchema.properties?.user?.type).toBe('object');
    });

    it('should preserve description fields', () => {
      const yamlSchema = {
        result: {
          type: 'string',
          description: 'The result of the operation',
        },
      };

      const jsonSchema = validator.convertToJsonSchema(yamlSchema);

      expect(jsonSchema.properties?.result?.description).toBe('The result of the operation');
    });
  });

  describe('formatValidationErrors', () => {
    it('should format ajv errors into structured format', () => {
      const schema = {
        type: 'object',
        properties: {
          name: { type: 'string' },
        },
        required: ['name'],
      };

      const invalidData = { name: 123 }; // number instead of string

      const result = validator.validateData(invalidData, schema);

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toHaveProperty('code');
      expect(result.errors[0]).toHaveProperty('message');
      expect(result.errors[0]).toHaveProperty('path');
    });
  });
});
