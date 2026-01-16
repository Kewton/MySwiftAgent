/**
 * CapabilityRegistry - Project-based capability management
 *
 * Issue #365: Extends capability management with project organization
 * Allows registering, filtering, and managing capabilities per project.
 */

import type {
  CapabilityExtended,
  CapabilityFilterExtended,
  CapabilityStatus,
} from '../../shared/types/capability.types.js';

/**
 * Internal project storage structure
 */
interface ProjectCapabilityStore {
  projectId: string;
  capabilities: Map<string, CapabilityExtended>;
  sharedRefs: string[];
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Registry statistics
 */
export interface RegistryStats {
  totalProjects: number;
  totalCapabilities: number;
  byCategory: Record<string, number>;
  byStatus: Record<CapabilityStatus, number>;
}

/**
 * CapabilityRegistry - Manages capabilities organized by project
 *
 * Features:
 * - Register capabilities for specific projects
 * - Filter capabilities by category, status, tags, search term
 * - Include shared capabilities across projects
 * - Statistics and reporting
 */
export class CapabilityRegistry {
  private readonly projects: Map<string, ProjectCapabilityStore>;

  constructor() {
    this.projects = new Map();
  }

  /**
   * Register a capability for a specific project
   *
   * @param projectId - The project identifier
   * @param capability - The capability to register
   */
  registerForProject(projectId: string, capability: CapabilityExtended): void {
    let project = this.projects.get(projectId);

    if (!project) {
      project = {
        projectId,
        capabilities: new Map(),
        sharedRefs: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      this.projects.set(projectId, project);
    }

    project.capabilities.set(capability.id, capability);
    project.updatedAt = new Date();
  }

  /**
   * Get capabilities for a project with optional filtering
   *
   * @param projectId - The project identifier
   * @param filter - Optional filter criteria
   * @returns Array of capabilities matching the filter
   */
  getByProject(projectId: string, filter?: CapabilityFilterExtended): CapabilityExtended[] {
    const project = this.projects.get(projectId);

    if (!project) {
      return [];
    }

    let capabilities = Array.from(project.capabilities.values());

    if (filter) {
      capabilities = this.applyFilter(capabilities, filter);
    }

    return capabilities;
  }

  /**
   * Get a specific capability by project and id
   *
   * @param projectId - The project identifier
   * @param capabilityId - The capability identifier
   * @returns The capability if found, undefined otherwise
   */
  getCapability(projectId: string, capabilityId: string): CapabilityExtended | undefined {
    const project = this.projects.get(projectId);
    return project?.capabilities.get(capabilityId);
  }

  /**
   * Include shared capabilities in a project
   *
   * @param projectId - The project to add shared refs to
   * @param sharedIds - Array of capability IDs to include as shared
   */
  includeShared(projectId: string, sharedIds: string[]): void {
    let project = this.projects.get(projectId);

    if (!project) {
      project = {
        projectId,
        capabilities: new Map(),
        sharedRefs: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      this.projects.set(projectId, project);
    }

    // Add only new shared refs (avoid duplicates)
    for (const id of sharedIds) {
      if (!project.sharedRefs.includes(id)) {
        project.sharedRefs.push(id);
      }
    }
    project.updatedAt = new Date();
  }

  /**
   * Get shared capability references for a project
   *
   * @param projectId - The project identifier
   * @returns Array of shared capability IDs
   */
  getSharedRefs(projectId: string): string[] {
    const project = this.projects.get(projectId);
    return project?.sharedRefs ?? [];
  }

  /**
   * Unregister a capability from a project
   *
   * @param projectId - The project identifier
   * @param capabilityId - The capability identifier
   * @returns true if unregistered, false if not found
   */
  unregisterFromProject(projectId: string, capabilityId: string): boolean {
    const project = this.projects.get(projectId);

    if (!project) {
      return false;
    }

    const deleted = project.capabilities.delete(capabilityId);
    if (deleted) {
      project.updatedAt = new Date();
    }

    return deleted;
  }

  /**
   * List all project IDs
   *
   * @returns Array of project identifiers
   */
  listProjects(): string[] {
    return Array.from(this.projects.keys());
  }

  /**
   * Get registry statistics
   *
   * @returns Statistics about the registry
   */
  getStats(): RegistryStats {
    const stats: RegistryStats = {
      totalProjects: this.projects.size,
      totalCapabilities: 0,
      byCategory: {},
      byStatus: {
        available: 0,
        unavailable: 0,
        deprecated: 0,
      },
    };

    for (const project of this.projects.values()) {
      for (const capability of project.capabilities.values()) {
        stats.totalCapabilities++;
        stats.byCategory[capability.category] =
          (stats.byCategory[capability.category] ?? 0) + 1;
        stats.byStatus[capability.status]++;
      }
    }

    return stats;
  }

  /**
   * Clear all projects and capabilities
   */
  clear(): void {
    this.projects.clear();
  }

  /**
   * Apply filter to capabilities
   */
  private applyFilter(
    capabilities: CapabilityExtended[],
    filter: CapabilityFilterExtended
  ): CapabilityExtended[] {
    let filtered = capabilities;

    if (filter.category) {
      filtered = filtered.filter((c) => c.category === filter.category);
    }

    if (filter.status) {
      filtered = filtered.filter((c) => c.status === filter.status);
    }

    if (filter.tags && filter.tags.length > 0) {
      const filterTags = filter.tags;
      filtered = filtered.filter((c) => filterTags.some((tag) => c.tags?.includes(tag)));
    }

    if (filter.searchTerm) {
      const term = filter.searchTerm.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(term) || c.description.toLowerCase().includes(term)
      );
    }

    return filtered;
  }
}

/**
 * Factory function to create CapabilityRegistry
 */
export function createCapabilityRegistry(): CapabilityRegistry {
  return new CapabilityRegistry();
}
