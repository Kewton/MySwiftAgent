/**
 * ApiRestNode - REST API executor
 *
 * Issue #363: Executes HTTP requests
 * Issue #372: Extended with capability_id support for URL resolution
 * Issue #377: Added getRequiredSecrets for dynamic secrets injection
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
 * Extended node configuration with capability support
 */
export interface ApiRestNodeConfig {
  /** Direct URL (legacy mode) */
  url?: string;
  /** Capability ID for URL resolution (new mode) */
  capability_id?: string;
  /** Project ID for capability lookup */
  project_id?: string;
  /** HTTP method (required for url mode, optional for capability_id mode) */
  method?: string;
  /** Custom headers */
  headers?: Record<string, string>;
  /** Authentication configuration */
  auth?: AuthConfig;
  /** Request body (with variable interpolation support) */
  body?: unknown;
  /** Request timeout in milliseconds */
  timeout_ms?: number;
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
 * - capability_id for URL resolution (Issue #372)
 * - Dynamic secret requirements based on auth config (Issue #377)
 */
export class ApiRestNodeExecutor implements NodeExecutor {
  readonly type = 'api_rest' as const;

  /**
   * Issue #377: Get dynamic secret requirements based on node configuration
   *
   * Returns the secret key(s) needed based on the auth configuration.
   *
   * @param config - Node configuration
   * @returns Promise resolving to array of required secret keys
   */
  async getRequiredSecrets(config: NodeConfig): Promise<string[]> {
    const nodeConfig = config.config as ApiRestNodeConfig;
    const secrets: string[] = [];

    // Check for auth configuration
    if (nodeConfig.auth?.secret_key) {
      secrets.push(nodeConfig.auth.secret_key);
    }

    return secrets;
  }

  /**
   * Execute HTTP request
   *
   * Two modes of operation:
   * 1. Direct URL (legacy): url is specified directly
   * 2. Capability mode (new): capability_id is specified, URL is resolved
   */
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    const nodeConfig = config.config as ApiRestNodeConfig;
    const { url, capability_id, project_id } = nodeConfig;

    // Mode 1: capability_id specified - delegate to CapabilityExecutor
    if (capability_id) {
      return this.executeWithCapability(
        capability_id,
        project_id ?? 'default_project',
        params,
        context
      );
    }

    // Mode 2: Direct URL - execute directly
    if (url) {
      return this.executeDirectUrl(nodeConfig, params, context);
    }

    // Neither url nor capability_id specified
    return {
      success: false,
      output: null,
      error: {
        code: 'CONFIGURATION_ERROR',
        message: 'Either url or capability_id must be specified',
      },
    };
  }

  /**
   * Execute using capability_id with CapabilityExecutor
   * Issue #372: Uses ICapabilityExecutor from NodeExecutionContext
   */
  private async executeWithCapability(
    capabilityId: string,
    projectId: string,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    if (!context.capabilityExecutor) {
      return {
        success: false,
        output: null,
        error: {
          code: 'EXECUTOR_NOT_AVAILABLE',
          message:
            'CapabilityExecutor is not available in context. Ensure the executor is properly initialized.',
        },
      };
    }

    return context.capabilityExecutor.execute(capabilityId, params, context, projectId);
  }

  /**
   * Execute with direct URL (legacy mode)
   */
  private async executeDirectUrl(
    nodeConfig: ApiRestNodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const { url, method = 'GET', headers = {}, auth, body: configBody } = nodeConfig;

      // URL should be defined at this point (checked in execute)
      if (!url) {
        return {
          success: false,
          output: null,
          error: {
            code: 'CONFIGURATION_ERROR',
            message: 'URL is required for direct URL execution',
          },
        };
      }

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
      // Priority: config.body > params.body
      const rawBody = configBody ?? params.body;
      if (method !== 'GET' && method !== 'HEAD' && rawBody) {
        // Resolve variable references in body
        const resolvedBody = this.resolveVariables(rawBody, context);
        options.body = JSON.stringify(resolvedBody);
        requestHeaders['Content-Type'] ??= 'application/json';
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
   *
   * Validates both legacy URL mode and capability_id mode.
   * At least one of url or capability_id must be specified.
   */
  validate(config: NodeConfig): NodeValidationResult {
    const errors: string[] = [];
    const nodeConfig = config.config as ApiRestNodeConfig;
    const { url, capability_id, method } = nodeConfig;

    // Either url or capability_id must be specified
    if (!url && !capability_id) {
      errors.push('Either url or capability_id is required');
    }

    // Method is required for direct URL mode
    // For capability_id mode, method is optional (derived from capability)
    if (!capability_id && !method) {
      errors.push('method is required when using url');
    } else if (method && !VALID_METHODS.includes(method.toUpperCase())) {
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
   * Resolve variable references in body
   *
   * Supports:
   * - ${inputs.field} - workflow input variables
   * - ${step_id.field} - step output variables
   */
  private resolveVariables(value: unknown, context: NodeExecutionContext): unknown {
    if (value === null || value === undefined) {
      return value;
    }

    // Handle arrays
    if (Array.isArray(value)) {
      return value.map((item) => this.resolveVariables(item, context));
    }

    // Handle objects
    if (typeof value === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(value)) {
        result[key] = this.resolveVariables(val, context);
      }
      return result;
    }

    // Handle strings with variable references
    if (typeof value === 'string') {
      // Check for ${...} pattern
      const match = value.match(/^\$\{(.+)\}$/);
      if (match) {
        const path = match[1]!;
        return this.resolvePath(path, context);
      }
    }

    return value;
  }

  /**
   * Resolve a variable path
   *
   * Paths:
   * - inputs.field - workflow input
   * - step_id.field - step output
   */
  private resolvePath(path: string, context: NodeExecutionContext): unknown {
    const parts = path.split('.');
    if (parts.length === 0) {
      return undefined;
    }

    const root = parts[0]!;
    const rest = parts.slice(1);

    let value: unknown;

    if (root === 'inputs') {
      // Access workflow inputs from context.variables['input']
      value = context.variables['input'] as Record<string, unknown> | undefined;
    } else if (root === 'steps') {
      // Access step results: steps.step_id.field
      if (rest.length === 0) {
        return undefined;
      }
      const stepId = rest[0]!;
      value = context.stepResults[stepId];
      // Navigate the remaining path after stepId
      for (let i = 1; i < rest.length; i++) {
        if (value === null || value === undefined) {
          return undefined;
        }
        if (typeof value === 'object') {
          value = (value as Record<string, unknown>)[rest[i]!];
        } else {
          return undefined;
        }
      }
      return value;
    } else {
      // Try direct step result access: step_id.field
      value = context.stepResults[root];
    }

    // Navigate nested path
    for (const part of rest) {
      if (value === null || value === undefined) {
        return undefined;
      }
      if (typeof value === 'object') {
        value = (value as Record<string, unknown>)[part];
      } else {
        return undefined;
      }
    }

    return value;
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
        return { [auth.header_name ?? 'X-API-Key']: token };
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
