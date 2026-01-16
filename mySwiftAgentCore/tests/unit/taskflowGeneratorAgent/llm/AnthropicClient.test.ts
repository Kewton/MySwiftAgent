/**
 * AnthropicClient Unit Tests
 *
 * Issue #364: Anthropic LLM client implementation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AnthropicClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/AnthropicClient.js';
import type { LLMClientConfig } from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type { LLMPrompt, LLMOptions } from '../../../../src/taskflowGeneratorAgent/types/llm.js';

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('AnthropicClient', () => {
  let client: AnthropicClient;
  let config: LLMClientConfig;

  beforeEach(() => {
    vi.clearAllMocks();

    config = {
      apiKey: 'test-api-key',
      defaultModel: 'claude-3-5-sonnet-20241022',
      defaultMaxTokens: 4096,
      defaultTemperature: 0.7,
    };

    client = new AnthropicClient(config);
  });

  describe('constructor', () => {
    it('should create instance with config', () => {
      expect(client).toBeInstanceOf(AnthropicClient);
      expect(client.getProviderName()).toBe('anthropic');
    });

    it('should store configuration', () => {
      const storedConfig = client.getConfig();
      expect(storedConfig.apiKey).toBe('test-api-key');
      expect(storedConfig.defaultModel).toBe('claude-3-5-sonnet-20241022');
    });
  });

  describe('generate', () => {
    it('should make API call with correct parameters', async () => {
      const mockResponse = {
        content: [{ type: 'text', text: '{"workflow": "test"}' }],
        model: 'claude-3-5-sonnet-20241022',
        usage: {
          input_tokens: 100,
          output_tokens: 50,
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
        'https://api.anthropic.com/v1/messages',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'x-api-key': 'test-api-key',
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
          }),
        })
      );

      expect(response.content).toBe('{"workflow": "test"}');
      expect(response.model).toBe('claude-3-5-sonnet-20241022');
      expect(response.usage.promptTokens).toBe(100);
      expect(response.usage.completionTokens).toBe(50);
    });

    it('should use custom model from options', async () => {
      const mockResponse = {
        content: [{ type: 'text', text: 'response' }],
        model: 'claude-3-opus-20240229',
        usage: { input_tokens: 50, output_tokens: 25 },
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
        model: 'claude-3-opus-20240229',
        temperature: 0.5,
        maxTokens: 2048,
      };

      const response = await client.generate(prompt, options);

      const fetchCall = mockFetch.mock.calls[0];
      const requestBody = JSON.parse(fetchCall[1].body);

      expect(requestBody.model).toBe('claude-3-opus-20240229');
      expect(requestBody.temperature).toBe(0.5);
      expect(requestBody.max_tokens).toBe(2048);
      expect(response.model).toBe('claude-3-opus-20240229');
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

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      await expect(client.generate(prompt)).rejects.toThrow('Network error');
    });

    it('should include system message correctly', async () => {
      const mockResponse = {
        content: [{ type: 'text', text: 'response' }],
        model: 'claude-3-5-sonnet-20241022',
        usage: { input_tokens: 50, output_tokens: 25 },
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

      expect(requestBody.system).toBe('You are a helpful assistant.');
      expect(requestBody.messages).toContainEqual({
        role: 'user',
        content: 'Hello',
      });
    });
  });

  describe('getProviderName', () => {
    it('should return anthropic', () => {
      expect(client.getProviderName()).toBe('anthropic');
    });
  });
});
