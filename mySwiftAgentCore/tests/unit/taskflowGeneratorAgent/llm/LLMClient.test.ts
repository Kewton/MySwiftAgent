/**
 * LLMClient Interface Unit Tests
 *
 * Issue #364: LLM client abstraction
 */

import { describe, it, expect, vi } from 'vitest';
import { z } from 'zod';
import type {
  LLMClient,
  LLMClientConfig,
} from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import { BaseLLMClient } from '../../../../src/taskflowGeneratorAgent/llm/LLMClient.js';
import type { LLMPrompt, LLMOptions, LLMResponse } from '../../../../src/taskflowGeneratorAgent/types/llm.js';

// Mock LLM Client for testing
class MockLLMClient extends BaseLLMClient {
  private mockResponse: string;

  constructor(config: LLMClientConfig, mockResponse: string = '{"result": "test"}') {
    super(config);
    this.mockResponse = mockResponse;
  }

  async callApi(prompt: LLMPrompt, options?: LLMOptions): Promise<LLMResponse> {
    return {
      content: this.mockResponse,
      model: options?.model || this.config.defaultModel,
      usage: {
        promptTokens: 100,
        completionTokens: 50,
        totalTokens: 150,
      },
      latencyMs: 500,
      systemPrompt: prompt.system,
      userPrompt: prompt.user,
    };
  }

  getProviderName(): string {
    return 'mock';
  }
}

describe('LLMClient Interface', () => {
  describe('BaseLLMClient', () => {
    it('should store configuration', () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
        defaultMaxTokens: 4096,
        defaultTemperature: 0.7,
      };

      const client = new MockLLMClient(config);

      // Use toMatchObject because BaseLLMClient adds default values (timeout)
      expect(client.getConfig()).toMatchObject(config);
      // Verify default timeout is applied
      expect(client.getConfig().timeout).toBe(30000);
    });

    it('should provide provider name', () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const client = new MockLLMClient(config);

      expect(client.getProviderName()).toBe('mock');
    });
  });

  describe('generate method', () => {
    it('should call api and return response', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const client = new MockLLMClient(config);

      const prompt: LLMPrompt = {
        system: 'You are a helpful assistant.',
        user: 'Generate something.',
      };

      const response = await client.generate(prompt);

      expect(response).toBeDefined();
      expect(response.content).toBe('{"result": "test"}');
      expect(response.model).toBe('test-model');
    });

    it('should use provided options', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const client = new MockLLMClient(config);

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      const options: LLMOptions = {
        model: 'custom-model',
        temperature: 0.5,
        maxTokens: 2048,
      };

      const response = await client.generate(prompt, options);

      expect(response.model).toBe('custom-model');
    });
  });

  describe('generateStructured method', () => {
    it('should parse response according to schema', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const mockResponse = JSON.stringify({
        workflow_name: 'test_workflow',
        steps: [{ id: 'step1', type: 'transform' }],
      });

      const client = new MockLLMClient(config, mockResponse);

      const prompt: LLMPrompt = {
        system: 'Generate workflow.',
        user: 'Create a test workflow.',
      };

      const schema = z.object({
        workflow_name: z.string(),
        steps: z.array(
          z.object({
            id: z.string(),
            type: z.string(),
          })
        ),
      });

      const result = await client.generateStructured(prompt, schema);

      expect(result.data.workflow_name).toBe('test_workflow');
      expect(result.data.steps).toHaveLength(1);
      expect(result.raw.content).toBe(mockResponse);
    });

    it('should throw error for invalid JSON', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const client = new MockLLMClient(config, 'not valid json');

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      const schema = z.object({
        data: z.string(),
      });

      await expect(client.generateStructured(prompt, schema)).rejects.toThrow();
    });

    it('should throw error for schema mismatch', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const client = new MockLLMClient(config, JSON.stringify({ wrong_field: 'value' }));

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      const schema = z.object({
        required_field: z.string(),
      });

      await expect(client.generateStructured(prompt, schema)).rejects.toThrow();
    });

    it('should extract JSON from markdown code blocks', async () => {
      const config: LLMClientConfig = {
        apiKey: 'test-key',
        defaultModel: 'test-model',
      };

      const markdownResponse = '```json\n{"workflow_name": "test"}\n```';
      const client = new MockLLMClient(config, markdownResponse);

      const prompt: LLMPrompt = {
        system: 'System',
        user: 'User',
      };

      const schema = z.object({
        workflow_name: z.string(),
      });

      const result = await client.generateStructured(prompt, schema);

      expect(result.data.workflow_name).toBe('test');
    });
  });
});
