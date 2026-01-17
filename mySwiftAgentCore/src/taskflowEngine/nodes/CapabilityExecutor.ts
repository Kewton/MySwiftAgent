/**
 * CapabilityExecutor - Executes capabilities by resolving URLs and making HTTP requests
 *
 * Issue #372: Capability-based API execution for TaskFlowEngine
 *
 * Features:
 * - Resolves capability IDs to full URLs using URLResolver
 * - Handles authentication based on capability configuration
 * - Executes HTTP requests with proper error handling
 */

import type { CapabilityRegistry } from '../../capabilityManagement/registry/CapabilityRegistry.js';
import type { URLResolver } from '../../capabilityManagement/endpoint/URLResolver.js';
import type { ResolvedEndpoint } from '../../capabilityManagement/endpoint/types.js';
import type { NodeResult, NodeExecutionContext, NodeValidationResult } from './BaseNode.js';

/**
 * CapabilityExecutor options
 */
export interface CapabilityExecutorOptions {
  /** Capability registry for capability lookup */
  capabilityRegistry: CapabilityRegistry;
  /** URL resolver for endpoint resolution */
  urlResolver: URLResolver;
}

/**
 * CapabilityExecutor - Executes capabilities by ID
 *
 * Responsibilities:
 * - Look up capability by ID from registry
 * - Resolve complete URL using URLResolver
 * - Execute HTTP request with authentication
 * - Return standardized NodeResult
 */
export class CapabilityExecutor {
  private readonly registry: CapabilityRegistry;
  private readonly urlResolver: URLResolver;

  constructor(options: CapabilityExecutorOptions) {
    this.registry = options.capabilityRegistry;
    this.urlResolver = options.urlResolver;
  }

  /**
   * Execute a capability by ID
   *
   * @param capabilityId - The capability identifier
   * @param params - Parameters to pass to the capability
   * @param context - Execution context with secrets
   * @param projectId - Project ID (defaults to 'default_project')
   * @returns NodeResult with execution outcome
   */
  async execute(
    capabilityId: string,
    params: Record<string, unknown>,
    context: NodeExecutionContext,
    projectId = 'default_project'
  ): Promise<NodeResult> {
    try {
      // Look up capability
      const capability = this.registry.getCapability(projectId, capabilityId);

      if (!capability) {
        return {
          success: false,
          output: null,
          error: {
            code: 'CAPABILITY_NOT_FOUND',
            message: `Capability '${capabilityId}' not found in project '${projectId}'`,
          },
        };
      }

      // Resolve URL
      let resolvedEndpoint: ResolvedEndpoint;
      try {
        resolvedEndpoint = await this.urlResolver.resolveCapabilityUrl(capability, projectId);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          output: null,
          error: {
            code: 'URL_RESOLUTION_ERROR',
            message: `Failed to resolve URL for capability '${capabilityId}': ${message}`,
          },
        };
      }

      // Build request headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...resolvedEndpoint.headers,
      };

      // Add authentication header
      if (resolvedEndpoint.auth) {
        const authHeader = this.buildAuthHeader(resolvedEndpoint.auth, context.secrets);
        if (authHeader) {
          Object.assign(headers, authHeader);
        }
      }

      // Build request options
      const method = resolvedEndpoint.method ?? 'POST';
      const options: RequestInit = {
        method,
        headers,
      };

      // Add body for non-GET/HEAD methods
      // Issue #372: Extract params.body if it exists (TaskFlow workflow format)
      if (method !== 'GET' && method !== 'HEAD') {
        const bodyContent = ('body' in params) ? params.body : params;
        if (bodyContent && typeof bodyContent === 'object' && Object.keys(bodyContent as Record<string, unknown>).length > 0) {
          options.body = JSON.stringify(bodyContent);
        }
      }

      // Execute request
      const response = await fetch(resolvedEndpoint.url, options);

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
            details: {
              status: response.status,
              body: errorBody,
            },
          },
        };
      }

      // Parse response
      const data = await response.json();

      return {
        success: true,
        output: data,
        metadata: {
          url: resolvedEndpoint.url,
          method,
          status: response.status,
          capabilityId,
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
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
   * Validate that a capability can be executed
   *
   * @param capabilityId - The capability identifier
   * @param projectId - Project ID (defaults to 'default_project')
   * @returns Validation result
   */
  async validate(
    capabilityId: string,
    projectId = 'default_project'
  ): Promise<NodeValidationResult> {
    const errors: string[] = [];

    // Check capability exists
    const capability = this.registry.getCapability(projectId, capabilityId);

    if (!capability) {
      return {
        valid: false,
        errors: [`Capability '${capabilityId}' not found`],
      };
    }

    // Check capability has endpoint
    if (!capability._internal?.endpoint) {
      errors.push(`Capability '${capabilityId}' has no endpoint defined`);
    }

    // Try to resolve URL
    if (errors.length === 0) {
      try {
        await this.urlResolver.resolveCapabilityUrl(capability, projectId);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        errors.push(`URL resolution failed: ${message}`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Build authentication header based on auth type
   */
  private buildAuthHeader(
    auth: ResolvedEndpoint['auth'],
    secrets: Record<string, string>
  ): Record<string, string> | null {
    if (!auth) {
      return null;
    }

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
 * Factory function to create CapabilityExecutor
 *
 * @param registry - CapabilityRegistry instance
 * @param urlResolver - URLResolver instance
 * @returns CapabilityExecutor instance
 */
export function createCapabilityExecutor(
  registry: CapabilityRegistry,
  urlResolver: URLResolver
): CapabilityExecutor {
  return new CapabilityExecutor({
    capabilityRegistry: registry,
    urlResolver,
  });
}
