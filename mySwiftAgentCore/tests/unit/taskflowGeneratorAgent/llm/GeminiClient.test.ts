/**
 * GeminiClient Unit Tests
 *
 * Issue #364: Gemini LLM client tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { GeminiClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/GeminiClient.js';
import { LLMApiError } from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type { LLMPrompt } from '../../../../src/taskflowGeneratorAgent/types/llm.js';

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('GeminiClient', () => {
  let client: GeminiClient;

  beforeEach(() => {
    mockFetch.mockReset();
    client = new GeminiClient({
      apiKey: 'test-api-key',
      defaultModel: 'gemini-1.5-pro',
      defaultMaxTokens: 4096,
      defaultTemperature: 0.7,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('constructor', () => {
    it('should use default baseUrl', () => {
      const c = new GeminiClient({
        apiKey: 'test-key',
        defaultModel: 'gemini-1.5-pro',
      });

      expect(c.getProviderName()).toBe('gemini');
    });

    it('should use custom baseUrl', () => {
      const c = new GeminiClient({
        apiKey: 'test-key',
        defaultModel: 'gemini-1.5-pro',
        baseUrl: 'https://custom.api.com/v1',
      });

      expect(c.getProviderName()).toBe('gemini');
    });
  });

  describe('getProviderName', () => {
    it('should return gemini', () => {
      expect(client.getProviderName()).toBe('gemini');
    });
  });

  describe('generate', () => {
    it('should make correct API call', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [
            {
              content: {
                parts: [{ text: '{"result": "success"}' }],
                role: 'model',
              },
              finishReason: 'STOP',
            },
          ],
          usageMetadata: {
            promptTokenCount: 100,
            candidatesTokenCount: 50,
            totalTokenCount: 150,
          },
          modelVersion: 'gemini-1.5-pro-002',
        }),
      });

      const prompt: LLMPrompt = {
        system: 'You are a helpful assistant.',
        user: 'Generate something.',
      };

      const response = await client.generate(prompt);

      expect(response.content).toBe('{"result": "success"}');
      expect(response.model).toBe('gemini-1.5-pro-002');
      expect(response.usage.promptTokens).toBe(100);
      expect(response.usage.completionTokens).toBe(50);
    });

    it('should include system instruction in request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      const prompt: LLMPrompt = {
        system: 'You are a JSON generator.',
        user: 'Create JSON.',
      };

      await client.generate(prompt);

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.systemInstruction).toBeDefined();
      expect(body.systemInstruction.parts[0].text).toBe('You are a JSON generator.');
    });

    it('should include examples as user/model pairs', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      const prompt: LLMPrompt = {
        system: 'System prompt',
        user: 'User message',
        examples: [
          { input: 'Example input', output: 'Example output' },
        ],
      };

      await client.generate(prompt);

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body.contents).toHaveLength(3); // 2 example messages + 1 user message
      expect(body.contents[0].role).toBe('user');
      expect(body.contents[0].parts[0].text).toBe('Example input');
      expect(body.contents[1].role).toBe('model');
      expect(body.contents[1].parts[0].text).toBe('Example output');
    });

    it('should include API key in URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      await client.generate({
        system: 'System',
        user: 'User',
      });

      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[0]).toContain('key=test-api-key');
    });

    it('should use custom options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      await client.generate(
        { system: 'System', user: 'User' },
        {
          model: 'gemini-1.5-flash',
          temperature: 0.3,
          maxTokens: 2048,
        }
      );

      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(callArgs[0]).toContain('gemini-1.5-flash');
      expect(body.generationConfig.temperature).toBe(0.3);
      expect(body.generationConfig.maxOutputTokens).toBe(2048);
    });

    it('should throw LLMApiError on API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () => Promise.resolve({
          error: {
            code: 400,
            message: 'Invalid request',
            status: 'INVALID_ARGUMENT',
          },
        }),
      });

      await expect(
        client.generate({ system: 'System', user: 'User' })
      ).rejects.toThrow(LLMApiError);
    });

    it('should handle missing usage metadata', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
          // usageMetadata is missing
        }),
      });

      const response = await client.generate({
        system: 'System',
        user: 'User',
      });

      expect(response.usage.promptTokens).toBe(0);
      expect(response.usage.completionTokens).toBe(0);
      expect(response.usage.totalTokens).toBe(0);
    });

    it('should handle empty candidates', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [],
        }),
      });

      const response = await client.generate({
        system: 'System',
        user: 'User',
      });

      expect(response.content).toBe('');
    });

    it('should handle multiple parts in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [
            {
              content: {
                parts: [
                  { text: 'Part 1' },
                  { text: 'Part 2' },
                  { text: 'Part 3' },
                ],
              },
            },
          ],
        }),
      });

      const response = await client.generate({
        system: 'System',
        user: 'User',
      });

      expect(response.content).toBe('Part 1Part 2Part 3');
    });

    it('should record latency', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      const response = await client.generate({
        system: 'System',
        user: 'User',
      });

      expect(response.latencyMs).toBeGreaterThanOrEqual(0);
    });

    it('should include prompt in response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [{ content: { parts: [{ text: 'response' }] } }],
        }),
      });

      const prompt: LLMPrompt = {
        system: 'System prompt',
        user: 'User prompt',
      };

      const response = await client.generate(prompt);

      expect(response.systemPrompt).toBe('System prompt');
      expect(response.userPrompt).toBe('User prompt');
    });
  });

  describe('generateStructured', () => {
    it('should parse JSON response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          candidates: [
            {
              content: {
                parts: [{ text: '{"workflow_name": "test", "steps": []}' }],
              },
            },
          ],
        }),
      });

      const { z } = await import('zod');
      const schema = z.object({
        workflow_name: z.string(),
        steps: z.array(z.unknown()),
      });

      const result = await client.generateStructured(
        { system: 'Generate JSON', user: 'Create workflow' },
        schema
      );

      expect(result.data.workflow_name).toBe('test');
      expect(result.data.steps).toEqual([]);
    });
  });
});
