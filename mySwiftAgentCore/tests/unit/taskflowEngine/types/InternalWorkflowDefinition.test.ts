/**
 * InternalWorkflowDefinition Types Unit Tests
 *
 * Issue #363: Internal workflow definition type validation
 */

import { describe, it, expect } from 'vitest';
import {
  InternalWorkflowDefinitionSchema,
  type InternalWorkflowDefinition,
  type InternalWorkflowStep,
} from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('InternalWorkflowDefinition Types', () => {
  describe('InternalWorkflowStep', () => {
    it('should have the correct structure', () => {
      const step: InternalWorkflowStep = {
        id: 'step_1',
        name: 'Step One',
        type: 'api_rest',
        config: { method: 'GET', url: 'https://api.example.com' },
        params: { key: 'value' },
        dependsOn: ['step_0'],
        retryPolicy: {
          maxRetries: 3,
          delayMs: 1000,
          exponentialBackoff: true,
        },
        timeout: 30000,
      };

      expect(step.id).toBe('step_1');
      expect(step.dependsOn).toContain('step_0');
      expect(step.retryPolicy?.maxRetries).toBe(3);
    });
  });

  describe('InternalWorkflowDefinition', () => {
    it('should validate a complete internal workflow', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_123',
        name: 'test_workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Fetch Data',
            type: 'api_rest',
            config: { method: 'GET', url: 'https://api.example.com' },
            params: {},
          },
        ],
        inputSchema: {
          type: 'object',
          properties: {
            user_id: { type: 'string', description: 'User ID' },
          },
        },
        outputSchema: {
          type: 'object',
          properties: {
            result: { type: 'object', description: 'Result' },
          },
        },
        outputMapping: {
          result: '${step_1.output}',
        },
        timeout: 300000,
        variables: { key: 'value' },
      };

      const result = InternalWorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(true);
    });

    it('should validate workflow with minimal required fields', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_minimal',
        name: 'minimal_workflow',
        version: '1.0.0',
        steps: [],
        inputSchema: { type: 'object', properties: {} },
        outputSchema: { type: 'object', properties: {} },
        outputMapping: {},
      };

      const result = InternalWorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(true);
    });

    it('should reject workflow missing required fields', () => {
      const workflow = {
        id: 'wf_incomplete',
        name: 'incomplete',
        // Missing version, steps, schemas, outputMapping
      };

      const result = InternalWorkflowDefinitionSchema.safeParse(workflow);
      expect(result.success).toBe(false);
    });

    it('should extend WorkflowDefinition properties', () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_extended',
        name: 'extended_workflow',
        version: '2.0.0',
        steps: [],
        inputSchema: { type: 'object', properties: {} },
        outputSchema: { type: 'object', properties: {} },
        outputMapping: {},
        timeout: 60000,
        variables: { env: 'test' },
      };

      expect(workflow.timeout).toBe(60000);
      expect(workflow.variables).toEqual({ env: 'test' });
    });
  });
});
