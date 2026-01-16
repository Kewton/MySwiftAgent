/**
 * TaskFlowGeneratorClient - TypeScript SDK for generator API
 *
 * Issue #364: Client SDK for programmatic API access
 */

import {
  BatchGenerationResponseSchema,
  GenerationStatusResponseSchema,
  type BatchGenerationRequest,
  type BatchGenerationResponse,
  type GenerationStatusResponse,
} from '../types/generator.js';

/**
 * Client Configuration
 */
export interface TaskFlowGeneratorClientConfig {
  baseUrl: string;
  apiToken?: string;
  timeout?: number;
}

/**
 * Client Error
 */
export class TaskFlowGeneratorClientError extends Error {
  readonly statusCode: number;
  readonly body: unknown;

  constructor(message: string, statusCode: number, body?: unknown) {
    super(message);
    this.name = 'TaskFlowGeneratorClientError';
    this.statusCode = statusCode;
    this.body = body;
  }
}

/**
 * TaskFlowGeneratorClient - SDK for TaskFlow Generator API
 *
 * Features:
 * - Type-safe API calls
 * - Automatic request/response validation
 * - Error handling
 * - Timeout support
 */
export class TaskFlowGeneratorClient {
  private readonly config: Required<TaskFlowGeneratorClientConfig>;

  constructor(config: TaskFlowGeneratorClientConfig) {
    this.config = {
      baseUrl: config.baseUrl.replace(/\/$/, ''),
      apiToken: config.apiToken ?? '',
      timeout: config.timeout ?? 120000, // 2 minutes default for batch operations
    };
  }

  /**
   * Generate workflows for batch of tasks
   *
   * @param request - Batch generation request
   * @returns Batch generation response
   */
  async generateBatch(
    request: BatchGenerationRequest
  ): Promise<BatchGenerationResponse> {
    const response = await this.request<BatchGenerationResponse>(
      'POST',
      '/api/v1/generator/workflow/batch',
      request
    );

    // Validate response
    const parseResult = BatchGenerationResponseSchema.safeParse(response);
    if (!parseResult.success) {
      throw new TaskFlowGeneratorClientError(
        'Invalid response from server',
        0,
        parseResult.error
      );
    }

    return parseResult.data;
  }

  /**
   * Get generation status
   *
   * @param traceId - Trace ID to check
   * @returns Generation status
   */
  async getStatus(traceId: string): Promise<GenerationStatusResponse> {
    const response = await this.request<GenerationStatusResponse>(
      'GET',
      `/api/v1/generator/status/${encodeURIComponent(traceId)}`
    );

    // Validate response
    const parseResult = GenerationStatusResponseSchema.safeParse(response);
    if (!parseResult.success) {
      throw new TaskFlowGeneratorClientError(
        'Invalid response from server',
        0,
        parseResult.error
      );
    }

    return parseResult.data;
  }

  /**
   * Check service health
   *
   * @returns True if healthy
   */
  async isHealthy(): Promise<boolean> {
    try {
      const response = await this.request<{ status: string }>(
        'GET',
        '/api/v1/generator/health'
      );
      return response.status === 'healthy';
    } catch {
      return false;
    }
  }

  /**
   * Wait for generation to complete
   *
   * @param traceId - Trace ID to wait for
   * @param options - Polling options
   * @returns Final status
   */
  async waitForCompletion(
    traceId: string,
    options?: {
      pollIntervalMs?: number;
      timeoutMs?: number;
    }
  ): Promise<GenerationStatusResponse> {
    const pollInterval = options?.pollIntervalMs ?? 1000;
    const timeout = options?.timeoutMs ?? 300000; // 5 minutes default

    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const status = await this.getStatus(traceId);

      if (status.status === 'completed' || status.status === 'failed') {
        return status;
      }

      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new TaskFlowGeneratorClientError(
      `Timeout waiting for generation ${traceId}`,
      0
    );
  }

  /**
   * Make HTTP request
   */
  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const url = `${this.config.baseUrl}${path}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (this.config.apiToken) {
      headers['Authorization'] = `Bearer ${this.config.apiToken}`;
    }

    const options: RequestInit = {
      method,
      headers,
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.timeout);
    options.signal = controller.signal;

    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        let errorBody: unknown;
        try {
          errorBody = await response.json();
        } catch {
          errorBody = response.statusText;
        }

        throw new TaskFlowGeneratorClientError(
          `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorBody
        );
      }

      return (await response.json()) as T;
    } finally {
      clearTimeout(timeout);
    }
  }
}

/**
 * Factory function
 */
export function createTaskFlowGeneratorClient(
  config: TaskFlowGeneratorClientConfig
): TaskFlowGeneratorClient {
  return new TaskFlowGeneratorClient(config);
}
