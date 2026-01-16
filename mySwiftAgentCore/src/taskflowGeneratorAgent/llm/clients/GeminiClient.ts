/**
 * GeminiClient - Google Gemini API client
 *
 * Issue #364: Gemini LLM provider implementation
 */

import { BaseLLMClient, LLMApiError, type LLMClientConfig } from '../LLMClient.js';
import type { LLMPrompt, LLMOptions, LLMResponse } from '../../types/llm.js';

/**
 * Gemini API Content Part
 */
interface GeminiPart {
  text: string;
}

/**
 * Gemini API Content
 */
interface GeminiContent {
  role: 'user' | 'model';
  parts: GeminiPart[];
}

/**
 * Gemini API Request
 */
interface GeminiRequest {
  contents: GeminiContent[];
  systemInstruction?: {
    parts: GeminiPart[];
  };
  generationConfig?: {
    temperature?: number;
    maxOutputTokens?: number;
    candidateCount?: number;
  };
}

/**
 * Gemini API Response
 */
interface GeminiResponse {
  candidates: Array<{
    content: {
      parts: GeminiPart[];
      role: string;
    };
    finishReason?: string;
  }>;
  usageMetadata?: {
    promptTokenCount: number;
    candidatesTokenCount: number;
    totalTokenCount: number;
  };
  modelVersion?: string;
}

/**
 * Gemini Error Response
 */
interface GeminiError {
  error: {
    code: number;
    message: string;
    status: string;
  };
}

/**
 * GeminiClient - Gemini API client implementation
 */
export class GeminiClient extends BaseLLMClient {
  private readonly baseUrl: string;

  constructor(config: LLMClientConfig) {
    super(config);
    this.baseUrl = config.baseUrl ?? 'https://generativelanguage.googleapis.com/v1beta';
  }

  /**
   * Make API call to Gemini
   */
  protected async callApi(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse> {
    const startTime = Date.now();

    const model = options?.model ?? this.config.defaultModel;
    const maxTokens = options?.maxTokens ?? this.config.defaultMaxTokens ?? 4096;
    const temperature = options?.temperature ?? this.config.defaultTemperature;

    const requestBody: GeminiRequest = {
      contents: this.buildContents(prompt),
      systemInstruction: {
        parts: [{ text: prompt.system }],
      },
      generationConfig: {
        temperature,
        maxOutputTokens: maxTokens,
        candidateCount: 1,
      },
    };

    const url = `${this.baseUrl}/models/${model}:generateContent?key=${this.config.apiKey}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorBody = (await response.json()) as GeminiError;
      throw new LLMApiError(
        `Gemini API error: ${errorBody.error?.message ?? response.statusText}`,
        'gemini',
        response.status
      );
    }

    const data = (await response.json()) as GeminiResponse;
    const latencyMs = Date.now() - startTime;

    // Extract content from first candidate
    const content = data.candidates[0]?.content?.parts
      .map((part) => part.text)
      .join('') ?? '';

    return {
      content,
      model: data.modelVersion ?? model,
      usage: {
        promptTokens: data.usageMetadata?.promptTokenCount ?? 0,
        completionTokens: data.usageMetadata?.candidatesTokenCount ?? 0,
        totalTokens: data.usageMetadata?.totalTokenCount ?? 0,
      },
      latencyMs,
      systemPrompt: prompt.system,
      userPrompt: prompt.user,
      temperature,
      maxTokens,
    };
  }

  /**
   * Build contents array for Gemini API
   */
  private buildContents(prompt: LLMPrompt): GeminiContent[] {
    const contents: GeminiContent[] = [];

    // Add examples as user/model pairs
    if (prompt.examples) {
      for (const example of prompt.examples) {
        contents.push({
          role: 'user',
          parts: [{ text: example.input }],
        });
        contents.push({
          role: 'model',
          parts: [{ text: example.output }],
        });
      }
    }

    // Add main user message
    contents.push({
      role: 'user',
      parts: [{ text: prompt.user }],
    });

    return contents;
  }

  /**
   * Get provider name
   */
  getProviderName(): string {
    return 'gemini';
  }
}
