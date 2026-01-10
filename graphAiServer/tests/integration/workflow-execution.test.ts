/**
 * Integration Tests for Workflow Execution
 *
 * These tests verify the complete workflow execution pipeline.
 *
 * @module tests/integration/workflow-execution
 * @see Issue #348
 */

import { parseWorkflow } from '../../src/engine/parser/workflow-parser';
import { executeWorkflow, hasWorkflowErrors, getWorkflowOutput } from '../../src/engine/executor/workflow-executor';

describe('Workflow Execution Integration', () => {
  // ============================================================
  // Sequential Workflow Tests
  // ============================================================

  describe('Sequential Workflow', () => {
    it('should execute a simple sequential workflow with transforms', async () => {
      const definition = {
        workflow_name: 'sequential_test',
        input_schema: { name: 'string', greeting: 'string' },
        output_schema: { message: 'string' },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: {
              mode: 'template',
              template: '{{greeting}}, {{name}}!',
            },
            params: {
              greeting: '${inputs.greeting}',
              name: '${inputs.name}',
            },
          },
          {
            id: 'step2',
            type: 'transform',
            config: {
              mode: 'template',
              template: 'Final: {{previous}}',
            },
            params: {
              previous: '${step1.output.result}',
            },
          },
        ],
        output: {
          message: '${step2.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      expect(parseResult.success).toBe(true);

      const result = await executeWorkflow(parseResult.workflow!, {
        name: 'World',
        greeting: 'Hello',
      });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.message).toBe('Final: Hello, World!');
    });

    it('should pass data between sequential steps', async () => {
      const definition = {
        workflow_name: 'data_chain',
        input_schema: { count: 'number' },
        output_schema: { doubled: 'string' },
        steps: [
          {
            id: 'format_number',
            type: 'transform',
            config: {
              mode: 'template',
              template: 'Count is {{count}}',
            },
            params: {
              count: '${inputs.count}',
            },
          },
          {
            id: 'wrap_result',
            type: 'transform',
            config: {
              mode: 'template',
              template: '[{{message}}]',
            },
            params: {
              message: '${format_number.output.result}',
            },
          },
        ],
        output: {
          doubled: '${wrap_result.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, { count: 42 });

      const output = getWorkflowOutput(result);
      expect(output?.doubled).toBe('[Count is 42]');
    });
  });

  // ============================================================
  // Parallel Workflow Tests
  // ============================================================

  describe('Parallel Workflow', () => {
    it('should execute parallel steps and collect results', async () => {
      const definition = {
        workflow_name: 'parallel_test',
        input_schema: { prefix: 'string' },
        output_schema: { result_a: 'string', result_b: 'string' },
        steps: [
          {
            type: 'parallel',
            steps: [
              {
                id: 'branch_a',
                type: 'transform',
                config: {
                  mode: 'template',
                  template: 'A: {{prefix}}',
                },
                params: { prefix: '${inputs.prefix}' },
              },
              {
                id: 'branch_b',
                type: 'transform',
                config: {
                  mode: 'template',
                  template: 'B: {{prefix}}',
                },
                params: { prefix: '${inputs.prefix}' },
              },
            ],
          },
        ],
        output: {
          result_a: '${branch_a.output.result}',
          result_b: '${branch_b.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, { prefix: 'Test' });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.result_a).toBe('A: Test');
      expect(output?.result_b).toBe('B: Test');
    });
  });

  // ============================================================
  // Mixed Pattern Tests
  // ============================================================

  describe('Mixed Pattern (Sequential + Parallel)', () => {
    it('should execute sequential step followed by parallel steps', async () => {
      const definition = {
        workflow_name: 'mixed_pattern',
        input_schema: { base: 'string' },
        output_schema: { combined: 'string' },
        steps: [
          // Sequential: prepare base
          {
            id: 'prepare',
            type: 'transform',
            config: {
              mode: 'template',
              template: 'Base: {{base}}',
            },
            params: { base: '${inputs.base}' },
          },
          // Parallel: branch processing
          {
            type: 'parallel',
            steps: [
              {
                id: 'upper',
                type: 'transform',
                config: {
                  mode: 'template',
                  template: 'UPPER({{value}})',
                },
                params: { value: '${prepare.output.result}' },
              },
              {
                id: 'lower',
                type: 'transform',
                config: {
                  mode: 'template',
                  template: 'lower({{value}})',
                },
                params: { value: '${prepare.output.result}' },
              },
            ],
          },
          // Sequential: combine
          {
            id: 'combine',
            type: 'transform',
            config: {
              mode: 'concat',
              separator: ' | ',
              fields: ['a', 'b'],
            },
            params: {
              a: '${upper.output.result}',
              b: '${lower.output.result}',
            },
          },
        ],
        output: {
          combined: '${combine.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, { base: 'Test' });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.combined).toBe('UPPER(Base: Test) | lower(Base: Test)');
    });
  });

  // ============================================================
  // Error Handling Tests
  // ============================================================

  describe('Error Handling', () => {
    it('should capture errors in workflow result', async () => {
      const definition = {
        workflow_name: 'error_test',
        input_schema: {},
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'failing_step',
            type: 'transform',
            config: {
              mode: 'map',
              source_field: 'items',
              template: '{{this}}',
            },
            params: {
              items: 'not an array', // This will fail
            },
          },
        ],
        output: {
          result: '${failing_step.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {});

      expect(hasWorkflowErrors(result)).toBe(true);
      expect(result.errors['failing_step']).toBeDefined();
      expect(result.errors['failing_step'].code).toBe('INVALID_SOURCE');
    });

    it('should continue after error in parallel step', async () => {
      const definition = {
        workflow_name: 'partial_error',
        input_schema: {},
        output_schema: { ok_result: 'string' },
        steps: [
          {
            type: 'parallel',
            steps: [
              {
                id: 'ok_step',
                type: 'transform',
                config: { mode: 'template', template: 'OK' },
                params: {},
              },
              {
                id: 'fail_step',
                type: 'transform',
                config: { mode: 'template' }, // No template = fail
                params: {},
              },
            ],
          },
        ],
        output: {
          ok_result: '${ok_step.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {});

      // Should have errors but also have success results
      expect(result.errors['fail_step']).toBeDefined();
      expect(result.results['ok_step']).toEqual({ result: 'OK' });
    });
  });

  // ============================================================
  // Output Mapping Tests
  // ============================================================

  describe('Output Mapping', () => {
    it('should correctly map outputs from multiple steps', async () => {
      const definition = {
        workflow_name: 'multi_output',
        input_schema: { x: 'number', y: 'number' },
        output_schema: {
          input_x: 'string',
          input_y: 'string',
          sum_result: 'string',
        },
        steps: [
          {
            id: 'format_x',
            type: 'transform',
            config: { mode: 'template', template: 'X is {{x}}' },
            params: { x: '${inputs.x}' },
          },
          {
            id: 'format_y',
            type: 'transform',
            config: { mode: 'template', template: 'Y is {{y}}' },
            params: { y: '${inputs.y}' },
          },
          {
            id: 'combine',
            type: 'transform',
            config: { mode: 'concat', separator: ' + ', fields: ['a', 'b'] },
            params: {
              a: '${format_x.output.result}',
              b: '${format_y.output.result}',
            },
          },
        ],
        output: {
          input_x: '${format_x.output.result}',
          input_y: '${format_y.output.result}',
          sum_result: '${combine.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, { x: 10, y: 20 });

      const output = getWorkflowOutput(result);
      expect(output).toEqual({
        input_x: 'X is 10',
        input_y: 'Y is 20',
        sum_result: 'X is 10 + Y is 20',
      });
    });
  });

  // ============================================================
  // Context and Variable Resolution Tests
  // ============================================================

  describe('Variable Resolution', () => {
    it('should resolve inputs reference correctly', async () => {
      const definition = {
        workflow_name: 'input_resolution',
        input_schema: {
          user: 'object',
        },
        output_schema: { name: 'string' },
        steps: [
          {
            id: 'extract',
            type: 'transform',
            config: { mode: 'template', template: '{{user.name}}' },
            params: {
              user: '${inputs.user}',
            },
          },
        ],
        output: {
          name: '${extract.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {
        user: { name: 'Alice', age: 30 },
      });

      const output = getWorkflowOutput(result);
      expect(output?.name).toBe('Alice');
    });

    it('should handle default values in references', async () => {
      const definition = {
        workflow_name: 'default_values',
        input_schema: {},
        output_schema: { value: 'string' },
        steps: [
          {
            id: 'with_default',
            type: 'transform',
            config: { mode: 'template', template: 'Value: {{value}}' },
            params: {
              value: "${inputs.missing ?? 'default_value'}",
            },
          },
        ],
        output: {
          value: '${with_default.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {});

      const output = getWorkflowOutput(result);
      expect(output?.value).toBe('Value: default_value');
    });
  });

  // ============================================================
  // Issue #349 Tests: Transform/Conditional Enhancements
  // ============================================================

  describe('Issue #349: Map Mode @index Helper', () => {
    it('should support @index in map mode', async () => {
      const definition = {
        workflow_name: 'map_with_index',
        input_schema: { products: 'array' },
        output_schema: { numbered_list: 'array' },
        steps: [
          {
            id: 'create_list',
            type: 'transform',
            config: {
              mode: 'map',
              source_field: 'products',
              template: '{{@index}}. {{name}}',
            },
            params: {
              products: '${inputs.products}',
            },
          },
        ],
        output: {
          numbered_list: '${create_list.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      expect(parseResult.success).toBe(true);

      const result = await executeWorkflow(parseResult.workflow!, {
        products: [{ name: 'Apple' }, { name: 'Banana' }, { name: 'Cherry' }],
      });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.numbered_list).toEqual(['0. Apple', '1. Banana', '2. Cherry']);
    });

    it('should support @last in map mode', async () => {
      const definition = {
        workflow_name: 'map_with_last',
        input_schema: { items: 'array' },
        output_schema: { formatted: 'array' },
        steps: [
          {
            id: 'format_list',
            type: 'transform',
            config: {
              mode: 'map',
              source_field: 'items',
              template: '{{name}}{{#if @last}} (end){{/if}}',
            },
            params: {
              items: '${inputs.items}',
            },
          },
        ],
        output: {
          formatted: '${format_list.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {
        items: [{ name: 'A' }, { name: 'B' }, { name: 'C' }],
      });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.formatted).toEqual(['A', 'B', 'C (end)']);
    });
  });

  describe('Issue #349: Merge Mode JSON Auto-Parse', () => {
    it('should auto-parse JSON strings in merge mode', async () => {
      const definition = {
        workflow_name: 'merge_json_parse',
        input_schema: { user_settings: 'object' },
        output_schema: { merged: 'object' },
        steps: [
          {
            id: 'create_defaults',
            type: 'transform',
            config: {
              mode: 'template',
              template: '{"theme": "light", "language": "ja"}',
            },
            params: {},
          },
          {
            id: 'merge_settings',
            type: 'transform',
            config: {
              mode: 'merge',
              strategy: 'shallow',
            },
            params: {
              defaults: '${create_defaults.output.result}',
              user: '${inputs.user_settings}',
            },
          },
        ],
        output: {
          merged: '${merge_settings.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      expect(parseResult.success).toBe(true);

      const result = await executeWorkflow(parseResult.workflow!, {
        user_settings: { theme: 'dark' },
      });

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect((output?.merged as Record<string, unknown>).theme).toBe('dark');
      expect((output?.merged as Record<string, unknown>).language).toBe('ja');
    });
  });

  describe('Issue #349: Coalesce Chain', () => {
    it('should resolve coalesce chain with first valid value', async () => {
      const definition = {
        workflow_name: 'coalesce_chain',
        input_schema: {},
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: { mode: 'template', template: 'Value A' },
            params: {},
          },
        ],
        output: {
          result: "${step_a.output.result ?? 'fallback'}",
        },
      };

      const parseResult = parseWorkflow(definition);
      const result = await executeWorkflow(parseResult.workflow!, {});

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.result).toBe('Value A');
    });

    it('should use fallback when input is undefined', async () => {
      const definition = {
        workflow_name: 'coalesce_fallback',
        input_schema: { optional_value: 'string' },
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'step_a',
            type: 'transform',
            config: { mode: 'template', template: 'Value: {{value}}' },
            params: {
              value: "${inputs.optional_value ?? 'default_value'}",
            },
          },
        ],
        output: {
          result: '${step_a.output.result}',
        },
      };

      const parseResult = parseWorkflow(definition);
      expect(parseResult.success).toBe(true);

      const result = await executeWorkflow(parseResult.workflow!, {});

      expect(hasWorkflowErrors(result)).toBe(false);

      const output = getWorkflowOutput(result);
      expect(output?.result).toBe('Value: default_value');
    });
  });
});
