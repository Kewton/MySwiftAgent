/**
 * URLResolver - Resolves capability endpoints to complete URLs
 *
 * Issue #372: Converts relative capability endpoints to full URLs
 *
 * Resolution strategy:
 * 1. If capability has api_source in _internal.config, use matching endpoint
 * 2. Otherwise, match endpoint_prefix against the capability's endpoint path
 * 3. Build complete URL by combining base_url and endpoint path
 */

import type { CapabilityExtended, AuthType } from '../../shared/types/capability.types.js';
import type {
  IEndpointConfigManager,
  ApiEndpointsConfig,
  EndpointConfig,
  ResolvedEndpoint,
  URLResolverOptions,
  EndpointAuthConfig,
} from './types.js';
import { EndpointResolutionError } from './types.js';

/**
 * Map capability auth_type to resolved endpoint auth type
 */
function mapAuthType(authType: AuthType): EndpointAuthConfig['type'] {
  switch (authType) {
    case 'bearer_token':
      return 'bearer';
    case 'basic':
      return 'basic';
    case 'api_key':
      return 'api_key';
    case 'oauth2':
      return 'bearer'; // OAuth2 typically uses bearer tokens
    case 'none':
    default:
      return 'bearer'; // Default fallback
  }
}

/**
 * URLResolver - Resolves capability endpoints to complete URLs
 *
 * Responsibilities:
 * - Load endpoint configurations from EndpointConfigManager
 * - Match capabilities to appropriate base URLs
 * - Build complete URLs with authentication information
 */
export class URLResolver {
  private readonly configManager: IEndpointConfigManager;
  private readonly defaultProjectId: string;

  constructor(options: URLResolverOptions) {
    this.configManager = options.configManager;
    this.defaultProjectId = options.defaultProjectId ?? 'default_project';
  }

  /**
   * Resolve capability to a complete URL with authentication
   *
   * @param capability - Capability with endpoint information
   * @param projectId - Project ID (uses default if not specified)
   * @returns Resolved endpoint with complete URL
   * @throws EndpointResolutionError if resolution fails
   */
  async resolveCapabilityUrl(
    capability: CapabilityExtended,
    projectId?: string
  ): Promise<ResolvedEndpoint> {
    const effectiveProjectId = projectId ?? this.defaultProjectId;

    // Validate capability has endpoint information
    if (!capability._internal?.endpoint) {
      throw new EndpointResolutionError(
        `Capability '${capability.id}' has no endpoint defined in _internal section`,
        capability.id
      );
    }

    const endpoint = capability._internal.endpoint;

    // Load endpoint configurations
    const endpoints = await this.configManager.loadProjectEndpoints(effectiveProjectId);

    // Find matching base URL configuration
    const matchingConfig = this.findMatchingConfigForCapability(capability, endpoints);

    if (!matchingConfig) {
      throw new EndpointResolutionError(
        `No matching base URL configuration found for capability '${capability.id}' with endpoint '${endpoint}'`,
        capability.id,
        endpoint
      );
    }

    // Build the complete URL
    const url = this.buildUrl(matchingConfig.base_url, endpoint);

    // Build resolved endpoint
    const resolved: ResolvedEndpoint = {
      url,
      method: capability._internal.method,
    };

    // Add authentication if configured
    if (capability._internal.auth_type && capability._internal.auth_type !== 'none') {
      resolved.auth = {
        type: mapAuthType(capability._internal.auth_type),
        secret_key: capability._internal.secret_key ?? '',
      };
    }

    // Add timeout if specified
    if (capability._internal.timeout_ms) {
      resolved.timeout_ms = capability._internal.timeout_ms;
    }

    // Add headers if specified
    if (capability._internal.headers) {
      resolved.headers = capability._internal.headers;
    }

    return resolved;
  }

  /**
   * Find matching endpoint configuration for a capability
   *
   * Strategy:
   * 1. Check if capability has explicit api_source in _internal.config
   * 2. Fall back to endpoint_prefix matching
   */
  private findMatchingConfigForCapability(
    capability: CapabilityExtended,
    endpoints: ApiEndpointsConfig
  ): EndpointConfig | undefined {
    const internalConfig = capability._internal?.config as
      | { api_source?: string }
      | undefined;

    // Check for explicit api_source
    if (internalConfig?.api_source) {
      const config = endpoints[internalConfig.api_source];
      if (config) {
        return config;
      }
    }

    // Fall back to endpoint_prefix matching
    const endpoint = capability._internal?.endpoint;
    if (endpoint) {
      return this.findMatchingConfig(endpoint, endpoints);
    }

    return undefined;
  }

  /**
   * Find matching configuration by endpoint_prefix
   *
   * Matches the endpoint path against configured prefixes.
   * Returns the most specific match (longest prefix).
   *
   * @param endpoint - Endpoint path to match
   * @param endpoints - Available endpoint configurations
   * @returns Matching configuration or undefined
   */
  findMatchingConfig(
    endpoint: string,
    endpoints: ApiEndpointsConfig
  ): EndpointConfig | undefined {
    let bestMatch: EndpointConfig | undefined;
    let bestMatchLength = 0;

    for (const config of Object.values(endpoints)) {
      const prefix = config.endpoint_prefix;

      if (prefix && endpoint.startsWith(prefix)) {
        // Use the most specific (longest) match
        if (prefix.length > bestMatchLength) {
          bestMatch = config;
          bestMatchLength = prefix.length;
        }
      }
    }

    return bestMatch;
  }

  /**
   * Build complete URL from base URL and endpoint
   *
   * Handles trailing/leading slashes correctly:
   * - http://localhost:8004 + /v1/api -> http://localhost:8004/v1/api
   * - http://localhost:8004/ + /v1/api -> http://localhost:8004/v1/api
   * - http://localhost:8004/ + v1/api -> http://localhost:8004/v1/api
   */
  private buildUrl(baseUrl: string, endpoint: string): string {
    // Remove trailing slash from base URL
    const normalizedBase = baseUrl.replace(/\/+$/, '');

    // Ensure endpoint starts with /
    const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

    return `${normalizedBase}${normalizedEndpoint}`;
  }
}

/**
 * Factory function to create URLResolver
 *
 * @param configManager - EndpointConfigManager instance
 * @param defaultProjectId - Default project ID (optional)
 * @returns URLResolver instance
 */
export function createURLResolver(
  configManager: IEndpointConfigManager,
  defaultProjectId?: string
): URLResolver {
  return new URLResolver({ configManager, defaultProjectId });
}
