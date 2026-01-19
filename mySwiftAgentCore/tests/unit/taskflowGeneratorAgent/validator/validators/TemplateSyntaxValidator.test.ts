/**
 * TemplateSyntaxValidator Unit Tests
 *
 * Issue #381: Template syntax validation for {{expression}} and $.steps.xxx patterns
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { TemplateSyntaxValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/TemplateSyntaxValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { EnhancedValidationContext } from '../../../../../src/taskflowGeneratorAgent/types/validation.js';

describe('TemplateSyntaxValidator', () => {
  let validator: TemplateSyntaxValidator;

  beforeEach(() => {
    validator = new TemplateSyntaxValidator();
  });

  const createContext = (): EnhancedValidationContext => ({
    capabilities: [],
    projectId: 'test-project',
    additionalContext: {
      enableTemplateValidation: true,
    },
  });

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('TemplateSyntaxValidator');
    });
  });

  describe('valid templates', () => {
    it('should pass for workflow without templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: { value: 'plain text' },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for valid mustache templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{variable}}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for valid JSON path references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { value: '$steps.previous.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for valid mixed templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{$.steps.previous.result}}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for $.input and $.env references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: {
              a: '$.input.query',
              b: '$.env.API_KEY',
            },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });
  });

  describe('mustache syntax errors', () => {
    it('should fail for unclosed mustache template', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{unclosed' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('TEMPLATE_SYNTAX_ERROR');
    });

    it('should fail for unmatched closing braces', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: 'text}}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('TEMPLATE_SYNTAX_ERROR');
    });

    it('should fail for nested mustache templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{{{nested}}}}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });

    it('should fail for empty mustache expression', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{}}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });
  });

  describe('JSON path syntax errors', () => {
    it('should fail for invalid JSON path prefix', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { value: '$.invalid.path' }, // $.invalid is not steps, input, or env
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('TEMPLATE_SYNTAX_ERROR');
    });

    it('should fail for incomplete JSON path', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { value: '$steps.' }, // Incomplete
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });
  });

  describe('transform node special handling', () => {
    it('should apply stricter validation for transform nodes', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              template: '{{malformed',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].path).toContain('step_001');
    });
  });

  describe('error messages', () => {
    it('should include helpful error message', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{unclosed' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      const error = result.errors![0] as any;
      expect(error.suggestion).toBeDefined();
      expect(error.suggestion.message).toBeDefined();
    });
  });

  describe('multiple templates in single step', () => {
    it('should validate all templates in a step', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              a: '{{valid}}',
              b: '{{invalid',
              c: '{{also_invalid',
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors!.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('nested object validation', () => {
    it('should detect errors in deeply nested templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              level1: {
                level2: {
                  level3: '{{broken',
                },
              },
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });

    it('should detect errors in array templates', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {
              items: ['{{valid}}', '{{invalid'],
            },
            params: {},
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });
  });

  describe('skip validation when disabled', () => {
    it('should skip validation when enableTemplateValidation is false', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_001',
            type: 'transform',
            config: {},
            params: { template: '{{broken' },
          },
        ],
        output: {},
      };

      const context: EnhancedValidationContext = {
        capabilities: [],
        projectId: 'test-project',
        additionalContext: {
          enableTemplateValidation: false,
        },
      };

      const result = await validator.validate(workflow, context);

      // Should pass when validation is disabled
      expect(result.isValid).toBe(true);
    });
  });
});
