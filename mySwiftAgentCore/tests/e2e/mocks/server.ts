/**
 * MSW Mock Server
 *
 * Issue #379: Mock server configuration for E2E testing
 */

import { setupServer } from 'msw/node';
import { handlers, resetRequestTracker, requestTracker } from './handlers.js';
import type { HttpHandler } from 'msw';

/**
 * Create MSW server with default handlers
 */
export const server = setupServer(...handlers);

/**
 * Server lifecycle helpers
 */
export const mockServer = {
  /**
   * Start server with default handlers
   */
  start(): void {
    server.listen({
      onUnhandledRequest: 'bypass', // Allow unhandled requests to pass through
    });
  },

  /**
   * Stop server
   */
  stop(): void {
    server.close();
  },

  /**
   * Reset handlers to defaults and clear tracked requests
   */
  reset(): void {
    server.resetHandlers();
    resetRequestTracker();
  },

  /**
   * Add custom handlers for specific tests
   */
  use(...customHandlers: HttpHandler[]): void {
    server.use(...customHandlers);
  },

  /**
   * Get request tracker
   */
  getRequestTracker() {
    return requestTracker;
  },

  /**
   * Get all tracked requests
   */
  getTrackedRequests() {
    return requestTracker.getRequests();
  },

  /**
   * Check if server intercepted any requests
   */
  hasInterceptedRequests(): boolean {
    return requestTracker.hasRequests();
  },

  /**
   * Get request count
   */
  getRequestCount(): number {
    return requestTracker.getRequestCount();
  },
};

/**
 * Export server for direct access
 */
export { server as mswServer };

/**
 * Vitest lifecycle hooks for MSW
 *
 * Usage in test files:
 * ```ts
 * import { setupMswLifecycle } from '../mocks/server';
 *
 * describe('My E2E Test', () => {
 *   setupMswLifecycle();
 *
 *   test('should work', async () => {
 *     // MSW is automatically started and reset
 *   });
 * });
 * ```
 */
export function setupMswLifecycle() {
  // These are imported at runtime by vitest
  const { beforeAll, afterAll, afterEach } = require('vitest');

  beforeAll(() => {
    mockServer.start();
  });

  afterEach(() => {
    mockServer.reset();
  });

  afterAll(() => {
    mockServer.stop();
  });
}
