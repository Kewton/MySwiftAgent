/**
 * Unit Tests for Workflow Schema Validation
 *
 * @module tests/unit/engine/test-schemas
 * @see Issue #348
 */

import {
  WorkflowDefinitionSchema,
  ApiRestConfigSchema,
  CodeJsConfigSchema,
  TransformConfigSchema,
  StepSchema,
  validateWorkflowDefinition,
  zodErrorToValidationErrors,
} from '../../../src/engine/schemas/workflow-schema';

describe('Workflow Schema Validation', () => {
  // ============================================================
  // ApiRestConfigSchema Tests
  // ============================================================

  describe('ApiRestConfigSchema', () => {
    it('should validate a valid HTTPS URL', () => {
      const config = {
        method: 'GET',
        url: 'https://api.example.com/users',
      };

      const result = ApiRestConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should reject HTTP URL', () => {
      const config = {
        method: 'GET',
        url: 'http://api.example.com/users',
      };

      const result = ApiRestConfigSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it('should allow environment variable references in URL', () => {
      const config = {
        method: 'POST',
        url: '${env.API_BASE_URL}/users',
      };

      const result = ApiRestConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should allow secrets references in URL', () => {
      const config = {
        method: 'GET',
        url: '${secrets.PRIVATE_API_URL}/data',
      };

      const result = ApiRestConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should set default timeout_ms', () => {
      const config = {
        method: 'GET',
        url: 'https://api.example.com',
      };

      const result = ApiRestConfigSchema.parse(config);
      expect(result.timeout_ms).toBe(30000);
    });

    it('should set default verify_ssl', () => {
      const config = {
        method: 'GET',
        url: 'https://api.example.com',
      };

      const result = ApiRestConfigSchema.parse(config);
      expect(result.verify_ssl).toBe(true);
    });

    it('should validate all HTTP methods', () => {
      const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

      for (const method of methods) {
        const config = {
          method,
          url: 'https://api.example.com',
        };

        const result = ApiRestConfigSchema.safeParse(config);
        expect(result.success).toBe(true);
      }
    });

    it('should reject invalid HTTP method', () => {
      const config = {
        method: 'INVALID',
        url: 'https://api.example.com',
      };

      const result = ApiRestConfigSchema.safeParse(config);
      expect(result.success).toBe(false);
    });
  });

  // ============================================================
  // CodeJsConfigSchema Tests
  // ============================================================

  describe('CodeJsConfigSchema', () => {
    it('should validate a valid script path', () => {
      const config = {
        path: 'utils/calculator.js',
      };

      const result = CodeJsConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should reject path traversal', () => {
      const config = {
        path: '../../../etc/passwd',
      };

      const result = CodeJsConfigSchema.safeParse(config);
      expect(result.success).toBe(false);
    });

    it('should set default function_name', () => {
      const config = {
        path: 'script.js',
      };

      const result = CodeJsConfigSchema.parse(config);
      expect(result.function_name).toBe('main');
    });

    it('should allow custom function_name', () => {
      const config = {
        path: 'script.js',
        function_name: 'calculate',
      };

      const result = CodeJsConfigSchema.parse(config);
      expect(result.function_name).toBe('calculate');
    });
  });

  // ============================================================
  // TransformConfigSchema Tests
  // ============================================================

  describe('TransformConfigSchema', () => {
    it('should validate template mode', () => {
      const config = {
        mode: 'template',
        template: '{{name}} has {{count}} items',
      };

      const result = TransformConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should validate concat mode', () => {
      const config = {
        mode: 'concat',
        separator: ', ',
        fields: ['field1', 'field2'],
      };

      const result = TransformConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should validate map mode', () => {
      const config = {
        mode: 'map',
        source_field: 'items',
        template: '- {{name}}',
      };

      const result = TransformConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should validate merge mode', () => {
      const config = {
        mode: 'merge',
        strategy: 'deep',
      };

      const result = TransformConfigSchema.safeParse(config);
      expect(result.success).toBe(true);
    });

    it('should set default mode', () => {
      const config = {};

      const result = TransformConfigSchema.parse(config);
      expect(result.mode).toBe('template');
    });
  });

  // ============================================================
  // StepSchema Tests
  // ============================================================

  describe('StepSchema', () => {
    it('should validate an api_rest step', () => {
      const step = {
        id: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/data',
        },
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a transform step', () => {
      const step = {
        id: 'format_output',
        type: 'transform',
        config: {
          mode: 'template',
          template: 'Result: {{value}}',
        },
        params: {
          value: '${fetch_data.output.result}',
        },
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a code_js step', () => {
      const step = {
        id: 'calculate',
        type: 'code_js',
        config: {
          path: 'math/sum.js',
          function_name: 'sumAll',
        },
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a parallel block', () => {
      const step = {
        type: 'parallel',
        steps: [
          {
            id: 'fetch_users',
            type: 'api_rest',
            config: { method: 'GET', url: 'https://api.example.com/users' },
          },
          {
            id: 'fetch_posts',
            type: 'api_rest',
            config: { method: 'GET', url: 'https://api.example.com/posts' },
          },
        ],
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should reject invalid step ID', () => {
      const step = {
        id: '123invalid',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com',
        },
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(false);
    });

    it('should reject empty parallel block', () => {
      const step = {
        type: 'parallel',
        steps: [],
      };

      const result = StepSchema.safeParse(step);
      expect(result.success).toBe(false);
    });
  });

  // ============================================================
  // WorkflowDefinitionSchema Tests
  // ============================================================

  describe('WorkflowDefinitionSchema', () => {
    const validWorkflow = {
      workflow_name: 'test_workflow',
      description: 'A test workflow',
      input_schema: {
        user_id: 'string',
      },
      output_schema: {
        result: 'string',
      },
      steps: [
        {
          id: 'fetch_user',
          type: 'api_rest',
          config: {
            method: 'GET',
            url: 'https://api.example.com/users/${inputs.user_id}',
          },
          output_schema: {
            name: 'string',
          },
        },
      ],
      output: {
        result: '${fetch_user.output.name}',
      },
    };

    it('should validate a complete workflow', () => {
      const result = WorkflowDefinitionSchema.safeParse(validWorkflow);
      expect(result.success).toBe(true);
    });

    it('should reject missing workflow_name', () => {
      const workflow = { ...validWorkflow };
      delete (workflow as any).workflow_name;

      const result = WorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(false);
    });

    it('should reject empty steps array', () => {
      const workflow = { ...validWorkflow, steps: [] };

      const result = WorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(false);
    });

    it('should validate workflow with parallel steps', () => {
      const workflow = {
        ...validWorkflow,
        steps: [
          {
            type: 'parallel',
            steps: [
              {
                id: 'fetch_a',
                type: 'api_rest',
                config: { method: 'GET', url: 'https://api.example.com/a' },
              },
              {
                id: 'fetch_b',
                type: 'api_rest',
                config: { method: 'GET', url: 'https://api.example.com/b' },
              },
            ],
          },
        ],
        output: {
          result: '${fetch_a.output.data}',
        },
      };

      const result = WorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(true);
    });
  });

  // ============================================================
  // Helper Function Tests
  // ============================================================

  describe('validateWorkflowDefinition', () => {
    it('should return success for valid workflow', () => {
      const workflow = {
        workflow_name: 'test',
        input_schema: { id: 'string' },
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template', template: '{{id}}' },
            params: { id: '${inputs.id}' },
          },
        ],
        output: { result: '${step1.output.result}' },
      };

      const result = validateWorkflowDefinition(workflow);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toBeDefined();
      }
    });

    it('should return errors for invalid workflow', () => {
      const workflow = {
        workflow_name: '',
        input_schema: {},
        output_schema: {},
        steps: [],
        output: {},
      };

      const result = validateWorkflowDefinition(workflow);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.errors).toBeDefined();
      }
    });
  });

  describe('zodErrorToValidationErrors', () => {
    it('should convert Zod errors to validation errors', () => {
      const result = WorkflowDefinitionSchema.safeParse({});

      if (!result.success) {
        const errors = zodErrorToValidationErrors(result.error);
        expect(Array.isArray(errors)).toBe(true);
        expect(errors.length).toBeGreaterThan(0);
        expect(errors[0]).toHaveProperty('path');
        expect(errors[0]).toHaveProperty('message');
        expect(errors[0]).toHaveProperty('code');
      }
    });
  });
});
