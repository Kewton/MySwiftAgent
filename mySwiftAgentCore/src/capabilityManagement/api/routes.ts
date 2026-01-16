/**
 * Capability API Routes
 *
 * Issue #365: REST API endpoint configuration for capability management
 */

import { Hono } from 'hono';
import { createCapabilityHandlers, type CapabilityHandlerDependencies } from './handlers.js';

/**
 * Create capability API routes
 *
 * @param deps - Handler dependencies
 * @returns Hono app with all capability routes configured
 */
export function createCapabilityRoutes(deps: CapabilityHandlerDependencies): Hono {
  const app = new Hono();

  // Mount capability handlers
  const handlers = createCapabilityHandlers(deps);
  app.route('/', handlers);

  return app;
}

export { type CapabilityHandlerDependencies };
