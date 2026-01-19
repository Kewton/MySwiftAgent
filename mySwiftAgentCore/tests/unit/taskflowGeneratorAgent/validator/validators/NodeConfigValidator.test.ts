/**
 * NodeConfigValidator Unit Tests
 *
 * Issue #375: Validates node configuration based on node type specifications
 * Issue #375 (iteration-2): Added tests for YAML loading integration
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import {
  NodeConfigValidator,
  loadNodeTypeSpecsFromYaml,
  resetNodeTypeSpecsCache,
} from '../../../../../src/taskflowGeneratorAgent/validator/validators/NodeConfigValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('NodeConfigValidator', () => {
  const validator = new NodeConfigValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('NodeConfigValidator');
    });
  });

  describe('transform node validation', () => {
    it('should pass when transform node has template config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform_data',
            type: 'transform',
            config: {
              template: '{"result": "{{input.value}}"}',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should pass when transform node has mapping config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform_data',
            type: 'transform',
            config: {
              mapping: {
                output_field: '$.input.value',
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

    it('should fail when transform node has neither template nor mapping', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
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

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'TRANSFORM_MISSING_CONFIG')).toBe(true);
    });

    it('should warn when transform node uses unsupported expression config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform_data',
            type: 'transform',
            config: {
              expression: 'input.value * 2', // expression is not supported
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'TRANSFORM_UNSUPPORTED_CONFIG')).toBe(true);
    });
  });

  describe('api_rest node validation', () => {
    it('should pass when api_rest node has capability_id', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {
              capability_id: 'api_weather',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should pass when api_rest node has url config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com/data',
              method: 'GET',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail when api_rest node has neither capability_id nor url', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'API_REST_MISSING_CONFIG')).toBe(true);
    });
  });

  describe('llm node validation', () => {
    it('should pass when llm node has prompt config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'llm_call',
            type: 'llm',
            config: {
              prompt: 'Generate a summary of: {{input.text}}',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail when llm node is missing prompt', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'llm_call',
            type: 'llm',
            config: {
              model: 'claude-sonnet-4-20250514',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'LLM_MISSING_PROMPT')).toBe(true);
    });
  });

  describe('code_js node validation', () => {
    it('should pass when code_js node has code config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'code_step',
            type: 'code_js',
            config: {
              code: 'return input.value * 2;',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail when code_js node is missing code', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'code_step',
            type: 'code_js',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'CODE_JS_MISSING_CODE')).toBe(true);
    });
  });

  describe('parallel node validation', () => {
    it('should pass when parallel node has branches config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'parallel_step',
            type: 'parallel',
            config: {
              branches: ['branch1', 'branch2'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail when parallel node has empty branches', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'parallel_step',
            type: 'parallel',
            config: {
              branches: [],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'PARALLEL_EMPTY_BRANCHES')).toBe(true);
    });
  });

  describe('action node validation', () => {
    it('should pass when action node has action_type config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'action_step',
            type: 'action',
            config: {
              action_type: 'notify',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });

    it('should fail when action node is missing action_type', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'action_step',
            type: 'action',
            config: {},
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'ACTION_MISSING_TYPE')).toBe(true);
    });
  });

  /**
   * Issue #375 (iteration-2): YAML Loading Integration Tests
   */
  describe('YAML loading integration', () => {
    const testYamlPath = '/tmp/test-node-types-spec.yaml';

    afterEach(() => {
      // Clean up test file
      try {
        fs.unlinkSync(testYamlPath);
      } catch {
        // Ignore cleanup errors
      }
      // Reset cache to clear loaded specs
      resetNodeTypeSpecsCache();
    });

    it('should load specs from YAML file', () => {
      // Create test YAML content matching the structure
      const yamlContent = `
node_types:
  transform:
    description: Test transform node
    supported_config:
      template:
        type: string
        description: Template string
      mapping:
        type: object
        description: Mapping object
    unsupported_config:
      - expression
    validation_rules:
      - rule: oneOf
        fields: [template, mapping]
`;

      fs.writeFileSync(testYamlPath, yamlContent);

      const specs = loadNodeTypeSpecsFromYaml(testYamlPath);

      expect(specs).not.toBeNull();
      expect(specs).toHaveProperty('transform');
      expect(specs!.transform.optionalConfig).toContain('template');
      expect(specs!.transform.optionalConfig).toContain('mapping');
      expect(specs!.transform.unsupportedConfig).toContain('expression');
      expect(specs!.transform.oneOfRequired).toEqual([['template', 'mapping']]);
    });

    it('should extract required fields from YAML', () => {
      const yamlContent = `
node_types:
  llm:
    supported_config:
      prompt:
        type: string
        required: true
      model:
        type: string
`;

      fs.writeFileSync(testYamlPath, yamlContent);

      const specs = loadNodeTypeSpecsFromYaml(testYamlPath);

      expect(specs).not.toBeNull();
      expect(specs).toHaveProperty('llm');
      expect(specs!.llm.requiredConfig).toContain('prompt');
      expect(specs!.llm.optionalConfig).toContain('model');
    });

    it('should return null for invalid YAML', () => {
      fs.writeFileSync(testYamlPath, 'invalid: yaml: content: {{}}');

      const specs = loadNodeTypeSpecsFromYaml(testYamlPath);

      expect(specs).toBeNull();
    });

    it('should return null for non-existent file', () => {
      const specs = loadNodeTypeSpecsFromYaml('/nonexistent/path/file.yaml');

      expect(specs).toBeNull();
    });

    it('should return null for YAML without node_types key', () => {
      fs.writeFileSync(testYamlPath, 'other_key: value');

      const specs = loadNodeTypeSpecsFromYaml(testYamlPath);

      expect(specs).toBeNull();
    });
  });

  describe('YAML-loaded validator behavior', () => {
    it('should use specs and expose them via getSpecs', () => {
      const validator = new NodeConfigValidator();
      const specs = validator.getSpecs();

      // Verify specs are loaded and have expected structure
      expect(specs).toBeDefined();
      expect(specs).toHaveProperty('transform');
      expect(specs).toHaveProperty('llm');
      expect(specs).toHaveProperty('api_rest');
    });

    it('should validate correctly regardless of spec source', async () => {
      // This test ensures validation works whether specs come from
      // YAML file or fallback constants
      const validator = new NodeConfigValidator();

      const validWorkflow: TaskFlowDefinition = {
        workflow_name: 'test',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { template: '{}' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(validWorkflow, defaultContext);
      expect(result.isValid).toBe(true);
    });
  });
});
