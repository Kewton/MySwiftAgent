/**
 * SecurityValidator Unit Tests
 *
 * Issue #364: Security validation tests
 */

import { describe, it, expect } from 'vitest';
import { SecurityValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/SecurityValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationContext } from '../../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';

describe('SecurityValidator', () => {
  const validator = new SecurityValidator();

  const defaultContext: ValidationContext = {
    capabilities: [],
    projectId: 'test-project',
  };

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('SecurityValidator');
    });
  });

  describe('code_js step validation', () => {
    it('should fail for eval() usage', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'eval("console.log(1)")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'UNSAFE_CODE')).toBe(true);
    });

    it('should fail for Function constructor', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'new Function("return 1")()' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for require() usage', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'const fs = require("fs")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for dynamic import', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'await import("fs")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for process access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'process.exit(1)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for fs module access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'fs.readFileSync("/etc/passwd")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should fail for child_process access', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'child_process.exec("ls")' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
    });

    it('should pass for safe code', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'run_code',
            type: 'code_js',
            config: { code: 'return input.data.map(x => x * 2)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('api_rest step validation', () => {
    it('should warn for non-https URL on external domain', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'http://api.example.com/data' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'INSECURE_HTTP')).toBe(true);
    });

    it('should warn for localhost URL', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'http://localhost:8080/api' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'LOCALHOST_URL')).toBe(true);
    });

    it('should not warn for https URL', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: 'https://api.example.com/data' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.filter((w) => w.code === 'INSECURE_HTTP').length).toBe(0);
    });

    it('should skip validation for variable URLs', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: { url: '$input.api_url' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('transform step validation', () => {
    it('should fail for eval in expression', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: { expression: 'eval(input.code)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'UNSAFE_EXPRESSION')).toBe(true);
    });

    it('should pass for safe expression', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'transform',
            type: 'transform',
            config: { expression: 'input.value * 2' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(true);
    });
  });

  describe('dangerous patterns', () => {
    it('should detect shell injection pattern', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { value: '`rm -rf /`' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'SHELL_INJECTION')).toBe(true);
    });

    it('should detect command substitution', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { value: '$(whoami)' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'COMMAND_SUBSTITUTION')).toBe(true);
    });

    it('should detect path traversal', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { path: '../../../etc/passwd' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.isValid).toBe(false);
      expect(result.errors.some((e) => e.code === 'PATH_TRAVERSAL')).toBe(true);
    });

    it('should warn about sensitive data (password)', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { data: 'user_password' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      // Sensitive data is a warning, not an error
      expect(result.warnings?.some((w) => w.code === 'SENSITIVE_DATA')).toBe(true);
    });

    it('should warn about API key references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: { key: 'my_api_key' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, defaultContext);

      expect(result.warnings?.some((w) => w.code === 'SENSITIVE_DATA')).toBe(true);
    });
  });

  describe('nested dangerous patterns', () => {
    it('should detect patterns in nested objects', async () => {
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
                  value: '../../../etc/passwd',
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

    it('should detect patterns in arrays', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        version: '1.0',
        input_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_one',
            type: 'transform',
            config: {
              items: ['safe', '$(rm -rf /)'],
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
