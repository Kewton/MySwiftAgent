/**
 * CapabilityRegistry Unit Tests
 *
 * Issue #365: Project-based capability management
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  CapabilityRegistry,
  createCapabilityRegistry,
} from '../../../src/capabilityManagement/registry/CapabilityRegistry.js';
import type {
  CapabilityExtended,
  CapabilityFilterExtended,
} from '../../../src/shared/types/capability.types.js';

describe('CapabilityRegistry', () => {
  let registry: CapabilityRegistry;

  // Sample capability for testing
  const sampleCapability: CapabilityExtended = {
    id: 'google_search',
    name: 'Google Search',
    description: 'Search the web using Google',
    version: '1.0.0',
    status: 'available',
    category: 'search',
    parameters: [
      {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Search query',
      },
    ],
    returnType: 'object',
    tags: ['search', 'web'],
    project: 'default_project',
    _internal: {
      endpoint: 'https://api.google.com/search',
      method: 'GET',
      auth_type: 'api_key',
      secret_key: 'GOOGLE_API_KEY',
    },
  };

  const anotherCapability: CapabilityExtended = {
    id: 'weather_api',
    name: 'Weather API',
    description: 'Get weather information',
    version: '1.0.0',
    status: 'available',
    category: 'utility',
    parameters: [
      {
        name: 'location',
        type: 'string',
        required: true,
        description: 'Location name',
      },
    ],
    returnType: 'object',
    tags: ['weather', 'api'],
    project: 'another_project',
  };

  beforeEach(() => {
    registry = new CapabilityRegistry();
  });

  describe('registerForProject', () => {
    it('should register a capability for a project', () => {
      registry.registerForProject('default_project', sampleCapability);

      const capabilities = registry.getByProject('default_project');
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.id).toBe('google_search');
    });

    it('should register multiple capabilities for a project', () => {
      registry.registerForProject('default_project', sampleCapability);
      registry.registerForProject('default_project', {
        ...anotherCapability,
        id: 'another_cap',
        project: 'default_project',
      });

      const capabilities = registry.getByProject('default_project');
      expect(capabilities).toHaveLength(2);
    });

    it('should update capability if same id is registered', () => {
      registry.registerForProject('default_project', sampleCapability);

      const updatedCap = { ...sampleCapability, name: 'Updated Google Search' };
      registry.registerForProject('default_project', updatedCap);

      const capabilities = registry.getByProject('default_project');
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.name).toBe('Updated Google Search');
    });
  });

  describe('getByProject', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleCapability);
      registry.registerForProject('another_project', anotherCapability);
    });

    it('should return capabilities for a specific project', () => {
      const capabilities = registry.getByProject('default_project');
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.id).toBe('google_search');
    });

    it('should return empty array for non-existent project', () => {
      const capabilities = registry.getByProject('non_existent');
      expect(capabilities).toEqual([]);
    });

    it('should filter by category', () => {
      registry.registerForProject('default_project', {
        ...anotherCapability,
        id: 'weather_default',
        project: 'default_project',
      });

      const filter: CapabilityFilterExtended = { category: 'search' };
      const capabilities = registry.getByProject('default_project', filter);
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.category).toBe('search');
    });

    it('should filter by status', () => {
      registry.registerForProject('default_project', {
        ...sampleCapability,
        id: 'deprecated_cap',
        status: 'deprecated',
      });

      const filter: CapabilityFilterExtended = { status: 'available' };
      const capabilities = registry.getByProject('default_project', filter);
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.status).toBe('available');
    });

    it('should filter by tags', () => {
      const filter: CapabilityFilterExtended = { tags: ['web'] };
      const capabilities = registry.getByProject('default_project', filter);
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.tags).toContain('web');
    });

    it('should filter by search term', () => {
      const filter: CapabilityFilterExtended = { searchTerm: 'google' };
      const capabilities = registry.getByProject('default_project', filter);
      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.name.toLowerCase()).toContain('google');
    });
  });

  describe('getCapability', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleCapability);
    });

    it('should return a specific capability by id', () => {
      const capability = registry.getCapability('default_project', 'google_search');
      expect(capability).toBeDefined();
      expect(capability?.id).toBe('google_search');
    });

    it('should return undefined for non-existent capability', () => {
      const capability = registry.getCapability('default_project', 'non_existent');
      expect(capability).toBeUndefined();
    });

    it('should return undefined for non-existent project', () => {
      const capability = registry.getCapability('non_existent', 'google_search');
      expect(capability).toBeUndefined();
    });
  });

  describe('includeShared', () => {
    beforeEach(() => {
      // Register a shared capability
      registry.registerForProject('shared', {
        ...sampleCapability,
        id: 'shared_cap',
        project: 'shared',
      });
      registry.registerForProject('default_project', anotherCapability);
    });

    it('should include shared capabilities in project', () => {
      registry.includeShared('default_project', ['shared_cap']);

      const sharedRefs = registry.getSharedRefs('default_project');
      expect(sharedRefs).toContain('shared_cap');
    });

    it('should not duplicate shared refs', () => {
      registry.includeShared('default_project', ['shared_cap']);
      registry.includeShared('default_project', ['shared_cap']);

      const sharedRefs = registry.getSharedRefs('default_project');
      expect(sharedRefs.filter((r) => r === 'shared_cap')).toHaveLength(1);
    });
  });

  describe('unregisterFromProject', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleCapability);
    });

    it('should unregister a capability from a project', () => {
      const result = registry.unregisterFromProject('default_project', 'google_search');
      expect(result).toBe(true);

      const capabilities = registry.getByProject('default_project');
      expect(capabilities).toHaveLength(0);
    });

    it('should return false for non-existent capability', () => {
      const result = registry.unregisterFromProject('default_project', 'non_existent');
      expect(result).toBe(false);
    });
  });

  describe('listProjects', () => {
    it('should return all project ids', () => {
      registry.registerForProject('project1', sampleCapability);
      registry.registerForProject('project2', anotherCapability);

      const projects = registry.listProjects();
      expect(projects).toContain('project1');
      expect(projects).toContain('project2');
    });
  });

  describe('getStats', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleCapability);
      registry.registerForProject('another_project', anotherCapability);
    });

    it('should return registry statistics', () => {
      const stats = registry.getStats();
      expect(stats.totalProjects).toBe(2);
      expect(stats.totalCapabilities).toBe(2);
      expect(stats.byCategory['search']).toBe(1);
      expect(stats.byCategory['utility']).toBe(1);
    });
  });
});

describe('createCapabilityRegistry factory', () => {
  it('should create a CapabilityRegistry instance', () => {
    const registry = createCapabilityRegistry();
    expect(registry).toBeInstanceOf(CapabilityRegistry);
  });
});
