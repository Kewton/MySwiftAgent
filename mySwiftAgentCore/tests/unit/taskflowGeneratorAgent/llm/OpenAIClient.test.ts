/**
 * OpenAIClient Unit Tests
 *
 * Issue #364: OpenAI LLM client implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OpenAIClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/OpenAIClient.js';
import type { LLMClientConfig } from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type { LLMPrompt, LLMOptions } from '../../../../src/taskflowGeneratorAgent/types/llm.js';

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('OpenAIClient', () => {
  let client: OpenAIClient;
  let config: LLMClientConfig;

  beforeEach(() => {
    vi.clearAllMocks();

    config = {
      apiKey: 'test-api-key',
      defaultModel: 'gpt-4-turbo-preview',
      defaultMaxTokens: 4096,
      defaultTemperature: 0.7,
    };

    client = new OpenAIClient(config);
  });

  describe('constructor', () => {
    it('should create instance with config', () => {
      expect(client).toBeInstanceOf(OpenAIClient);
      expect(client.getProviderName()).toBe('openai');
    });
  });

  describe('generate', () => {
    it('should make API call with correct parameters', async () => {
      const mockResponse = {
        choices: [
          {
            message: {
              content: '{"workflow": "test"}',
            },
          },
        ],
        model: 'gpt-4-turbo-preview',
        usage: {
          prompt_tokens: 100,
          completion_tokens: 50,
          total_tokens: 150,
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const prompt: LLMPrompt = {
        system: 'You are a workflow generator.',
        user: 'Generate a test workflow.',
      };

      const response = await client.generate(prompt);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.openai.com/v1/chat/completions',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-api-key',
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(response.content).toBe('{"workflow": "test"}');
      expect(response.model).toBe('gpt-4-turbo-preview');
      expect(response.usage.promptTokens).toBe(100);
      expect(response.usage.completionTokens).toBe(50);
    });

    it('should use custom model from options', async () => {
      const mockResponse = {
        choices: [{ message: { content: 'response' } }],
        model: 'gpt-4o',
        usage: { prompt_tokens: 50, completion_tokens: 25, total_tokens: 75 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      const options: LLMOptions = {
        model: 'gpt-4o',
        temperature: 0.5,
        maxTokens: 2048,
      };

      const response = await client.generate(prompt, options);

      const fetchCall = mockFetch.mock.calls[0];
      const requestBody = JSON.parse(fetchCall[1].body);

      expect(requestBody.model).toBe('gpt-4o');
      expect(requestBody.temperature).toBe(0.5);
      expect(requestBody.max_tokens).toBe(2048);
      expect(response.model).toBe('gpt-4o');
    });

    it('should throw error on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: () => Promise.resolve({ error: { message: 'Rate limit exceeded' } }),
      });

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      await expect(client.generate(prompt)).rejects.toThrow();
    });

    it('should include messages in correct format', async () => {
      const mockResponse = {
        choices: [{ message: { content: 'response' } }],
        model: 'gpt-4-turbo-preview',
        usage: { prompt_tokens: 50, completion_tokens: 25, total_tokens: 75 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const prompt: LLMPrompt = {
        system: 'You are a helpful assistant.',
        user: 'Hello',
      };

      await client.generate(prompt);

      const fetchCall = mockFetch.mock.calls[0];
      const requestBody = JSON.parse(fetchCall[1].body);

      expect(requestBody.messages).toContainEqual({
        role: 'system',
        content: 'You are a helpful assistant.',
      });
      expect(requestBody.messages).toContainEqual({
        role: 'user',
        content: 'Hello',
      });
    });
  });

  describe('getProviderName', () => {
    it('should return openai', () => {
      expect(client.getProviderName()).toBe('openai');
    });
  });
});
