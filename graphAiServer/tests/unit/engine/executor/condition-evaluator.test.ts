/**
 * Tests for Condition Evaluator
 *
 * @module tests/unit/engine/executor/condition-evaluator
 * @see Issue #348
 */

import {
  evaluateCondition,
  parseConditionExpression,
  parseAllowedValue,
  compareValues,
  type ConditionEvaluationResult,
  type ComparisonOperator,
  type AllowedPrimitive,
} from '../../../../src/engine/executor/condition-evaluator.js';
import { ContextManager } from '../../../../src/engine/context/context-manager.js';

describe('Condition Evaluator', () => {
  // ============================================================
  // parseConditionExpression tests
  // ============================================================
  describe('parseConditionExpression', () => {
    it('should parse simple equality expression', () => {
      const result = parseConditionExpression("${user.output.status} == 'active'");
      expect(result).not.toBeNull();
      expect(result?.variable).toBe('user.output.status');
      expect(result?.operator).toBe('==');
      expect(result?.value).toBe('active');
    });

    it('should parse inequality expression', () => {
      const result = parseConditionExpression("${count.output.value} != 0");
      expect(result).not.toBeNull();
      expect(result?.variable).toBe('count.output.value');
      expect(result?.operator).toBe('!=');
      expect(result?.value).toBe(0);
    });

    it('should parse greater than expression', () => {
      const result = parseConditionExpression('${data.output.count} > 100');
      expect(result).not.toBeNull();
      expect(result?.variable).toBe('data.output.count');
      expect(result?.operator).toBe('>');
      expect(result?.value).toBe(100);
    });

    it('should parse less than expression', () => {
      const result = parseConditionExpression('${score.output.value} < 50');
      expect(result).not.toBeNull();
      expect(result?.operator).toBe('<');
      expect(result?.value).toBe(50);
    });

    it('should parse greater than or equal expression', () => {
      const result = parseConditionExpression('${amount.output.total} >= 1000');
      expect(result).not.toBeNull();
      expect(result?.operator).toBe('>=');
      expect(result?.value).toBe(1000);
    });

    it('should parse less than or equal expression', () => {
      const result = parseConditionExpression('${price.output.value} <= 99.99');
      expect(result).not.toBeNull();
      expect(result?.operator).toBe('<=');
      expect(result?.value).toBe(99.99);
    });

    it('should parse boolean true value', () => {
      const result = parseConditionExpression('${flag.output.enabled} == true');
      expect(result?.value).toBe(true);
    });

    it('should parse boolean false value', () => {
      const result = parseConditionExpression('${flag.output.disabled} == false');
      expect(result?.value).toBe(false);
    });

    it('should parse null value', () => {
      const result = parseConditionExpression('${item.output.data} == null');
      expect(result?.value).toBe(null);
    });

    it('should parse negative numbers', () => {
      const result = parseConditionExpression('${temp.output.value} > -10');
      expect(result?.value).toBe(-10);
    });

    it('should parse double-quoted strings', () => {
      const result = parseConditionExpression('${status.output.code} == "success"');
      expect(result?.value).toBe('success');
    });

    it('should return null for invalid expressions', () => {
      expect(parseConditionExpression('invalid expression')).toBeNull();
      expect(parseConditionExpression('${var}')).toBeNull();
      expect(parseConditionExpression('${var} === "value"')).toBeNull(); // === not allowed
    });

    // Security tests
    it('should reject object literals (security)', () => {
      const result = parseConditionExpression('${var.output.data} == {"key": "value"}');
      expect(result).toBeNull();
    });

    it('should reject array literals (security)', () => {
      const result = parseConditionExpression('${var.output.data} == [1, 2, 3]');
      expect(result).toBeNull();
    });

    it('should reject function calls (security)', () => {
      const result = parseConditionExpression('${var.output.data} == Date.now()');
      expect(result).toBeNull();
    });

    it('should reject bracket notation in variable path (security)', () => {
      const result = parseConditionExpression("${var['key'].output} == 'value'");
      expect(result).toBeNull();
    });
  });

  // ============================================================
  // parseAllowedValue tests
  // ============================================================
  describe('parseAllowedValue', () => {
    it('should parse single-quoted strings', () => {
      expect(parseAllowedValue("'hello'")).toBe('hello');
      expect(parseAllowedValue("'hello world'")).toBe('hello world');
    });

    it('should parse double-quoted strings', () => {
      expect(parseAllowedValue('"hello"')).toBe('hello');
    });

    it('should parse integers', () => {
      expect(parseAllowedValue('123')).toBe(123);
      expect(parseAllowedValue('-456')).toBe(-456);
    });

    it('should parse floats', () => {
      expect(parseAllowedValue('12.34')).toBe(12.34);
      expect(parseAllowedValue('-56.78')).toBe(-56.78);
    });

    it('should parse booleans', () => {
      expect(parseAllowedValue('true')).toBe(true);
      expect(parseAllowedValue('false')).toBe(false);
    });

    it('should parse null', () => {
      expect(parseAllowedValue('null')).toBe(null);
    });

    it('should return undefined for invalid values', () => {
      expect(parseAllowedValue('undefined')).toBeUndefined();
      expect(parseAllowedValue('{}')).toBeUndefined();
      expect(parseAllowedValue('[]')).toBeUndefined();
      expect(parseAllowedValue('someVar')).toBeUndefined();
    });
  });

  // ============================================================
  // compareValues tests
  // ============================================================
  describe('compareValues', () => {
    it('should compare equality', () => {
      expect(compareValues('active', '==', 'active')).toBe(true);
      expect(compareValues('active', '==', 'inactive')).toBe(false);
      expect(compareValues(100, '==', 100)).toBe(true);
      expect(compareValues(true, '==', true)).toBe(true);
      expect(compareValues(null, '==', null)).toBe(true);
    });

    it('should compare inequality', () => {
      expect(compareValues('active', '!=', 'inactive')).toBe(true);
      expect(compareValues('active', '!=', 'active')).toBe(false);
    });

    it('should compare greater than', () => {
      expect(compareValues(100, '>', 50)).toBe(true);
      expect(compareValues(50, '>', 100)).toBe(false);
      expect(compareValues(100, '>', 100)).toBe(false);
    });

    it('should compare less than', () => {
      expect(compareValues(50, '<', 100)).toBe(true);
      expect(compareValues(100, '<', 50)).toBe(false);
    });

    it('should compare greater than or equal', () => {
      expect(compareValues(100, '>=', 50)).toBe(true);
      expect(compareValues(100, '>=', 100)).toBe(true);
      expect(compareValues(50, '>=', 100)).toBe(false);
    });

    it('should compare less than or equal', () => {
      expect(compareValues(50, '<=', 100)).toBe(true);
      expect(compareValues(100, '<=', 100)).toBe(true);
      expect(compareValues(100, '<=', 50)).toBe(false);
    });
  });

  // ============================================================
  // evaluateCondition tests (integration)
  // ============================================================
  describe('evaluateCondition', () => {
    let context: ContextManager;

    beforeEach(() => {
      context = new ContextManager({ userId: 'user123' });
      // Set up outputs for testing
      context.setOutput('user', { status: 'active', role: 'admin' });
      context.setOutput('count', { value: 150 });
      context.setOutput('flag', { enabled: true });
    });

    it('should evaluate string equality', () => {
      const result = evaluateCondition("${user.output.status} == 'active'", context);
      expect(result.result).toBe(true);
      expect(result.error).toBeUndefined();
    });

    it('should evaluate string inequality', () => {
      const result = evaluateCondition("${user.output.status} == 'inactive'", context);
      expect(result.result).toBe(false);
    });

    it('should evaluate number comparison', () => {
      const result = evaluateCondition('${count.output.value} > 100', context);
      expect(result.result).toBe(true);
    });

    it('should evaluate boolean comparison', () => {
      const result = evaluateCondition('${flag.output.enabled} == true', context);
      expect(result.result).toBe(true);
    });

    it('should return false for undefined variables', () => {
      const result = evaluateCondition("${undefined_node.output.value} == 'test'", context);
      // Should return false when variable is not found
      expect(result.result).toBe(false);
    });

    it('should return error for invalid expression format', () => {
      const result = evaluateCondition('invalid expression', context);
      expect(result.result).toBe(false);
      expect(result.error).toBe('Invalid condition expression format');
    });

    it('should include evaluatedCondition for debugging', () => {
      const result = evaluateCondition("${user.output.status} == 'active'", context);
      expect(result.evaluatedCondition).toContain('active');
    });
  });
});
