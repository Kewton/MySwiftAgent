/**
 * Authentication Middleware Unit Tests
 *
 * Tests for auth middleware functions
 */

import { describe, it, expect } from 'vitest';
import { Hono } from 'hono';
import {
  createAuthMiddleware,
  requireAdmin,
  getAuth,
  isAuthenticated,
  isAdmin,
  type AuthConfig,
  type AuthResult,
} from '../../../src/middleware/auth.js';

describe('Auth Middleware', () => {
  const authConfig: AuthConfig = {
    apiToken: 'valid-api-token',
    adminToken: 'valid-admin-token',
    skipPaths: ['/health', '/public'],
  };

  it('should allow requests with valid API token in Authorization header', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/protected', (c) => c.json({ ok: true }));

    const res = await app.request('/protected', {
      headers: {
        Authorization: 'Bearer valid-api-token',
      },
    });

    expect(res.status).toBe(200);
  });

  it('should allow requests with valid API token in X-API-Token header', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/protected', (c) => c.json({ ok: true }));

    const res = await app.request('/protected', {
      headers: {
        'X-API-Token': 'valid-api-token',
      },
    });

    expect(res.status).toBe(200);
  });

  it('should allow requests with admin token', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/protected', (c) => c.json({ ok: true }));

    const res = await app.request('/protected', {
      headers: {
        Authorization: 'Bearer valid-admin-token',
      },
    });

    expect(res.status).toBe(200);
  });

  it('should reject requests without token', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/protected', (c) => c.json({ ok: true }));

    const res = await app.request('/protected');
    expect(res.status).toBe(401);
  });

  it('should reject requests with invalid token', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/protected', (c) => c.json({ ok: true }));

    const res = await app.request('/protected', {
      headers: {
        Authorization: 'Bearer invalid-token',
      },
    });

    expect(res.status).toBe(403);
  });

  it('should skip authentication for configured paths', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/health', (c) => c.json({ ok: true }));
    app.get('/public', (c) => c.json({ ok: true }));

    const healthRes = await app.request('/health');
    expect(healthRes.status).toBe(200);

    const publicRes = await app.request('/public');
    expect(publicRes.status).toBe(200);
  });

  it('should set auth context for API token', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/check', (c) => {
      const auth = getAuth(c);
      return c.json(auth);
    });

    const res = await app.request('/check', {
      headers: {
        Authorization: 'Bearer valid-api-token',
      },
    });

    const body = (await res.json()) as AuthResult;
    expect(body.authenticated).toBe(true);
    expect(body.tokenType).toBe('api');
  });

  it('should set auth context for admin token', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/check', (c) => {
      const auth = getAuth(c);
      return c.json(auth);
    });

    const res = await app.request('/check', {
      headers: {
        Authorization: 'Bearer valid-admin-token',
      },
    });

    const body = (await res.json()) as AuthResult;
    expect(body.authenticated).toBe(true);
    expect(body.tokenType).toBe('admin');
  });
});

describe('requireAdmin Middleware', () => {
  const authConfig: AuthConfig = {
    apiToken: 'valid-api-token',
    adminToken: 'valid-admin-token',
  };

  it('should allow admin access', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.use('/admin/*', requireAdmin());
    app.get('/admin/action', (c) => c.json({ ok: true }));

    const res = await app.request('/admin/action', {
      headers: {
        Authorization: 'Bearer valid-admin-token',
      },
    });

    expect(res.status).toBe(200);
  });

  it('should reject non-admin access to admin routes', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.use('/admin/*', requireAdmin());
    app.get('/admin/action', (c) => c.json({ ok: true }));

    const res = await app.request('/admin/action', {
      headers: {
        Authorization: 'Bearer valid-api-token',
      },
    });

    expect(res.status).toBe(403);
  });

  it('should reject unauthenticated access', async () => {
    const app = new Hono();
    // Explicitly set auth to undefined
    app.use('/admin/*', (c, next) => {
      c.set('auth', undefined);
      return next();
    });
    app.use('/admin/*', requireAdmin());
    app.get('/admin/action', (c) => c.json({ ok: true }));

    const res = await app.request('/admin/action');
    expect(res.status).toBe(401);
  });
});

describe('Auth Helper Functions', () => {
  const authConfig: AuthConfig = {
    apiToken: 'valid-api-token',
    adminToken: 'valid-admin-token',
  };

  it('isAuthenticated should return true for authenticated requests', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/check', (c) => {
      return c.json({ authenticated: isAuthenticated(c) });
    });

    const res = await app.request('/check', {
      headers: {
        Authorization: 'Bearer valid-api-token',
      },
    });

    const body = (await res.json()) as { authenticated: boolean };
    expect(body.authenticated).toBe(true);
  });

  it('isAuthenticated should return false for unauthenticated requests', async () => {
    const app = new Hono();
    app.get('/check', (c) => {
      return c.json({ authenticated: isAuthenticated(c) });
    });

    const res = await app.request('/check');
    const body = (await res.json()) as { authenticated: boolean };
    expect(body.authenticated).toBe(false);
  });

  it('isAdmin should return true for admin requests', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/check', (c) => {
      return c.json({ isAdmin: isAdmin(c) });
    });

    const res = await app.request('/check', {
      headers: {
        Authorization: 'Bearer valid-admin-token',
      },
    });

    const body = (await res.json()) as { isAdmin: boolean };
    expect(body.isAdmin).toBe(true);
  });

  it('isAdmin should return false for non-admin requests', async () => {
    const app = new Hono();
    app.use('*', createAuthMiddleware(authConfig));
    app.get('/check', (c) => {
      return c.json({ isAdmin: isAdmin(c) });
    });

    const res = await app.request('/check', {
      headers: {
        Authorization: 'Bearer valid-api-token',
      },
    });

    const body = (await res.json()) as { isAdmin: boolean };
    expect(body.isAdmin).toBe(false);
  });

  it('getAuth should return undefined when no auth is set', async () => {
    const app = new Hono();
    app.get('/check', (c) => {
      const auth = getAuth(c);
      return c.json({ auth });
    });

    const res = await app.request('/check');
    const body = (await res.json()) as { auth: AuthResult | undefined };
    expect(body.auth).toBeUndefined();
  });
});
