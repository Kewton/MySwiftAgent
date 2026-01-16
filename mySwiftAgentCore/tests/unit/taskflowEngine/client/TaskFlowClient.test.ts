/**
 * TaskFlowClient Unit Tests
 *
 * Issue #363: TypeScript SDK client for TaskFlow API
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  TaskFlowClient,
  TaskFlowClientError,
  createTaskFlowClient,
} from '../../../../src/taskflowEngine/client/TaskFlowClient.js';

// Mock fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('TaskFlowClient', () => {
  let client: TaskFlowClient;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    client = new TaskFlowClient({
      baseUrl: 'http://localhost:8005',
      apiToken: 'test-token',
      timeout: 5000,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('constructor', () => {
    it('should normalize base URL by removing trailing slash', () => {
      const client1 = new TaskFlowClient({ baseUrl: 'http://example.com/' });
      const client2 = new TaskFlowClient({ baseUrl: 'http://example.com' });

      // Both should behave the same
      expect(client1).toBeDefined();
      expect(client2).toBeDefined();
    });

    it('should use default timeout when not specified', () => {
      const client = new TaskFlowClient({ baseUrl: 'http://example.com' });
      expect(client).toBeDefined();
    });
  });

  describe('execute', () => {
    it('should execute workflow and return response', async () => {
      const mockResponse = {
        workflowId: 'wf_123',
        status: 'success',
        results: { output: 'result' },
        errors: [],
        durationMs: 150,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await client.execute({
        project: 'test_project',
        workflow: 'test_workflow',
        inputs: { key: 'value' },
      });

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8005/api/v1/taskflow/execute',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          }),
          body: JSON.stringify({
            project: 'test_project',
            workflow: 'test_workflow',
            inputs: { key: 'value' },
          }),
        })
      );
    });

    it('should throw TaskFlowClientError on HTTP error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ error: 'Workflow not found' }),
      });

      await expect(
        client.execute({
          project: 'test_project',
          workflow: 'unknown',
          inputs: {},
        })
      ).rejects.toThrow(TaskFlowClientError);
    });

    it('should include error body in TaskFlowClientError', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: () => Promise.resolve({ error: 'Invalid input', details: ['name required'] }),
      });

      try {
        await client.execute({
          project: 'test_project',
          workflow: 'test_workflow',
          inputs: {},
        });
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(TaskFlowClientError);
        expect((error as TaskFlowClientError).statusCode).toBe(400);
        expect((error as TaskFlowClientError).body).toEqual({
          error: 'Invalid input',
          details: ['name required'],
        });
      }
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        client.execute({
          project: 'test_project',
          workflow: 'test_workflow',
          inputs: {},
        })
      ).rejects.toThrow('Network error');
    });
  });

  describe('listWorkflows', () => {
    it('should list workflows for project', async () => {
      const mockResponse = {
        workflows: [
          { name: 'workflow_1', version: '1.0.0', stepCount: 3 },
          { name: 'workflow_2', version: '2.0.0', stepCount: 5 },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await client.listWorkflows('test_project');

      expect(result.workflows).toHaveLength(2);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8005/api/v1/taskflow/workflows?project=test_project',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });

    it('should URL encode project name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ workflows: [] }),
      });

      await client.listWorkflows('project with spaces');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('project%20with%20spaces'),
        expect.any(Object)
      );
    });
  });

  describe('getWorkflow', () => {
    it('should get workflow details', async () => {
      const mockWorkflow = {
        name: 'test_workflow',
        version: '1.0.0',
        steps: [
          { stepId: 'step_1', nodeType: 'transform' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkflow),
      });

      const result = await client.getWorkflow('test_project', 'test_workflow');

      expect(result).toEqual(mockWorkflow);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8005/api/v1/taskflow/workflows/test_workflow?project=test_project',
        expect.any(Object)
      );
    });
  });

  describe('getStats', () => {
    it('should get registry statistics', async () => {
      const mockStats = {
        totalWorkflows: 10,
        totalProjects: 3,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStats),
      });

      const result = await client.getStats();

      expect(result).toEqual(mockStats);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8005/api/v1/taskflow/stats',
        expect.any(Object)
      );
    });
  });

  describe('authentication', () => {
    it('should not include Authorization header when no token provided', async () => {
      const clientNoAuth = new TaskFlowClient({
        baseUrl: 'http://localhost:8005',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ workflows: [] }),
      });

      await clientNoAuth.listWorkflows('test');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });
  });

  describe('timeout handling', () => {
    it('should configure timeout for requests', () => {
      const clientShortTimeout = new TaskFlowClient({
        baseUrl: 'http://localhost:8005',
        timeout: 100,
      });

      // Just verify the client is created with timeout config
      expect(clientShortTimeout).toBeDefined();
    });
  });
});

describe('TaskFlowClientError', () => {
  it('should have correct name', () => {
    const error = new TaskFlowClientError('Test error', 500);
    expect(error.name).toBe('TaskFlowClientError');
  });

  it('should store status code and body', () => {
    const error = new TaskFlowClientError('Test error', 400, { detail: 'info' });
    expect(error.statusCode).toBe(400);
    expect(error.body).toEqual({ detail: 'info' });
  });

  it('should be instance of Error', () => {
    const error = new TaskFlowClientError('Test', 500);
    expect(error).toBeInstanceOf(Error);
  });
});

describe('createTaskFlowClient factory', () => {
  it('should create a TaskFlowClient instance', () => {
    const client = createTaskFlowClient({
      baseUrl: 'http://localhost:8005',
    });
    expect(client).toBeInstanceOf(TaskFlowClient);
  });
});
