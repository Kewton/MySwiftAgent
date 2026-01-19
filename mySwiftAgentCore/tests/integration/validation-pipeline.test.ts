/**
 * ValidationPipeline Integration Tests
 *
 * Issue #375: Integration tests for the full validation pipeline
 */

import { describe, it, expect } from 'vitest';
import { ValidationPipeline } from '../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import { OutputMappingValidator } from '../../src/taskflowGeneratorAgent/validator/validators/OutputMappingValidator.js';
import { NodeConfigValidator } from '../../src/taskflowGeneratorAgent/validator/validators/NodeConfigValidator.js';
import type { TaskFlowDefinition } from '../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('ValidationPipeline Integration', () => {
  describe('with all validators', () => {
    it('should run all validators and aggregate results', async () => {
      // Create pipeline with new validators
      const pipeline = new ValidationPipeline();
      pipeline.addValidator(new OutputMappingValidator());
      pipeline.addValidator(new NodeConfigValidator());

      const context: ValidationContext = {
        capabilities: [
          {
            id: 'api_weather',
            name: 'Weather API',
            category: 'api',
            status: 'available',
          },
        ],
        projectId: 'test-project',
      };

      const validWorkflow: TaskFlowDefinition = {
        workflow_name: 'weather_report',
        input_schema: {
          type: 'object',
          properties: {
            location: { type: 'string', description: 'Location' },
          },
        },
        output_schema: {
          type: 'object',
          properties: {
            temperature: { type: 'number', description: 'Temperature' },
            summary: { type: 'string', description: 'Summary' },
          },
          required: ['temperature', 'summary'],
        },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: { capability_id: 'api_weather' },
            params: { location: '$input.location' },
          },
          {
            id: 'format_output',
            type: 'transform',
            config: {
              mapping: {
                temp: '$.get_weather.temperature',
                desc: '$.get_weather.description',
              },
            },
            params: {},
          },
        ],
        output: {
          temperature: '$steps.format_output.temp',
          summary: '$steps.format_output.desc',
        },
      };

      const result = await pipeline.validate(validWorkflow, context);

      expect(result.isValid).toBe(true);
    });

    it('should collect errors from multiple validators', async () => {
      const pipeline = new ValidationPipeline();
      pipeline.addValidator(new OutputMappingValidator());
      pipeline.addValidator(new NodeConfigValidator());

      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const invalidWorkflow: TaskFlowDefinition = {
        workflow_name: 'invalid_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'string', description: 'Result' },
          },
          required: ['result', 'missingField'],
        },
        steps: [
          {
            id: 'transform_step',
            type: 'transform',
            config: {}, // Missing template or mapping
            params: {},
          },
        ],
        output: {
          result: '$steps.transform_step.data',
          // missingField is required but not in output
        },
      };

      const result = await pipeline.validate(invalidWorkflow, context);

      expect(result.isValid).toBe(false);
      // Should have errors from both validators
      expect(result.errors.some((e) => e.code === 'TRANSFORM_MISSING_CONFIG')).toBe(true);
      expect(result.errors.some((e) => e.code === 'OUTPUT_MAPPING_MISSING_REQUIRED')).toBe(true);
    });
  });

  describe('complex workflow validation', () => {
    it('should validate a complex multi-step workflow', async () => {
      const pipeline = new ValidationPipeline();
      pipeline.addValidator(new OutputMappingValidator());
      pipeline.addValidator(new NodeConfigValidator());

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
                conditions: { type: 'string' },
              },
            },
          },
          {
            id: 'llm_summarizer',
            name: 'LLM Summarizer',
            category: 'llm',
            status: 'available',
          },
        ],
        projectId: 'test-project',
      };

      const complexWorkflow: TaskFlowDefinition = {
        workflow_name: 'weather_summary_email',
        input_schema: {
          type: 'object',
          properties: {
            location: { type: 'string', description: 'Location' },
            recipient: { type: 'string', description: 'Email recipient' },
          },
          required: ['location', 'recipient'],
        },
        output_schema: {
          type: 'object',
          properties: {
            emailSent: { type: 'boolean', description: 'Email sent status' },
            summary: { type: 'string', description: 'Weather summary' },
          },
          required: ['emailSent', 'summary'],
        },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: { capability_id: 'api_weather' },
            params: { location: '$input.location' },
          },
          {
            id: 'generate_summary',
            type: 'llm',
            config: {
              prompt:
                'Summarize the weather: Temperature: {{steps.get_weather.temperature}}, Conditions: {{steps.get_weather.conditions}}',
            },
            params: {},
          },
          {
            id: 'format_email',
            type: 'transform',
            config: {
              template:
                '{"subject": "Weather Update", "body": "{{steps.generate_summary.text}}"}',
            },
            params: {},
          },
        ],
        output: {
          emailSent: '$steps.format_email.sent',
          summary: '$steps.generate_summary.text',
        },
      };

      const result = await pipeline.validate(complexWorkflow, context);

      expect(result.isValid).toBe(true);
    });
  });

  describe('validator ordering', () => {
    it('should run validators in order and collect all errors', async () => {
      const pipeline = new ValidationPipeline();

      // Add validators in specific order
      pipeline.addValidator(new NodeConfigValidator());
      pipeline.addValidator(new OutputMappingValidator());

      const validators = pipeline.getValidators();
      expect(validators[validators.length - 2].name).toBe('NodeConfigValidator');
      expect(validators[validators.length - 1].name).toBe('OutputMappingValidator');
    });
  });
});
