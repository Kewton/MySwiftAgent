/**
 * Capability Routes Unit Tests
 *
 * Issue #365: API routes configuration tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { Hono } from 'hono';
import { createCapabilityRoutes } from '../../../src/capabilityManagement/api/routes.js';
import { CapabilityRegistry } from '../../../src/capabilityManagement/registry/CapabilityRegistry.js';
import { CapabilitySanitizer } from '../../../src/capabilityManagement/loader/YamlLoader.js';
import type { CapabilityExtended } from '../../../src/shared/types/capability.types.js';

describe('Capability Routes', () => {
  let app: Hono;
  let registry: CapabilityRegistry;
  let sanitizer: CapabilitySanitizer;

  const sampleCapability: CapabilityExtended = {
    id: 'test_cap',
    name: 'Test Capability',
    description: 'A test capability',
    version: '1.0.0',
    status: 'available',
    category: 'test',
    parameters: [],
    returnType: 'string',
    project: 'test_project',
  };

  beforeEach(() => {
    registry = new CapabilityRegistry();
    sanitizer = new CapabilitySanitizer();
    registry.registerForProject('test_project', sampleCapability);

    const routes = createCapabilityRoutes({ registry, sanitizer });
    app = new Hono();
    app.route('/', routes);
  });

  it('should create routes with correct structure', async () => {
    const res = await app.request('/api/v1/capabilities?project=test_project');
    expect(res.status).toBe(200);

    const body = (await res.json()) as { capabilities: unknown[] };
    expect(body.capabilities).toHaveLength(1);
  });

  it('should handle capability routes through main router', async () => {
    const res = await app.request('/api/v1/capabilities/test_cap?project=test_project');
    expect(res.status).toBe(200);

    const body = (await res.json()) as { capability: CapabilityExtended };
    expect(body.capability.id).toBe('test_cap');
  });

  it('should export route handler dependencies', () => {
    // Verify the routes can be created and exported
    const routes = createCapabilityRoutes({ registry, sanitizer });
    expect(routes).toBeDefined();
  });
});
