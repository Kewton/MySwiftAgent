/**
 * SuggestionHelper Unit Tests
 *
 * Issue #381: Error message improvement with Levenshtein distance
 */

import { describe, it, expect } from 'vitest';
import { SuggestionHelper } from '../../../../../src/taskflowGeneratorAgent/validator/utils/SuggestionHelper.js';

describe('SuggestionHelper', () => {
  describe('levenshteinDistance', () => {
    it('should return 0 for identical strings', () => {
      expect(SuggestionHelper.levenshteinDistance('hello', 'hello')).toBe(0);
      expect(SuggestionHelper.levenshteinDistance('', '')).toBe(0);
    });

    it('should return length of non-empty string when comparing with empty', () => {
      expect(SuggestionHelper.levenshteinDistance('hello', '')).toBe(5);
      expect(SuggestionHelper.levenshteinDistance('', 'world')).toBe(5);
    });

    it('should calculate single character changes', () => {
      // Single substitution
      expect(SuggestionHelper.levenshteinDistance('cat', 'bat')).toBe(1);
      // Single insertion
      expect(SuggestionHelper.levenshteinDistance('cat', 'cats')).toBe(1);
      // Single deletion
      expect(SuggestionHelper.levenshteinDistance('cats', 'cat')).toBe(1);
    });

    it('should calculate multiple changes', () => {
      expect(SuggestionHelper.levenshteinDistance('kitten', 'sitting')).toBe(3);
      expect(SuggestionHelper.levenshteinDistance('saturday', 'sunday')).toBe(3);
    });

    it('should be case sensitive', () => {
      expect(SuggestionHelper.levenshteinDistance('Hello', 'hello')).toBe(1);
      expect(SuggestionHelper.levenshteinDistance('ABC', 'abc')).toBe(3);
    });
  });

  describe('findClosestMatch', () => {
    const candidates = ['step_001', 'step_002', 'analyze_data', 'transform_result'];

    it('should find exact match', () => {
      const result = SuggestionHelper.findClosestMatch('step_001', candidates);
      expect(result).toBe('step_001');
    });

    it('should find closest match for typos', () => {
      // Minor typo
      const result = SuggestionHelper.findClosestMatch('step_01', candidates);
      expect(result).toBe('step_001');
    });

    it('should find closest match case-insensitively', () => {
      const result = SuggestionHelper.findClosestMatch('STEP_001', candidates);
      expect(result).toBe('step_001');
    });

    it('should return undefined when no match within maxDistance', () => {
      const result = SuggestionHelper.findClosestMatch(
        'completely_different',
        candidates,
        3
      );
      expect(result).toBeUndefined();
    });

    it('should respect maxDistance parameter', () => {
      // 'step_01' has distance 1 from 'step_001'
      const result1 = SuggestionHelper.findClosestMatch('step_01', candidates, 1);
      expect(result1).toBe('step_001');

      // With maxDistance 0, no match unless exact
      const result2 = SuggestionHelper.findClosestMatch('step_01', candidates, 0);
      expect(result2).toBeUndefined();
    });

    it('should return undefined for empty candidates', () => {
      const result = SuggestionHelper.findClosestMatch('anything', []);
      expect(result).toBeUndefined();
    });

    it('should find best match among multiple close candidates', () => {
      const similarCandidates = ['result', 'results', 'resultz'];
      const result = SuggestionHelper.findClosestMatch('result', similarCandidates);
      expect(result).toBe('result');
    });
  });

  describe('createFieldNotFoundSuggestion', () => {
    const availableFields = ['result', 'status', 'data', 'message'];
    const capabilityName = 'google_search';

    it('should suggest closest match when available', () => {
      const suggestion = SuggestionHelper.createFieldNotFoundSuggestion(
        'resul', // typo
        availableFields,
        capabilityName
      );

      expect(suggestion.message).toContain('result');
      expect(suggestion.closestMatch).toBe('result');
      expect(suggestion.availableOptions).toEqual(availableFields);
    });

    it('should provide generic message when no close match', () => {
      const suggestion = SuggestionHelper.createFieldNotFoundSuggestion(
        'xyz_nonexistent',
        availableFields,
        capabilityName
      );

      expect(suggestion.message).toContain(capabilityName);
      expect(suggestion.closestMatch).toBeUndefined();
      expect(suggestion.availableOptions).toEqual(availableFields);
    });

    it('should include example usage', () => {
      const suggestion = SuggestionHelper.createFieldNotFoundSuggestion(
        'unknown',
        availableFields,
        capabilityName
      );

      expect(suggestion.example).toBeDefined();
      expect(suggestion.example).toContain('$steps');
    });

    it('should handle empty available fields', () => {
      const suggestion = SuggestionHelper.createFieldNotFoundSuggestion(
        'field',
        [],
        capabilityName
      );

      expect(suggestion.availableOptions).toEqual([]);
      expect(suggestion.closestMatch).toBeUndefined();
      expect(suggestion.example).toBeUndefined();
    });
  });

  describe('createStepNotFoundSuggestion', () => {
    const availableSteps = ['step_001', 'step_002', 'analyze', 'transform'];

    it('should suggest closest match when available', () => {
      const suggestion = SuggestionHelper.createStepNotFoundSuggestion(
        'step_01', // typo
        availableSteps
      );

      expect(suggestion.message).toContain('step_001');
      expect(suggestion.closestMatch).toBe('step_001');
      expect(suggestion.availableOptions).toEqual(availableSteps);
    });

    it('should provide generic message when no close match', () => {
      const suggestion = SuggestionHelper.createStepNotFoundSuggestion(
        'nonexistent_step_xyz',
        availableSteps
      );

      expect(suggestion.message).toContain('does not exist');
      expect(suggestion.closestMatch).toBeUndefined();
    });

    it('should include example usage', () => {
      const suggestion = SuggestionHelper.createStepNotFoundSuggestion(
        'unknown',
        availableSteps
      );

      expect(suggestion.example).toBeDefined();
      expect(suggestion.example).toContain('$steps');
      expect(suggestion.example).toContain(availableSteps[0]);
    });

    it('should handle empty available steps', () => {
      const suggestion = SuggestionHelper.createStepNotFoundSuggestion('step', []);

      expect(suggestion.availableOptions).toEqual([]);
      expect(suggestion.example).toBeUndefined();
    });
  });

  describe('createTemplateSyntaxSuggestion', () => {
    it('should provide suggestion for unclosed mustache', () => {
      const suggestion = SuggestionHelper.createTemplateSyntaxSuggestion(
        '{{expression',
        'UNCLOSED_MUSTACHE'
      );

      expect(suggestion.message).toContain('}}');
      expect(suggestion.example).toBeDefined();
    });

    it('should provide suggestion for invalid JSON path', () => {
      const suggestion = SuggestionHelper.createTemplateSyntaxSuggestion(
        '$invalid.path',
        'INVALID_JSON_PATH'
      );

      expect(suggestion.message).toBeDefined();
      expect(suggestion.example).toContain('$.steps');
    });

    it('should provide suggestion for nested expression error', () => {
      const suggestion = SuggestionHelper.createTemplateSyntaxSuggestion(
        '{{{{nested}}}}',
        'NESTED_EXPRESSION'
      );

      expect(suggestion.message).toBeDefined();
    });
  });
});
