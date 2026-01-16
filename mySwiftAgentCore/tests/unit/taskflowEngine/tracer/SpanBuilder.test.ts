/**
 * SpanBuilder Unit Tests
 *
 * Issue #363: Fluent span builder for Langfuse tracing
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  SpanBuilder,
  createSpanBuilder,
} from '../../../../src/taskflowEngine/tracer/SpanBuilder.js';
import { LangfuseTracer } from '../../../../src/taskflowEngine/tracer/LangfuseTracer.js';

describe('SpanBuilder', () => {
  let tracer: LangfuseTracer;
  let traceId: string;
  let builder: SpanBuilder;

  beforeEach(() => {
    tracer = new LangfuseTracer({
      enabled: true,
      publicKey: 'test-pk',
      secretKey: 'test-sk',
    });
    traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
    builder = new SpanBuilder(tracer, traceId);
  });

  describe('fluent API', () => {
    it('should set step ID', () => {
      const result = builder.withStepId('step_1');

      expect(result).toBe(builder);
    });

    it('should set step name', () => {
      const result = builder.withStepName('Step 1');

      expect(result).toBe(builder);
    });

    it('should set step type', () => {
      const result = builder.withStepType('transform');

      expect(result).toBe(builder);
    });

    it('should add metadata', () => {
      const result = builder.withMetadata({ key: 'value' });

      expect(result).toBe(builder);
    });

    it('should chain multiple calls', () => {
      const result = builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .withMetadata({ extra: 'data' });

      expect(result).toBe(builder);
    });
  });

  describe('start', () => {
    it('should start span and return self', () => {
      const result = builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      expect(result).toBe(builder);
      expect(builder.getSpanId()).not.toBeNull();
    });

    it('should create span in tracer', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      const trace = tracer.getTrace(traceId) as { spans?: Array<unknown> };
      expect(trace.spans).toHaveLength(1);
    });
  });

  describe('success', () => {
    it('should end span with success status', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      builder.success({ result: 'data' });

      const trace = tracer.getTrace(traceId) as {
        spans?: Array<{ status?: string; output?: unknown }>;
      };
      expect(trace.spans?.[0].status).toBe('success');
      expect(trace.spans?.[0].output).toEqual({ result: 'data' });
    });

    it('should handle success without output', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      builder.success();

      const trace = tracer.getTrace(traceId) as {
        spans?: Array<{ status?: string }>;
      };
      expect(trace.spans?.[0].status).toBe('success');
    });
  });

  describe('failure', () => {
    it('should end span with failed status', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      builder.failure('Test error');

      const trace = tracer.getTrace(traceId) as {
        spans?: Array<{ status?: string; error?: unknown }>;
      };
      expect(trace.spans?.[0].status).toBe('failed');
      expect(trace.spans?.[0].error).toBeDefined();
    });

    it('should handle Error objects', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      builder.failure(new Error('Error object'));

      const trace = tracer.getTrace(traceId) as {
        spans?: Array<{ status?: string }>;
      };
      expect(trace.spans?.[0].status).toBe('failed');
    });

    it('should log error to tracer', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      builder.failure('Error message', { context: 'test' });

      const trace = tracer.getTrace(traceId) as {
        errors?: Array<{ message: string }>;
      };
      expect(trace.errors).toHaveLength(1);
    });
  });

  describe('getSpanId', () => {
    it('should return null before start', () => {
      expect(builder.getSpanId()).toBeNull();
    });

    it('should return span ID after start', () => {
      builder
        .withStepId('step_1')
        .withStepName('Step 1')
        .withStepType('transform')
        .start();

      expect(builder.getSpanId()).not.toBeNull();
      expect(builder.getSpanId()).toMatch(/^span_step_1_/);
    });
  });

  describe('getTraceId', () => {
    it('should return trace ID', () => {
      expect(builder.getTraceId()).toBe(traceId);
    });
  });
});

describe('createSpanBuilder factory', () => {
  it('should create a SpanBuilder instance', () => {
    const tracer = new LangfuseTracer({
      enabled: true,
      publicKey: 'pk',
      secretKey: 'sk',
    });
    const traceId = tracer.startWorkflowTrace('wf_test', 'Test');

    const builder = createSpanBuilder(tracer, traceId);

    expect(builder).toBeInstanceOf(SpanBuilder);
  });
});
