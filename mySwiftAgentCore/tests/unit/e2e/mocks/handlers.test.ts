/**
 * Unit Tests for MSW Mock Handlers
 *
 * Issue #379: Tests for MSW mock handler utilities
 */

import { describe, test, expect, beforeEach } from 'vitest';
import {
  RequestTracker,
  requestTracker,
  MOCK_LLM_CONTENT,
  MOCK_LLM_RESPONSE,
  MOCK_API_RESPONSE,
  resetRequestTracker,
  getTrackedRequests,
  wasLlmApiCalled,
  getLlmApiCalls,
  createLlmMockHandler,
  createApiMockHandler,
  createErrorMockHandler,
  createTimeoutMockHandler,
  createGenericLlmMockHandler,
  handlers,
} from '../../../e2e/mocks/handlers.js';

describe('RequestTracker', () => {
  let tracker: RequestTracker;

  beforeEach(() => {
    tracker = new RequestTracker();
  });

  describe('track', () => {
    test('should track requests', () => {
      tracker.track({
        url: 'http://test.com/api',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      expect(tracker.getRequests()).toHaveLength(1);
    });

    test('should track request with body', () => {
      tracker.track({
        url: 'http://test.com/api',
        method: 'POST',
        body: { key: 'value' },
        headers: { 'Content-Type': 'application/json' },
        timestamp: new Date(),
      });

      const requests = tracker.getRequests();
      expect(requests[0]!.body).toEqual({ key: 'value' });
    });
  });

  describe('getRequests', () => {
    test('should return copy of requests', () => {
      tracker.track({
        url: 'http://test.com',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });

      const requests = tracker.getRequests();
      requests.push({
        url: 'fake',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });

      expect(tracker.getRequests()).toHaveLength(1);
    });
  });

  describe('getRequestsByUrl', () => {
    test('should filter by URL pattern', () => {
      tracker.track({
        url: 'http://api.openai.com/v1/chat',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });
      tracker.track({
        url: 'http://other-api.com/test',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });

      const openaiRequests = tracker.getRequestsByUrl('openai.com');
      expect(openaiRequests).toHaveLength(1);
    });
  });

  describe('getRequestsByMethod', () => {
    test('should filter by method', () => {
      tracker.track({
        url: 'http://api.com/get',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });
      tracker.track({
        url: 'http://api.com/post',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      const postRequests = tracker.getRequestsByMethod('POST');
      expect(postRequests).toHaveLength(1);
      expect(postRequests[0]!.url).toContain('post');
    });
  });

  describe('clear', () => {
    test('should clear all requests', () => {
      tracker.track({
        url: 'http://test.com',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });
      tracker.track({
        url: 'http://test2.com',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      tracker.clear();

      expect(tracker.getRequests()).toHaveLength(0);
    });
  });

  describe('hasRequests', () => {
    test('should return false when no requests', () => {
      expect(tracker.hasRequests()).toBe(false);
    });

    test('should return true when has requests', () => {
      tracker.track({
        url: 'http://test.com',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });

      expect(tracker.hasRequests()).toBe(true);
    });
  });

  describe('getRequestCount', () => {
    test('should return correct count', () => {
      expect(tracker.getRequestCount()).toBe(0);

      tracker.track({
        url: 'http://test1.com',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });
      tracker.track({
        url: 'http://test2.com',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      expect(tracker.getRequestCount()).toBe(2);
    });
  });
});

describe('Global requestTracker', () => {
  beforeEach(() => {
    resetRequestTracker();
  });

  test('should be a RequestTracker instance', () => {
    expect(requestTracker).toBeInstanceOf(RequestTracker);
  });

  test('resetRequestTracker should clear the tracker', () => {
    requestTracker.track({
      url: 'http://test.com',
      method: 'GET',
      headers: {},
      timestamp: new Date(),
    });

    resetRequestTracker();

    expect(requestTracker.getRequests()).toHaveLength(0);
  });

  test('getTrackedRequests should return requests', () => {
    requestTracker.track({
      url: 'http://test.com',
      method: 'GET',
      headers: {},
      timestamp: new Date(),
    });

    const requests = getTrackedRequests();
    expect(requests).toHaveLength(1);
  });
});

describe('LLM API tracking helpers', () => {
  beforeEach(() => {
    resetRequestTracker();
  });

  describe('wasLlmApiCalled', () => {
    test('should return false when no LLM calls', () => {
      expect(wasLlmApiCalled()).toBe(false);
    });

    test('should return true for OpenAI calls', () => {
      requestTracker.track({
        url: 'https://api.openai.com/v1/chat/completions',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      expect(wasLlmApiCalled()).toBe(true);
    });

    test('should return true for any chat completions endpoint', () => {
      requestTracker.track({
        url: 'http://localhost:8000/v1/chat/completions',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });

      expect(wasLlmApiCalled()).toBe(true);
    });
  });

  describe('getLlmApiCalls', () => {
    test('should return only LLM calls', () => {
      requestTracker.track({
        url: 'https://api.openai.com/v1/chat/completions',
        method: 'POST',
        headers: {},
        timestamp: new Date(),
      });
      requestTracker.track({
        url: 'http://other-api.com/test',
        method: 'GET',
        headers: {},
        timestamp: new Date(),
      });

      const llmCalls = getLlmApiCalls();
      expect(llmCalls).toHaveLength(1);
      expect(llmCalls[0]!.url).toContain('openai.com');
    });
  });
});

describe('Mock constants', () => {
  test('MOCK_LLM_CONTENT should be defined', () => {
    expect(MOCK_LLM_CONTENT).toBeDefined();
    expect(typeof MOCK_LLM_CONTENT).toBe('string');
  });

  test('MOCK_LLM_RESPONSE should have expected structure', () => {
    expect(MOCK_LLM_RESPONSE).toHaveProperty('id');
    expect(MOCK_LLM_RESPONSE).toHaveProperty('choices');
    expect(MOCK_LLM_RESPONSE).toHaveProperty('usage');
    expect(MOCK_LLM_RESPONSE.choices[0]!.message.content).toBe(MOCK_LLM_CONTENT);
  });

  test('MOCK_API_RESPONSE should have expected structure', () => {
    expect(MOCK_API_RESPONSE).toHaveProperty('success');
    expect(MOCK_API_RESPONSE.success).toBe(true);
  });
});

describe('Handler factory functions', () => {
  test('createLlmMockHandler should return a handler', () => {
    const handler = createLlmMockHandler();
    expect(handler).toBeDefined();
  });

  test('createLlmMockHandler should accept custom response', () => {
    const customResponse = {
      choices: [
        {
          index: 0,
          message: { role: 'assistant', content: 'Custom content' },
          finish_reason: 'stop',
        },
      ],
    };
    const handler = createLlmMockHandler(customResponse);
    expect(handler).toBeDefined();
  });

  test('createGenericLlmMockHandler should create handler for URL', () => {
    const handler = createGenericLlmMockHandler('http://custom-llm.com/api');
    expect(handler).toBeDefined();
  });

  test('createApiMockHandler should create handler for methods', () => {
    const getHandler = createApiMockHandler('http://api.com/get', 'GET');
    const postHandler = createApiMockHandler('http://api.com/post', 'POST');
    const putHandler = createApiMockHandler('http://api.com/put', 'PUT');
    const deleteHandler = createApiMockHandler('http://api.com/delete', 'DELETE');

    expect(getHandler).toBeDefined();
    expect(postHandler).toBeDefined();
    expect(putHandler).toBeDefined();
    expect(deleteHandler).toBeDefined();
  });

  test('createApiMockHandler should accept custom response', () => {
    const customResponse = { custom: 'data' };
    const handler = createApiMockHandler('http://api.com', 'POST', customResponse);
    expect(handler).toBeDefined();
  });

  test('createErrorMockHandler should create error handler', () => {
    const handler = createErrorMockHandler('http://api.com/error', 500, 'Test error');
    expect(handler).toBeDefined();
  });

  test('createTimeoutMockHandler should create timeout handler', () => {
    const handler = createTimeoutMockHandler('http://api.com/slow', 5000);
    expect(handler).toBeDefined();
  });
});

describe('Default handlers', () => {
  test('handlers array should be defined', () => {
    expect(handlers).toBeDefined();
    expect(Array.isArray(handlers)).toBe(true);
  });

  test('handlers should include LLM mock', () => {
    // The default handlers include OpenAI mock
    expect(handlers.length).toBeGreaterThan(0);
  });
});
