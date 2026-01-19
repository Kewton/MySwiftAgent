/**
 * TaskFlow Reload API Routes
 *
 * Issue #375: REST API endpoint for workflow hot reload
 * Issue #378: Added status field for partial success model
 */

import { Hono } from 'hono';
import type { WorkflowReloader } from '../../taskflowEngine/loader/WorkflowReloader.js';

/**
 * Reload handler dependencies
 */
export interface ReloadHandlerDependencies {
  reloader: WorkflowReloader;
}

/**
 * Reload request body
 */
export interface ReloadRequest {
  project?: string;
  file_path?: string;
}

/**
 * Create reload workflow handler
 */
export function createReloadHandler(deps: ReloadHandlerDependencies): (c: import('hono').Context) => Promise<Response> {
  return async (c: import('hono').Context): Promise<Response> => {
    try {
      const body = (await c.req.json()) as ReloadRequest;
      const { project, file_path } = body;

      // If specific file path is provided, reload single workflow
      if (file_path && project) {
        const result = await deps.reloader.reloadWorkflow(project, file_path);

        if (!result.success) {
          return c.json(
            {
              success: false,
              error: result.error,
            },
            400
          );
        }

        return c.json({
          success: true,
          message: `Workflow "${result.workflowName}" reloaded successfully`,
          workflowName: result.workflowName,
        });
      }

      // If project is provided, reload all workflows for that project
      if (project) {
        const result = await deps.reloader.reloadProject(project);

        // Issue #378: Include status field for partial success model
        return c.json({
          status: result.status,
          success: result.success,
          message: result.status === 'success'
            ? `Reloaded ${result.reloadedCount} workflows for project "${project}"`
            : result.status === 'partial_success'
              ? `Partial reload: ${result.reloadedCount} workflows reloaded, ${result.failedCount} failed`
              : `Failed to reload workflows for project "${project}"`,
          reloadedCount: result.reloadedCount,
          failedCount: result.failedCount,
          workflowNames: result.workflowNames,
          errors: result.errors,
        });
      }

      // If nothing specified, reload all projects
      const result = await deps.reloader.reloadAll();

      const totalReloaded = result.projectResults.reduce(
        (sum, r) => sum + r.reloadedCount,
        0
      );

      const totalFailed = result.projectResults.reduce(
        (sum, r) => sum + r.failedCount,
        0
      );

      // Issue #378: Include status field for partial success model
      return c.json({
        status: result.status,
        success: result.success,
        message: result.status === 'success'
          ? `Reloaded ${totalReloaded} workflows across ${result.projectResults.length} projects`
          : result.status === 'partial_success'
            ? `Partial reload: ${totalReloaded} workflows reloaded, ${totalFailed} failed`
            : `Failed to reload workflows`,
        totalReloaded,
        totalFailed,
        projectResults: result.projectResults.map((r) => ({
          status: r.status,
          reloadedCount: r.reloadedCount,
          failedCount: r.failedCount,
          workflowNames: r.workflowNames,
          errors: r.errors,
        })),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return c.json({ success: false, error: message }, 500);
    }
  };
}

/**
 * Create TaskFlow reload routes
 *
 * Routes:
 * - POST /api/v1/taskflow/reload - Reload workflows
 */
export function createTaskFlowReloadRoutes(deps: ReloadHandlerDependencies): Hono {
  const app = new Hono();

  // Reload workflows
  app.post('/reload', createReloadHandler(deps));

  return app;
}

/**
 * Create full reload API with /api/v1/taskflow prefix
 */
export function createTaskFlowReloadApi(deps: ReloadHandlerDependencies): Hono {
  const app = new Hono();

  app.route('/api/v1/taskflow', createTaskFlowReloadRoutes(deps));

  return app;
}
