/**
 * MSW Mock Handlers
 *
 * Issue #379: HTTP mock handlers for E2E testing
 *
 * Provides mock responses for:
 * - OpenAI LLM API
 * - External REST APIs
 */

import { http, HttpResponse } from 'msw';

/**
 * Mock LLM response content
 */
export const MOCK_LLM_CONTENT = 'Mocked summary of search results';

/**
 * Mock LLM response with usage stats
 */
export const MOCK_LLM_RESPONSE = {
  id: 'chatcmpl-mock-123',
  object: 'chat.completion',
  created: Date.now(),
  model: 'gpt-4o-mini',
  choices: [
    {
      index: 0,
      message: {
        role: 'assistant',
        content: MOCK_LLM_CONTENT,
      },
      finish_reason: 'stop',
    },
  ],
  usage: {
    prompt_tokens: 100,
    completion_tokens: 50,
    total_tokens: 150,
  },
};

/**
 * Mock external API response
 */
export const MOCK_API_RESPONSE = {
  success: true,
  timestamp: new Date().toISOString(),
  data: {
    processed: true,
    message: 'Mock API processed successfully',
  },
};

/**
 * Track intercepted requests
 */
export interface InterceptedRequest {
  url: string;
  method: string;
  body?: unknown;
  headers: Record<string, string>;
  timestamp: Date;
}

/**
 * Request tracker for assertions
 */
export class RequestTracker {
  private requests: InterceptedRequest[] = [];

  track(request: InterceptedRequest): void {
    this.requests.push(request);
  }

  getRequests(): InterceptedRequest[] {
    return [...this.requests];
  }

  getRequestsByUrl(urlPattern: string): InterceptedRequest[] {
    return this.requests.filter((r) => r.url.includes(urlPattern));
  }

  getRequestsByMethod(method: string): InterceptedRequest[] {
    return this.requests.filter((r) => r.method === method);
  }

  clear(): void {
    this.requests = [];
  }

  hasRequests(): boolean {
    return this.requests.length > 0;
  }

  getRequestCount(): number {
    return this.requests.length;
  }
}

/**
 * Global request tracker
 */
export const requestTracker = new RequestTracker();

/**
 * Create LLM API mock handler (OpenAI format)
 */
export function createLlmMockHandler(customResponse?: Partial<typeof MOCK_LLM_RESPONSE>) {
  return http.post('https://api.openai.com/v1/chat/completions', async ({ request }) => {
    // Track request
    const body = await request.clone().json();
    requestTracker.track({
      url: request.url,
      method: 'POST',
      body,
      headers: Object.fromEntries(request.headers.entries()),
      timestamp: new Date(),
    });

    const response = {
      ...MOCK_LLM_RESPONSE,
      ...customResponse,
      created: Date.now(),
    };

    return HttpResponse.json(response);
  });
}

/**
 * Create mock handler for any LLM endpoint
 */
export function createGenericLlmMockHandler(urlPattern: string) {
  return http.post(urlPattern, async ({ request }) => {
    const body = await request.clone().json();
    requestTracker.track({
      url: request.url,
      method: 'POST',
      body,
      headers: Object.fromEntries(request.headers.entries()),
      timestamp: new Date(),
    });

    return HttpResponse.json(MOCK_LLM_RESPONSE);
  });
}

/**
 * Create external API mock handler
 */
export function createApiMockHandler(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'POST',
  customResponse?: unknown
) {
  const handlerMethod = method === 'GET' ? http.get
    : method === 'PUT' ? http.put
    : method === 'DELETE' ? http.delete
    : http.post;

  return handlerMethod(url, async ({ request }) => {
    let body: unknown = null;
    if (method !== 'GET') {
      try {
        body = await request.clone().json();
      } catch {
        body = await request.clone().text();
      }
    }

    requestTracker.track({
      url: request.url,
      method,
      body,
      headers: Object.fromEntries(request.headers.entries()),
      timestamp: new Date(),
    });

    const response = customResponse ?? {
      ...MOCK_API_RESPONSE,
      received: body,
    };

    return HttpResponse.json(response);
  });
}

/**
 * Create error mock handler
 */
export function createErrorMockHandler(
  url: string,
  statusCode: number,
  errorMessage: string
) {
  return http.all(url, async ({ request }) => {
    requestTracker.track({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      timestamp: new Date(),
    });

    return HttpResponse.json(
      {
        error: {
          message: errorMessage,
          type: 'mock_error',
          code: `ERROR_${statusCode}`,
        },
      },
      { status: statusCode }
    );
  });
}

/**
 * Create timeout mock handler
 */
export function createTimeoutMockHandler(url: string, delayMs: number) {
  return http.all(url, async ({ request }) => {
    requestTracker.track({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      timestamp: new Date(),
    });

    await new Promise((resolve) => setTimeout(resolve, delayMs));

    return HttpResponse.json({ success: true, delayed: true });
  });
}

/**
 * Default handlers for E2E tests
 */
export const handlers = [
  // OpenAI LLM API mock
  createLlmMockHandler(),

  // Mock output service
  createApiMockHandler('http://mock-output-service', 'POST'),
  createApiMockHandler('http://mock-output-service/*', 'POST'),

  // Mock external APIs
  createApiMockHandler('http://mock-api/*', 'GET'),
  createApiMockHandler('http://mock-api/*', 'POST'),
];

/**
 * Reset request tracker
 */
export function resetRequestTracker(): void {
  requestTracker.clear();
}

/**
 * Get all tracked requests
 */
export function getTrackedRequests(): InterceptedRequest[] {
  return requestTracker.getRequests();
}

/**
 * Check if any LLM API calls were made
 */
export function wasLlmApiCalled(): boolean {
  return requestTracker.getRequestsByUrl('openai.com').length > 0 ||
    requestTracker.getRequestsByUrl('/v1/chat/completions').length > 0;
}

/**
 * Get LLM API calls
 */
export function getLlmApiCalls(): InterceptedRequest[] {
  return requestTracker.getRequests().filter(
    (r) => r.url.includes('openai.com') || r.url.includes('/v1/chat/completions')
  );
}
