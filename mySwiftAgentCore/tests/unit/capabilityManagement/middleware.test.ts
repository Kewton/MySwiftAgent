/**
 * Capability Middleware Unit Tests
 *
 * Issue #365: Middleware for API rate limiting and validation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Hono } from 'hono';
import {
  createRateLimiter,
  requireProject,
  requireAdminForCreate,
} from '../../../src/capabilityManagement/api/middleware.js';

describe('Capability Middleware', () => {
  describe('createRateLimiter', () => {
    it('should allow requests under the limit', async () => {
      const app = new Hono();
      app.use('*', createRateLimiter({ maxRequests: 5, windowMs: 60000 }));
      app.get('/test', (c) => c.text('OK'));

      const res = await app.request('/test');
      expect(res.status).toBe(200);
    });

    it('should set rate limit headers', async () => {
      const app = new Hono();
      app.use('*', createRateLimiter({ maxRequests: 10, windowMs: 60000 }));
      app.get('/test', (c) => c.text('OK'));

      const res = await app.request('/test');

      expect(res.headers.get('X-RateLimit-Limit')).toBe('10');
      expect(res.headers.get('X-RateLimit-Remaining')).toBe('9');
      expect(res.headers.get('X-RateLimit-Reset')).toBeDefined();
    });

    it('should reject requests over the limit', async () => {
      const app = new Hono();
      app.use('*', createRateLimiter({ maxRequests: 2, windowMs: 60000 }));
      app.get('/test', (c) => c.text('OK'));

      // First two requests should succeed
      await app.request('/test');
      await app.request('/test');

      // Third request should be rate limited
      const res = await app.request('/test');
      expect(res.status).toBe(429);
    });

    it('should use X-Forwarded-For header for client identification', async () => {
      const app = new Hono();
      app.use('*', createRateLimiter({ maxRequests: 2, windowMs: 60000 }));
      app.get('/test', (c) => c.text('OK'));

      // Requests from different IPs should have separate limits
      const res1 = await app.request('/test', {
        headers: { 'X-Forwarded-For': '192.168.1.1' },
      });
      const res2 = await app.request('/test', {
        headers: { 'X-Forwarded-For': '192.168.1.2' },
      });

      expect(res1.status).toBe(200);
      expect(res2.status).toBe(200);
    });

    it('should use request ID from auth context', async () => {
      const app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'api', requestId: 'unique-id' });
        await next();
      });
      app.use('*', createRateLimiter({ maxRequests: 2, windowMs: 60000 }));
      app.get('/test', (c) => c.text('OK'));

      // Requests with same request ID should share rate limit
      await app.request('/test');
      await app.request('/test');
      const res = await app.request('/test');

      expect(res.status).toBe(429);
    });
  });

  describe('requireProject', () => {
    it('should pass when project is provided', async () => {
      const app = new Hono();
      app.use('*', requireProject());
      app.get('/test', (c) => c.text('OK'));

      const res = await app.request('/test?project=default');
      expect(res.status).toBe(200);
    });

    it('should return 400 when project is missing', async () => {
      const app = new Hono();
      app.use('*', requireProject());
      app.get('/test', (c) => c.text('OK'));

      const res = await app.request('/test');
      expect(res.status).toBe(400);
    });
  });

  describe('requireAdminForCreate', () => {
    it('should pass GET requests without admin check', async () => {
      const app = new Hono();
      app.use('*', requireAdminForCreate());
      app.get('/test', (c) => c.text('OK'));

      const res = await app.request('/test');
      expect(res.status).toBe(200);
    });

    it('should return 401 for POST without auth', async () => {
      const app = new Hono();
      app.use('*', requireAdminForCreate());
      app.post('/test', (c) => c.text('OK'));

      const res = await app.request('/test', { method: 'POST' });
      expect(res.status).toBe(401);
    });

    it('should return 403 for POST with non-admin token', async () => {
      const app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'api' });
        await next();
      });
      app.use('*', requireAdminForCreate());
      app.post('/test', (c) => c.text('OK'));

      const res = await app.request('/test', { method: 'POST' });
      expect(res.status).toBe(403);
    });

    it('should pass POST with admin token', async () => {
      const app = new Hono();
      app.use('*', async (c, next) => {
        c.set('auth', { authenticated: true, tokenType: 'admin' });
        await next();
      });
      app.use('*', requireAdminForCreate());
      app.post('/test', (c) => c.text('OK'));

      const res = await app.request('/test', { method: 'POST' });
      expect(res.status).toBe(200);
    });
  });
});
