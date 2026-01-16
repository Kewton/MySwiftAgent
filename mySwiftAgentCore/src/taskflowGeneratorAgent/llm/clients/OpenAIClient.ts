/**
 * OpenAIClient - OpenAI GPT API client
 *
 * Issue #364: OpenAI LLM provider implementation
 */

import { BaseLLMClient, LLMApiError, type LLMClientConfig } from '../LLMClient.js';
import type { LLMPrompt, LLMOptions, LLMResponse } from '../../types/llm.js';

/**
 * OpenAI API Message
 */
interface OpenAIMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * OpenAI API Request
 */
interface OpenAIRequest {
  model: string;
  messages: OpenAIMessage[];
  max_tokens?: number;
  temperature?: number;
}

/**
 * OpenAI API Response
 */
interface OpenAIResponse {
  choices: Array<{
    message: {
      content: string;
    };
    finish_reason?: string;
  }>;
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

/**
 * OpenAI Error Response
 */
interface OpenAIError {
  error: {
    type: string;
    message: string;
    code?: string;
  };
}

/**
 * OpenAIClient - GPT API client implementation
 */
export class OpenAIClient extends BaseLLMClient {
  private readonly baseUrl: string;

  constructor(config: LLMClientConfig) {
    super(config);
    this.baseUrl = config.baseUrl ?? 'https://api.openai.com/v1';
  }

  /**
   * Make API call to OpenAI
   */
  protected async callApi(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse> {
    const startTime = Date.now();

    const model = options?.model ?? this.config.defaultModel;
    const maxTokens = options?.maxTokens ?? this.config.defaultMaxTokens ?? 4096;
    const temperature = options?.temperature ?? this.config.defaultTemperature;

    const requestBody: OpenAIRequest = {
      model,
      messages: this.buildMessages(prompt),
      max_tokens: maxTokens,
      temperature,
    };

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = (await response.json()) as OpenAIError;
      throw new LLMApiError(
        `OpenAI API error: ${errorBody.error?.message ?? response.statusText}`,
        'openai',
        response.status
      );
    }

    const data = (await response.json()) as OpenAIResponse;
    const latencyMs = Date.now() - startTime;

    // Extract content from first choice
    const content = data.choices[0]?.message?.content ?? '';

    return {
      content,
      model: data.model,
      usage: {
        promptTokens: data.usage.prompt_tokens,
        completionTokens: data.usage.completion_tokens,
        totalTokens: data.usage.total_tokens,
      },
      latencyMs,
      systemPrompt: prompt.system,
      userPrompt: prompt.user,
      temperature,
      maxTokens,
    };
  }

  /**
   * Build messages array for OpenAI API
   */
  private buildMessages(prompt: LLMPrompt): OpenAIMessage[] {
    const messages: OpenAIMessage[] = [];

    // Add system message
    messages.push({ role: 'system', content: prompt.system });

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
    return 'openai';
  }
}
