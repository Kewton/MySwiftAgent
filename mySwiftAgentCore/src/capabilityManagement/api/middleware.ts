/**
 * Capability API Middleware
 *
 * Issue #365: Middleware for authentication and rate limiting
 */

import type { MiddlewareHandler, Context, Next } from 'hono';
import { HTTPException } from 'hono/http-exception';
import type { AuthResult } from '../../middleware/auth.js';

/**
 * Rate limit configuration
 */
export interface RateLimitConfig {
  maxRequests: number;
  windowMs: number;
}

/**
 * Rate limit entry for tracking requests
 */
interface RateLimitEntry {
  count: number;
  resetAt: number;
}

/**
 * Create rate limiting middleware
 *
 * @param config - Rate limit configuration
 * @returns Middleware handler
 */
export function createRateLimiter(config: RateLimitConfig): MiddlewareHandler {
  const store = new Map<string, RateLimitEntry>();

  return async (c: Context, next: Next): Promise<Response | undefined> => {
    const key = getClientKey(c);
    const now = Date.now();

    let entry = store.get(key);

    if (!entry || now > entry.resetAt) {
      entry = {
        count: 0,
        resetAt: now + config.windowMs,
      };
    }

    entry.count++;

    if (entry.count > config.maxRequests) {
      throw new HTTPException(429, {
        message: 'Too many requests. Please try again later.',
      });
    }

    store.set(key, entry);

    // Set rate limit headers
    c.header('X-RateLimit-Limit', String(config.maxRequests));
    c.header('X-RateLimit-Remaining', String(Math.max(0, config.maxRequests - entry.count)));
    c.header('X-RateLimit-Reset', String(Math.ceil(entry.resetAt / 1000)));

    await next();
    return;
  };
}

/**
 * Get client key for rate limiting
 */
function getClientKey(c: Context): string {
  // Use API token if available
  const auth = c.get('auth') as AuthResult | undefined;
  if (auth?.requestId) {
    return auth.requestId;
  }

  // Fall back to IP address
  const forwarded = c.req.header('X-Forwarded-For');
  if (forwarded) {
    return forwarded.split(',')[0]?.trim() ?? 'unknown';
  }

  // Use a default key for unknown clients
  return 'unknown';
}

/**
 * Create project validation middleware
 * Ensures project query parameter is present for capability endpoints
 */
export function requireProject(): MiddlewareHandler {
  return async (c: Context, next: Next): Promise<Response | undefined> => {
    const project = c.req.query('project');

    if (!project) {
      throw new HTTPException(400, {
        message: 'project query parameter is required',
      });
    }

    await next();
    return;
  };
}

/**
 * Create admin-only middleware for capability creation
 */
export function requireAdminForCreate(): MiddlewareHandler {
  return async (c: Context, next: Next): Promise<Response | undefined> => {
    // Only apply to POST requests
    if (c.req.method !== 'POST') {
      await next();
      return;
    }

    const auth = c.get('auth') as AuthResult | undefined;

    if (!auth?.authenticated) {
      throw new HTTPException(401, {
        message: 'Authentication required',
      });
    }

    if (auth.tokenType !== 'admin') {
      throw new HTTPException(403, {
        message: 'Admin privileges required for this operation',
      });
    }

    await next();
    return;
  };
}
