/**
 * Tests for Semantic Validator
 *
 * @module tests/unit/engine/validator/semantic-validator
 * @see Issue #348
 */

import { SemanticValidator } from '../../../../src/engine/validator/semantic-validator.js';

describe('SemanticValidator', () => {
  let validator: SemanticValidator;

  beforeEach(() => {
    validator = new SemanticValidator();
  });

  describe('checkVariableReferences', () => {
    it('should pass when all references are valid', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: { userId: 'string' },
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'fetch_user',
            type: 'api_rest',
            config: {
              method: 'GET',
              url: 'https://api.example.com/users/${inputs.userId}',
            },
          },
          {
            id: 'process',
            type: 'transform',
            config: {
              mode: 'template',
              template: 'User: ${fetch_user.output.name}',
            },
          },
        ],
        output: {
          result: '${process.output.result}',
        },
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(true);
      expect(result.issues).toHaveLength(0);
    });

    it('should detect references to undefined steps', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {
              mode: 'template',
              template: '${undefined_step.output.data}',
            },
          },
        ],
        output: {
          result: '${step1.output.result}',
        },
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.issues).toHaveLength(1);
      expect(result.issues[0].code).toBe('UNDEFINED_STEP_REFERENCE');
      expect(result.issues[0].agentFeedback).toBeDefined();
      expect(result.issues[0].agentFeedback?.category).toBe('reference');
      expect(result.issues[0].agentFeedback?.allowedValues).toContain('step1');
    });

    it('should allow inputs, env, and secrets references', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: { query: 'string' },
        output_schema: {},
        steps: [
          {
            id: 'api_call',
            type: 'api_rest',
            config: {
              method: 'GET',
              url: '${env.API_BASE_URL}/search',
              headers: {
                Authorization: 'Bearer ${secrets.API_KEY}',
              },
              body: {
                query: '${inputs.query}',
              },
            },
          },
        ],
        output: {},
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(true);
    });
  });

  describe('checkDuplicateIds', () => {
    it('should detect duplicate step IDs', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          { id: 'step1', type: 'transform', config: { mode: 'template' } },
          { id: 'step1', type: 'transform', config: { mode: 'template' } }, // Duplicate
        ],
        output: {},
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.code === 'DUPLICATE_STEP_ID')).toBe(true);
    });

    it('should detect duplicates in parallel blocks', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          { id: 'step1', type: 'transform', config: { mode: 'template' } },
          {
            type: 'parallel',
            steps: [
              { id: 'step1', type: 'transform', config: { mode: 'template' } }, // Duplicate
              { id: 'step2', type: 'transform', config: { mode: 'template' } },
            ],
          },
        ],
        output: {},
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.code === 'DUPLICATE_STEP_ID')).toBe(true);
    });
  });

  describe('checkOutputMapping', () => {
    it('should detect invalid output references', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: { result: 'string' },
        steps: [
          { id: 'step1', type: 'transform', config: { mode: 'template' } },
        ],
        output: {
          result: '${unknown_step.output.data}', // Invalid reference
        },
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.code === 'INVALID_OUTPUT_REFERENCE')).toBe(true);
    });

    it('should allow inputs reference in output', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: { data: 'string' },
        output_schema: { result: 'string' },
        steps: [
          { id: 'step1', type: 'transform', config: { mode: 'template' } },
        ],
        output: {
          result: '${inputs.data}', // Valid inputs reference
        },
      };

      const result = validator.validate(definition);

      // Should not have INVALID_OUTPUT_REFERENCE error for inputs
      const outputRefError = result.issues.find((i) => i.code === 'INVALID_OUTPUT_REFERENCE');
      expect(outputRefError).toBeUndefined();
    });
  });

  describe('conditional step handling', () => {
    it('should validate references in conditional then branch', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          { id: 'check', type: 'api_rest', config: { method: 'GET', url: 'https://api.example.com' } },
          {
            type: 'conditional',
            condition: "${check.output.status} == 'active'",
            then: [
              {
                id: 'process',
                type: 'transform',
                config: {
                  mode: 'template',
                  template: '${undefined_step.output.data}', // Invalid
                },
              },
            ],
          },
        ],
        output: {},
      };

      const result = validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.code === 'UNDEFINED_STEP_REFERENCE')).toBe(true);
    });

    it('should collect step IDs from conditional branches', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          { id: 'check', type: 'api_rest', config: { method: 'GET', url: 'https://api.example.com' } },
          {
            type: 'conditional',
            condition: "${check.output.status} == 'active'",
            then: [
              { id: 'then_step', type: 'transform', config: { mode: 'template' } },
            ],
            else: [
              { id: 'else_step', type: 'transform', config: { mode: 'template' } },
            ],
          },
          {
            id: 'final',
            type: 'transform',
            config: {
              mode: 'template',
              template: '${then_step.output.result ?? else_step.output.result}',
            },
          },
        ],
        output: {
          result: '${final.output.result}',
        },
      };

      const result = validator.validate(definition);

      // Should be valid - then_step and else_step are defined in conditional
      expect(result.valid).toBe(true);
    });
  });

  describe('agentFeedback generation', () => {
    it('should provide fix example for undefined step reference', () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          { id: 'valid_step', type: 'transform', config: { mode: 'template' } },
          {
            id: 'ref_step',
            type: 'transform',
            config: {
              mode: 'template',
              template: '${invalid_step.output.data}',
            },
          },
        ],
        output: {},
      };

      const result = validator.validate(definition);
      const issue = result.issues.find((i) => i.code === 'UNDEFINED_STEP_REFERENCE');

      expect(issue?.agentFeedback).toBeDefined();
      expect(issue?.agentFeedback?.fixExample).toContain('valid_step');
    });
  });
});
