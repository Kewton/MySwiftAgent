/**
 * LLM Types Unit Tests
 *
 * Issue #364: LLM-related type definitions
 */

import { describe, it, expect } from 'vitest';
import {
  LLMPromptSchema,
  LLMOptionsSchema,
  LLMResponseSchema,
  LLMUsageSchema,
  type LLMPrompt,
  type LLMOptions,
  type LLMResponse,
  type LLMUsage,
} from '../../../../src/taskflowGeneratorAgent/types/llm.js';

describe('LLM Types', () => {
  describe('LLMPrompt', () => {
    it('should validate a complete prompt', () => {
      const prompt: LLMPrompt = {
        system: 'You are a helpful assistant.',
        user: 'Generate a workflow for user analysis.',
        examples: [
          {
            input: 'Example input',
            output: 'Example output',
          },
        ],
      };

      const result = LLMPromptSchema.safeParse(prompt);
      expect(result.success).toBe(true);
    });

    it('should validate prompt without examples', () => {
      const prompt: LLMPrompt = {
        system: 'You are a helpful assistant.',
        user: 'Generate a workflow.',
      };

      const result = LLMPromptSchema.safeParse(prompt);
      expect(result.success).toBe(true);
    });

    it('should reject prompt without required fields', () => {
      const invalidPrompt = {
        system: 'System prompt only',
      };

      const result = LLMPromptSchema.safeParse(invalidPrompt);
      expect(result.success).toBe(false);
    });
  });

  describe('LLMOptions', () => {
    it('should validate options with defaults', () => {
      const options: LLMOptions = {};

      const result = LLMOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should validate complete options', () => {
      const options: LLMOptions = {
        model: 'claude-3-5-sonnet-20241022',
        temperature: 0.7,
        maxTokens: 4096,
        timeout: 30000,
      };

      const result = LLMOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should reject invalid temperature', () => {
      const options = {
        temperature: 2.5, // max is 2.0
      };

      const result = LLMOptionsSchema.safeParse(options);
      expect(result.success).toBe(false);
    });

    it('should reject negative temperature', () => {
      const options = {
        temperature: -0.5,
      };

      const result = LLMOptionsSchema.safeParse(options);
      expect(result.success).toBe(false);
    });
  });

  describe('LLMUsage', () => {
    it('should validate usage statistics', () => {
      const usage: LLMUsage = {
        promptTokens: 100,
        completionTokens: 200,
        totalTokens: 300,
      };

      const result = LLMUsageSchema.safeParse(usage);
      expect(result.success).toBe(true);
    });

    it('should allow optional totalTokens', () => {
      const usage: LLMUsage = {
        promptTokens: 100,
        completionTokens: 200,
      };

      const result = LLMUsageSchema.safeParse(usage);
      expect(result.success).toBe(true);
    });
  });

  describe('LLMResponse', () => {
    it('should validate a complete response', () => {
      const response: LLMResponse = {
        content: '{"workflow_name": "test"}',
        model: 'claude-3-5-sonnet-20241022',
        usage: {
          promptTokens: 100,
          completionTokens: 200,
          totalTokens: 300,
        },
        latencyMs: 1500,
        systemPrompt: 'System prompt',
        userPrompt: 'User prompt',
        temperature: 0.7,
        maxTokens: 4096,
      };

      const result = LLMResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });

    it('should validate minimal response', () => {
      const response: LLMResponse = {
        content: 'Response content',
        model: 'gpt-4',
        usage: {
          promptTokens: 50,
          completionTokens: 100,
        },
        latencyMs: 500,
      };

      const result = LLMResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });

    it('should reject response without required fields', () => {
      const invalidResponse = {
        content: 'Response content',
        // missing model, usage, latencyMs
      };

      const result = LLMResponseSchema.safeParse(invalidResponse);
      expect(result.success).toBe(false);
    });
  });
});
