/**
 * Capability Management Index Unit Tests
 *
 * Issue #365: Test that all exports are accessible
 */

import { describe, it, expect } from 'vitest';
import * as capabilityManagement from '../../../src/capabilityManagement/index.js';
import * as registryExports from '../../../src/capabilityManagement/registry/index.js';
import * as loaderExports from '../../../src/capabilityManagement/loader/index.js';
import * as apiExports from '../../../src/capabilityManagement/api/index.js';
import * as clientExports from '../../../src/capabilityManagement/client/index.js';

describe('Capability Management Module Exports', () => {
  describe('Main index exports', () => {
    it('should export CapabilityManagement class', () => {
      expect(capabilityManagement.CapabilityManagement).toBeDefined();
    });

    it('should export createCapabilityManagement factory', () => {
      expect(capabilityManagement.createCapabilityManagement).toBeDefined();
    });

    it('should export CapabilityRegistry', () => {
      expect(capabilityManagement.CapabilityRegistry).toBeDefined();
    });

    it('should export createCapabilityRegistry', () => {
      expect(capabilityManagement.createCapabilityRegistry).toBeDefined();
    });

    it('should export ProjectManager', () => {
      expect(capabilityManagement.ProjectManager).toBeDefined();
    });

    it('should export createProjectManager', () => {
      expect(capabilityManagement.createProjectManager).toBeDefined();
    });

    it('should export YamlLoader', () => {
      expect(capabilityManagement.YamlLoader).toBeDefined();
    });

    it('should export CapabilitySanitizer', () => {
      expect(capabilityManagement.CapabilitySanitizer).toBeDefined();
    });

    it('should export createYamlLoader', () => {
      expect(capabilityManagement.createYamlLoader).toBeDefined();
    });

    it('should export createSanitizer', () => {
      expect(capabilityManagement.createSanitizer).toBeDefined();
    });

    it('should export createCapabilityHandlers', () => {
      expect(capabilityManagement.createCapabilityHandlers).toBeDefined();
    });

    it('should export createCapabilityRoutes', () => {
      expect(capabilityManagement.createCapabilityRoutes).toBeDefined();
    });

    it('should export createRateLimiter', () => {
      expect(capabilityManagement.createRateLimiter).toBeDefined();
    });

    it('should export requireProject', () => {
      expect(capabilityManagement.requireProject).toBeDefined();
    });

    it('should export requireAdminForCreate', () => {
      expect(capabilityManagement.requireAdminForCreate).toBeDefined();
    });

    it('should export CapabilityClient', () => {
      expect(capabilityManagement.CapabilityClient).toBeDefined();
    });

    it('should export createCapabilityClient', () => {
      expect(capabilityManagement.createCapabilityClient).toBeDefined();
    });

    it('should export CapabilityClientError', () => {
      expect(capabilityManagement.CapabilityClientError).toBeDefined();
    });
  });

  describe('Registry index exports', () => {
    it('should export CapabilityRegistry', () => {
      expect(registryExports.CapabilityRegistry).toBeDefined();
    });

    it('should export createCapabilityRegistry', () => {
      expect(registryExports.createCapabilityRegistry).toBeDefined();
    });

    it('should export ProjectManager', () => {
      expect(registryExports.ProjectManager).toBeDefined();
    });

    it('should export createProjectManager', () => {
      expect(registryExports.createProjectManager).toBeDefined();
    });
  });

  describe('Loader index exports', () => {
    it('should export YamlLoader', () => {
      expect(loaderExports.YamlLoader).toBeDefined();
    });

    it('should export CapabilitySanitizer', () => {
      expect(loaderExports.CapabilitySanitizer).toBeDefined();
    });

    it('should export createYamlLoader', () => {
      expect(loaderExports.createYamlLoader).toBeDefined();
    });

    it('should export createSanitizer', () => {
      expect(loaderExports.createSanitizer).toBeDefined();
    });
  });

  describe('API index exports', () => {
    it('should export createCapabilityHandlers', () => {
      expect(apiExports.createCapabilityHandlers).toBeDefined();
    });

    it('should export createCapabilityRoutes', () => {
      expect(apiExports.createCapabilityRoutes).toBeDefined();
    });

    it('should export createRateLimiter', () => {
      expect(apiExports.createRateLimiter).toBeDefined();
    });

    it('should export requireProject', () => {
      expect(apiExports.requireProject).toBeDefined();
    });

    it('should export requireAdminForCreate', () => {
      expect(apiExports.requireAdminForCreate).toBeDefined();
    });
  });

  describe('Client index exports', () => {
    it('should export CapabilityClient', () => {
      expect(clientExports.CapabilityClient).toBeDefined();
    });

    it('should export createCapabilityClient', () => {
      expect(clientExports.createCapabilityClient).toBeDefined();
    });

    it('should export CapabilityClientError', () => {
      expect(clientExports.CapabilityClientError).toBeDefined();
    });
  });
});
