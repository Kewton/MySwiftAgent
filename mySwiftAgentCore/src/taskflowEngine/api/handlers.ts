/**
 * TaskFlow API Handlers
 *
 * Issue #363: REST API request handlers
 */

import type { Context } from 'hono';
import type { WorkflowRegistry } from '../registry/WorkflowRegistry.js';
import type { TaskFlowEngine } from '../TaskFlowEngine.js';
import type { SchemaValidator } from '../validator/SchemaValidator.js';
import type { LangfuseTracer } from '../tracer/LangfuseTracer.js';
import type { SecretManager } from '../../shared/context/SecretManager.js';

/**
 * Handler dependencies
 */
export interface HandlerDependencies {
  registry: WorkflowRegistry;
  executor: TaskFlowEngine;
  validator: SchemaValidator;
  tracer?: LangfuseTracer;
  secretManager?: SecretManager;
}

/**
 * Execute workflow request
 */
export interface ExecuteWorkflowRequest {
  project: string;
  workflow: string;
  inputs: Record<string, unknown>;
}

/**
 * Create execute workflow handler
 */
export function createExecuteHandler(deps: HandlerDependencies) {
  return async (c: Context) => {
    try {
      const body = await c.req.json() as ExecuteWorkflowRequest;
      const { project, workflow: workflowName, inputs } = body;

      if (!project || !workflowName) {
        return c.json(
          { error: 'project and workflow are required' },
          400
        );
      }

      // Get workflow from registry
      const workflow = deps.registry.getWorkflow(project, workflowName);
      if (!workflow) {
        return c.json(
          { error: `Workflow '${workflowName}' not found in project '${project}'` },
          404
        );
      }

      // Validate inputs
      const inputValidation = deps.validator.validateInputs(workflow, inputs);
      if (!inputValidation.valid) {
        return c.json(
          { error: 'Input validation failed', details: inputValidation.errors },
          400
        );
      }

      // Start trace if tracer is available
      let traceId: string | undefined;
      if (deps.tracer) {
        traceId = deps.tracer.startWorkflowTrace(workflow.id, workflow.name);
      }

      // Get secrets from SecretManager if available
      let secrets: Record<string, string> = {};
      if (deps.secretManager) {
        // Get commonly needed secrets for workflow execution
        const secretKeys = ['OPENAI_API_KEY', 'LLM_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY'];
        for (const key of secretKeys) {
          const value = await deps.secretManager.get(key);
          if (value) {
            secrets[key] = value;
          }
        }
      }

      // Execute workflow
      const result = await deps.executor.execute(workflow, {
        inputs,
        secrets,
      });

      // End trace
      if (deps.tracer && traceId) {
        deps.tracer.endWorkflowTrace(traceId, result);
      }

      return c.json({
        workflowId: result.workflowId,
        status: result.status,
        results: result.metadata?.output,
        errors: result.errors.map((e) => ({
          stepId: e.stepId,
          code: e.errorCode,
          message: e.errorMessage,
        })),
        traceId,
        durationMs: result.durationMs,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return c.json({ error: message }, 500);
    }
  };
}

/**
 * Create list workflows handler
 */
export function createListWorkflowsHandler(deps: HandlerDependencies) {
  return async (c: Context) => {
    try {
      const project = c.req.query('project');

      if (!project) {
        return c.json({ error: 'project query parameter is required' }, 400);
      }

      const workflows = deps.registry.getByProject(project);

      return c.json({
        workflows: workflows.map((w) => ({
          name: w.name,
          version: w.version,
          inputSchema: w.inputSchema,
          outputSchema: w.outputSchema,
          stepCount: w.steps.length,
        })),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return c.json({ error: message }, 500);
    }
  };
}

/**
 * Create get workflow handler
 */
export function createGetWorkflowHandler(deps: HandlerDependencies) {
  return async (c: Context) => {
    try {
      const project = c.req.query('project');
      const name = c.req.param('name');

      if (!project || !name) {
        return c.json(
          { error: 'project query parameter and name path parameter are required' },
          400
        );
      }

      const workflow = deps.registry.getWorkflow(project, name);

      if (!workflow) {
        return c.json(
          { error: `Workflow '${name}' not found in project '${project}'` },
          404
        );
      }

      // Convert to external format
      return c.json({
        workflow_name: workflow.name,
        version: workflow.version,
        input_schema: workflow.inputSchema,
        output_schema: workflow.outputSchema,
        steps: workflow.steps.map((s) => ({
          id: s.id,
          type: s.type,
          description: s.name,
        })),
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return c.json({ error: message }, 500);
    }
  };
}

/**
 * Create registry stats handler
 */
export function createStatsHandler(deps: HandlerDependencies) {
  return async (c: Context) => {
    try {
      const stats = deps.registry.getStats();
      return c.json(stats);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return c.json({ error: message }, 500);
    }
  };
}
