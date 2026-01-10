/**
 * Unit Tests for Context Manager
 *
 * Tests coalesce chain resolution and circular reference detection.
 *
 * @module tests/unit/engine/context/context-manager
 * @see Issue #349
 */

import {
  ContextManager,
  createContext,
  MAX_COALESCE_REFERENCES,
} from '../../../../src/engine/context/context-manager';

describe('ContextManager', () => {
  let context: ContextManager;

  beforeEach(() => {
    context = createContext({ test_input: 'value' });
  });

  // ============================================================
  // Basic Reference Resolution
  // ============================================================

  describe('Basic Reference Resolution', () => {
    it('should resolve inputs reference', async () => {
      const result = await context.resolveReference('inputs.test_input');
      expect(result).toBe('value');
    });

    it('should resolve node output reference', async () => {
      context.setOutput('node1', { result: 'output_value' });
      const result = await context.resolveReference('node1.output.result');
      expect(result).toBe('output_value');
    });

    it('should return default value when reference is undefined', async () => {
      const result = await context.resolveReference("inputs.missing ?? 'default'");
      expect(result).toBe('default');
    });
  });

  // ============================================================
  // Coalesce Chain Tests
  // ============================================================

  describe('Coalesce Chain Resolution', () => {
    it('should resolve first non-null value in chain', async () => {
      context.setOutput('a', null);
      context.setOutput('b', { result: 'value_b' });
      context.setOutput('c', { result: 'value_c' });

      const result = await context.resolveReference(
        'a.output.result ?? b.output.result ?? c.output.result'
      );
      expect(result).toBe('value_b');
    });

    it('should return literal default as last fallback', async () => {
      context.setOutput('a', null);
      context.setOutput('b', null);

      const result = await context.resolveReference(
        "a.output.result ?? b.output.result ?? 'fallback'"
      );
      expect(result).toBe('fallback');
    });

    it('should return first value if not null', async () => {
      context.setOutput('a', { result: 'first' });
      context.setOutput('b', { result: 'second' });

      const result = await context.resolveReference(
        'a.output.result ?? b.output.result'
      );
      expect(result).toBe('first');
    });

    it('should handle numeric default value', async () => {
      const result = await context.resolveReference('inputs.missing ?? 42');
      expect(result).toBe(42);
    });

    it('should handle boolean default value', async () => {
      const result = await context.resolveReference('inputs.missing ?? true');
      expect(result).toBe(true);
    });

    it('should handle null default value', async () => {
      const result = await context.resolveReference('inputs.missing ?? null');
      expect(result).toBeNull();
    });
  });

  // ============================================================
  // Coalesce Chain Security Tests
  // ============================================================

  describe('Coalesce Chain Security', () => {
    it('should limit coalesce chain length', async () => {
      // Create a chain with 15 references (exceeds MAX_COALESCE_REFERENCES = 10)
      const refs = Array(15)
        .fill(null)
        .map((_, i) => `ref${i}.output.result`);
      const longChain = refs.join(' ?? ');

      await expect(context.resolveReference(longChain)).rejects.toThrow(
        /exceeds maximum length/
      );
    });

    it('should allow chain of exactly MAX_COALESCE_REFERENCES', async () => {
      // Create a chain with exactly 10 references
      const refs = Array(MAX_COALESCE_REFERENCES)
        .fill(null)
        .map((_, i) => `ref${i}.output.result`);
      const validChain = refs.join(' ?? ');

      // Set one of the outputs to ensure it resolves
      context.setOutput('ref5', { result: 'found' });

      const result = await context.resolveReference(validChain);
      expect(result).toBe('found');
    });

    it('should export MAX_COALESCE_REFERENCES constant', () => {
      expect(MAX_COALESCE_REFERENCES).toBe(10);
    });
  });

  // ============================================================
  // Reference Resolution Behavior Tests
  // ============================================================

  describe('Reference Resolution Behavior', () => {
    it('should handle same reference appearing multiple times in chain', async () => {
      // ${a ?? a} - 'a' appears twice, should just return undefined
      // (each reference is processed independently)
      const result = await context.resolveReference('a.output ?? a.output');
      expect(result).toBeUndefined();
    });

    it('should allow same reference appearing after resolution completes', async () => {
      // ${a ?? b ?? a} - 'a' appears twice but first one is resolved first
      // Since first 'a' resolves to null/undefined, we continue to 'b'
      // After 'b' is resolved, we can try 'a' again (it's been removed from tracking)
      context.setOutput('a', null);
      context.setOutput('b', { result: 'value_b' });

      const result = await context.resolveReference(
        'a.output.result ?? b.output.result ?? a.output.result'
      );
      expect(result).toBe('value_b');
    });

    it('should handle non-existent references gracefully', async () => {
      // References to nodes that don't exist should return undefined
      const result = await context.resolveReference('nonexistent.output.result');
      expect(result).toBeUndefined();
    });
  });

  // ============================================================
  // Edge Cases
  // ============================================================

  describe('Edge Cases', () => {
    it('should handle empty object as value', async () => {
      context.setOutput('empty', {});
      const result = await context.resolveReference('empty.output.result ?? "default"');
      expect(result).toBe('default');
    });

    it('should handle empty array as value', async () => {
      context.setOutput('arr', { result: [] });
      const result = await context.resolveReference('arr.output.result');
      expect(result).toEqual([]);
    });

    it('should handle whitespace in coalesce chain', async () => {
      context.setOutput('a', { result: 'value_a' });
      const result = await context.resolveReference(
        '  a.output.result   ??   "default"  '
      );
      expect(result).toBe('value_a');
    });

    it('should handle mixed reference and literal values', async () => {
      const result = await context.resolveReference(
        "inputs.missing ?? inputs.also_missing ?? 'literal_default'"
      );
      expect(result).toBe('literal_default');
    });
  });
});
