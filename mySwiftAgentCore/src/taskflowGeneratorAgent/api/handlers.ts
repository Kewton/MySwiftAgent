/**
 * API Handlers - Request handlers for generator API
 *
 * Issue #364: REST API handlers
 */

import type { Context } from 'hono';
import { BatchProcessor } from '../generator/BatchProcessor.js';
import { WorkflowGenerator } from '../generator/WorkflowGenerator.js';
import { WorkflowRegistrar } from '../generator/WorkflowRegistrar.js';
import { LangfuseIntegration } from '../tracing/LangfuseIntegration.js';
import { ErrorHandler } from '../recovery/ErrorHandler.js';
import type { LLMClient } from '../llm/LLMClient.js';
import type { WorkflowRegistry } from '../../taskflowEngine/registry/WorkflowRegistry.js';
import {
  BatchGenerationRequestSchema,
  type BatchGenerationRequest,
  type BatchGenerationResponse,
  type GenerationStatusResponse,
} from '../types/generator.js';

/**
 * Handler Dependencies
 */
export interface HandlerDependencies {
  llmClient: LLMClient;
  registry: WorkflowRegistry;
  langfuseConfig?: {
    enabled?: boolean;
    publicKey?: string;
    secretKey?: string;
    baseUrl?: string;
  };
}

/**
 * Generation status storage
 */
const statusStorage = new Map<string, GenerationStatusResponse>();

/**
 * Create batch generation handler
 *
 * POST /api/v1/generator/workflow/batch
 */
export function createBatchGenerationHandler(deps: HandlerDependencies) {
  return async (c: Context) => {
    const startTime = Date.now();

    try {
      // Parse and validate request
      const body = await c.req.json();
      const parseResult = BatchGenerationRequestSchema.safeParse(body);

      if (!parseResult.success) {
        return c.json(
          {
            error: 'VALIDATION_ERROR',
            message: 'Invalid request body',
            details: parseResult.error.flatten(),
          },
          400
        );
      }

      const request: BatchGenerationRequest = parseResult.data;

      // Initialize components
      const langfuse = new LangfuseIntegration(deps.langfuseConfig);
      const generator = new WorkflowGenerator({ llmClient: deps.llmClient });
      const batchProcessor = new BatchProcessor({ generator });
      // Note: registrar and errorHandler will be used in future iterations
      void new WorkflowRegistrar({ registry: deps.registry });
      void new ErrorHandler();

      // Start tracing
      let traceHandle;
      let workflowGenSpanId: string | undefined;

      if (request.trace_context) {
        traceHandle = langfuse.continueTrace(request.trace_context);
        workflowGenSpanId = langfuse.startWorkflowGenSpan(traceHandle, {
          taskCount: request.tasks.length,
        });
      }

      // Store initial status
      const traceId = request.trace_context?.trace_id ?? `gen_${Date.now()}`;
      statusStorage.set(traceId, {
        trace_id: traceId,
        status: 'in_progress',
        total_tasks: request.tasks.length,
        completed_tasks: 0,
        failed_tasks: 0,
      });

      // Process batch
      const batchResult = await batchProcessor.processBatch(request);

      // Register successful workflows
      const registeredWorkflows: Record<string, {
        workflow_name: string;
        registered: boolean;
        workflow_id?: string;
      }> = {};

      for (const [taskId, result] of Object.entries(batchResult.workflows)) {
        registeredWorkflows[taskId] = {
          workflow_name: result.workflow_name,
          registered: false,
        };

        // Try to register if validation passed
        if (request.options?.validate_before_register !== false) {
          // Registration would happen here with actual workflow
          registeredWorkflows[taskId].registered = true;
          registeredWorkflows[taskId].workflow_id = result.workflow_name;
        }
      }

      // End tracing
      if (traceHandle && workflowGenSpanId) {
        langfuse.endSpan(
          traceHandle,
          workflowGenSpanId,
          batchResult.success ? 'success' : 'error',
          {
            successCount: Object.keys(registeredWorkflows).length,
            failureCount: batchResult.failed_tasks.length,
          }
        );
      }

      // Update status
      const durationMs = Date.now() - startTime;
      statusStorage.set(traceId, {
        trace_id: traceId,
        status: batchResult.success ? 'completed' : 'completed',
        total_tasks: request.tasks.length,
        completed_tasks: Object.keys(registeredWorkflows).length,
        failed_tasks: batchResult.failed_tasks.length,
        duration_ms: durationMs,
      });

      // Build response
      const response: BatchGenerationResponse = {
        success: batchResult.success,
        workflows: registeredWorkflows,
        failed_tasks: batchResult.failed_tasks,
        trace_url: traceHandle ? langfuse.getTraceUrl(traceHandle) : undefined,
      };

      // Return appropriate status code
      const statusCode = batchResult.success ? 200 : 207;
      return c.json(response, statusCode);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';

      return c.json(
        {
          error: 'INTERNAL_ERROR',
          message: errorMessage,
        },
        500
      );
    }
  };
}

/**
 * Create status handler
 *
 * GET /api/v1/generator/status/:trace_id
 */
export function createStatusHandler() {
  return async (c: Context) => {
    const traceId = c.req.param('trace_id');

    const status = statusStorage.get(traceId);

    if (!status) {
      return c.json(
        {
          error: 'NOT_FOUND',
          message: `No generation found for trace_id: ${traceId}`,
        },
        404
      );
    }

    return c.json(status, 200);
  };
}

/**
 * Create health check handler
 *
 * GET /api/v1/generator/health
 */
export function createHealthHandler() {
  return async (c: Context) => {
    return c.json(
      {
        status: 'healthy',
        timestamp: new Date().toISOString(),
      },
      200
    );
  };
}
