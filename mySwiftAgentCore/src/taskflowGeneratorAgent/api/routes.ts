/**
 * API Routes - Hono route definitions for generator API
 *
 * Issue #364: REST API routes
 */

import { Hono } from 'hono';
import type { HandlerDependencies } from './handlers.js';
import {
  createBatchGenerationHandler,
  createStatusHandler,
  createHealthHandler,
} from './handlers.js';

/**
 * Create Generator API routes
 *
 * Routes:
 * - POST /batch - Generate workflows for batch of tasks
 * - GET /status/:trace_id - Get generation status
 * - GET /health - Health check
 */
export function createGeneratorRoutes(deps: HandlerDependencies): Hono {
  const app = new Hono();

  // Batch generation
  app.post('/batch', createBatchGenerationHandler(deps));

  // Status check
  app.get('/status/:trace_id', createStatusHandler());

  // Health check
  app.get('/health', createHealthHandler());

  return app;
}

/**
 * Create full API with /api/v1/generator prefix
 */
export function createGeneratorApi(deps: HandlerDependencies): Hono {
  const app = new Hono();

  // Mount routes under /api/v1/generator/workflow
  app.route('/api/v1/generator/workflow', createGeneratorRoutes(deps));

  // Also mount health at /api/v1/generator/health for convenience
  app.get('/api/v1/generator/health', createHealthHandler());

  return app;
}
