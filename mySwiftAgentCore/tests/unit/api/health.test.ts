/**
 * Health API Unit Tests
 *
 * Tests for health check endpoints
 */

import { describe, it, expect, vi } from 'vitest';
import { Hono } from 'hono';
import { createHealthRoutes, createMyVaultCheck, type HealthCheckConfig } from '../../../src/api/health.js';

describe('Health Routes', () => {
  const baseConfig: HealthCheckConfig = {
    serviceName: 'test-service',
    version: '1.0.0',
    startTime: new Date(),
  };

  it('should return healthy status for /health', async () => {
    const app = new Hono();
    const healthRoutes = createHealthRoutes(baseConfig);
    app.route('/', healthRoutes);

    const res = await app.request('/health');
    expect(res.status).toBe(200);

    const body = await res.json() as Record<string, unknown>;
    expect(body.status).toBe('healthy');
    expect(body.service).toBe('test-service');
    expect(body.version).toBe('1.0.0');
    expect(typeof body.uptime).toBe('number');
    expect(body.timestamp).toBeDefined();
  });

  it('should return live status for /health/live', async () => {
    const app = new Hono();
    const healthRoutes = createHealthRoutes(baseConfig);
    app.route('/', healthRoutes);

    const res = await app.request('/health/live');
    expect(res.status).toBe(200);

    const body = await res.json() as Record<string, unknown>;
    expect(body.alive).toBe(true);
  });

  it('should return ready status for /health/ready', async () => {
    const app = new Hono();
    const healthRoutes = createHealthRoutes(baseConfig);
    app.route('/', healthRoutes);

    const res = await app.request('/health/ready');
    expect(res.status).toBe(200);

    const body = await res.json() as Record<string, unknown>;
    expect(body.ready).toBe(true);
  });

  it('should return detailed health with dependencies', async () => {
    const mockDependencyCheck = vi.fn().mockResolvedValue({
      name: 'test-dependency',
      status: 'healthy',
      latencyMs: 10,
    });

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [mockDependencyCheck],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/detailed');
    expect(res.status).toBe(200);

    const body = await res.json() as Record<string, unknown>;
    expect(body.status).toBe('healthy');
    expect(body.dependencies).toBeDefined();
    expect((body.dependencies as Array<Record<string, unknown>>).length).toBe(1);
    expect((body.dependencies as Array<Record<string, unknown>>)[0]?.name).toBe('test-dependency');
    expect(mockDependencyCheck).toHaveBeenCalled();
  });

  it('should return degraded status when dependency is unhealthy', async () => {
    const unhealthyDependency = vi.fn().mockResolvedValue({
      name: 'failing-dependency',
      status: 'unhealthy',
      message: 'Connection failed',
    });

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [unhealthyDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/detailed');
    expect(res.status).toBe(200);

    const body = await res.json() as Record<string, unknown>;
    expect(body.status).toBe('degraded');
  });

  it('should return not ready when dependency is unhealthy', async () => {
    const unhealthyDependency = vi.fn().mockResolvedValue({
      name: 'failing-dependency',
      status: 'unhealthy',
      message: 'Service unavailable',
    });

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [unhealthyDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/ready');
    expect(res.status).toBe(503);

    const body = await res.json() as Record<string, unknown>;
    expect(body.ready).toBe(false);
    expect(body.reason).toContain('unhealthy');
  });
});

describe('Health Routes Edge Cases', () => {
  const baseConfig: HealthCheckConfig = {
    serviceName: 'test-service',
    version: '1.0.0',
    startTime: new Date(),
  };

  it('should handle dependency check that throws an error', async () => {
    const throwingDependency = vi.fn().mockRejectedValue(new Error('Connection timeout'));

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [throwingDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/detailed');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.status).toBe('degraded');
    const deps = body.dependencies as Array<Record<string, unknown>>;
    expect(deps[0]?.status).toBe('unhealthy');
    expect(deps[0]?.message).toBe('Connection timeout');
  });

  it('should handle dependency check with non-Error thrown', async () => {
    const throwingDependency = vi.fn().mockRejectedValue('String error');

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [throwingDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/detailed');
    expect(res.status).toBe(200);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.status).toBe('degraded');
    const deps = body.dependencies as Array<Record<string, unknown>>;
    expect(deps[0]?.message).toBe('Unknown error');
  });

  it('should return not ready when dependency check throws', async () => {
    const throwingDependency = vi.fn().mockRejectedValue(new Error('Check failed'));

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [throwingDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/ready');
    expect(res.status).toBe(503);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.ready).toBe(false);
    expect(body.reason).toBe('Check failed');
  });

  it('should return not ready with generic message when non-Error thrown', async () => {
    const throwingDependency = vi.fn().mockRejectedValue('Non-error thrown');

    const configWithDeps: HealthCheckConfig = {
      ...baseConfig,
      dependencyChecks: [throwingDependency],
    };

    const app = new Hono();
    const healthRoutes = createHealthRoutes(configWithDeps);
    app.route('/', healthRoutes);

    const res = await app.request('/health/ready');
    expect(res.status).toBe(503);

    const body = (await res.json()) as Record<string, unknown>;
    expect(body.ready).toBe(false);
    expect(body.reason).toBe('Dependency check failed');
  });
});

describe('MyVault Dependency Check', () => {
  it('should create MyVault check function', () => {
    const check = createMyVaultCheck('http://localhost:8003');
    expect(typeof check).toBe('function');
  });

  it('should return unhealthy when MyVault is not available', async () => {
    // Use a port that won't be listening
    const check = createMyVaultCheck('http://localhost:19999');

    const result = await check();
    expect(result.name).toBe('myvault');
    expect(result.status).toBe('unhealthy');
    expect(result.latencyMs).toBeGreaterThanOrEqual(0);
  });

  it('should return healthy when MyVault responds with 200', async () => {
    // Mock fetch for this test
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
    }) as typeof fetch;

    try {
      const check = createMyVaultCheck('http://localhost:8003');
      const result = await check();

      expect(result.name).toBe('myvault');
      expect(result.status).toBe('healthy');
      expect(result.latencyMs).toBeGreaterThanOrEqual(0);
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should return unhealthy when MyVault responds with non-200', async () => {
    // Mock fetch for this test
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }) as typeof fetch;

    try {
      const check = createMyVaultCheck('http://localhost:8003');
      const result = await check();

      expect(result.name).toBe('myvault');
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('HTTP 500');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should return unhealthy with error message when fetch throws', async () => {
    // Mock fetch to throw error
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error')) as typeof fetch;

    try {
      const check = createMyVaultCheck('http://localhost:8003');
      const result = await check();

      expect(result.name).toBe('myvault');
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('Network error');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should return unhealthy with generic message for non-Error throws', async () => {
    // Mock fetch to throw non-Error
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockRejectedValue('Some failure') as typeof fetch;

    try {
      const check = createMyVaultCheck('http://localhost:8003');
      const result = await check();

      expect(result.name).toBe('myvault');
      expect(result.status).toBe('unhealthy');
      expect(result.message).toBe('Connection failed');
    } finally {
      global.fetch = originalFetch;
    }
  });
});
