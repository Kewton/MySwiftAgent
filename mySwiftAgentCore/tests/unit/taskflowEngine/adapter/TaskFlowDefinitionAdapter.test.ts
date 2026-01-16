/**
 * TaskFlowDefinitionAdapter Unit Tests
 *
 * Issue #363: Type conversion adapter tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  TaskFlowDefinitionAdapter,
} from '../../../../src/taskflowEngine/adapter/TaskFlowDefinitionAdapter.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('TaskFlowDefinitionAdapter', () => {
  const sampleTaskFlowDefinition: TaskFlowDefinition = {
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
        params: {
          user_id: '${input.user_id}',
        },
      },
      {
        id: 'transform_data',
        type: 'transform',
        description: 'Transform user data',
        config: {
          template: '{"name": "{{fetch_user.output.name}}"}',
        },
        params: {
          source: '${fetch_user.output}',
        },
      },
    ],
    output: {
      result: '${transform_data.output}',
    },
  };

  describe('toInternal', () => {
    it('should convert TaskFlowDefinition to InternalWorkflowDefinition', () => {
      const internal = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);

      expect(internal.name).toBe('user_analysis_workflow');
      expect(internal.version).toBe('1.0.0');
      expect(internal.inputSchema).toEqual(sampleTaskFlowDefinition.input_schema);
      expect(internal.outputSchema).toEqual(sampleTaskFlowDefinition.output_schema);
      expect(internal.outputMapping).toEqual(sampleTaskFlowDefinition.output);
    });

    it('should generate a unique id', () => {
      const internal1 = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);
      const internal2 = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);

      expect(internal1.id).toContain('wf_user_analysis_workflow_');
      expect(internal1.id).not.toBe(internal2.id);
    });

    it('should convert steps with proper structure', () => {
      const internal = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);

      expect(internal.steps).toHaveLength(2);
      expect(internal.steps[0]?.id).toBe('fetch_user');
      expect(internal.steps[0]?.name).toBe('Fetch user data');
      expect(internal.steps[0]?.type).toBe('api_rest');
    });

    it('should extract dependencies from params', () => {
      const internal = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);

      // transform_data depends on fetch_user
      const transformStep = internal.steps.find(s => s.id === 'transform_data');
      expect(transformStep?.dependsOn).toContain('fetch_user');
    });

    it('should set default timeout', () => {
      const internal = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);
      expect(internal.timeout).toBe(300000);
    });

    it('should use step id as name if description is missing', () => {
      const taskflow: TaskFlowDefinition = {
        ...sampleTaskFlowDefinition,
        steps: [
          {
            id: 'step_without_description',
            type: 'transform',
            config: {},
            params: {},
          },
        ],
      };

      const internal = TaskFlowDefinitionAdapter.toInternal(taskflow);
      expect(internal.steps[0]?.name).toBe('step_without_description');
    });
  });

  describe('toExternal', () => {
    let internalWorkflow: InternalWorkflowDefinition;

    beforeEach(() => {
      internalWorkflow = {
        id: 'wf_test_123',
        name: 'test_workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Step One',
            type: 'api_rest',
            config: { method: 'GET', url: 'https://api.example.com' },
            params: {},
          },
        ],
        inputSchema: {
          type: 'object',
          properties: {
            input_param: { type: 'string', description: 'Input' },
          },
        },
        outputSchema: {
          type: 'object',
          properties: {
            output_param: { type: 'string', description: 'Output' },
          },
        },
        outputMapping: {
          output_param: '${step_1.output}',
        },
        timeout: 60000,
      };
    });

    it('should convert InternalWorkflowDefinition to TaskFlowDefinition', () => {
      const external = TaskFlowDefinitionAdapter.toExternal(internalWorkflow);

      expect(external.workflow_name).toBe('test_workflow');
      expect(external.input_schema).toEqual(internalWorkflow.inputSchema);
      expect(external.output_schema).toEqual(internalWorkflow.outputSchema);
      expect(external.output).toEqual(internalWorkflow.outputMapping);
    });

    it('should convert steps back to TaskFlowStep format', () => {
      const external = TaskFlowDefinitionAdapter.toExternal(internalWorkflow);

      expect(external.steps).toHaveLength(1);
      expect(external.steps[0]?.id).toBe('step_1');
      expect(external.steps[0]?.type).toBe('api_rest');
    });
  });

  describe('roundtrip conversion', () => {
    it('should preserve data through toInternal -> toExternal', () => {
      const internal = TaskFlowDefinitionAdapter.toInternal(sampleTaskFlowDefinition);
      const external = TaskFlowDefinitionAdapter.toExternal(internal);

      expect(external.workflow_name).toBe(sampleTaskFlowDefinition.workflow_name);
      expect(external.input_schema).toEqual(sampleTaskFlowDefinition.input_schema);
      expect(external.output_schema).toEqual(sampleTaskFlowDefinition.output_schema);
      expect(external.output).toEqual(sampleTaskFlowDefinition.output);
      expect(external.steps).toHaveLength(sampleTaskFlowDefinition.steps.length);
    });
  });

  describe('dependency extraction', () => {
    it('should extract multiple dependencies', () => {
      const taskflow: TaskFlowDefinition = {
        workflow_name: 'multi_dep_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          { id: 'step_b', type: 'transform', config: {}, params: {} },
          {
            id: 'step_c',
            type: 'transform',
            config: {},
            params: {
              a: '${step_a.output}',
              b: '${step_b.output}',
            },
          },
        ],
        output: {},
      };

      const internal = TaskFlowDefinitionAdapter.toInternal(taskflow);
      const stepC = internal.steps.find(s => s.id === 'step_c');

      expect(stepC?.dependsOn).toContain('step_a');
      expect(stepC?.dependsOn).toContain('step_b');
      expect(stepC?.dependsOn).toHaveLength(2);
    });

    it('should not duplicate dependencies', () => {
      const taskflow: TaskFlowDefinition = {
        workflow_name: 'dup_dep_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: {
              first: '${step_a.output}',
              second: '${step_a.output.nested}',
            },
          },
        ],
        output: {},
      };

      const internal = TaskFlowDefinitionAdapter.toInternal(taskflow);
      const stepB = internal.steps.find(s => s.id === 'step_b');

      expect(stepB?.dependsOn?.filter(d => d === 'step_a')).toHaveLength(1);
    });

    it('should handle input references without creating dependencies', () => {
      const taskflow: TaskFlowDefinition = {
        workflow_name: 'input_ref_workflow',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: {
              value: '${input.user_id}',
            },
          },
        ],
        output: {},
      };

      const internal = TaskFlowDefinitionAdapter.toInternal(taskflow);
      const stepA = internal.steps.find(s => s.id === 'step_a');

      // input is not a step, so no dependencies
      expect(stepA?.dependsOn).toEqual([]);
    });
  });
});
