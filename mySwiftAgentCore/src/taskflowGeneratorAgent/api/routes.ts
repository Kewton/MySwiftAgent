/**
 * API Routes - Hono route definitions for generator API
 *
 * Issue #364: REST API routes
 * Issue #370: WorkflowRegistrar initialization for persistence
 */

import { Hono } from 'hono';
import type { HandlerDependencies } from './handlers.js';
import {
  createBatchGenerationHandler,
  createStatusHandler,
  createHealthHandler,
} from './handlers.js';
import { WorkflowRegistrar } from '../generator/WorkflowRegistrar.js';
import { WorkflowStorage } from '../storage/WorkflowStorage.js';
import { createLogger } from '../../utils/logger/Logger.js';

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

/**
 * Issue #370: Create initialized Generator API with WorkflowRegistrar
 *
 * This function creates a WorkflowRegistrar with storage and initializes it
 * to restore workflows from disk. Use this for production deployments.
 *
 * @param deps - Handler dependencies (llmClient, registry, langfuseConfig)
 * @returns Promise resolving to initialized Hono app
 */
export async function createInitializedGeneratorApi(
  deps: Omit<HandlerDependencies, 'registrar'>
): Promise<Hono> {
  const logger = createLogger({ name: 'generator-api' });
  const storage = new WorkflowStorage();

  // Create WorkflowRegistrar with storage for persistence
  const registrar = new WorkflowRegistrar({
    registry: deps.registry,
    storage,
    logger,
  });

  // Initialize registrar to restore workflows from disk
  await registrar.initialize();

  // Create API with initialized registrar
  return createGeneratorApi({
    ...deps,
    registrar,
  });
}
