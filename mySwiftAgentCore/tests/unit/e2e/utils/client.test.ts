/**
 * Unit Tests for E2E API Client
 *
 * Issue #379: Tests for E2E test utilities
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  E2EClient,
  createE2EClient,
  e2eClient,
  type E2EClientConfig,
  type WorkflowExecuteRequest,
} from '../../../e2e/utils/client.js';

describe('E2EClient', () => {
  describe('constructor', () => {
    test('should use default configuration', () => {
      const client = new E2EClient();
      expect(client.getBaseUrl()).toBe('http://localhost:8006');
    });

    test('should accept custom configuration', () => {
      const config: Partial<E2EClientConfig> = {
        baseUrl: 'http://custom-host:9000',
        timeout: 60000,
      };
      const client = new E2EClient(config);
      expect(client.getBaseUrl()).toBe('http://custom-host:9000');
    });

    test('should merge partial config with defaults', () => {
      const client = new E2EClient({ timeout: 5000 });
      expect(client.getBaseUrl()).toBe('http://localhost:8006');
    });
  });

  describe('executeWorkflow', () => {
    let client: E2EClient;
    const mockFetch = vi.fn();

    beforeEach(() => {
      client = new E2EClient({ timeout: 5000 });
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    test('should make POST request to correct endpoint', async () => {
      const mockResponse = {
        success: true,
        workflowId: 'test-workflow',
        workflowName: 'Test',
        status: 'success',
        stepResults: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const request: WorkflowExecuteRequest = {
        project: 'test-project',
        workflow: 'test-workflow',
        inputs: { key: 'value' },
      };

      const result = await client.executeWorkflow(request);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8006/api/v1/taskflow/execute',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    test('should throw error on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error'),
      });

      const request: WorkflowExecuteRequest = {
        project: 'test',
        workflow: 'test',
        inputs: {},
      };

      await expect(client.executeWorkflow(request)).rejects.toThrow('HTTP 500');
    });

    test('should throw timeout error on abort', async () => {
      mockFetch.mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            const error = new Error('Aborted');
            error.name = 'AbortError';
            reject(error);
          })
      );

      const request: WorkflowExecuteRequest = {
        project: 'test',
        workflow: 'test',
        inputs: {},
      };

      await expect(client.executeWorkflow(request)).rejects.toThrow('Request timeout');
    });
  });

  describe('health', () => {
    let client: E2EClient;
    const mockFetch = vi.fn();

    beforeEach(() => {
      client = new E2EClient();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    test('should make GET request to health endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy' }),
      });

      const result = await client.health();

      expect(mockFetch).toHaveBeenCalledWith('http://localhost:8006/health');
      expect(result).toEqual({ status: 'healthy' });
    });

    test('should throw error on health check failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
      });

      await expect(client.health()).rejects.toThrow('Health check failed');
    });
  });

  describe('listWorkflows', () => {
    let client: E2EClient;
    const mockFetch = vi.fn();

    beforeEach(() => {
      client = new E2EClient();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    test('should list workflows for project', async () => {
      const mockWorkflows = { workflows: ['workflow1', 'workflow2'] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkflows),
      });

      const result = await client.listWorkflows('test-project');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8006/api/v1/taskflow/workflows?project=test-project'
      );
      expect(result).toEqual(mockWorkflows);
    });

    test('should URL encode project name', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ workflows: [] }),
      });

      await client.listWorkflows('project with spaces');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8006/api/v1/taskflow/workflows?project=project%20with%20spaces'
      );
    });
  });

  describe('getWorkflow', () => {
    let client: E2EClient;
    const mockFetch = vi.fn();

    beforeEach(() => {
      client = new E2EClient();
      global.fetch = mockFetch;
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    test('should get workflow details', async () => {
      const mockWorkflow = { id: 'test', name: 'Test Workflow' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockWorkflow),
      });

      const result = await client.getWorkflow('project', 'workflow-name');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8006/api/v1/taskflow/workflows/workflow-name?project=project'
      );
      expect(result).toEqual(mockWorkflow);
    });
  });
});

describe('createE2EClient', () => {
  test('should create client with default config', () => {
    const client = createE2EClient();
    expect(client).toBeInstanceOf(E2EClient);
    expect(client.getBaseUrl()).toBe('http://localhost:8006');
  });

  test('should create client with custom config', () => {
    const client = createE2EClient({ baseUrl: 'http://custom:8000' });
    expect(client.getBaseUrl()).toBe('http://custom:8000');
  });
});

describe('e2eClient (default instance)', () => {
  test('should be an E2EClient instance', () => {
    expect(e2eClient).toBeInstanceOf(E2EClient);
  });

  test('should have default base URL', () => {
    expect(e2eClient.getBaseUrl()).toBe('http://localhost:8006');
  });
});
