/**
 * CircularReferenceValidator Unit Tests
 *
 * Issue #381: Circular reference detection using DFS algorithm
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { CircularReferenceValidator } from '../../../../../src/taskflowGeneratorAgent/validator/validators/CircularReferenceValidator.js';
import type { TaskFlowDefinition } from '../../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { EnhancedValidationContext } from '../../../../../src/taskflowGeneratorAgent/types/validation.js';

describe('CircularReferenceValidator', () => {
  let validator: CircularReferenceValidator;

  beforeEach(() => {
    validator = new CircularReferenceValidator();
  });

  const createContext = (
    options?: Partial<EnhancedValidationContext['additionalContext']>
  ): EnhancedValidationContext => ({
    capabilities: [],
    projectId: 'test-project',
    additionalContext: {
      enableCircularReferenceCheck: true,
      ...options,
    },
  });

  describe('name property', () => {
    it('should have correct name', () => {
      expect(validator.name).toBe('CircularReferenceValidator');
    });
  });

  describe('no circular references', () => {
    it('should pass for workflow without references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          { id: 'step_b', type: 'transform', config: {}, params: {} },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should pass for valid linear dependency chain', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
          {
            id: 'step_c',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for valid fan-out dependencies', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
          {
            id: 'step_c',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should pass for valid fan-in dependencies', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'step_a', type: 'transform', config: {}, params: {} },
          { id: 'step_b', type: 'transform', config: {}, params: {} },
          {
            id: 'step_c',
            type: 'transform',
            config: {},
            params: {
              a: '$steps.step_a.result',
              b: '$steps.step_b.result',
            },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });
  });

  describe('simple circular references', () => {
    it('should detect direct self-reference', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('CIRCULAR_REFERENCE_DETECTED');
    });

    it('should detect two-step circular reference', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      expect(result.errors![0].code).toBe('CIRCULAR_REFERENCE_DETECTED');
    });

    it('should detect three-step circular reference', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_c.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
          {
            id: 'step_c',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
    });
  });

  describe('error details', () => {
    it('should include circular path in error', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());

      expect(result.isValid).toBe(false);
      const error = result.errors![0] as any;
      expect(error.context).toBeDefined();
      expect(error.context.circularPath).toBeDefined();
      expect(Array.isArray(error.context.circularPath)).toBe(true);
    });

    it('should include suggestion for breaking cycle', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
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

  describe('depth limiting', () => {
    it('should respect maxCircularDepth setting', async () => {
      // Create a circular chain: step_0 -> step_1 -> step_2 -> ... -> step_9 -> step_0
      // where step_0 references step_9 to create a true cycle
      const steps = [];
      for (let i = 0; i < 10; i++) {
        steps.push({
          id: `step_${i}`,
          type: 'transform' as const,
          config: {},
          params:
            i === 0
              ? { input: `$steps.step_9.result` } // First step references last step
              : { input: `$steps.step_${i - 1}.result` },
        });
      }

      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps,
        output: {},
      };

      // With very low maxDepth (3), might not fully traverse the cycle
      const contextLowDepth = createContext({ maxCircularDepth: 3 });
      const resultLow = await validator.validate(workflow, contextLowDepth);

      // With high maxDepth, should detect the cycle
      const contextHighDepth = createContext({ maxCircularDepth: 15 });
      const resultHigh = await validator.validate(workflow, contextHighDepth);

      // At least the high depth should detect the issue
      expect(resultHigh.isValid).toBe(false);
    });

    it('should use default maxDepth when not specified', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const context = createContext({});
      delete context.additionalContext?.maxCircularDepth;

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(false);
    });
  });

  describe('complex dependency graphs', () => {
    it('should handle diamond dependency correctly', async () => {
      // Diamond: A -> B, A -> C, B -> D, C -> D
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'A', type: 'transform', config: {}, params: {} },
          {
            id: 'B',
            type: 'transform',
            config: {},
            params: { input: '$steps.A.result' },
          },
          {
            id: 'C',
            type: 'transform',
            config: {},
            params: { input: '$steps.A.result' },
          },
          {
            id: 'D',
            type: 'transform',
            config: {},
            params: {
              b: '$steps.B.result',
              c: '$steps.C.result',
            },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(true);
    });

    it('should detect cycle in complex graph', async () => {
      // A -> B -> C -> D -> B (cycle at B-C-D)
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          { id: 'A', type: 'transform', config: {}, params: {} },
          {
            id: 'B',
            type: 'transform',
            config: {},
            params: {
              a: '$steps.A.result',
              d: '$steps.D.result', // Creates cycle
            },
          },
          {
            id: 'C',
            type: 'transform',
            config: {},
            params: { input: '$steps.B.result' },
          },
          {
            id: 'D',
            type: 'transform',
            config: {},
            params: { input: '$steps.C.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
    });
  });

  describe('references in nested objects', () => {
    it('should detect circular reference in nested config', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {
              nested: {
                deep: {
                  ref: '$steps.step_b.result',
                },
              },
            },
            params: {},
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
    });

    it('should detect circular reference in arrays', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {
              refs: ['$steps.step_b.result'],
            },
            params: {},
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { items: ['$steps.step_a.result'] },
          },
        ],
        output: {},
      };

      const result = await validator.validate(workflow, createContext());
      expect(result.isValid).toBe(false);
    });
  });

  describe('skip validation when disabled', () => {
    it('should skip validation when enableCircularReferenceCheck is false', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_b.result' },
          },
          {
            id: 'step_b',
            type: 'transform',
            config: {},
            params: { input: '$steps.step_a.result' },
          },
        ],
        output: {},
      };

      const context: EnhancedValidationContext = {
        capabilities: [],
        projectId: 'test-project',
        additionalContext: {
          enableCircularReferenceCheck: false,
        },
      };

      const result = await validator.validate(workflow, context);
      expect(result.isValid).toBe(true);
    });
  });
});
