/**
 * ApiRestNode - REST API executor
 *
 * Issue #363: Executes HTTP requests
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';

const VALID_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'];

/**
 * Auth configuration
 */
interface AuthConfig {
  type: 'bearer' | 'basic' | 'api_key';
  secret_key: string;
  header_name?: string;
}

/**
 * ApiRestNodeExecutor - Executes REST API calls
 *
 * Supports:
 * - All HTTP methods
 * - URL variable interpolation
 * - Request headers
 * - Request body
 * - Authentication (Bearer, Basic, API Key)
 */
export class ApiRestNodeExecutor implements NodeExecutor {
  readonly type = 'api_rest' as const;

  /**
   * Execute HTTP request
   */
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const { url, method, headers = {}, auth } = config.config as {
        url: string;
        method: string;
        headers?: Record<string, string>;
        auth?: AuthConfig;
      };

      // Interpolate URL variables
      const interpolatedUrl = this.interpolateUrl(url, params);

      // Build headers
      const requestHeaders: Record<string, string> = { ...headers };

      // Add auth header if configured
      if (auth) {
        const authHeader = this.buildAuthHeader(auth, context.secrets);
        if (authHeader) {
          Object.assign(requestHeaders, authHeader);
        }
      }

      // Build request options
      const options: RequestInit = {
        method,
        headers: requestHeaders,
      };

      // Add body for non-GET methods
      if (method !== 'GET' && method !== 'HEAD' && params.body) {
        options.body = JSON.stringify(params.body);
        if (!requestHeaders['Content-Type']) {
          requestHeaders['Content-Type'] = 'application/json';
        }
      }

      // Execute request
      const response = await fetch(interpolatedUrl, options);

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
            code: 'HTTP_ERROR',
            message: `HTTP ${response.status}: ${response.statusText}`,
            details: { status: response.status, body: errorBody },
          },
        };
      }

      // Parse response
      const data = await response.json();

      return {
        success: true,
        output: data,
        metadata: {
          status: response.status,
          url: interpolatedUrl,
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: {
          code: 'NETWORK_ERROR',
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
    const { url, method } = config.config as { url?: string; method?: string };

    if (!url) {
      errors.push('url is required');
    }

    if (!method) {
      errors.push('method is required');
    } else if (!VALID_METHODS.includes(method.toUpperCase())) {
      errors.push(`Invalid method: ${method}. Must be one of: ${VALID_METHODS.join(', ')}`);
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Interpolate URL with parameters
   */
  private interpolateUrl(url: string, params: Record<string, unknown>): string {
    return url.replace(/\$\{(\w+)\}/g, (match, key) => {
      const value = params[key];
      return value !== undefined ? String(value) : match;
    });
  }

  /**
   * Build auth header
   */
  private buildAuthHeader(
    auth: AuthConfig,
    secrets: Record<string, string>
  ): Record<string, string> | null {
    const token = secrets[auth.secret_key];
    if (!token) {
      return null;
    }

    switch (auth.type) {
      case 'bearer':
        return { Authorization: `Bearer ${token}` };
      case 'basic':
        return { Authorization: `Basic ${token}` };
      case 'api_key':
        return { [auth.header_name || 'X-API-Key']: token };
      default:
        return null;
    }
  }
}

/**
 * Factory function
 */
export function createApiRestNodeExecutor(): ApiRestNodeExecutor {
  return new ApiRestNodeExecutor();
}
