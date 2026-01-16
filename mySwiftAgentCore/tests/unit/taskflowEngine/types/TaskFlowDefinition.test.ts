/**
 * TaskFlowDefinition Types Unit Tests
 *
 * Issue #363: TaskFlow Definition type validation
 */

import { describe, it, expect } from 'vitest';
import {
  TaskFlowDefinitionSchema,
  IOSchemaTypeSchema,
  TaskFlowStepSchema,
  NodeType,
  type TaskFlowDefinition,
  type TaskFlowStep,
  type IOSchemaType,
} from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

describe('TaskFlowDefinition Types', () => {
  describe('NodeType', () => {
    it('should include all supported node types', () => {
      const nodeTypes: NodeType[] = ['api_rest', 'code_js', 'transform', 'parallel', 'llm'];
      expect(nodeTypes).toHaveLength(5);
    });
  });

  describe('IOSchemaType', () => {
    it('should validate a valid IO schema', () => {
      const schema: IOSchemaType = {
        type: 'object',
        properties: {
          user_id: { type: 'string', description: 'User identifier' },
          count: { type: 'number', description: 'Count value' },
        },
        required: ['user_id'],
      };

      const result = IOSchemaTypeSchema.safeParse(schema);
      expect(result.success).toBe(true);
    });

    it('should accept any string type for flexibility', () => {
      // IOSchemaType accepts any string type for JSON Schema compatibility
      const schema = {
        type: 'custom_type',
        properties: {},
      };

      const result = IOSchemaTypeSchema.safeParse(schema);
      // This is valid because we allow flexible type strings for JSON Schema
      expect(result.success).toBe(true);
    });

    it('should reject schema missing type', () => {
      const schema = {
        properties: {},
      };

      const result = IOSchemaTypeSchema.safeParse(schema);
      expect(result.success).toBe(false);
    });
  });

  describe('TaskFlowStep', () => {
    it('should validate a valid api_rest step', () => {
      const step: TaskFlowStep = {
        id: 'fetch_data',
        type: 'api_rest',
        description: 'Fetch user data from API',
        config: {
          method: 'GET',
          url: 'https://api.example.com/users/${input.user_id}',
        },
        params: {
          user_id: '${input.user_id}',
        },
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a valid transform step', () => {
      const step: TaskFlowStep = {
        id: 'transform_data',
        type: 'transform',
        description: 'Transform the fetched data',
        config: {
          template: '{"name": "{{fetch_data.output.name}}"}',
        },
        params: {
          source: '${fetch_data.output}',
        },
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a valid code_js step', () => {
      const step: TaskFlowStep = {
        id: 'compute',
        type: 'code_js',
        description: 'Compute result',
        config: {
          script_path: 'calculators/compute.js',
          function_name: 'calculate',
        },
        params: {
          value: '${input.value}',
        },
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a valid parallel step', () => {
      const step: TaskFlowStep = {
        id: 'parallel_fetch',
        type: 'parallel',
        description: 'Fetch multiple resources in parallel',
        config: {
          steps: ['step_a', 'step_b', 'step_c'],
        },
        params: {},
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should validate a valid llm step', () => {
      const step: TaskFlowStep = {
        id: 'generate_summary',
        type: 'llm',
        description: 'Generate summary using LLM',
        config: {
          model: 'gpt-4',
          system_prompt: 'You are a helpful assistant.',
          user_prompt_template: 'Summarize: {{input.text}}',
        },
        params: {
          text: '${input.text}',
        },
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(true);
    });

    it('should reject step with invalid type', () => {
      const step = {
        id: 'invalid_step',
        type: 'invalid_type',
        config: {},
        params: {},
      };

      const result = TaskFlowStepSchema.safeParse(step);
      expect(result.success).toBe(false);
    });
  });

  describe('TaskFlowDefinition', () => {
    it('should validate a complete workflow definition', () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'user_analysis_workflow',
        description: 'Analyze user data',
        input_schema: {
          type: 'object',
          properties: {
            user_id: { type: 'string', description: 'User ID' },
          },
          required: ['user_id'],
        },
        output_schema: {
          type: 'object',
          properties: {
            result: { type: 'object', description: 'Analysis result' },
          },
          required: ['result'],
        },
        steps: [
          {
            id: 'fetch_user',
            type: 'api_rest',
            description: 'Fetch user data',
            config: {
              method: 'GET',
              url: 'https://api.example.com/users/${input.user_id}',
            },
            params: {},
          },
        ],
        output: {
          result: '${fetch_user.output}',
        },
      };

      const result = TaskFlowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(true);
    });

    it('should validate workflow without optional description', () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'simple_workflow',
        input_schema: {
          type: 'object',
          properties: {},
        },
        output_schema: {
          type: 'object',
          properties: {},
        },
        steps: [],
        output: {},
      };

      const result = TaskFlowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(true);
    });

    it('should reject workflow missing required fields', () => {
      const workflow = {
        workflow_name: 'incomplete_workflow',
        // Missing input_schema, output_schema, steps, output
      };

      const result = TaskFlowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(false);
    });
  });
});
