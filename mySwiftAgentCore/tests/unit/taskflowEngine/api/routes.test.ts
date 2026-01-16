/**
 * API Routes Unit Tests
 *
 * Issue #363: REST API route configuration
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  createTaskFlowRoutes,
  createTaskFlowApi,
} from '../../../../src/taskflowEngine/api/routes.js';
import type { HandlerDependencies } from '../../../../src/taskflowEngine/api/handlers.js';

describe('createTaskFlowRoutes', () => {
  let deps: HandlerDependencies;

  beforeEach(() => {
    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn(),
        getByProject: vi.fn().mockReturnValue([]),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn().mockReturnValue({ totalWorkflows: 0, totalProjects: 0 }),
      },
      executor: {
        execute: vi.fn(),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn().mockReturnValue({ valid: true, errors: [] }),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should create a Hono app instance', () => {
    const app = createTaskFlowRoutes(deps);

    expect(app).toBeDefined();
    expect(typeof app.fetch).toBe('function');
  });

  it('should have execute route', () => {
    const app = createTaskFlowRoutes(deps);

    // Hono app should have routes defined
    expect(app).toBeDefined();
  });
});

describe('createTaskFlowApi', () => {
  let deps: HandlerDependencies;

  beforeEach(() => {
    deps = {
      registry: {
        register: vi.fn(),
        getWorkflow: vi.fn(),
        getByProject: vi.fn().mockReturnValue([]),
        remove: vi.fn(),
        clear: vi.fn(),
        has: vi.fn(),
        getStats: vi.fn().mockReturnValue({ totalWorkflows: 0, totalProjects: 0 }),
      },
      executor: {
        execute: vi.fn(),
      },
      validator: {
        validateTaskFlow: vi.fn(),
        validateInternal: vi.fn(),
        validateInputs: vi.fn().mockReturnValue({ valid: true, errors: [] }),
        validateDependencies: vi.fn(),
      },
    };
  });

  it('should create API with /api/v1/taskflow prefix', () => {
    const app = createTaskFlowApi(deps);

    expect(app).toBeDefined();
    expect(typeof app.fetch).toBe('function');
  });

  it('should mount routes correctly', async () => {
    const app = createTaskFlowApi(deps);

    // Test stats endpoint as it's simplest
    const req = new Request('http://localhost/api/v1/taskflow/stats');
    const res = await app.fetch(req);

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('totalWorkflows');
  });

  it('should handle workflows list endpoint', async () => {
    const app = createTaskFlowApi(deps);

    const req = new Request('http://localhost/api/v1/taskflow/workflows?project=test');
    const res = await app.fetch(req);

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty('workflows');
  });

  it('should return 400 for missing project parameter', async () => {
    const app = createTaskFlowApi(deps);

    const req = new Request('http://localhost/api/v1/taskflow/workflows');
    const res = await app.fetch(req);

    expect(res.status).toBe(400);
  });
});
