/**
 * Capability Management - Agent capability registration and discovery
 *
 * This module provides capability management for the agent system,
 * including registration, discovery, and invocation of capabilities.
 *
 * @module capabilityManagement
 */

import type {
  Capability,
  CapabilityRegistryEntry,
  CapabilityInvocationRequest,
  CapabilityInvocationResult,
  CapabilityStatus,
} from '../shared/types/capability.types.js';

/**
 * Capability filter options
 */
export interface CapabilityFilter {
  category?: string;
  status?: CapabilityStatus;
  tags?: string[];
  searchTerm?: string;
}

/**
 * Capability Management configuration
 */
export interface CapabilityManagementConfig {
  enableCaching?: boolean;
  cacheTTL?: number;
}

/**
 * Capability Management class - manages capability registry
 */
export class CapabilityManagement {
  private readonly registry: Map<string, CapabilityRegistryEntry>;
  private readonly enableCaching: boolean;
  private readonly cacheTTL: number;

  constructor(config: CapabilityManagementConfig = {}) {
    this.enableCaching = config.enableCaching ?? true;
    this.cacheTTL = config.cacheTTL ?? 300000; // 5 minutes
    this.registry = new Map();
  }

  /**
   * Get caching configuration
   */
  getCacheConfig(): { enabled: boolean; ttl: number } {
    return { enabled: this.enableCaching, ttl: this.cacheTTL };
  }

  /**
   * Register a new capability
   *
   * @param capability - The capability to register
   */
  register(capability: Capability): void {
    const entry: CapabilityRegistryEntry = {
      capability,
      registeredAt: new Date(),
      lastUpdatedAt: new Date(),
      usageCount: 0,
    };
    this.registry.set(capability.id, entry);
  }

  /**
   * Unregister a capability
   *
   * @param capabilityId - The ID of the capability to unregister
   * @returns true if the capability was unregistered, false if not found
   */
  unregister(capabilityId: string): boolean {
    return this.registry.delete(capabilityId);
  }

  /**
   * Get a capability by ID
   *
   * @param capabilityId - The ID of the capability
   * @returns The capability if found, undefined otherwise
   */
  get(capabilityId: string): Capability | undefined {
    return this.registry.get(capabilityId)?.capability;
  }

  /**
   * List all registered capabilities
   *
   * @param filter - Optional filter criteria
   * @returns Array of capabilities matching the filter
   */
  list(filter?: CapabilityFilter): Capability[] {
    let capabilities = Array.from(this.registry.values()).map((e) => e.capability);

    if (filter) {
      if (filter.category) {
        capabilities = capabilities.filter((c) => c.category === filter.category);
      }
      if (filter.status) {
        capabilities = capabilities.filter((c) => c.status === filter.status);
      }
      if (filter.tags && filter.tags.length > 0) {
        const filterTags = filter.tags;
        capabilities = capabilities.filter((c) => filterTags.some((tag) => c.tags?.includes(tag)));
      }
      if (filter.searchTerm) {
        const term = filter.searchTerm.toLowerCase();
        capabilities = capabilities.filter(
          (c) => c.name.toLowerCase().includes(term) || c.description.toLowerCase().includes(term)
        );
      }
    }

    return capabilities;
  }

  /**
   * Invoke a capability
   *
   * @param request - The invocation request
   * @returns The invocation result
   */
  async invoke(request: CapabilityInvocationRequest): Promise<CapabilityInvocationResult> {
    const startTime = Date.now();

    const entry = this.registry.get(request.capabilityId);
    if (!entry) {
      return {
        capabilityId: request.capabilityId,
        status: 'failed',
        error: {
          code: 'CAPABILITY_NOT_FOUND',
          message: `Capability '${request.capabilityId}' not found`,
        },
        durationMs: Date.now() - startTime,
      };
    }

    const capability = entry.capability;

    if (capability.status !== 'available') {
      return {
        capabilityId: request.capabilityId,
        status: 'failed',
        error: {
          code: 'CAPABILITY_UNAVAILABLE',
          message: `Capability '${request.capabilityId}' is ${capability.status}`,
        },
        durationMs: Date.now() - startTime,
      };
    }

    // Update usage count
    entry.usageCount++;
    entry.lastUpdatedAt = new Date();

    // Stub implementation - return success with empty result
    return {
      capabilityId: request.capabilityId,
      status: 'success',
      result: { message: 'Capability invoked (stub implementation)' },
      durationMs: Date.now() - startTime,
      metadata: {
        invocationCount: entry.usageCount,
      },
    };
  }

  /**
   * Get statistics about registered capabilities
   */
  getStats(): {
    total: number;
    available: number;
    unavailable: number;
    deprecated: number;
    byCategory: Record<string, number>;
  } {
    const capabilities = this.list();
    const byCategory: Record<string, number> = {};

    for (const cap of capabilities) {
      byCategory[cap.category] = (byCategory[cap.category] ?? 0) + 1;
    }

    return {
      total: capabilities.length,
      available: capabilities.filter((c) => c.status === 'available').length,
      unavailable: capabilities.filter((c) => c.status === 'unavailable').length,
      deprecated: capabilities.filter((c) => c.status === 'deprecated').length,
      byCategory,
    };
  }

  /**
   * Clear all registered capabilities
   */
  clear(): void {
    this.registry.clear();
  }
}

/**
 * Factory function to create CapabilityManagement
 */
export function createCapabilityManagement(
  config?: CapabilityManagementConfig
): CapabilityManagement {
  return new CapabilityManagement(config);
}

// Types are exported via their interface definitions above

// ============================================
// Issue #365: Extended exports for project-based capability management
// ============================================

// Registry exports
export {
  CapabilityRegistry,
  createCapabilityRegistry,
  type RegistryStats,
} from './registry/CapabilityRegistry.js';

export {
  ProjectManager,
  createProjectManager,
  type ProjectInfo,
  type ProjectUpdate,
  type ProjectStats,
} from './registry/ProjectManager.js';

// Loader exports
export {
  YamlLoader,
  CapabilitySanitizer,
  createYamlLoader,
  createSanitizer,
  type YamlLoaderConfig,
  type LoaderStrategy,
} from './loader/YamlLoader.js';

// API exports
export {
  createCapabilityHandlers,
  createCapabilityRoutes,
  createRateLimiter,
  requireProject,
  requireAdminForCreate,
  type CapabilityHandlerDependencies,
  type RateLimitConfig,
} from './api/index.js';

// Client exports
export {
  CapabilityClient,
  createCapabilityClient,
  CapabilityClientError,
  type CapabilityClientConfig,
} from './client/CapabilityClient.js';

// ============================================
// Issue #372: Endpoint management exports
// ============================================

export {
  EndpointConfigManager,
  createEndpointConfigManager,
} from './endpoint/EndpointConfigManager.js';

export { URLResolver, createURLResolver } from './endpoint/URLResolver.js';

export {
  type EndpointConfig,
  type ApiEndpointsConfig,
  type EndpointAuthConfig,
  type ResolvedEndpoint,
  type ProjectIndexConfig,
  type EndpointConfigManagerOptions,
  type URLResolverOptions,
  type IEndpointConfigManager,
  EndpointResolutionError,
} from './endpoint/types.js';
