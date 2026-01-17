/**
 * Endpoint Management Types
 *
 * Issue #372: Type definitions for capability API endpoint URL resolution
 *
 * This module defines types for managing API endpoint configurations,
 * including base URLs, environment variable resolution, and endpoint matching.
 */

import { z } from 'zod';

/**
 * Single endpoint configuration
 */
export interface EndpointConfig {
  /** Base URL (may contain environment variables) */
  base_url: string;
  /** Human-readable description */
  description: string;
  /** URL prefix for matching endpoints */
  endpoint_prefix?: string;
}

/**
 * API endpoints configuration map
 */
export interface ApiEndpointsConfig {
  [key: string]: EndpointConfig;
}

/**
 * Authentication configuration for resolved endpoints
 */
export interface EndpointAuthConfig {
  type: 'bearer' | 'basic' | 'api_key';
  secret_key: string;
  header_name?: string;
}

/**
 * Resolved endpoint information
 */
export interface ResolvedEndpoint {
  /** Complete URL with base URL resolved */
  url: string;
  /** Authentication configuration */
  auth?: EndpointAuthConfig;
  /** Request timeout in milliseconds */
  timeout_ms?: number;
  /** HTTP method */
  method?: string;
  /** Custom headers */
  headers?: Record<string, string>;
}

/**
 * Endpoint resolution error
 *
 * Thrown when URL resolution fails due to missing configuration
 * or invalid capability setup.
 */
export class EndpointResolutionError extends Error {
  constructor(
    message: string,
    public readonly capabilityId: string,
    public readonly endpoint?: string
  ) {
    super(message);
    this.name = 'EndpointResolutionError';
    // Ensure prototype chain is correct for instanceof checks
    Object.setPrototypeOf(this, EndpointResolutionError.prototype);
  }
}

/**
 * Project index configuration (from index.yaml)
 */
export interface ProjectIndexConfig {
  /** List of capability IDs */
  capabilities?: string[];
  /** API endpoint configurations */
  api_endpoints?: ApiEndpointsConfig;
}

/**
 * EndpointConfigManager options
 */
export interface EndpointConfigManagerOptions {
  /** Base path for configuration files */
  basePath: string;
  /** Enable caching of loaded configurations */
  enableCache?: boolean;
}

/**
 * URLResolver options
 */
export interface URLResolverOptions {
  /** EndpointConfigManager instance */
  configManager: IEndpointConfigManager;
  /** Default project ID when not specified */
  defaultProjectId?: string;
}

/**
 * EndpointConfigManager interface
 */
export interface IEndpointConfigManager {
  /**
   * Load endpoint configurations for a project
   */
  loadProjectEndpoints(projectId: string): Promise<ApiEndpointsConfig>;

  /**
   * Resolve environment variables in a string
   */
  resolveEnvVars(value: string): string;

  /**
   * Clear cached configurations
   */
  clearCache(): void;
}

// ============================================
// Zod Schemas for Validation
// ============================================

/**
 * EndpointConfig schema
 */
export const EndpointConfigSchema = z.object({
  base_url: z.string(),
  description: z.string(),
  endpoint_prefix: z.string().optional(),
});

/**
 * ApiEndpointsConfig schema
 */
export const ApiEndpointsConfigSchema = z.record(z.string(), EndpointConfigSchema);

/**
 * ProjectIndexConfig schema
 */
export const ProjectIndexConfigSchema = z.object({
  capabilities: z.array(z.string()).optional(),
  api_endpoints: ApiEndpointsConfigSchema.optional(),
});

/**
 * EndpointAuthConfig schema
 */
export const EndpointAuthConfigSchema = z.object({
  type: z.enum(['bearer', 'basic', 'api_key']),
  secret_key: z.string(),
  header_name: z.string().optional(),
});

/**
 * ResolvedEndpoint schema
 */
export const ResolvedEndpointSchema = z.object({
  url: z.string(),
  auth: EndpointAuthConfigSchema.optional(),
  timeout_ms: z.number().optional(),
  method: z.string().optional(),
  headers: z.record(z.string()).optional(),
});
