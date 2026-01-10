/**
 * Unit Tests for Transform Node
 *
 * @module tests/unit/nodes/test-transform-node
 * @see Issue #348
 */

import { TransformNode, createTransformNode } from '../../../src/nodes/transform-node';
import { ContextManager } from '../../../src/engine/context/context-manager';
import type { TransformStep } from '../../../src/types/taskflow';

describe('TransformNode', () => {
  let context: ContextManager;

  beforeEach(() => {
    context = new ContextManager({ name: 'Test User', count: 5 });
  });

  // ============================================================
  // Template Mode
  // ============================================================

  describe('Template Mode', () => {
    it('should expand a simple template', async () => {
      const step: TransformStep = {
        id: 'format_greeting',
        type: 'transform',
        config: {
          mode: 'template',
          template: 'Hello, {{name}}!',
        },
        params: {
          name: '${inputs.name}',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'Hello, Test User!' });
    });

    it('should handle template with multiple variables', async () => {
      const step: TransformStep = {
        id: 'format_message',
        type: 'transform',
        config: {
          mode: 'template',
          template: '{{name}} has {{count}} items.',
        },
        params: {
          name: '${inputs.name}',
          count: '${inputs.count}',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'Test User has 5 items.' });
    });

    it('should handle template with conditionals', async () => {
      const step: TransformStep = {
        id: 'conditional_message',
        type: 'transform',
        config: {
          mode: 'template',
          template: '{{#if hasItems}}You have items{{else}}No items{{/if}}',
        },
        params: {
          hasItems: true,
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'You have items' });
    });

    it('should handle template with each block', async () => {
      const step: TransformStep = {
        id: 'list_items',
        type: 'transform',
        config: {
          mode: 'template',
          template: '{{#each items}}{{this}},{{/each}}',
        },
        params: {
          items: ['a', 'b', 'c'],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'a,b,c,' });
    });

    it('should fail for missing template', async () => {
      const step: TransformStep = {
        id: 'no_template',
        type: 'transform',
        config: {
          mode: 'template',
        },
        params: {},
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('TEMPLATE_ERROR');
    });
  });

  // ============================================================
  // Concat Mode
  // ============================================================

  describe('Concat Mode', () => {
    it('should concatenate strings with default separator', async () => {
      const step: TransformStep = {
        id: 'concat_strings',
        type: 'transform',
        config: {
          mode: 'concat',
          fields: ['a', 'b', 'c'],
        },
        params: {
          a: 'first',
          b: 'second',
          c: 'third',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'first, second, third' });
    });

    it('should concatenate with custom separator', async () => {
      const step: TransformStep = {
        id: 'concat_custom',
        type: 'transform',
        config: {
          mode: 'concat',
          separator: ' | ',
          fields: ['x', 'y'],
        },
        params: {
          x: 'A',
          y: 'B',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'A | B' });
    });

    it('should flatten and concatenate arrays', async () => {
      const step: TransformStep = {
        id: 'concat_arrays',
        type: 'transform',
        config: {
          mode: 'concat',
          fields: ['arr1', 'arr2'],
        },
        params: {
          arr1: ['a', 'b'],
          arr2: ['c', 'd'],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      // Mixed types return as array
      expect(result.output).toEqual({ result: 'a, b, c, d' });
    });
  });

  // ============================================================
  // Map Mode
  // ============================================================

  describe('Map Mode', () => {
    it('should map array elements with template', async () => {
      const step: TransformStep = {
        id: 'map_items',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '- {{name}}: {{value}}',
        },
        params: {
          items: [
            { name: 'Item 1', value: 100 },
            { name: 'Item 2', value: 200 },
          ],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['- Item 1: 100', '- Item 2: 200'],
      });
    });

    it('should provide index in map template', async () => {
      const step: TransformStep = {
        id: 'map_with_index',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '{{index}}: {{name}}',
        },
        params: {
          items: [{ name: 'a', index: 0 }, { name: 'b', index: 1 }, { name: 'c', index: 2 }],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['0: a', '1: b', '2: c'],
      });
    });

    it('should fail for non-array source', async () => {
      const step: TransformStep = {
        id: 'map_invalid',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '{{this}}',
        },
        params: {
          items: 'not an array',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('INVALID_SOURCE');
    });
  });

  // ============================================================
  // Merge Mode
  // ============================================================

  describe('Merge Mode', () => {
    it('should shallow merge objects', async () => {
      const step: TransformStep = {
        id: 'merge_shallow',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'shallow',
        },
        params: {
          obj1: { a: 1, b: 2 },
          obj2: { c: 3 },
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect((result.output as any).result).toMatchObject({ a: 1, b: 2, c: 3 });
    });

    it('should deep merge objects', async () => {
      const step: TransformStep = {
        id: 'merge_deep',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'deep',
        },
        params: {
          base: { config: { timeout: 30 } },
          override: { config: { retries: 3 } },
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
    });
  });

  // ============================================================
  // Execution Logging
  // ============================================================

  describe('Execution Logging', () => {
    it('should include log in result', async () => {
      const step: TransformStep = {
        id: 'with_log',
        type: 'transform',
        config: {
          mode: 'template',
          template: 'test',
        },
        params: {},
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.log).toBeDefined();
      expect(result.log.nodeId).toBe('with_log');
      expect(result.log.state).toBe('completed');
      expect(result.log.startTime).toBeLessThanOrEqual(result.log.endTime);
    });
  });

  // ============================================================
  // Handlebars Helpers
  // ============================================================

  describe('Handlebars Helpers', () => {
    it('should support eq helper', async () => {
      const step: TransformStep = {
        id: 'eq_helper',
        type: 'transform',
        config: {
          mode: 'template',
          template: '{{#if (eq status "active")}}Active{{else}}Inactive{{/if}}',
        },
        params: {
          status: 'active',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'Active' });
    });

    it('should support json helper', async () => {
      const step: TransformStep = {
        id: 'json_helper',
        type: 'transform',
        config: {
          mode: 'template',
          template: 'Data: {{{json data}}}',
        },
        params: {
          data: { key: 'value' },
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect((result.output as any).result).toContain('"key":"value"');
    });

    it('should support length helper', async () => {
      const step: TransformStep = {
        id: 'length_helper',
        type: 'transform',
        config: {
          mode: 'template',
          template: 'Count: {{length items}}',
        },
        params: {
          items: [1, 2, 3, 4, 5],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 'Count: 5' });
    });
  });

  // ============================================================
  // Map Mode @index Helper Tests (Issue #349)
  // ============================================================

  describe('Map Mode @index Helper (Issue #349)', () => {
    it('should support @index helper in map mode', async () => {
      const step: TransformStep = {
        id: 'map_with_at_index',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '{{@index}}. {{name}}',
        },
        params: {
          items: [{ name: 'apple' }, { name: 'banana' }, { name: 'cherry' }],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['0. apple', '1. banana', '2. cherry'],
      });
    });

    it('should support @first helper in map mode', async () => {
      const step: TransformStep = {
        id: 'map_with_at_first',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '{{name}}{{#if @first}} (first){{/if}}',
        },
        params: {
          items: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['a (first)', 'b', 'c'],
      });
    });

    it('should support @last helper in map mode', async () => {
      const step: TransformStep = {
        id: 'map_with_at_last',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'items',
          template: '{{name}}{{#if @last}} (last){{/if}}',
        },
        params: {
          items: [{ name: 'x' }, { name: 'y' }, { name: 'z' }],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['x', 'y', 'z (last)'],
      });
    });

    it('should support combined @index, @first, @last in map mode', async () => {
      const step: TransformStep = {
        id: 'map_combined_helpers',
        type: 'transform',
        config: {
          mode: 'map',
          source_field: 'products',
          template: '{{@index}}. {{name}}{{#if @last}} (last item){{/if}}',
        },
        params: {
          products: [
            { name: 'apple' },
            { name: 'banana' },
            { name: 'cherry' },
          ],
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        result: ['0. apple', '1. banana', '2. cherry (last item)'],
      });
    });
  });

  // ============================================================
  // Merge Mode JSON Auto-Parse Tests (Issue #349)
  // ============================================================

  describe('Merge Mode JSON Auto-Parse (Issue #349)', () => {
    it('should auto-parse JSON string parameters in merge mode', async () => {
      const step: TransformStep = {
        id: 'merge_json_string',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'shallow',
        },
        params: {
          defaults: '{"theme": "light", "language": "ja"}',
          user_prefs: { theme: 'dark' },
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      const output = (result.output as { result: Record<string, unknown> }).result;
      expect(output.theme).toBe('dark');
      expect(output.language).toBe('ja');
    });

    it('should handle deep merge with JSON string', async () => {
      const step: TransformStep = {
        id: 'merge_deep_json',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'deep',
        },
        params: {
          base: '{"config": {"timeout": 30, "retries": 3}}',
          override: { config: { timeout: 60 } },
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      const output = (result.output as { result: Record<string, unknown> }).result;
      expect((output.config as Record<string, unknown>).timeout).toBe(60);
      expect((output.config as Record<string, unknown>).retries).toBe(3);
    });

    it('should handle invalid JSON gracefully as string', async () => {
      const step: TransformStep = {
        id: 'merge_invalid_json',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'shallow',
        },
        params: {
          valid: { a: 1 },
          invalid: 'not valid json',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      const output = (result.output as { result: Record<string, unknown> }).result;
      expect(output.a).toBe(1);
      expect(output.invalid).toBe('not valid json');
    });

    it('should handle JSON array string', async () => {
      const step: TransformStep = {
        id: 'merge_json_array',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'shallow',
        },
        params: {
          obj: { key: 'value' },
          arr: '[1, 2, 3]',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      const output = (result.output as { result: Record<string, unknown> }).result;
      expect(output.key).toBe('value');
      // Arrays should be preserved as-is (not merged into object)
      expect(output.arr).toEqual([1, 2, 3]);
    });

    it('should handle whitespace around JSON', async () => {
      const step: TransformStep = {
        id: 'merge_json_whitespace',
        type: 'transform',
        config: {
          mode: 'merge',
          strategy: 'shallow',
        },
        params: {
          config: '  { "setting": true }  ',
        },
      };

      const node = createTransformNode(step);
      const result = await node.execute(context);

      expect(result.success).toBe(true);
      const output = (result.output as { result: Record<string, unknown> }).result;
      expect(output.setting).toBe(true);
    });
  });
});
