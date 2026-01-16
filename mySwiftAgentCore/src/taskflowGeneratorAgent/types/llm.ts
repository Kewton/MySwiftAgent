/**
 * LLM Types - Type definitions for LLM interactions
 *
 * Issue #364: LLM client abstraction types
 */

import { z } from 'zod';

/**
 * LLM Prompt - Input for LLM generation
 */
export const LLMPromptSchema = z.object({
  system: z.string(),
  user: z.string(),
  examples: z
    .array(
      z.object({
        input: z.string(),
        output: z.string(),
      })
    )
    .optional(),
});

export type LLMPrompt = z.infer<typeof LLMPromptSchema>;

/**
 * LLM Options - Configuration for LLM calls
 */
export const LLMOptionsSchema = z.object({
  model: z.string().optional(),
  temperature: z.number().min(0).max(2).optional(),
  maxTokens: z.number().int().positive().optional(),
  timeout: z.number().int().positive().optional(),
});

export type LLMOptions = z.infer<typeof LLMOptionsSchema>;

/**
 * LLM Usage - Token usage statistics
 */
export const LLMUsageSchema = z.object({
  promptTokens: z.number().int().nonnegative(),
  completionTokens: z.number().int().nonnegative(),
  totalTokens: z.number().int().nonnegative().optional(),
});

export type LLMUsage = z.infer<typeof LLMUsageSchema>;

/**
 * LLM Response - Response from LLM
 */
export const LLMResponseSchema = z.object({
  content: z.string(),
  model: z.string(),
  usage: LLMUsageSchema,
  latencyMs: z.number().int().nonnegative(),
  systemPrompt: z.string().optional(),
  userPrompt: z.string().optional(),
  temperature: z.number().optional(),
  maxTokens: z.number().int().optional(),
});

export type LLMResponse = z.infer<typeof LLMResponseSchema>;

/**
 * Structured Response - LLM response with parsed content
 */
export interface StructuredResponse<T> {
  data: T;
  raw: LLMResponse;
}

/**
 * LLM Provider - Supported LLM providers
 */
export type LLMProvider = 'anthropic' | 'openai' | 'gemini';

/**
 * LLM Model Configuration
 */
export interface LLMModelConfig {
  provider: LLMProvider;
  model: string;
  maxTokens: number;
  temperature: number;
}

/**
 * Default model configurations
 */
export const DEFAULT_MODEL_CONFIGS: Record<LLMProvider, LLMModelConfig> = {
  anthropic: {
    provider: 'anthropic',
    model: 'claude-3-5-sonnet-20241022',
    maxTokens: 4096,
    temperature: 0.7,
  },
  openai: {
    provider: 'openai',
    model: 'gpt-4-turbo-preview',
    maxTokens: 4096,
    temperature: 0.7,
  },
  gemini: {
    provider: 'gemini',
    model: 'gemini-pro',
    maxTokens: 4096,
    temperature: 0.7,
  },
};
