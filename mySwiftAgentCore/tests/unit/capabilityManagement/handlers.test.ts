/**
 * Capability API Handlers Unit Tests
 *
 * Issue #365: REST API handlers for capability management
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Hono } from 'hono';
import {
  createCapabilityHandlers,
  type CapabilityHandlerDependencies,
} from '../../../src/capabilityManagement/api/handlers.js';
import { CapabilityRegistry } from '../../../src/capabilityManagement/registry/CapabilityRegistry.js';
import { CapabilitySanitizer } from '../../../src/capabilityManagement/loader/YamlLoader.js';
import type { CapabilityExtended } from '../../../src/shared/types/capability.types.js';

describe('Capability API Handlers', () => {
  let app: Hono;
  let registry: CapabilityRegistry;
  let sanitizer: CapabilitySanitizer;

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

  beforeEach(() => {
    registry = new CapabilityRegistry();
    sanitizer = new CapabilitySanitizer();
    registry.registerForProject('default_project', sampleCapability);

    const deps: CapabilityHandlerDependencies = {
      registry,
      sanitizer,
    };

    app = new Hono();
    const handlers = createCapabilityHandlers(deps);
    app.route('/', handlers);
  });

  describe('GET /api/v1/capabilities', () => {
    it('should return capabilities for a project', async () => {
      const res = await app.request('/api/v1/capabilities?project=default_project');
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capabilities: unknown[] };
      expect(body.capabilities).toHaveLength(1);
    });

    it('should return 400 if project is missing', async () => {
      const res = await app.request('/api/v1/capabilities');
      expect(res.status).toBe(400);

      const body = (await res.json()) as { error: string };
      expect(body.error).toContain('project');
    });

    it('should exclude _internal section from response', async () => {
      const res = await app.request('/api/v1/capabilities?project=default_project');
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capabilities: CapabilityExtended[] };
      const capability = body.capabilities[0];
      expect(capability?._internal).toBeUndefined();
    });

    it('should filter by category', async () => {
      const res = await app.request('/api/v1/capabilities?project=default_project&category=search');
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capabilities: CapabilityExtended[] };
      expect(body.capabilities).toHaveLength(1);
    });

    it('should return empty array for project with no capabilities', async () => {
      const res = await app.request('/api/v1/capabilities?project=empty_project');
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capabilities: unknown[] };
      expect(body.capabilities).toEqual([]);
    });
  });

  describe('GET /api/v1/capabilities/:id', () => {
    it('should return a specific capability', async () => {
      const res = await app.request(
        '/api/v1/capabilities/google_search?project=default_project'
      );
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capability: CapabilityExtended };
      expect(body.capability.id).toBe('google_search');
    });

    it('should return 404 for non-existent capability', async () => {
      const res = await app.request(
        '/api/v1/capabilities/non_existent?project=default_project'
      );
      expect(res.status).toBe(404);
    });

    it('should return 400 if project is missing', async () => {
      const res = await app.request('/api/v1/capabilities/google_search');
      expect(res.status).toBe(400);
    });

    it('should exclude _internal from response', async () => {
      const res = await app.request(
        '/api/v1/capabilities/google_search?project=default_project'
      );
      expect(res.status).toBe(200);

      const body = (await res.json()) as { capability: CapabilityExtended };
      expect(body.capability._internal).toBeUndefined();
    });
  });

  describe('GET /api/v1/capabilities/yaml', () => {
    it('should return capabilities in YAML format', async () => {
      const res = await app.request('/api/v1/capabilities/yaml?project=default_project');
      expect(res.status).toBe(200);

      const contentType = res.headers.get('content-type');
      expect(contentType).toContain('text/yaml');
    });

    it('should return 400 if project is missing', async () => {
      const res = await app.request('/api/v1/capabilities/yaml');
      expect(res.status).toBe(400);
    });

    it('should exclude _internal from YAML output', async () => {
      const res = await app.request('/api/v1/capabilities/yaml?project=default_project');
      expect(res.status).toBe(200);

      const yamlContent = await res.text();
      expect(yamlContent).not.toContain('_internal');
      expect(yamlContent).not.toContain('secret_key');
    });
  });

  describe('POST /api/v1/capabilities (admin only)', () => {
    it('should create a new capability when admin', async () => {
      const newCapability: CapabilityExtended = {
        id: 'new_capability',
        name: 'New Capability',
        description: 'A new capability',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
        project: 'default_project',
      };

      // Set auth context for admin (simulated)
      app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'admin' });
        await next();
      });
      const handlers = createCapabilityHandlers({ registry, sanitizer });
      app.route('/', handlers);

      const res = await app.request('/api/v1/capabilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCapability),
      });

      expect(res.status).toBe(201);

      const body = (await res.json()) as { capability: CapabilityExtended };
      expect(body.capability.id).toBe('new_capability');
    });

    it('should return 403 for non-admin', async () => {
      const newCapability = {
        id: 'test',
        name: 'Test',
        description: 'Test',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
        project: 'default_project',
      };

      // Set auth context for regular user
      app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'api' });
        await next();
      });
      const handlers = createCapabilityHandlers({ registry, sanitizer });
      app.route('/', handlers);

      const res = await app.request('/api/v1/capabilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCapability),
      });

      expect(res.status).toBe(403);
    });

    it('should return 400 for invalid capability data', async () => {
      app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'admin' });
        await next();
      });
      const handlers = createCapabilityHandlers({ registry, sanitizer });
      app.route('/', handlers);

      const res = await app.request('/api/v1/capabilities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invalid: 'data' }),
      });

      expect(res.status).toBe(400);
    });
  });
});
