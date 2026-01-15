/**
 * Authentication Middleware - Hono middleware for API authentication
 *
 * Provides token-based authentication for API endpoints.
 */

import type { Context, Next, MiddlewareHandler } from 'hono';
import { HTTPException } from 'hono/http-exception';

/**
 * Authentication configuration
 */
export interface AuthConfig {
  apiToken: string;
  adminToken?: string;
  skipPaths?: string[];
}

/**
 * Token type
 */
export type TokenType = 'api' | 'admin';

/**
 * Authentication result stored in context
 */
export interface AuthResult {
  authenticated: boolean;
  tokenType?: TokenType;
  requestId?: string;
}

/**
 * Create authentication middleware
 */
export function createAuthMiddleware(config: AuthConfig): MiddlewareHandler {
  const skipPaths = new Set(config.skipPaths ?? ['/health', '/']);

  return async (c: Context, next: Next): Promise<Response | undefined> => {
    // Skip authentication for specific paths
    const path = c.req.path;
    if (skipPaths.has(path)) {
      await next();
      return;
    }

    // Get authorization header
    const authHeader = c.req.header('Authorization');
    const apiTokenHeader = c.req.header('X-API-Token');

    let token: string | undefined;
    let tokenType: TokenType = 'api';

    // Check Authorization header (Bearer token)
    if (authHeader?.startsWith('Bearer ')) {
      token = authHeader.substring(7);
    } else if (apiTokenHeader) {
      // Check X-API-Token header
      token = apiTokenHeader;
    }

    if (!token) {
      throw new HTTPException(401, {
        message: 'Authentication required. Provide Authorization header or X-API-Token.',
      });
    }

    // Validate token
    if (config.adminToken && token === config.adminToken) {
      tokenType = 'admin';
    } else if (token === config.apiToken) {
      tokenType = 'api';
    } else {
      throw new HTTPException(403, {
        message: 'Invalid authentication token.',
      });
    }

    // Store auth result in context
    const authResult: AuthResult = {
      authenticated: true,
      tokenType,
      requestId: c.req.header('X-Request-ID'),
    };
    c.set('auth', authResult);

    await next();
    return;
  };
}

/**
 * Create admin-only middleware
 * Requires the request to be authenticated with an admin token
 */
export function requireAdmin(): MiddlewareHandler {
  return async (c: Context, next: Next): Promise<Response | undefined> => {
    const auth = c.get('auth') as AuthResult | undefined;

    if (!auth?.authenticated) {
      throw new HTTPException(401, {
        message: 'Authentication required.',
      });
    }

    if (auth.tokenType !== 'admin') {
      throw new HTTPException(403, {
        message: 'Admin privileges required.',
      });
    }

    await next();
    return;
  };
}

/**
 * Get authentication result from context
 */
export function getAuth(c: Context): AuthResult | undefined {
  return c.get('auth') as AuthResult | undefined;
}

/**
 * Check if request is authenticated
 */
export function isAuthenticated(c: Context): boolean {
  const auth = getAuth(c);
  return auth?.authenticated ?? false;
}

/**
 * Check if request has admin privileges
 */
export function isAdmin(c: Context): boolean {
  const auth = getAuth(c);
  return auth?.tokenType === 'admin';
}
