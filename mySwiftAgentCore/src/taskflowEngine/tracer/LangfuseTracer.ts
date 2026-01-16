/**
 * LangfuseTracer - Langfuse integration for tracing
 *
 * Issue #363: Provides tracing for workflow execution
 */

import type { WorkflowExecutionResult, StepResult } from '../../shared/types/workflow.types.js';

/**
 * Tracer configuration
 */
export interface TracerConfig {
  enabled?: boolean;
  publicKey?: string;
  secretKey?: string;
  baseUrl?: string;
}

/**
 * Span metadata
 */
export interface SpanMetadata {
  workflowId?: string;
  workflowName?: string;
  stepId?: string;
  stepName?: string;
  [key: string]: unknown;
}

/**
 * LangfuseTracer - Traces workflow execution
 *
 * Features:
 * - Workflow-level traces
 * - Step-level spans
 * - Error tracking
 * - Mock mode when credentials not available
 */
export class LangfuseTracer {
  private readonly config: TracerConfig;
  private readonly enabled: boolean;
  private traces: Map<string, unknown> = new Map();

  constructor(config: TracerConfig = {}) {
    this.config = config;
    this.enabled = config.enabled !== false &&
      !!(config.publicKey && config.secretKey);
  }

  /**
   * Start a workflow trace
   */
  startWorkflowTrace(
    workflowId: string,
    workflowName: string,
    metadata?: SpanMetadata
  ): string {
    const traceId = `trace_${workflowId}_${Date.now()}`;

    if (this.enabled) {
      // In production, this would create a Langfuse trace
      // For now, we store locally for testing
      this.traces.set(traceId, {
        id: traceId,
        name: workflowName,
        metadata,
        startTime: new Date(),
        spans: [],
      });
    }

    return traceId;
  }

  /**
   * End a workflow trace
   */
  endWorkflowTrace(
    traceId: string,
    result: WorkflowExecutionResult
  ): void {
    if (!this.enabled) return;

    const trace = this.traces.get(traceId);
    if (trace) {
      Object.assign(trace, {
        endTime: new Date(),
        status: result.status,
        output: result.metadata,
      });
    }
  }

  /**
   * Start a step span
   */
  startStepSpan(
    traceId: string,
    stepId: string,
    stepName: string,
    stepType: string,
    metadata?: SpanMetadata
  ): string {
    const spanId = `span_${stepId}_${Date.now()}`;

    if (this.enabled) {
      const trace = this.traces.get(traceId) as {
        spans?: Array<unknown>;
      } | undefined;

      if (trace && trace.spans) {
        trace.spans.push({
          id: spanId,
          name: stepName,
          type: stepType,
          metadata,
          startTime: new Date(),
        });
      }
    }

    return spanId;
  }

  /**
   * End a step span
   */
  endStepSpan(
    traceId: string,
    spanId: string,
    result: StepResult
  ): void {
    if (!this.enabled) return;

    const trace = this.traces.get(traceId) as {
      spans?: Array<{ id: string; endTime?: Date; status?: string; output?: unknown; error?: unknown }>;
    } | undefined;

    if (trace && trace.spans) {
      const span = trace.spans.find((s) => s.id === spanId);
      if (span) {
        span.endTime = new Date();
        span.status = result.status;
        span.output = result.output;
        if (result.error) {
          span.error = result.error;
        }
      }
    }
  }

  /**
   * Log error
   */
  logError(
    traceId: string,
    spanId: string | undefined,
    error: Error | string,
    metadata?: Record<string, unknown>
  ): void {
    if (!this.enabled) return;

    const message = error instanceof Error ? error.message : error;
    const trace = this.traces.get(traceId) as {
      errors?: Array<unknown>;
    } | undefined;

    if (trace) {
      if (!trace.errors) {
        trace.errors = [];
      }
      trace.errors.push({
        spanId,
        message,
        metadata,
        timestamp: new Date(),
      });
    }
  }

  /**
   * Get trace (for testing)
   */
  getTrace(traceId: string): unknown {
    return this.traces.get(traceId);
  }

  /**
   * Check if tracing is enabled
   */
  isEnabled(): boolean {
    return this.enabled;
  }

  /**
   * Get tracer configuration
   */
  getConfig(): TracerConfig {
    return this.config;
  }

  /**
   * Flush traces (in production, this would send to Langfuse)
   */
  async flush(): Promise<void> {
    if (!this.enabled) return;

    // In production, this would send traces to Langfuse
    // For now, we just clear local traces
    this.traces.clear();
  }
}

/**
 * Factory function
 */
export function createLangfuseTracer(config?: TracerConfig): LangfuseTracer {
  return new LangfuseTracer(config);
}
