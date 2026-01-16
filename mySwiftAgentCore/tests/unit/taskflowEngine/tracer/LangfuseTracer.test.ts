/**
 * LangfuseTracer Unit Tests
 *
 * Issue #363: Langfuse tracing integration
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  LangfuseTracer,
  createLangfuseTracer,
} from '../../../../src/taskflowEngine/tracer/LangfuseTracer.js';
import type { WorkflowExecutionResult, StepResult } from '../../../../src/shared/types/workflow.types.js';

describe('LangfuseTracer', () => {
  describe('with enabled config', () => {
    let tracer: LangfuseTracer;

    beforeEach(() => {
      tracer = new LangfuseTracer({
        enabled: true,
        publicKey: 'test-public-key',
        secretKey: 'test-secret-key',
      });
    });

    describe('isEnabled', () => {
      it('should return true when configured with keys', () => {
        expect(tracer.isEnabled()).toBe(true);
      });
    });

    describe('startWorkflowTrace', () => {
      it('should create a trace and return trace ID', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');

        expect(traceId).toMatch(/^trace_wf_test_/);
        expect(tracer.getTrace(traceId)).toBeDefined();
      });

      it('should include metadata in trace', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow', {
          userId: 'user_123',
        });

        const trace = tracer.getTrace(traceId) as { metadata?: Record<string, unknown> };
        expect(trace.metadata?.userId).toBe('user_123');
      });
    });

    describe('endWorkflowTrace', () => {
      it('should update trace with result', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');

        const result: WorkflowExecutionResult = {
          workflowId: 'wf_test',
          workflowName: 'Test Workflow',
          status: 'success',
          stepResults: [],
          errors: [],
          recoveryActions: [],
          startTime: new Date(),
          endTime: new Date(),
          durationMs: 100,
        };

        tracer.endWorkflowTrace(traceId, result);

        const trace = tracer.getTrace(traceId) as { status?: string; endTime?: Date };
        expect(trace.status).toBe('success');
        expect(trace.endTime).toBeDefined();
      });
    });

    describe('startStepSpan', () => {
      it('should create a span within a trace', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
        const spanId = tracer.startStepSpan(traceId, 'step_1', 'Step 1', 'transform');

        expect(spanId).toMatch(/^span_step_1_/);

        const trace = tracer.getTrace(traceId) as { spans?: Array<{ id: string }> };
        expect(trace.spans?.some((s) => s.id === spanId)).toBe(true);
      });

      it('should include step metadata', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
        tracer.startStepSpan(traceId, 'step_1', 'Step 1', 'api_rest', {
          url: 'http://example.com',
        });

        const trace = tracer.getTrace(traceId) as {
          spans?: Array<{ metadata?: Record<string, unknown> }>;
        };
        expect(trace.spans?.[0]?.metadata?.url).toBe('http://example.com');
      });
    });

    describe('endStepSpan', () => {
      it('should update span with result', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
        const spanId = tracer.startStepSpan(traceId, 'step_1', 'Step 1', 'transform');

        const stepResult: StepResult = {
          stepId: 'step_1',
          stepName: 'Step 1',
          status: 'success',
          output: { data: 'result' },
          startTime: new Date(),
          endTime: new Date(),
          durationMs: 50,
        };

        tracer.endStepSpan(traceId, spanId, stepResult);

        const trace = tracer.getTrace(traceId) as {
          spans?: Array<{ id: string; status?: string; output?: unknown }>;
        };
        const span = trace.spans?.find((s) => s.id === spanId);
        expect(span?.status).toBe('success');
        expect(span?.output).toEqual({ data: 'result' });
      });

      it('should record error information', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
        const spanId = tracer.startStepSpan(traceId, 'step_1', 'Step 1', 'api_rest');

        const stepResult: StepResult = {
          stepId: 'step_1',
          stepName: 'Step 1',
          status: 'failed',
          error: {
            stepId: 'step_1',
            stepName: 'Step 1',
            errorCode: 'HTTP_ERROR',
            errorMessage: 'Request failed',
            timestamp: new Date(),
            recoverable: true,
          },
          startTime: new Date(),
          endTime: new Date(),
          durationMs: 50,
        };

        tracer.endStepSpan(traceId, spanId, stepResult);

        const trace = tracer.getTrace(traceId) as {
          spans?: Array<{ id: string; error?: unknown }>;
        };
        const span = trace.spans?.find((s) => s.id === spanId);
        expect(span?.error).toBeDefined();
      });
    });

    describe('logError', () => {
      it('should log error to trace', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');
        const spanId = tracer.startStepSpan(traceId, 'step_1', 'Step 1', 'transform');

        tracer.logError(traceId, spanId, 'Test error message', { context: 'test' });

        const trace = tracer.getTrace(traceId) as {
          errors?: Array<{ message: string; spanId?: string }>;
        };
        expect(trace.errors).toHaveLength(1);
        expect(trace.errors?.[0].message).toBe('Test error message');
        expect(trace.errors?.[0].spanId).toBe(spanId);
      });

      it('should handle Error objects', () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');

        tracer.logError(traceId, undefined, new Error('Error object'));

        const trace = tracer.getTrace(traceId) as {
          errors?: Array<{ message: string }>;
        };
        expect(trace.errors?.[0].message).toBe('Error object');
      });
    });

    describe('flush', () => {
      it('should clear traces', async () => {
        const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');

        await tracer.flush();

        expect(tracer.getTrace(traceId)).toBeUndefined();
      });
    });
  });

  describe('with disabled config', () => {
    let tracer: LangfuseTracer;

    beforeEach(() => {
      tracer = new LangfuseTracer({ enabled: false });
    });

    it('should return false for isEnabled', () => {
      expect(tracer.isEnabled()).toBe(false);
    });

    it('should still return trace ID but not store trace', () => {
      const traceId = tracer.startWorkflowTrace('wf_test', 'Test Workflow');

      expect(traceId).toBeDefined();
      expect(tracer.getTrace(traceId)).toBeUndefined();
    });
  });

  describe('without credentials', () => {
    let tracer: LangfuseTracer;

    beforeEach(() => {
      tracer = new LangfuseTracer({});
    });

    it('should be disabled without keys', () => {
      expect(tracer.isEnabled()).toBe(false);
    });
  });
});

describe('createLangfuseTracer factory', () => {
  it('should create a LangfuseTracer instance', () => {
    const tracer = createLangfuseTracer();
    expect(tracer).toBeInstanceOf(LangfuseTracer);
  });

  it('should accept config', () => {
    const tracer = createLangfuseTracer({
      enabled: true,
      publicKey: 'pk',
      secretKey: 'sk',
    });
    expect(tracer.isEnabled()).toBe(true);
  });
});
