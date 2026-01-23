/**
 * LlmNode Unit Tests
 *
 * Issue #363: LLM API integration node
 * Issue #377: Added tests for requiredSecrets property
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  LlmNodeExecutor,
  createLlmNodeExecutor,
} from '../../../../src/taskflowEngine/nodes/LlmNode.js';
import type { NodeConfig, ExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('LlmNodeExecutor', () => {
  let executor: LlmNodeExecutor;
  let context: ExecutionContext;

  beforeEach(() => {
    vi.clearAllMocks();
    executor = new LlmNodeExecutor();
    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {
        OPENAI_API_KEY: 'test-key',
      },
    };
  });

  describe('type', () => {
    it('should have type llm', () => {
      expect(executor.type).toBe('llm');
    });
  });

  /**
   * Issue #377: Tests for static requiredSecrets property
   */
  describe('requiredSecrets (Issue #377, Issue #396)', () => {
    it('should have requiredSecrets property', () => {
      expect(executor.requiredSecrets).toBeDefined();
      expect(Array.isArray(executor.requiredSecrets)).toBe(true);
    });

    it('should include OPENAI_API_KEY in requiredSecrets', () => {
      expect(executor.requiredSecrets).toContain('OPENAI_API_KEY');
    });

    it('should NOT include LLM_API_KEY in requiredSecrets (Issue #396: optional fallback)', () => {
      // LLM_API_KEY is now an optional fallback, not a required secret
      expect(executor.requiredSecrets).not.toContain('LLM_API_KEY');
    });

    it('should be a readonly array with only OPENAI_API_KEY', () => {
      // Issue #396: Only OPENAI_API_KEY is required, LLM_API_KEY is optional fallback
      const secrets = executor.requiredSecrets;
      expect(secrets.length).toBe(1);
      expect(secrets[0]).toBe('OPENAI_API_KEY');
    });
  });

  describe('validate', () => {
    it('should validate config with prompt', () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Summarize the following text: {{text}}',
          model: 'gpt-4',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should require prompt', () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          model: 'gpt-4',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('prompt is required');
    });

    it('should use default model if not specified', () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });
  });

  describe('execute', () => {
    it('should call OpenAI API with prompt', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Say hello to {{name}}',
          model: 'gpt-4',
        },
      };
      const params = { name: 'World' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            choices: [
              {
                message: {
                  content: 'Hello, World!',
                },
              },
            ],
            usage: {
              prompt_tokens: 10,
              completion_tokens: 5,
              total_tokens: 15,
            },
          }),
      });

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        content: 'Hello, World!',
        usage: {
          prompt_tokens: 10,
          completion_tokens: 5,
          total_tokens: 15,
        },
      });
      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.openai.com/v1/chat/completions',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer test-key',
          }),
        })
      );
    });

    it('should handle API error response', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () => Promise.resolve({ error: { message: 'Invalid API key' } }),
      });

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('LLM_API_ERROR');
    });

    it('should handle missing API key', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
        },
      };
      context.secrets = {};

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('LLM_CONFIG_ERROR');
    });

    it('should use system prompt when provided', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
          system_prompt: 'You are a helpful assistant.',
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            choices: [{ message: { content: 'Hi!' } }],
            usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
          }),
      });

      await executor.execute(config, {}, context);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('You are a helpful assistant'),
        })
      );
    });

    it('should apply temperature setting', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
          temperature: 0.5,
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            choices: [{ message: { content: 'Hi!' } }],
            usage: { prompt_tokens: 5, completion_tokens: 2, total_tokens: 7 },
          }),
      });

      await executor.execute(config, {}, context);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"temperature":0.5'),
        })
      );
    });

    it('should handle network errors', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Hello',
        },
      };

      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('LLM_NETWORK_ERROR');
    });

    it('should interpolate variables in prompt', async () => {
      const config: NodeConfig = {
        nodeId: 'llm_1',
        type: 'llm',
        config: {
          prompt: 'Translate "{{text}}" to {{language}}',
        },
      };
      const params = { text: 'Hello', language: 'Japanese' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            choices: [{ message: { content: 'こんにちは' } }],
            usage: { prompt_tokens: 10, completion_tokens: 3, total_tokens: 13 },
          }),
      });

      await executor.execute(config, params, context);

      // Verify fetch was called with body containing interpolated prompt
      expect(mockFetch).toHaveBeenCalled();
      const callArgs = mockFetch.mock.calls[0];
      const body = JSON.parse(callArgs[1].body);
      expect(body.messages[0].content).toBe('Translate "Hello" to Japanese');
    });
  });
});

describe('createLlmNodeExecutor factory', () => {
  it('should create a LlmNodeExecutor instance', () => {
    const executor = createLlmNodeExecutor();
    expect(executor).toBeInstanceOf(LlmNodeExecutor);
  });
});
