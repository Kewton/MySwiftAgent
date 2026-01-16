/**
 * LLMClientFactory - Factory for creating LLM clients
 *
 * Issue #364: Factory pattern with MyVault integration
 *
 * IMPORTANT: API keys must be retrieved from MyVault.
 * Environment variable fallback is PROHIBITED.
 */

import type { LLMClient, LLMClientConfig } from './LLMClient.js';
import { AnthropicClient } from './clients/AnthropicClient.js';
import { OpenAIClient } from './clients/OpenAIClient.js';
import { GeminiClient } from './clients/GeminiClient.js';
import type { LLMProvider } from '../types/llm.js';

/**
 * MyVault Client Interface
 */
export interface MyVaultClient {
  getSecret(key: string): Promise<string>;
}

/**
 * Model to provider mapping
 */
const MODEL_PROVIDER_MAP: Record<string, LLMProvider> = {
  // Anthropic models
  'claude-3-5-sonnet-20241022': 'anthropic',
  'claude-3-opus-20240229': 'anthropic',
  'claude-3-sonnet-20240229': 'anthropic',
  'claude-3-haiku-20240307': 'anthropic',

  // OpenAI models
  'gpt-4-turbo-preview': 'openai',
  'gpt-4-turbo': 'openai',
  'gpt-4o': 'openai',
  'gpt-4o-mini': 'openai',
  'gpt-4': 'openai',
  'gpt-3.5-turbo': 'openai',

  // Gemini models
  'gemini-pro': 'gemini',
  'gemini-1.5-pro': 'gemini',
  'gemini-1.5-flash': 'gemini',
};

/**
 * Provider to secret key mapping
 */
const PROVIDER_SECRET_KEYS: Record<LLMProvider, string> = {
  anthropic: 'anthropic_api_key',
  openai: 'openai_api_key',
  gemini: 'gemini_api_key',
};

/**
 * LLMClientFactory - Creates LLM clients with MyVault integration
 *
 * Features:
 * - Provider detection from model name
 * - MyVault-based API key retrieval
 * - Client caching for efficiency
 */
export class LLMClientFactory {
  private readonly myVaultClient: MyVaultClient;
  private readonly clientCache: Map<string, LLMClient> = new Map();

  constructor(myVaultClient: MyVaultClient) {
    this.myVaultClient = myVaultClient;
  }

  /**
   * Create LLM client for specified model
   *
   * @param modelName - Model name (e.g., 'claude-3-5-sonnet-20241022')
   * @returns LLM client instance
   */
  async create(modelName: string): Promise<LLMClient> {
    // Check cache first
    const cached = this.clientCache.get(modelName);
    if (cached) {
      return cached;
    }

    const provider = this.getProviderForModel(modelName);
    if (!provider) {
      throw new Error(`Unknown model: ${modelName}. Supported models: ${this.getSupportedModels().join(', ')}`);
    }

    // Get API key from MyVault (no environment variable fallback!)
    const secretKey = PROVIDER_SECRET_KEYS[provider];
    const apiKey = await this.myVaultClient.getSecret(secretKey);

    const config: LLMClientConfig = {
      apiKey,
      defaultModel: modelName,
      defaultMaxTokens: 4096,
      defaultTemperature: 0.7,
    };

    let client: LLMClient;

    switch (provider) {
      case 'anthropic':
        client = new AnthropicClient(config);
        break;
      case 'openai':
        client = new OpenAIClient(config);
        break;
      case 'gemini':
        client = new GeminiClient(config);
        break;
      default:
        throw new Error(`Unsupported provider: ${provider}`);
    }

    // Cache the client
    this.clientCache.set(modelName, client);

    return client;
  }

  /**
   * Get provider for model name
   *
   * @param modelName - Model name
   * @returns Provider name or null if unknown
   */
  getProviderForModel(modelName: string): LLMProvider | null {
    // Direct lookup
    const provider = MODEL_PROVIDER_MAP[modelName];
    if (provider) {
      return provider;
    }

    // Pattern matching for model prefixes
    if (modelName.startsWith('claude')) {
      return 'anthropic';
    }
    if (modelName.startsWith('gpt')) {
      return 'openai';
    }
    if (modelName.startsWith('gemini')) {
      return 'gemini';
    }

    return null;
  }

  /**
   * Get list of supported models
   *
   * @returns Array of supported model names
   */
  getSupportedModels(): string[] {
    return Object.keys(MODEL_PROVIDER_MAP);
  }

  /**
   * Clear client cache
   */
  clearCache(): void {
    this.clientCache.clear();
  }
}

/**
 * Factory function for creating LLMClientFactory
 */
export function createLLMClientFactory(myVaultClient: MyVaultClient): LLMClientFactory {
  return new LLMClientFactory(myVaultClient);
}
