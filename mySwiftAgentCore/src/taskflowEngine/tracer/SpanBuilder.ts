/**
 * SpanBuilder - Fluent API for building spans
 *
 * Issue #363: Builder pattern for creating trace spans
 */

import type { LangfuseTracer, SpanMetadata } from './LangfuseTracer.js';

/**
 * SpanBuilder - Fluent builder for spans
 *
 * Features:
 * - Fluent API for span creation
 * - Automatic duration calculation
 * - Error handling integration
 */
export class SpanBuilder {
  private readonly tracer: LangfuseTracer;
  private readonly traceId: string;
  private spanId: string | null = null;
  private stepId: string = '';
  private stepName: string = '';
  private stepType: string = '';
  private metadata: SpanMetadata = {};
  private startTime: Date | null = null;

  constructor(tracer: LangfuseTracer, traceId: string) {
    this.tracer = tracer;
    this.traceId = traceId;
  }

  /**
   * Set step ID
   */
  withStepId(stepId: string): this {
    this.stepId = stepId;
    return this;
  }

  /**
   * Set step name
   */
  withStepName(stepName: string): this {
    this.stepName = stepName;
    return this;
  }

  /**
   * Set step type
   */
  withStepType(stepType: string): this {
    this.stepType = stepType;
    return this;
  }

  /**
   * Add metadata
   */
  withMetadata(metadata: SpanMetadata): this {
    this.metadata = { ...this.metadata, ...metadata };
    return this;
  }

  /**
   * Start the span
   */
  start(): this {
    this.startTime = new Date();
    this.spanId = this.tracer.startStepSpan(
      this.traceId,
      this.stepId,
      this.stepName,
      this.stepType,
      this.metadata
    );
    return this;
  }

  /**
   * End the span with success
   */
  success(output?: unknown): void {
    if (!this.spanId) return;

    const endTime = new Date();
    this.tracer.endStepSpan(this.traceId, this.spanId, {
      stepId: this.stepId,
      stepName: this.stepName,
      status: 'success',
      output,
      startTime: this.startTime || endTime,
      endTime,
      durationMs: endTime.getTime() - (this.startTime?.getTime() || endTime.getTime()),
    });
  }

  /**
   * End the span with failure
   */
  failure(error: Error | string, metadata?: Record<string, unknown>): void {
    if (!this.spanId) return;

    const endTime = new Date();
    const errorMessage = error instanceof Error ? error.message : error;

    this.tracer.logError(this.traceId, this.spanId, error, metadata);
    this.tracer.endStepSpan(this.traceId, this.spanId, {
      stepId: this.stepId,
      stepName: this.stepName,
      status: 'failed',
      error: {
        stepId: this.stepId,
        stepName: this.stepName,
        errorCode: 'EXECUTION_ERROR',
        errorMessage,
        timestamp: endTime,
        recoverable: false,
      },
      startTime: this.startTime || endTime,
      endTime,
      durationMs: endTime.getTime() - (this.startTime?.getTime() || endTime.getTime()),
    });
  }

  /**
   * Get span ID
   */
  getSpanId(): string | null {
    return this.spanId;
  }

  /**
   * Get trace ID
   */
  getTraceId(): string {
    return this.traceId;
  }
}

/**
 * Factory function
 */
export function createSpanBuilder(
  tracer: LangfuseTracer,
  traceId: string
): SpanBuilder {
  return new SpanBuilder(tracer, traceId);
}
