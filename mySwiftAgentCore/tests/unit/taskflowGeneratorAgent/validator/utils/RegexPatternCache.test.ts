/**
 * RegexPatternCache Unit Tests
 *
 * Issue #381: Pre-compiled regex pattern cache for validation
 * Implements Singleton/Flyweight Pattern
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { RegexPatternCache } from '../../../../../src/taskflowGeneratorAgent/validator/utils/RegexPatternCache.js';

describe('RegexPatternCache', () => {
  describe('Singleton Pattern', () => {
    it('should return the same instance on multiple calls', () => {
      const instance1 = RegexPatternCache.getInstance();
      const instance2 = RegexPatternCache.getInstance();

      expect(instance1).toBe(instance2);
    });

    it('should be defined', () => {
      const instance = RegexPatternCache.getInstance();
      expect(instance).toBeDefined();
    });
  });

  describe('Pre-compiled Patterns', () => {
    let cache: RegexPatternCache;

    beforeEach(() => {
      cache = RegexPatternCache.getInstance();
    });

    describe('stepReference pattern', () => {
      it('should have stepReference pattern', () => {
        const pattern = cache.getPattern('stepReference');
        expect(pattern).toBeDefined();
        expect(pattern).toBeInstanceOf(RegExp);
      });

      it('should match valid step references', () => {
        const pattern = cache.getPattern('stepReference')!;
        const testCases = [
          { input: '$steps.step_001.result', expected: ['step_001', 'result'] },
          { input: '$steps.analyze_data.output', expected: ['analyze_data', 'output'] },
          { input: '$steps.step-1.field_name', expected: ['step-1', 'field_name'] },
        ];

        for (const testCase of testCases) {
          pattern.lastIndex = 0; // Reset for global pattern
          const match = pattern.exec(testCase.input);
          expect(match).toBeTruthy();
          expect(match![1]).toBe(testCase.expected[0]);
          expect(match![2]).toBe(testCase.expected[1]);
        }
      });

      it('should not match invalid step references', () => {
        const pattern = cache.getPattern('stepReference')!;
        const invalidInputs = [
          '$step.step_001.result', // missing 's'
          'steps.step_001.result', // missing '$'
          '$steps.123invalid.result', // starts with number
        ];

        for (const input of invalidInputs) {
          pattern.lastIndex = 0;
          const match = pattern.exec(input);
          expect(match).toBeFalsy();
        }
      });
    });

    describe('mustache pattern', () => {
      it('should have mustache pattern', () => {
        const pattern = cache.getPattern('mustache');
        expect(pattern).toBeDefined();
        expect(pattern).toBeInstanceOf(RegExp);
      });

      it('should match mustache templates', () => {
        const pattern = cache.getPattern('mustache')!;
        const testCases = [
          '{{expression}}',
          '{{$.steps.step_001.result}}',
          '{{variable}}',
        ];

        for (const input of testCases) {
          pattern.lastIndex = 0;
          const match = pattern.exec(input);
          expect(match).toBeTruthy();
        }
      });
    });

    describe('jsonPath pattern', () => {
      it('should have jsonPath pattern', () => {
        const pattern = cache.getPattern('jsonPath');
        expect(pattern).toBeDefined();
        expect(pattern).toBeInstanceOf(RegExp);
      });

      it('should match JSON path expressions', () => {
        const pattern = cache.getPattern('jsonPath')!;
        const testCases = ['$.steps', '$.input', '$.env'];

        for (const input of testCases) {
          pattern.lastIndex = 0;
          const match = pattern.exec(input);
          expect(match).toBeTruthy();
        }
      });
    });

    describe('mixed pattern', () => {
      it('should have mixed pattern', () => {
        const pattern = cache.getPattern('mixed');
        expect(pattern).toBeDefined();
        expect(pattern).toBeInstanceOf(RegExp);
      });

      it('should match mixed mustache-jsonPath templates', () => {
        const pattern = cache.getPattern('mixed')!;
        const input = '{{$.steps.step_001.result}}';
        pattern.lastIndex = 0;
        const match = pattern.exec(input);
        expect(match).toBeTruthy();
      });
    });
  });

  describe('Pattern Isolation', () => {
    it('should return new RegExp instances to prevent lastIndex conflicts', () => {
      const cache = RegexPatternCache.getInstance();
      const pattern1 = cache.getPattern('stepReference');
      const pattern2 = cache.getPattern('stepReference');

      // Different instances but same source
      expect(pattern1).not.toBe(pattern2);
      expect(pattern1!.source).toBe(pattern2!.source);
      expect(pattern1!.flags).toBe(pattern2!.flags);
    });

    it('should allow concurrent usage without interference', () => {
      const cache = RegexPatternCache.getInstance();
      const text = '$steps.step_a.field1 and $steps.step_b.field2';

      const pattern1 = cache.getPattern('stepReference')!;
      const pattern2 = cache.getPattern('stepReference')!;

      // Both should find matches independently
      const match1 = pattern1.exec(text);
      const match2 = pattern2.exec(text);

      expect(match1).toBeTruthy();
      expect(match2).toBeTruthy();
      expect(match1![1]).toBe('step_a');
      expect(match2![1]).toBe('step_a'); // Same first match, not affected by pattern1
    });
  });

  describe('Unknown Pattern', () => {
    it('should return undefined for unknown pattern names', () => {
      const cache = RegexPatternCache.getInstance();
      const pattern = cache.getPattern('nonExistentPattern');
      expect(pattern).toBeUndefined();
    });
  });

  describe('getAllPatternNames', () => {
    it('should return all available pattern names', () => {
      const cache = RegexPatternCache.getInstance();
      const names = cache.getAllPatternNames();

      expect(names).toContain('stepReference');
      expect(names).toContain('mustache');
      expect(names).toContain('jsonPath');
      expect(names).toContain('mixed');
    });
  });
});
