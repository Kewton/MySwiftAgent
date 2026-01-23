/**
 * API Handlers - Request handlers for generator API
 *
 * Issue #364: REST API handlers
 * Issue #374: Capability Enrichment Layer for complete parameter information
 */

import type { Context } from 'hono';
import { BatchProcessor } from '../generator/BatchProcessor.js';
import { WorkflowGenerator } from '../generator/WorkflowGenerator.js';
import { WorkflowRegistrar } from '../generator/WorkflowRegistrar.js';
import { WorkflowStorage } from '../storage/WorkflowStorage.js';
import { LangfuseIntegration } from '../tracing/LangfuseIntegration.js';
import { ErrorHandler } from '../recovery/ErrorHandler.js';
import { createLogger } from '../../utils/logger/Logger.js';
import type { LLMClient } from '../llm/LLMClient.js';
import type { WorkflowRegistry } from '../../taskflowEngine/registry/WorkflowRegistry.js';
import type { CapabilityRegistry } from '../../capabilityManagement/registry/CapabilityRegistry.js';
import type { CapabilityExtended } from '../../shared/types/capability.types.js';
import {
  BatchGenerationRequestSchema,
  type BatchGenerationRequest,
  type BatchGenerationResponse,
  type GenerationStatusResponse,
  type Capability,
  type CapabilityForPrompt,
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
  /**
   * Issue #370: Optional pre-configured WorkflowRegistrar
   * If provided, will be used instead of creating a new one per request.
   * This allows initialize() to be called once at server startup.
   */
  registrar?: WorkflowRegistrar;
  /**
   * Issue #374: Optional CapabilityRegistry for capability enrichment
   * If provided, capabilities from requests will be enriched with full
   * parameter definitions from YAML files.
   */
  capabilityRegistry?: CapabilityRegistry;
  /**
   * Issue #396: Optional WorkflowStorage for reload API
   * If provided, reload API can load from generated workflows directory.
   */
  storage?: WorkflowStorage;
}

/**
 * Issue #374: Enrich capabilities with full parameter definitions
 *
 * This function takes the minimal capabilities from the API request and
 * enriches them with complete parameter definitions from the CapabilityRegistry.
 * This ensures that:
 * - PromptBuilder has complete capability specifications for LLM prompts
 * - WorkflowCapabilityValidator can validate required parameters
 *
 * @param capabilities - Capabilities from API request (may lack parameters)
 * @param projectId - Project ID to look up capabilities
 * @param registry - CapabilityRegistry with full YAML definitions
 * @returns Enriched capabilities with complete parameter information
 */
function enrichCapabilities(
  capabilities: Capability[],
  projectId: string,
  registry: CapabilityRegistry | undefined
): CapabilityForPrompt[] {
  if (!registry) {
    // No registry available, return capabilities as-is
    return capabilities as CapabilityForPrompt[];
  }

  return capabilities.map((cap) => {
    const fullDef: CapabilityExtended | undefined = registry.getCapability(projectId, cap.id);

    if (fullDef) {
      // Enrich with full definition from registry
      // Issue #374: Map capability examples to CapabilityForPrompt format
      // The YAML examples use taskflow_step field directly
      const mappedExamples = fullDef.examples?.map((ex) => {
        // Try taskflow_step first (current YAML format), then fall back to input for backward compatibility
        const step = (ex as unknown as Record<string, unknown>).taskflow_step ?? ex.input;
        return {
          description: ex.description,
          taskflow_step: step as {
            id: string;
            type: string;
            config: Record<string, unknown>;
            params: Record<string, unknown>;
          } | undefined,
        };
      });

      return {
        ...cap,
        parameters: fullDef.parameters ?? cap.parameters,
        examples: mappedExamples,
        responseSchema: fullDef.returnType
          ? { type: fullDef.returnType }
          : undefined,
        metadata: fullDef.metadata as CapabilityForPrompt['metadata'],
      } as CapabilityForPrompt;
    }

    // Capability not found in registry, return as-is
    return cap as CapabilityForPrompt;
  });
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
      // Issue #370: Create Logger and WorkflowStorage for persistence
      const logger = createLogger({ name: 'generator-api' });
      const langfuse = new LangfuseIntegration(deps.langfuseConfig);
      const generator = new WorkflowGenerator({ llmClient: deps.llmClient });
      const batchProcessor = new BatchProcessor({ generator, logger });
      // Issue #368: Use WorkflowRegistrar to register generated workflows
      // Issue #370: Use pre-configured registrar if provided, otherwise create new one with storage
      const registrar = deps.registrar ?? new WorkflowRegistrar({
        registry: deps.registry,
        storage: new WorkflowStorage(),
        logger,
      });
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

      // Issue #374: Enrich capabilities with full parameter definitions from registry
      const enrichedCapabilities = enrichCapabilities(
        request.capabilities,
        request.project_id,
        deps.capabilityRegistry
      );

      // Log enrichment results for debugging
      const enrichedCount = enrichedCapabilities.filter(
        (c) => c.parameters && c.parameters.length > 0
      ).length;
      logger.info('Capabilities enriched', {
        projectId: request.project_id,
        totalCapabilities: request.capabilities.length,
        enrichedCount,
        registryAvailable: !!deps.capabilityRegistry,
      });

      // Process batch with enriched capabilities
      const enrichedRequest: BatchGenerationRequest = {
        ...request,
        capabilities: enrichedCapabilities as Capability[],
      };
      const batchResult = await batchProcessor.processBatch(enrichedRequest);

      // Issue #368: Register successful workflows using WorkflowRegistrar
      // Issue #370: Include file_path in response for persistence verification
      const registeredWorkflows: Record<string, {
        workflow_name: string;
        registered: boolean;
        workflow_id?: string;
        file_path?: string;
      }> = {};

      for (const [taskId, metadata] of Object.entries(batchResult.workflows)) {
        registeredWorkflows[taskId] = {
          workflow_name: metadata.workflow_name,
          registered: false,
        };

        // Try to register if validation passed
        if (request.options?.validate_before_register !== false) {
          // Issue #368: Get actual workflow definition and register it
          const workflow = batchResult.workflowDefinitions[taskId];
          if (workflow) {
            try {
              // Issue #373: Pass taskId for nested directory structure
              const regResult = await registrar.register(workflow, request.project_id, taskId);
              registeredWorkflows[taskId].registered = regResult.success;
              registeredWorkflows[taskId].workflow_id = regResult.workflowId;
              // Issue #370: Include file_path for persistence verification
              registeredWorkflows[taskId].file_path = regResult.filePath;
            } catch (error) {
              // Registration failed, log error but continue
              console.error(`Registration failed for ${taskId}:`, error);
              registeredWorkflows[taskId].registered = false;
            }
          }
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

      // Issue #368: Fix status bug - should be 'failed' when batch fails
      const durationMs = Date.now() - startTime;
      statusStorage.set(traceId, {
        trace_id: traceId,
        status: batchResult.success ? 'completed' : 'failed',
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
