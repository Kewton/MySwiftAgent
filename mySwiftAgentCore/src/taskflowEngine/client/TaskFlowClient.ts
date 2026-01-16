/**
 * TaskFlowClient - TypeScript SDK for TaskFlow API
 *
 * Issue #363: Client SDK for programmatic workflow execution
 */

/**
 * Client configuration
 */
export interface TaskFlowClientConfig {
  baseUrl: string;
  apiToken?: string;
  timeout?: number;
}

/**
 * Execute workflow request
 */
export interface ExecuteRequest {
  project: string;
  workflow: string;
  inputs: Record<string, unknown>;
}

/**
 * Execute workflow response
 */
export interface ExecuteResponse {
  workflowId: string;
  status: 'success' | 'partial_success' | 'failed';
  results: Record<string, unknown>;
  errors: Array<{
    stepId: string;
    code: string;
    message: string;
  }>;
  traceId?: string;
  durationMs: number;
}

/**
 * Workflow info
 */
export interface WorkflowInfo {
  name: string;
  version: string;
  inputSchema: unknown;
  outputSchema: unknown;
  stepCount: number;
}

/**
 * List workflows response
 */
export interface ListWorkflowsResponse {
  workflows: WorkflowInfo[];
}

/**
 * TaskFlowClient - SDK for TaskFlow API
 *
 * Features:
 * - Execute workflows
 * - List workflows
 * - Get workflow details
 * - Authentication support
 */
export class TaskFlowClient {
  private readonly config: Required<TaskFlowClientConfig>;

  constructor(config: TaskFlowClientConfig) {
    this.config = {
      baseUrl: config.baseUrl.replace(/\/$/, ''),
      apiToken: config.apiToken || '',
      timeout: config.timeout || 30000,
    };
  }

  /**
   * Execute a workflow
   *
   * @param request - Execute request
   * @returns Execute response
   */
  async execute(request: ExecuteRequest): Promise<ExecuteResponse> {
    const response = await this.request<ExecuteResponse>(
      'POST',
      '/api/v1/taskflow/execute',
      request
    );
    return response;
  }

  /**
   * List workflows for a project
   *
   * @param project - Project identifier
   * @returns List of workflows
   */
  async listWorkflows(project: string): Promise<ListWorkflowsResponse> {
    const response = await this.request<ListWorkflowsResponse>(
      'GET',
      `/api/v1/taskflow/workflows?project=${encodeURIComponent(project)}`
    );
    return response;
  }

  /**
   * Get workflow details
   *
   * @param project - Project identifier
   * @param name - Workflow name
   * @returns Workflow details
   */
  async getWorkflow(project: string, name: string): Promise<unknown> {
    const response = await this.request(
      'GET',
      `/api/v1/taskflow/workflows/${encodeURIComponent(name)}?project=${encodeURIComponent(project)}`
    );
    return response;
  }

  /**
   * Get registry statistics
   */
  async getStats(): Promise<unknown> {
    const response = await this.request('GET', '/api/v1/taskflow/stats');
    return response;
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

        throw new TaskFlowClientError(
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
 * TaskFlowClientError - Client-specific error
 */
export class TaskFlowClientError extends Error {
  readonly statusCode: number;
  readonly body: unknown;

  constructor(message: string, statusCode: number, body?: unknown) {
    super(message);
    this.name = 'TaskFlowClientError';
    this.statusCode = statusCode;
    this.body = body;
  }
}

/**
 * Factory function
 */
export function createTaskFlowClient(config: TaskFlowClientConfig): TaskFlowClient {
  return new TaskFlowClient(config);
}
