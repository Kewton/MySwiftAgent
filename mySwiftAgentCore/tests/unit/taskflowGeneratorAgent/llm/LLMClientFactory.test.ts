/**
 * LLMClientFactory Unit Tests
 *
 * Issue #364: LLM client factory with MyVault integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  LLMClientFactory,
  createLLMClientFactory,
} from '../../../../src/taskflowGeneratorAgent/llm/LLMClientFactory.js';
import { AnthropicClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/AnthropicClient.js';
import { OpenAIClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/OpenAIClient.js';
import { GeminiClient } from '../../../../src/taskflowGeneratorAgent/llm/clients/GeminiClient.js';

// Mock MyVault client
interface MockMyVaultClient {
  getSecret: (key: string) => Promise<string>;
}

describe('LLMClientFactory', () => {
  let mockMyVaultClient: MockMyVaultClient;
  let factory: LLMClientFactory;

  beforeEach(() => {
    mockMyVaultClient = {
      getSecret: vi.fn().mockImplementation((key: string) => {
        const secrets: Record<string, string> = {
          anthropic_api_key: 'test-anthropic-key',
          openai_api_key: 'test-openai-key',
          gemini_api_key: 'test-gemini-key',
        };
        const value = secrets[key];
        if (value) {
          return Promise.resolve(value);
        }
        return Promise.reject(new Error(`Secret not found: ${key}`));
      }),
    };

    factory = new LLMClientFactory(mockMyVaultClient);
  });

  describe('create', () => {
    it('should create AnthropicClient for claude models', async () => {
      const client = await factory.create('claude-3-5-sonnet-20241022');

      expect(client).toBeInstanceOf(AnthropicClient);
      expect(mockMyVaultClient.getSecret).toHaveBeenCalledWith('anthropic_api_key');
    });

    it('should create AnthropicClient for claude-3-opus', async () => {
      const client = await factory.create('claude-3-opus-20240229');

      expect(client).toBeInstanceOf(AnthropicClient);
    });

    it('should create OpenAIClient for gpt models', async () => {
      const client = await factory.create('gpt-4-turbo-preview');

      expect(client).toBeInstanceOf(OpenAIClient);
      expect(mockMyVaultClient.getSecret).toHaveBeenCalledWith('openai_api_key');
    });

    it('should create OpenAIClient for gpt-4o', async () => {
      const client = await factory.create('gpt-4o');

      expect(client).toBeInstanceOf(OpenAIClient);
    });

    it('should create GeminiClient for gemini models', async () => {
      const client = await factory.create('gemini-pro');

      expect(client).toBeInstanceOf(GeminiClient);
      expect(mockMyVaultClient.getSecret).toHaveBeenCalledWith('gemini_api_key');
    });

    it('should create GeminiClient for gemini-1.5-pro', async () => {
      const client = await factory.create('gemini-1.5-pro');

      expect(client).toBeInstanceOf(GeminiClient);
    });

    it('should throw error for unknown model', async () => {
      await expect(factory.create('unknown-model')).rejects.toThrow('Unknown model');
    });

    it('should throw error if API key not found in MyVault', async () => {
      mockMyVaultClient.getSecret = vi
        .fn()
        .mockRejectedValue(new Error('Secret not found'));

      await expect(factory.create('claude-3-5-sonnet-20241022')).rejects.toThrow(
        'Secret not found'
      );
    });
  });

  describe('getProviderForModel', () => {
    it('should return anthropic for claude models', () => {
      expect(factory.getProviderForModel('claude-3-5-sonnet-20241022')).toBe('anthropic');
      expect(factory.getProviderForModel('claude-3-opus-20240229')).toBe('anthropic');
    });

    it('should return openai for gpt models', () => {
      expect(factory.getProviderForModel('gpt-4-turbo-preview')).toBe('openai');
      expect(factory.getProviderForModel('gpt-4o')).toBe('openai');
    });

    it('should return gemini for gemini models', () => {
      expect(factory.getProviderForModel('gemini-pro')).toBe('gemini');
      expect(factory.getProviderForModel('gemini-1.5-pro')).toBe('gemini');
    });

    it('should return null for unknown models', () => {
      expect(factory.getProviderForModel('unknown-model')).toBeNull();
    });
  });

  describe('getSupportedModels', () => {
    it('should return list of supported models', () => {
      const models = factory.getSupportedModels();

      expect(models).toContain('claude-3-5-sonnet-20241022');
      expect(models).toContain('gpt-4-turbo-preview');
      expect(models).toContain('gemini-pro');
      expect(models.length).toBeGreaterThan(0);
    });
  });

  describe('caching', () => {
    it('should cache clients by model', async () => {
      const client1 = await factory.create('claude-3-5-sonnet-20241022');
      const client2 = await factory.create('claude-3-5-sonnet-20241022');

      expect(client1).toBe(client2);
      expect(mockMyVaultClient.getSecret).toHaveBeenCalledTimes(1);
    });

    it('should create different clients for different models', async () => {
      const anthropicClient = await factory.create('claude-3-5-sonnet-20241022');
      const openaiClient = await factory.create('gpt-4-turbo-preview');

      expect(anthropicClient).not.toBe(openaiClient);
      expect(mockMyVaultClient.getSecret).toHaveBeenCalledTimes(2);
    });
  });
});

describe('createLLMClientFactory', () => {
  it('should create factory instance', () => {
    const mockClient = {
      getSecret: vi.fn().mockResolvedValue('test-key'),
    };

    const factory = createLLMClientFactory(mockClient);

    expect(factory).toBeInstanceOf(LLMClientFactory);
  });
});
