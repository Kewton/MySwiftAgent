/**
 * Constants Unit Tests
 *
 * Issue #374: Configuration constants for feedback loop
 */

import { describe, it, expect } from 'vitest';
import {
  MAX_CAPABILITIES_PER_PROMPT,
  MAX_CAPABILITY_DESCRIPTION_LENGTH,
  MAX_RETRY_COUNT,
  DEFAULT_GENERATION_TIMEOUT_MS,
  RETRY_TIMEOUT_MULTIPLIER,
  STOP_WORDS,
  RELEVANCE_SCORING,
  FREQUENT_CATEGORIES,
} from '../../../src/taskflowGeneratorAgent/constants.js';

describe('Prompt Size Constants', () => {
  describe('MAX_CAPABILITIES_PER_PROMPT', () => {
    it('should be 50', () => {
      expect(MAX_CAPABILITIES_PER_PROMPT).toBe(50);
    });

    it('should be a positive integer', () => {
      expect(Number.isInteger(MAX_CAPABILITIES_PER_PROMPT)).toBe(true);
      expect(MAX_CAPABILITIES_PER_PROMPT).toBeGreaterThan(0);
    });
  });

  describe('MAX_CAPABILITY_DESCRIPTION_LENGTH', () => {
    it('should be 2000', () => {
      expect(MAX_CAPABILITY_DESCRIPTION_LENGTH).toBe(2000);
    });

    it('should be a positive integer', () => {
      expect(Number.isInteger(MAX_CAPABILITY_DESCRIPTION_LENGTH)).toBe(true);
      expect(MAX_CAPABILITY_DESCRIPTION_LENGTH).toBeGreaterThan(0);
    });
  });
});

describe('Feedback Loop Constants', () => {
  describe('MAX_RETRY_COUNT', () => {
    it('should be 3', () => {
      expect(MAX_RETRY_COUNT).toBe(3);
    });

    it('should be a positive integer', () => {
      expect(Number.isInteger(MAX_RETRY_COUNT)).toBe(true);
      expect(MAX_RETRY_COUNT).toBeGreaterThan(0);
    });
  });

  describe('DEFAULT_GENERATION_TIMEOUT_MS', () => {
    it('should be 30000 (30 seconds)', () => {
      expect(DEFAULT_GENERATION_TIMEOUT_MS).toBe(30000);
    });

    it('should be a reasonable timeout value', () => {
      expect(DEFAULT_GENERATION_TIMEOUT_MS).toBeGreaterThanOrEqual(10000);
      expect(DEFAULT_GENERATION_TIMEOUT_MS).toBeLessThanOrEqual(120000);
    });
  });

  describe('RETRY_TIMEOUT_MULTIPLIER', () => {
    it('should be 1.5', () => {
      expect(RETRY_TIMEOUT_MULTIPLIER).toBe(1.5);
    });

    it('should be greater than 1', () => {
      expect(RETRY_TIMEOUT_MULTIPLIER).toBeGreaterThan(1);
    });
  });
});

describe('Keyword Extraction Constants', () => {
  describe('STOP_WORDS', () => {
    it('should be an array', () => {
      expect(Array.isArray(STOP_WORDS)).toBe(true);
    });

    it('should include common stop words', () => {
      expect(STOP_WORDS).toContain('the');
      expect(STOP_WORDS).toContain('a');
      expect(STOP_WORDS).toContain('and');
      expect(STOP_WORDS).toContain('or');
      expect(STOP_WORDS).toContain('for');
    });

    it('should have all lowercase words', () => {
      for (const word of STOP_WORDS) {
        expect(word).toBe(word.toLowerCase());
      }
    });

    it('should have unique words', () => {
      const uniqueWords = new Set(STOP_WORDS);
      expect(uniqueWords.size).toBe(STOP_WORDS.length);
    });
  });
});

describe('Relevance Scoring Constants', () => {
  describe('RELEVANCE_SCORING', () => {
    it('should define NAME_MATCH score', () => {
      expect(RELEVANCE_SCORING.NAME_MATCH).toBe(10);
    });

    it('should define DESCRIPTION_MATCH score', () => {
      expect(RELEVANCE_SCORING.DESCRIPTION_MATCH).toBe(5);
    });

    it('should define CATEGORY_MATCH score', () => {
      expect(RELEVANCE_SCORING.CATEGORY_MATCH).toBe(3);
    });

    it('should define USE_CASE_MATCH score', () => {
      expect(RELEVANCE_SCORING.USE_CASE_MATCH).toBe(7);
    });

    it('should define FREQUENT_CATEGORY_BONUS score', () => {
      expect(RELEVANCE_SCORING.FREQUENT_CATEGORY_BONUS).toBe(2);
    });

    it('should have all positive scores', () => {
      expect(RELEVANCE_SCORING.NAME_MATCH).toBeGreaterThan(0);
      expect(RELEVANCE_SCORING.DESCRIPTION_MATCH).toBeGreaterThan(0);
      expect(RELEVANCE_SCORING.CATEGORY_MATCH).toBeGreaterThan(0);
      expect(RELEVANCE_SCORING.USE_CASE_MATCH).toBeGreaterThan(0);
      expect(RELEVANCE_SCORING.FREQUENT_CATEGORY_BONUS).toBeGreaterThan(0);
    });

    it('should prioritize name match over description', () => {
      expect(RELEVANCE_SCORING.NAME_MATCH).toBeGreaterThan(RELEVANCE_SCORING.DESCRIPTION_MATCH);
    });
  });

  describe('FREQUENT_CATEGORIES', () => {
    it('should be an array', () => {
      expect(Array.isArray(FREQUENT_CATEGORIES)).toBe(true);
    });

    it('should include common categories', () => {
      expect(FREQUENT_CATEGORIES).toContain('llm');
      expect(FREQUENT_CATEGORIES).toContain('api');
      expect(FREQUENT_CATEGORIES).toContain('utility');
    });

    it('should have all lowercase categories', () => {
      for (const category of FREQUENT_CATEGORIES) {
        expect(category).toBe(category.toLowerCase());
      }
    });

    it('should have unique categories', () => {
      const uniqueCategories = new Set(FREQUENT_CATEGORIES);
      expect(uniqueCategories.size).toBe(FREQUENT_CATEGORIES.length);
    });
  });
});
