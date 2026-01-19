/**
 * E2E Test API Client
 *
 * Issue #379: HTTP client for E2E testing
 */

/**
 * Workflow execution request
 */
export interface WorkflowExecuteRequest {
  project: string;
  workflow: string;
  inputs: Record<string, unknown>;
  options?: {
    timeout?: number;
    enableDebug?: boolean;
  };
}

/**
 * Workflow execution response
 */
export interface WorkflowExecuteResponse {
  success: boolean;
  workflowId: string;
  workflowName: string;
  status: 'success' | 'failed' | 'partial_success' | 'running';
  result?: Record<string, unknown>;
  stepResults: StepResult[];
  errors?: StepError[];
  executionTime?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Step result
 */
export interface StepResult {
  stepId: string;
  stepName: string;
  status: 'success' | 'failed' | 'skipped' | 'running';
  output?: unknown;
  error?: StepError;
  startTime?: string;
  endTime?: string;
  durationMs?: number;
}

/**
 * Step error
 */
export interface StepError {
  stepId?: string;
  stepName?: string;
  errorCode: string;
  errorMessage: string;
  timestamp?: string;
  recoverable?: boolean;
  context?: Record<string, unknown>;
}

/**
 * E2E API Client configuration
 */
export interface E2EClientConfig {
  baseUrl: string;
  timeout?: number;
}

/**
 * Default client configuration
 */
const DEFAULT_CONFIG: E2EClientConfig = {
  baseUrl: 'http://localhost:8006',
  timeout: 30000,
};

/**
 * E2E API Client
 *
 * Provides methods for interacting with TaskFlow API during E2E tests.
 */
export class E2EClient {
  private readonly config: Required<E2EClientConfig>;

  constructor(config: Partial<E2EClientConfig> = {}) {
    this.config = {
      baseUrl: config.baseUrl ?? DEFAULT_CONFIG.baseUrl,
      timeout: config.timeout ?? DEFAULT_CONFIG.timeout,
    };
  }

  /**
   * Execute a workflow
   */
  async executeWorkflow(request: WorkflowExecuteRequest): Promise<WorkflowExecuteResponse> {
    const url = `${this.config.baseUrl}/api/v1/taskflow/execute`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorBody}`);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timeout after ${this.config.timeout}ms`);
      }
      throw error;
    }
  }

  /**
   * Check health endpoint
   */
  async health(): Promise<{ status: string }> {
    const url = `${this.config.baseUrl}/health`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * List workflows for a project
   */
  async listWorkflows(project: string): Promise<{ workflows: string[] }> {
    const url = `${this.config.baseUrl}/api/v1/taskflow/workflows?project=${encodeURIComponent(project)}`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to list workflows: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Get workflow details
   */
  async getWorkflow(project: string, name: string): Promise<unknown> {
    const url = `${this.config.baseUrl}/api/v1/taskflow/workflows/${encodeURIComponent(name)}?project=${encodeURIComponent(project)}`;

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to get workflow: ${response.status}`);
    }

    return await response.json();
  }

  /**
   * Get base URL
   */
  getBaseUrl(): string {
    return this.config.baseUrl;
  }
}

/**
 * Create E2E client with default configuration
 */
export function createE2EClient(config?: Partial<E2EClientConfig>): E2EClient {
  return new E2EClient(config);
}

/**
 * Default E2E client instance
 */
export const e2eClient = createE2EClient();
