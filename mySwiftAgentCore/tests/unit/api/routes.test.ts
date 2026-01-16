/**
 * API Routes Unit Tests
 *
 * Tests for main API router
 */

import { describe, it, expect } from 'vitest';
import { Hono } from 'hono';
import { createApiRoutes, type ApiConfig } from '../../../src/api/routes.js';

describe('API Routes', () => {
  const config: ApiConfig = {
    serviceName: 'test-service',
    version: '1.0.0',
    startTime: new Date(),
  };

  it('should return service info at root', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    const res = await app.request('/');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.service).toBe('test-service');
    expect(body.version).toBe('1.0.0');
    expect(body.status).toBe('running');
    expect(body.endpoints).toBeDefined();
  });

  it('should return API v1 info', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    const res = await app.request('/api/v1');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.version).toBe('v1');
    expect(body.endpoints).toBeDefined();
  });

  it('should return taskflow stub', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    const res = await app.request('/api/v1/taskflow');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.service).toBe('TaskFlow Engine');
    expect(body.status).toBe('stub');
  });

  it('should return generator routes', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    // Generator routes are now real (not stubs)
    // Check that the health endpoint exists
    const res = await app.request('/api/v1/generator/health');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.status).toBe('healthy');
  });

  it('should return capabilities stub', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    const res = await app.request('/api/v1/capabilities');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.service).toBe('Capability Management');
    expect(body.status).toBe('stub');
  });

  it('should include health routes', async () => {
    const app = new Hono();
    const routes = await createApiRoutes(config);
    app.route('/', routes);

    const res = await app.request('/health');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.status).toBe('healthy');
  });

  it('should configure with MyVault base URL', async () => {
    const configWithVault: ApiConfig = {
      ...config,
      myVaultBaseUrl: 'http://localhost:8003',
    };

    const app = new Hono();
    const routes = await createApiRoutes(configWithVault);
    app.route('/', routes);

    // Just verify it doesn't crash
    const res = await app.request('/health');
    expect(res.status).toBe(200);
  });
});
