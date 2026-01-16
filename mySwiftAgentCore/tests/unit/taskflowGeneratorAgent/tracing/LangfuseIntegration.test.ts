/**
 * LangfuseIntegration Unit Tests
 *
 * Issue #364: Langfuse tracing integration tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  LangfuseIntegration,
  createLangfuseIntegration,
  type LangfuseIntegrationConfig,
} from '../../../../src/taskflowGeneratorAgent/tracing/LangfuseIntegration.js';
import type { TraceContext, TaskGenerationRequest } from '../../../../src/taskflowGeneratorAgent/types/generator.js';
import type { LLMResponse } from '../../../../src/taskflowGeneratorAgent/types/llm.js';

describe('LangfuseIntegration', () => {
  describe('constructor', () => {
    it('should create integration with default config', () => {
      const integration = new LangfuseIntegration();

      expect(integration.isEnabled()).toBe(false);
    });

    it('should enable integration when keys are provided', () => {
      const integration = new LangfuseIntegration({
        enabled: true,
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });

      expect(integration.isEnabled()).toBe(true);
    });

    it('should disable integration when enabled is false', () => {
      const integration = new LangfuseIntegration({
        enabled: false,
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });

      expect(integration.isEnabled()).toBe(false);
    });

    it('should disable integration when keys are missing', () => {
      const integration = new LangfuseIntegration({
        enabled: true,
        publicKey: 'pk_test',
        // secretKey missing
      });

      expect(integration.isEnabled()).toBe(false);
    });
  });

  describe('continueTrace', () => {
    it('should return trace handle with provided trace_id', () => {
      const integration = new LangfuseIntegration();
      const context: TraceContext = {
        trace_id: 'trace_123',
        parent_span_id: 'span_456',
      };

      const handle = integration.continueTrace(context);

      expect(handle.traceId).toBe('trace_123');
      expect(handle.spanId).toBe('span_456');
    });

    it('should generate trace_id when not provided', () => {
      const integration = new LangfuseIntegration();
      const context: TraceContext = {};

      const handle = integration.continueTrace(context);

      expect(handle.traceId).toMatch(/^trace_\d+$/);
    });

    it('should store trace data when enabled', () => {
      const integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });

      const context: TraceContext = {
        trace_id: 'trace_123',
        user_id: 'user_1',
        session_id: 'session_1',
        metadata: { key: 'value' },
      };

      const handle = integration.continueTrace(context);
      const trace = integration.getTrace(handle.traceId);

      expect(trace).toBeDefined();
      expect(trace?.userId).toBe('user_1');
      expect(trace?.sessionId).toBe('session_1');
      expect(trace?.metadata.key).toBe('value');
    });
  });

  describe('startWorkflowGenSpan', () => {
    let integration: LangfuseIntegration;
    let traceHandle: ReturnType<LangfuseIntegration['continueTrace']>;

    beforeEach(() => {
      integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });
      traceHandle = integration.continueTrace({ trace_id: 'trace_123' });
    });

    it('should return span ID', () => {
      const spanId = integration.startWorkflowGenSpan(traceHandle);

      expect(spanId).toMatch(/^span_wfgen_\d+$/);
    });

    it('should store span with metadata', () => {
      const spanId = integration.startWorkflowGenSpan(traceHandle, {
        taskCount: 5,
      });

      const trace = integration.getTrace(traceHandle.traceId);
      const span = trace?.spans.find((s) => s.id === spanId);

      expect(span).toBeDefined();
      expect(span?.name).toBe('WORKFLOW_GEN');
      expect(span?.metadata?.taskCount).toBe(5);
      expect(span?.metadata?.source).toBe('taskflowGeneratorAgent');
    });
  });

  describe('startTaskSpan', () => {
    let integration: LangfuseIntegration;
    let traceHandle: ReturnType<LangfuseIntegration['continueTrace']>;
    let parentSpanId: string;

    beforeEach(() => {
      integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });
      traceHandle = integration.continueTrace({ trace_id: 'trace_123' });
      parentSpanId = integration.startWorkflowGenSpan(traceHandle);
    });

    it('should return span ID with task ID', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_1',
        description: 'Test task',
        input_schema: {},
        output_schema: {},
      };

      const spanId = integration.startTaskSpan(traceHandle, parentSpanId, task);

      expect(spanId).toContain('task_1');
    });

    it('should store task metadata', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_1',
        task_master_id: 'tm_1',
        name: 'Test Task',
        description: 'Test task',
        input_schema: {},
        output_schema: {},
      };

      const spanId = integration.startTaskSpan(traceHandle, parentSpanId, task);
      const trace = integration.getTrace(traceHandle.traceId);
      const span = trace?.spans.find((s) => s.id === spanId);

      expect(span?.metadata?.taskId).toBe('task_1');
      expect(span?.metadata?.taskMasterId).toBe('tm_1');
      expect(span?.metadata?.taskName).toBe('Test Task');
    });
  });

  describe('endSpan', () => {
    let integration: LangfuseIntegration;
    let traceHandle: ReturnType<LangfuseIntegration['continueTrace']>;
    let spanId: string;

    beforeEach(() => {
      integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });
      traceHandle = integration.continueTrace({ trace_id: 'trace_123' });
      spanId = integration.startWorkflowGenSpan(traceHandle);
    });

    it('should set span status to success', () => {
      integration.endSpan(traceHandle, spanId, 'success', { result: 'ok' });

      const trace = integration.getTrace(traceHandle.traceId);
      const span = trace?.spans.find((s) => s.id === spanId);

      expect(span?.status).toBe('success');
      expect(span?.output).toEqual({ result: 'ok' });
      expect(span?.endTime).toBeDefined();
    });

    it('should set span status to error', () => {
      integration.endSpan(traceHandle, spanId, 'error', { error: 'failed' });

      const trace = integration.getTrace(traceHandle.traceId);
      const span = trace?.spans.find((s) => s.id === spanId);

      expect(span?.status).toBe('error');
    });

    it('should do nothing when disabled', () => {
      const disabledIntegration = new LangfuseIntegration();
      const handle = disabledIntegration.continueTrace({ trace_id: 'trace_123' });

      // Should not throw
      disabledIntegration.endSpan(handle, 'span_123', 'success');
    });
  });

  describe('recordGeneration', () => {
    let integration: LangfuseIntegration;
    let traceHandle: ReturnType<LangfuseIntegration['continueTrace']>;
    let spanId: string;

    beforeEach(() => {
      integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });
      traceHandle = integration.continueTrace({ trace_id: 'trace_123' });
      spanId = integration.startWorkflowGenSpan(traceHandle);
    });

    it('should record LLM generation', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_1',
        description: 'Test task',
        input_schema: {},
        output_schema: {},
      };

      const llmResponse: LLMResponse = {
        content: '{"workflow_name": "test"}',
        model: 'claude-sonnet-4-20250514',
        usage: {
          promptTokens: 100,
          completionTokens: 50,
          totalTokens: 150,
        },
        latencyMs: 500,
        systemPrompt: 'You are an assistant',
        userPrompt: 'Create a workflow',
      };

      integration.recordGeneration(traceHandle, spanId, task, llmResponse);

      const trace = integration.getTrace(traceHandle.traceId);

      expect(trace?.generations).toHaveLength(1);
      expect(trace?.generations[0]?.model).toBe('claude-sonnet-4-20250514');
      expect(trace?.generations[0]?.usage?.promptTokens).toBe(100);
      expect(trace?.generations[0]?.metadata?.latencyMs).toBe(500);
    });

    it('should do nothing when disabled', () => {
      const disabledIntegration = new LangfuseIntegration();
      const handle = disabledIntegration.continueTrace({ trace_id: 'trace_123' });

      const task: TaskGenerationRequest = {
        task_id: 'task_1',
        description: 'Test',
        input_schema: {},
        output_schema: {},
      };

      const llmResponse: LLMResponse = {
        content: '{}',
        model: 'test',
        usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
        latencyMs: 0,
      };

      // Should not throw
      disabledIntegration.recordGeneration(handle, 'span_123', task, llmResponse);
    });
  });

  describe('logError', () => {
    let integration: LangfuseIntegration;
    let traceHandle: ReturnType<LangfuseIntegration['continueTrace']>;
    let spanId: string;

    beforeEach(() => {
      integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });
      traceHandle = integration.continueTrace({ trace_id: 'trace_123' });
      spanId = integration.startWorkflowGenSpan(traceHandle);
    });

    it('should log error to trace', () => {
      const error = new Error('Test error');

      integration.logError(traceHandle, spanId, error);

      const trace = integration.getTrace(traceHandle.traceId);

      expect(trace?.errors).toHaveLength(1);
      expect(trace?.errors?.[0]?.message).toBe('Test error');
      expect(trace?.errors?.[0]?.spanId).toBe(spanId);
    });

    it('should append multiple errors', () => {
      integration.logError(traceHandle, spanId, new Error('Error 1'));
      integration.logError(traceHandle, spanId, new Error('Error 2'));

      const trace = integration.getTrace(traceHandle.traceId);

      expect(trace?.errors).toHaveLength(2);
    });

    it('should do nothing when disabled', () => {
      const disabledIntegration = new LangfuseIntegration();
      const handle = disabledIntegration.continueTrace({ trace_id: 'trace_123' });

      // Should not throw
      disabledIntegration.logError(handle, 'span_123', new Error('Test'));
    });
  });

  describe('getTraceUrl', () => {
    it('should return URL when enabled and baseUrl is set', () => {
      const integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
        baseUrl: 'https://langfuse.example.com',
      });

      const handle = integration.continueTrace({ trace_id: 'trace_123' });
      const url = integration.getTraceUrl(handle);

      expect(url).toBe('https://langfuse.example.com/trace/trace_123');
    });

    it('should return undefined when disabled', () => {
      const integration = new LangfuseIntegration();
      const handle = integration.continueTrace({ trace_id: 'trace_123' });

      const url = integration.getTraceUrl(handle);

      expect(url).toBeUndefined();
    });

    it('should return undefined when baseUrl is not set', () => {
      const integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
        // baseUrl not set
      });

      const handle = integration.continueTrace({ trace_id: 'trace_123' });
      const url = integration.getTraceUrl(handle);

      expect(url).toBeUndefined();
    });
  });

  describe('flush', () => {
    it('should clear traces', async () => {
      const integration = new LangfuseIntegration({
        publicKey: 'pk_test',
        secretKey: 'sk_test',
      });

      integration.continueTrace({ trace_id: 'trace_123' });
      expect(integration.getTrace('trace_123')).toBeDefined();

      await integration.flush();

      expect(integration.getTrace('trace_123')).toBeUndefined();
    });

    it('should do nothing when disabled', async () => {
      const integration = new LangfuseIntegration();

      // Should not throw
      await integration.flush();
    });
  });
});

describe('createLangfuseIntegration', () => {
  it('should create integration with config', () => {
    const integration = createLangfuseIntegration({
      publicKey: 'pk_test',
      secretKey: 'sk_test',
    });

    expect(integration).toBeInstanceOf(LangfuseIntegration);
    expect(integration.isEnabled()).toBe(true);
  });

  it('should create integration without config', () => {
    const integration = createLangfuseIntegration();

    expect(integration).toBeInstanceOf(LangfuseIntegration);
    expect(integration.isEnabled()).toBe(false);
  });
});
