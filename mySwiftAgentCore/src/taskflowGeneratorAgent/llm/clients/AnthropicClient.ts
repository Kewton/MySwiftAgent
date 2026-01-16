/**
 * AnthropicClient - Anthropic Claude API client
 *
 * Issue #364: Anthropic LLM provider implementation
 */

import { BaseLLMClient, LLMApiError, type LLMClientConfig } from '../LLMClient.js';
import type { LLMPrompt, LLMOptions, LLMResponse } from '../../types/llm.js';

/**
 * Anthropic API Message
 */
interface AnthropicMessage {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Anthropic API Request
 */
interface AnthropicRequest {
  model: string;
  max_tokens: number;
  temperature?: number;
  system?: string;
  messages: AnthropicMessage[];
}

/**
 * Anthropic API Response
 */
interface AnthropicResponse {
  content: Array<{ type: string; text: string }>;
  model: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
  };
  stop_reason?: string;
}

/**
 * Anthropic Error Response
 */
interface AnthropicError {
  error: {
    type: string;
    message: string;
  };
}

/**
 * AnthropicClient - Claude API client implementation
 */
export class AnthropicClient extends BaseLLMClient {
  private readonly baseUrl: string;

  constructor(config: LLMClientConfig) {
    super(config);
    this.baseUrl = config.baseUrl ?? 'https://api.anthropic.com/v1';
  }

  /**
   * Make API call to Anthropic
   */
  protected async callApi(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse> {
    const startTime = Date.now();

    const model = options?.model ?? this.config.defaultModel;
    const maxTokens = options?.maxTokens ?? this.config.defaultMaxTokens ?? 4096;
    const temperature = options?.temperature ?? this.config.defaultTemperature;

    const requestBody: AnthropicRequest = {
      model,
      max_tokens: maxTokens,
      temperature,
      system: prompt.system,
      messages: this.buildMessages(prompt),
    };

    const response = await fetch(`${this.baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = (await response.json()) as AnthropicError;
      throw new LLMApiError(
        `Anthropic API error: ${errorBody.error?.message ?? response.statusText}`,
        'anthropic',
        response.status
      );
    }

    const data = (await response.json()) as AnthropicResponse;
    const latencyMs = Date.now() - startTime;

    // Extract text content from response
    const content = data.content
      .filter((block) => block.type === 'text')
      .map((block) => block.text)
      .join('');

    return {
      content,
      model: data.model,
      usage: {
        promptTokens: data.usage.input_tokens,
        completionTokens: data.usage.output_tokens,
        totalTokens: data.usage.input_tokens + data.usage.output_tokens,
      },
      latencyMs,
      systemPrompt: prompt.system,
      userPrompt: prompt.user,
      temperature,
      maxTokens,
    };
  }

  /**
   * Build messages array for Anthropic API
   */
  private buildMessages(prompt: LLMPrompt): AnthropicMessage[] {
    const messages: AnthropicMessage[] = [];

    // Add examples as user/assistant pairs
    if (prompt.examples) {
      for (const example of prompt.examples) {
        messages.push({ role: 'user', content: example.input });
        messages.push({ role: 'assistant', content: example.output });
      }
    }

    // Add main user message
    messages.push({ role: 'user', content: prompt.user });

    return messages;
  }

  /**
   * Get provider name
   */
  getProviderName(): string {
    return 'anthropic';
  }
}
