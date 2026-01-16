/**
 * CapabilityValidator Unit Tests
 *
 * Issue #364: Capability validation tests
 */

import { describe, it, expect } from 'vitest';
import { CapabilityValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/CapabilityValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('CapabilityValidator', () => {
  const validator = new CapabilityValidator();

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('CapabilityValidator');
    });
  });

  describe('api_rest step validation', () => {
    it('should pass when capability exists and is available', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'api_weather', name: 'Weather API', status: 'available' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: {
              capability_id: 'api_weather',
              url: 'https://api.example.com/weather',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should fail when capability does not exist', async () => {
      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: {
              capability_id: 'nonexistent_capability',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'CAPABILITY_NOT_FOUND')).toBe(true);
    });

    it('should fail when capability is unavailable', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'api_weather', name: 'Weather API', status: 'unavailable' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: {
              capability_id: 'api_weather',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'CAPABILITY_UNAVAILABLE')).toBe(true);
    });

    it('should add warning when capability is deprecated', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'api_weather', name: 'Weather API', status: 'deprecated' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'get_weather',
            type: 'api_rest',
            config: {
              capability_id: 'api_weather',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true); // Deprecated is a warning, not an error
      expect(result.warnings?.some((w) => w.code === 'CAPABILITY_DEPRECATED')).toBe(true);
    });

    it('should pass when no capability_id is specified', async () => {
      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'get_data',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com/data',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });
  });

  describe('llm step validation', () => {
    it('should pass when llm capability exists', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'llm_claude', name: 'Claude LLM', status: 'available' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'generate_text',
            type: 'llm',
            config: { model: 'claude-sonnet-4-20250514' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });

    it('should add warning when no llm capability is defined', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'api_weather', name: 'Weather API', status: 'available' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'generate_text',
            type: 'llm',
            config: { model: 'claude-sonnet-4-20250514' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
      expect(result.warnings?.some((w) => w.code === 'NO_LLM_CAPABILITY')).toBe(true);
    });

    it('should detect gpt capability', async () => {
      const context: ValidationContext = {
        capabilities: [
          { id: 'gpt_4', name: 'GPT-4', status: 'available' },
        ],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'generate_text',
            type: 'llm',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
      expect(result.warnings?.some((w) => w.code === 'NO_LLM_CAPABILITY')).toBe(false);
    });
  });

  describe('other step types', () => {
    it('should pass for transform steps without capability checks', async () => {
      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform_data',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });

    it('should pass for code_js steps', async () => {
      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'return input;' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });
  });
});
