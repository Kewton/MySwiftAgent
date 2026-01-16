/**
 * CapabilityClient - TypeScript SDK for capability management
 *
 * Issue #365: Client library for accessing capability API
 * Provides a clean interface for fetching and managing capabilities.
 */

import type { PublicCapability } from '../../shared/types/capability.types.js';

/**
 * Client configuration
 */
export interface CapabilityClientConfig {
  /** Base URL of the mySwiftAgentCore service */
  baseUrl: string;
  /** API token for authentication */
  apiToken?: string;
  /** Request timeout in milliseconds */
  timeout?: number;
}

/**
 * API response for listing capabilities
 */
interface ListCapabilitiesResponse {
  capabilities: PublicCapability[];
  count: number;
  project: string;
}

/**
 * API response for getting a single capability
 */
interface GetCapabilityResponse {
  capability: PublicCapability;
}

/**
 * Client error
 */
export class CapabilityClientError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'CapabilityClientError';
  }
}

/**
 * CapabilityClient - SDK for capability management API
 *
 * Features:
 * - Fetch capabilities by project
 * - Get single capability
 * - Get capabilities as YAML
 * - Automatic authentication header handling
 */
export class CapabilityClient {
  private readonly baseUrl: string;
  private readonly apiToken?: string;
  private readonly timeout: number;

  constructor(config: CapabilityClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.apiToken = config.apiToken;
    this.timeout = config.timeout ?? 30000;
  }

  /**
   * Get capabilities for a project
   *
   * @param projectId - The project identifier
   * @returns Array of public capabilities
   * @throws CapabilityClientError on API failure
   */
  async getCapabilities(projectId: string): Promise<PublicCapability[]> {
    const url = `${this.baseUrl}/api/v1/capabilities?project=${encodeURIComponent(projectId)}`;

    const response = await this.fetch(url);

    if (!response.ok) {
      throw new CapabilityClientError(
        `Failed to fetch capabilities: ${response.statusText}`,
        response.status
      );
    }

    const data = (await response.json()) as ListCapabilitiesResponse;
    return data.capabilities;
  }

  /**
   * Get a specific capability
   *
   * @param projectId - The project identifier
   * @param capabilityId - The capability identifier
   * @returns The capability, or undefined if not found
   * @throws CapabilityClientError on API failure (except 404)
   */
  async getCapability(
    projectId: string,
    capabilityId: string
  ): Promise<PublicCapability | undefined> {
    const url = `${this.baseUrl}/api/v1/capabilities/${encodeURIComponent(capabilityId)}?project=${encodeURIComponent(projectId)}`;

    const response = await this.fetch(url);

    if (response.status === 404) {
      return undefined;
    }

    if (!response.ok) {
      throw new CapabilityClientError(
        `Failed to fetch capability: ${response.statusText}`,
        response.status
      );
    }

    const data = (await response.json()) as GetCapabilityResponse;
    return data.capability;
  }

  /**
   * Get capabilities in YAML format
   *
   * @param projectId - The project identifier
   * @returns YAML string of capabilities
   * @throws CapabilityClientError on API failure
   */
  async getCapabilitiesAsYaml(projectId: string): Promise<string> {
    const url = `${this.baseUrl}/api/v1/capabilities/yaml?project=${encodeURIComponent(projectId)}`;

    const response = await this.fetch(url);

    if (!response.ok) {
      throw new CapabilityClientError(
        `Failed to fetch capabilities as YAML: ${response.statusText}`,
        response.status
      );
    }

    return await response.text();
  }

  /**
   * Internal fetch method with authentication and timeout
   */
  private async fetch(url: string, options: RequestInit = {}): Promise<Response> {
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) ?? {}),
    };

    if (this.apiToken) {
      headers['X-API-Token'] = this.apiToken;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      return await fetch(url, {
        ...options,
        method: options.method ?? 'GET',
        headers,
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

/**
 * Factory function to create CapabilityClient
 */
export function createCapabilityClient(config: CapabilityClientConfig): CapabilityClient {
  return new CapabilityClient(config);
}
