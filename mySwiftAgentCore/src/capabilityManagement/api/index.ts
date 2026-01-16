/**
 * API module exports
 *
 * Issue #365: Capability API routes, handlers, and middleware
 */

export {
  createCapabilityHandlers,
  type CapabilityHandlerDependencies,
} from './handlers.js';

export { createCapabilityRoutes } from './routes.js';

export {
  createRateLimiter,
  requireProject,
  requireAdminForCreate,
  type RateLimitConfig,
} from './middleware.js';
