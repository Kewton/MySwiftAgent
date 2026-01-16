/**
 * TaskFlow API Routes
 *
 * Issue #363: REST API route definitions
 */

import { Hono } from 'hono';
import type { HandlerDependencies } from './handlers.js';
import {
  createExecuteHandler,
  createListWorkflowsHandler,
  createGetWorkflowHandler,
  createStatsHandler,
} from './handlers.js';

/**
 * Create TaskFlow API routes
 *
 * Routes:
 * - POST /api/v1/taskflow/execute - Execute a workflow
 * - GET /api/v1/taskflow/workflows - List workflows for a project
 * - GET /api/v1/taskflow/workflows/:name - Get workflow details
 * - GET /api/v1/taskflow/stats - Get registry statistics
 */
export function createTaskFlowRoutes(deps: HandlerDependencies): Hono {
  const app = new Hono();

  // Execute workflow
  app.post('/execute', createExecuteHandler(deps));

  // List workflows
  app.get('/workflows', createListWorkflowsHandler(deps));

  // Get workflow details
  app.get('/workflows/:name', createGetWorkflowHandler(deps));

  // Get stats
  app.get('/stats', createStatsHandler(deps));

  return app;
}

/**
 * Create full API with /api/v1/taskflow prefix
 */
export function createTaskFlowApi(deps: HandlerDependencies): Hono {
  const app = new Hono();

  app.route('/api/v1/taskflow', createTaskFlowRoutes(deps));

  return app;
}
