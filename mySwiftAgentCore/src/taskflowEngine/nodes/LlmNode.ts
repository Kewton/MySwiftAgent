/**
 * LlmNode - LLM API executor
 *
 * Issue #363: Executes LLM API calls
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';

/**
 * LLM configuration
 */
interface LlmConfig {
  prompt: string;
  model?: string;
  system_prompt?: string;
  api_url?: string;
  max_tokens?: number;
  temperature?: number;
}

/**
 * LlmNodeExecutor - Executes LLM API calls
 *
 * Supports:
 * - Multiple LLM providers
 * - Prompt templating
 * - Configurable parameters
 */
export class LlmNodeExecutor implements NodeExecutor {
  readonly type = 'llm' as const;

  /**
   * Execute LLM request
   */
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const llmConfig = config.config as unknown as LlmConfig;
      const {
        prompt,
        model = 'gpt-3.5-turbo',
        system_prompt,
        api_url = 'https://api.openai.com/v1/chat/completions',
        max_tokens = 1000,
        temperature = 0.7,
      } = llmConfig;

      // Get API key from secrets
      const apiKey = context.secrets['OPENAI_API_KEY'] || context.secrets['LLM_API_KEY'];
      if (!apiKey) {
        return {
          success: false,
          output: null,
          error: {
            code: 'LLM_CONFIG_ERROR',
            message: 'LLM API key not found in secrets',
          },
        };
      }

      // Build user prompt from template
      const userPrompt = this.interpolateTemplate(prompt, params);

      // Build messages
      const messages: Array<{ role: string; content: string }> = [];
      if (system_prompt) {
        messages.push({ role: 'system', content: system_prompt });
      }
      messages.push({ role: 'user', content: userPrompt });

      // Make API request
      const response = await fetch(api_url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model,
          messages,
          max_tokens,
          temperature,
        }),
      });

      if (!response.ok) {
        let errorBody: unknown;
        try {
          errorBody = await response.json();
        } catch {
          errorBody = response.statusText;
        }

        return {
          success: false,
          output: null,
          error: {
            code: 'LLM_API_ERROR',
            message: `LLM API error: ${response.status}`,
            details: errorBody,
          },
        };
      }

      const data = (await response.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
        usage?: {
          prompt_tokens?: number;
          completion_tokens?: number;
          total_tokens?: number;
        };
      };
      const content = data.choices?.[0]?.message?.content || '';

      return {
        success: true,
        output: {
          content,
          usage: data.usage || {},
        },
        metadata: {
          model,
          prompt: userPrompt,
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: {
          code: 'LLM_NETWORK_ERROR',
          message,
        },
      };
    }
  }

  /**
   * Validate configuration
   */
  validate(config: NodeConfig): NodeValidationResult {
    const errors: string[] = [];
    const { prompt } = config.config as unknown as LlmConfig;

    if (!prompt) {
      errors.push('prompt is required');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Interpolate template with values
   */
  private interpolateTemplate(
    template: string,
    params: Record<string, unknown>
  ): string {
    return template.replace(/\{\{([^}]+)\}\}/g, (match, key) => {
      const value = this.getNestedValue(params, key.trim());
      return value !== undefined ? String(value) : match;
    });
  }

  /**
   * Get nested value from object
   */
  private getNestedValue(
    obj: Record<string, unknown>,
    path: string
  ): unknown {
    const parts = path.split('.');
    let current: unknown = obj;

    for (const part of parts) {
      if (current === null || current === undefined) {
        return undefined;
      }
      if (typeof current === 'object') {
        current = (current as Record<string, unknown>)[part];
      } else {
        return undefined;
      }
    }

    return current;
  }
}

/**
 * Factory function
 */
export function createLlmNodeExecutor(): LlmNodeExecutor {
  return new LlmNodeExecutor();
}
