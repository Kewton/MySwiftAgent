/**
 * LLMClient - Abstract interface for LLM providers
 *
 * Issue #364: Provider-agnostic LLM client abstraction
 */

import { z } from 'zod';
import type {
  LLMPrompt,
  LLMOptions,
  LLMResponse,
  StructuredResponse,
} from '../types/llm.js';

/**
 * LLM Client Configuration
 */
export interface LLMClientConfig {
  apiKey: string;
  defaultModel: string;
  defaultMaxTokens?: number;
  defaultTemperature?: number;
  baseUrl?: string;
  timeout?: number;
}

/**
 * LLM Client Interface
 *
 * All LLM providers must implement this interface.
 */
export interface LLMClient {
  /**
   * Generate text response
   */
  generate(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse>;

  /**
   * Generate structured response with schema validation
   */
  generateStructured<T>(
    prompt: LLMPrompt,
    schema: z.ZodSchema<T>,
    options?: LLMOptions
  ): Promise<StructuredResponse<T>>;

  /**
   * Get provider name
   */
  getProviderName(): string;

  /**
   * Get configuration (without sensitive data)
   */
  getConfig(): LLMClientConfig;
}

/**
 * Base LLM Client - Common functionality for all providers
 */
export abstract class BaseLLMClient implements LLMClient {
  protected readonly config: LLMClientConfig;

  constructor(config: LLMClientConfig) {
    this.config = {
      ...config,
      defaultMaxTokens: config.defaultMaxTokens ?? 4096,
      defaultTemperature: config.defaultTemperature ?? 0.7,
      timeout: config.timeout ?? 30000,
    };
  }

  /**
   * Provider-specific API call implementation
   */
  protected abstract callApi(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse>;

  /**
   * Get provider name - must be implemented by subclasses
   */
  abstract getProviderName(): string;

  /**
   * Generate text response
   */
  async generate(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse> {
    const mergedOptions: LLMOptions = {
      model: options?.model ?? this.config.defaultModel,
      maxTokens: options?.maxTokens ?? this.config.defaultMaxTokens,
      temperature: options?.temperature ?? this.config.defaultTemperature,
      timeout: options?.timeout ?? this.config.timeout,
    };

    return this.callApi(prompt, mergedOptions);
  }

  /**
   * Generate structured response with schema validation
   */
  async generateStructured<T>(
    prompt: LLMPrompt,
    schema: z.ZodSchema<T>,
    options?: LLMOptions
  ): Promise<StructuredResponse<T>> {
    const response = await this.generate(prompt, options);

    // Extract JSON from response (handles markdown code blocks)
    const jsonContent = this.extractJson(response.content);

    // Parse JSON
    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonContent);
    } catch (error) {
      throw new LLMParseError(
        `Failed to parse LLM response as JSON: ${error instanceof Error ? error.message : 'Unknown error'}`,
        response.content
      );
    }

    // Validate against schema
    const result = schema.safeParse(parsed);
    if (!result.success) {
      throw new LLMValidationError(
        `LLM response does not match expected schema: ${result.error.message}`,
        response.content,
        result.error
      );
    }

    return {
      data: result.data,
      raw: response,
    };
  }

  /**
   * Get configuration
   */
  getConfig(): LLMClientConfig {
    return this.config;
  }

  /**
   * Extract JSON from response (handles markdown code blocks)
   */
  protected extractJson(content: string): string {
    // Try to extract from markdown code block
    const codeBlockMatch = content.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (codeBlockMatch?.[1]) {
      return codeBlockMatch[1].trim();
    }

    // Try to find JSON object or array
    const jsonMatch = content.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
    if (jsonMatch?.[1]) {
      return jsonMatch[1].trim();
    }

    // Return as-is
    return content.trim();
  }
}

/**
 * LLM Parse Error - Thrown when response cannot be parsed as JSON
 */
export class LLMParseError extends Error {
  readonly rawContent: string;

  constructor(message: string, rawContent: string) {
    super(message);
    this.name = 'LLMParseError';
    this.rawContent = rawContent;
  }
}

/**
 * LLM Validation Error - Thrown when response doesn't match schema
 */
export class LLMValidationError extends Error {
  readonly rawContent: string;
  readonly zodError: z.ZodError;

  constructor(message: string, rawContent: string, zodError: z.ZodError) {
    super(message);
    this.name = 'LLMValidationError';
    this.rawContent = rawContent;
    this.zodError = zodError;
  }
}

/**
 * LLM API Error - Thrown when API call fails
 */
export class LLMApiError extends Error {
  readonly statusCode?: number;
  readonly provider: string;

  constructor(message: string, provider: string, statusCode?: number) {
    super(message);
    this.name = 'LLMApiError';
    this.provider = provider;
    this.statusCode = statusCode;
  }
}
