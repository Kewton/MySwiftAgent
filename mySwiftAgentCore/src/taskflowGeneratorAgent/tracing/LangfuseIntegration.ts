/**
 * LangfuseIntegration - Langfuse tracing integration
 *
 * Issue #364: Trace context continuation from expertAgent
 */

import type { TraceContext, TaskGenerationRequest } from '../types/generator.js';
import type { LLMResponse } from '../types/llm.js';

/**
 * Span metadata
 */
export interface SpanMetadata {
  taskId?: string;
  taskMasterId?: string;
  phase?: string;
  source?: string;
  [key: string]: unknown;
}

/**
 * Generation metadata for LLM calls
 */
export interface GenerationMetadata {
  model: string;
  temperature?: number;
  maxTokens?: number;
  promptTokens: number;
  completionTokens: number;
  latencyMs: number;
}

/**
 * Trace handle returned from continueTrace
 */
export interface TraceHandle {
  traceId: string;
  spanId?: string;
}

/**
 * Langfuse Integration Configuration
 */
export interface LangfuseIntegrationConfig {
  enabled?: boolean;
  publicKey?: string;
  secretKey?: string;
  baseUrl?: string;
}

/**
 * LangfuseIntegration - Continues traces from expertAgent
 *
 * Features:
 * - Continue existing traces with trace_context
 * - Create WORKFLOW_GEN spans
 * - Record LLM generations
 * - Track token usage and latency
 */
export class LangfuseIntegration {
  private readonly config: LangfuseIntegrationConfig;
  private readonly enabled: boolean;
  private readonly traces: Map<string, TraceData> = new Map();

  constructor(config: LangfuseIntegrationConfig = {}) {
    this.config = config;
    this.enabled =
      config.enabled !== false && !!(config.publicKey && config.secretKey);
  }

  /**
   * Continue an existing trace from expertAgent
   *
   * @param context - Trace context from request
   * @returns Trace handle
   */
  continueTrace(context: TraceContext): TraceHandle {
    const traceId = context.trace_id ?? `trace_${Date.now()}`;

    if (this.enabled) {
      // Store trace data locally (in production, this would use Langfuse SDK)
      this.traces.set(traceId, {
        id: traceId,
        parentSpanId: context.parent_span_id,
        userId: context.user_id,
        sessionId: context.session_id,
        metadata: context.metadata ?? {},
        startTime: new Date(),
        spans: [],
        generations: [],
      });
    }

    return {
      traceId,
      spanId: context.parent_span_id,
    };
  }

  /**
   * Start WORKFLOW_GEN span
   *
   * @param traceHandle - Trace handle from continueTrace
   * @param metadata - Span metadata
   * @returns Span ID
   */
  startWorkflowGenSpan(
    traceHandle: TraceHandle,
    metadata?: SpanMetadata
  ): string {
    const spanId = `span_wfgen_${Date.now()}`;

    if (this.enabled) {
      const trace = this.traces.get(traceHandle.traceId);
      if (trace) {
        trace.spans.push({
          id: spanId,
          name: 'WORKFLOW_GEN',
          parentId: traceHandle.spanId,
          metadata: {
            ...metadata,
            source: 'taskflowGeneratorAgent',
            phase: 3,
          },
          startTime: new Date(),
        });
      }
    }

    return spanId;
  }

  /**
   * Start task-specific span
   *
   * @param traceHandle - Trace handle
   * @param parentSpanId - Parent span ID (WORKFLOW_GEN span)
   * @param task - Task being processed
   * @returns Span ID
   */
  startTaskSpan(
    traceHandle: TraceHandle,
    parentSpanId: string,
    task: TaskGenerationRequest
  ): string {
    const spanId = `span_task_${task.task_id}_${Date.now()}`;

    if (this.enabled) {
      const trace = this.traces.get(traceHandle.traceId);
      if (trace) {
        trace.spans.push({
          id: spanId,
          name: `task_${task.task_id}`,
          parentId: parentSpanId,
          metadata: {
            taskId: task.task_id,
            taskMasterId: task.task_master_id,
            taskName: task.name,
          },
          startTime: new Date(),
        });
      }
    }

    return spanId;
  }

  /**
   * End a span
   *
   * @param traceHandle - Trace handle
   * @param spanId - Span ID to end
   * @param status - Span status
   * @param output - Span output
   */
  endSpan(
    traceHandle: TraceHandle,
    spanId: string,
    status: 'success' | 'error',
    output?: unknown
  ): void {
    if (!this.enabled) return;

    const trace = this.traces.get(traceHandle.traceId);
    if (trace) {
      const span = trace.spans.find((s) => s.id === spanId);
      if (span) {
        span.endTime = new Date();
        span.status = status;
        span.output = output;
      }
    }
  }

  /**
   * Record LLM generation
   *
   * @param traceHandle - Trace handle
   * @param spanId - Parent span ID
   * @param task - Task that triggered generation
   * @param llmResponse - LLM response data
   */
  recordGeneration(
    traceHandle: TraceHandle,
    spanId: string,
    task: TaskGenerationRequest,
    llmResponse: LLMResponse
  ): void {
    if (!this.enabled) return;

    const trace = this.traces.get(traceHandle.traceId);
    if (trace) {
      trace.generations.push({
        id: `gen_${task.task_id}_${Date.now()}`,
        spanId,
        name: `workflow_generator_${task.task_id}`,
        model: llmResponse.model,
        modelParameters: {
          temperature: llmResponse.temperature,
          maxTokens: llmResponse.maxTokens,
        },
        input: {
          system: llmResponse.systemPrompt,
          user: llmResponse.userPrompt,
        },
        output: llmResponse.content,
        usage: {
          promptTokens: llmResponse.usage.promptTokens,
          completionTokens: llmResponse.usage.completionTokens,
        },
        metadata: {
          latencyMs: llmResponse.latencyMs,
          taskId: task.task_id,
          taskMasterId: task.task_master_id,
        },
      });
    }
  }

  /**
   * Log error to trace
   *
   * @param traceHandle - Trace handle
   * @param spanId - Span ID where error occurred
   * @param error - Error to log
   */
  logError(
    traceHandle: TraceHandle,
    spanId: string,
    error: Error
  ): void {
    if (!this.enabled) return;

    const trace = this.traces.get(traceHandle.traceId);
    if (trace) {
      if (!trace.errors) {
        trace.errors = [];
      }
      trace.errors.push({
        spanId,
        message: error.message,
        stack: error.stack,
        timestamp: new Date(),
      });
    }
  }

  /**
   * Get trace URL (for response)
   *
   * @param traceHandle - Trace handle
   * @returns Langfuse trace URL or undefined
   */
  getTraceUrl(traceHandle: TraceHandle): string | undefined {
    if (!this.enabled || !this.config.baseUrl) {
      return undefined;
    }

    return `${this.config.baseUrl}/trace/${traceHandle.traceId}`;
  }

  /**
   * Flush traces to Langfuse
   * In production, this would send to Langfuse API
   */
  async flush(): Promise<void> {
    if (!this.enabled) return;

    // In production, this would send traces to Langfuse
    // For now, just clear local storage
    this.traces.clear();
  }

  /**
   * Check if tracing is enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Get trace data (for testing)
   */
  getTrace(traceId: string): TraceData | undefined {
    return this.traces.get(traceId);
  }
}

/**
 * Internal trace data structure
 */
interface TraceData {
  id: string;
  parentSpanId?: string;
  userId?: string;
  sessionId?: string;
  metadata: Record<string, unknown>;
  startTime: Date;
  spans: SpanData[];
  generations: GenerationData[];
  errors?: ErrorData[];
}

interface SpanData {
  id: string;
  name: string;
  parentId?: string;
  metadata?: Record<string, unknown>;
  startTime: Date;
  endTime?: Date;
  status?: string;
  output?: unknown;
}

interface GenerationData {
  id: string;
  spanId: string;
  name: string;
  model: string;
  modelParameters?: Record<string, unknown>;
  input?: Record<string, unknown>;
  output?: string;
  usage?: {
    promptTokens: number;
    completionTokens: number;
  };
  metadata?: Record<string, unknown>;
}

interface ErrorData {
  spanId: string;
  message: string;
  stack?: string;
  timestamp: Date;
}

/**
 * Factory function
 */
export function createLangfuseIntegration(
  config?: LangfuseIntegrationConfig
): LangfuseIntegration {
  return new LangfuseIntegration(config);
}
