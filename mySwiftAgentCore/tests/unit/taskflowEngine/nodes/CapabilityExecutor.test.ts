/**
 * CapabilityExecutor Unit Tests
 *
 * Issue #372: Tests for capability-based API execution
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  CapabilityExecutor,
  createCapabilityExecutor,
} from '../../../../src/taskflowEngine/nodes/CapabilityExecutor.js';
import type { CapabilityRegistry } from '../../../../src/capabilityManagement/registry/CapabilityRegistry.js';
import type { URLResolver } from '../../../../src/capabilityManagement/endpoint/URLResolver.js';
import type { CapabilityExtended } from '../../../../src/shared/types/capability.types.js';
import type { NodeExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

// Mock fetch globally
global.fetch = vi.fn();

describe('CapabilityExecutor', () => {
  let executor: CapabilityExecutor;
  let mockRegistry: CapabilityRegistry;
  let mockUrlResolver: URLResolver;
  let mockCapability: CapabilityExtended;
  let context: NodeExecutionContext;

  beforeEach(() => {
    mockCapability = {
      id: 'google_search',
      name: 'Google Search',
      description: 'Search using Google',
      version: '1.0.0',
      status: 'available',
      category: 'utility',
      parameters: [
        {
          name: 'queries',
          type: 'array',
          required: true,
          description: 'Search queries',
        },
      ],
      returnType: 'object',
      _internal: {
        endpoint: '/v1/utility/google_search',
        method: 'POST',
        auth_type: 'api_key',
        secret_key: 'SERPER_API_KEY',
        timeout_ms: 10000,
      },
    };

    mockRegistry = {
      getCapability: vi.fn().mockReturnValue(mockCapability),
      registerForProject: vi.fn(),
      getByProject: vi.fn(),
      unregisterFromProject: vi.fn(),
      listProjects: vi.fn(),
      getStats: vi.fn(),
      clear: vi.fn(),
      includeShared: vi.fn(),
      getSharedRefs: vi.fn(),
    } as unknown as CapabilityRegistry;

    mockUrlResolver = {
      resolveCapabilityUrl: vi.fn().mockResolvedValue({
        url: 'http://localhost:8004/v1/utility/google_search',
        method: 'POST',
        auth: {
          type: 'api_key',
          secret_key: 'SERPER_API_KEY',
        },
        timeout_ms: 10000,
      }),
      findMatchingConfig: vi.fn(),
    } as unknown as URLResolver;

    executor = new CapabilityExecutor({
      capabilityRegistry: mockRegistry,
      urlResolver: mockUrlResolver,
    });

    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {
        SERPER_API_KEY: 'test-api-key-123',
      },
    };

    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create instance with registry and resolver', () => {
      expect(executor).toBeInstanceOf(CapabilityExecutor);
    });
  });

  describe('execute', () => {
    it('should execute capability and return success', async () => {
      const mockResponse = {
        results: [{ title: 'Test Result', link: 'https://example.com' }],
      };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await executor.execute(
        'google_search',
        { queries: ['test query'] },
        context,
        'default_project'
      );

      expect(result.success).toBe(true);
      expect(result.output).toEqual(mockResponse);
      expect(mockRegistry.getCapability).toHaveBeenCalledWith('default_project', 'google_search');
      expect(mockUrlResolver.resolveCapabilityUrl).toHaveBeenCalledWith(
        mockCapability,
        'default_project'
      );
    });

    it('should include API key in request headers', async () => {
      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute('google_search', { queries: ['test'] }, context, 'default_project');

      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8004/v1/utility/google_search',
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'test-api-key-123',
          }),
        })
      );
    });

    it('should include bearer token in request headers', async () => {
      (mockUrlResolver.resolveCapabilityUrl as ReturnType<typeof vi.fn>).mockResolvedValue({
        url: 'http://localhost:8004/v1/protected',
        method: 'GET',
        auth: {
          type: 'bearer',
          secret_key: 'BEARER_TOKEN',
        },
      });

      const contextWithToken: NodeExecutionContext = {
        ...context,
        secrets: { BEARER_TOKEN: 'my-bearer-token' },
      };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute('protected_api', {}, contextWithToken, 'default_project');

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer my-bearer-token',
          }),
        })
      );
    });

    it('should return error when capability not found', async () => {
      (mockRegistry.getCapability as ReturnType<typeof vi.fn>).mockReturnValue(undefined);

      const result = await executor.execute(
        'nonexistent',
        {},
        context,
        'default_project'
      );

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('CAPABILITY_NOT_FOUND');
      expect(result.error?.message).toContain('nonexistent');
    });

    it('should return error when URL resolution fails', async () => {
      (mockUrlResolver.resolveCapabilityUrl as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('No matching base URL configuration')
      );

      const result = await executor.execute(
        'google_search',
        {},
        context,
        'default_project'
      );

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('URL_RESOLUTION_ERROR');
    });

    it('should return error on HTTP error response', async () => {
      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Server error' }),
      });

      const result = await executor.execute(
        'google_search',
        { queries: ['test'] },
        context,
        'default_project'
      );

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('HTTP_ERROR');
      expect(result.error?.message).toContain('500');
    });

    it('should return error on network failure', async () => {
      (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

      const result = await executor.execute(
        'google_search',
        { queries: ['test'] },
        context,
        'default_project'
      );

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('NETWORK_ERROR');
    });

    it('should use POST method and send body for POST requests', async () => {
      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute(
        'google_search',
        { queries: ['test query'], num: 5 },
        context,
        'default_project'
      );

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ queries: ['test query'], num: 5 }),
        })
      );
    });

    it('should not send body for GET requests', async () => {
      (mockUrlResolver.resolveCapabilityUrl as ReturnType<typeof vi.fn>).mockResolvedValue({
        url: 'http://localhost:8004/v1/data',
        method: 'GET',
      });

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' }),
      });

      await executor.execute('get_data', {}, context, 'default_project');

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: 'GET',
        })
      );

      const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(callArgs?.[1]?.body).toBeUndefined();
    });

    it('should include custom headers from resolved endpoint', async () => {
      (mockUrlResolver.resolveCapabilityUrl as ReturnType<typeof vi.fn>).mockResolvedValue({
        url: 'http://localhost:8004/v1/custom',
        method: 'POST',
        headers: {
          'X-Custom-Header': 'custom-value',
          'X-Another': 'another-value',
        },
      });

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute('custom_api', {}, context, 'default_project');

      expect(fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Custom-Header': 'custom-value',
            'X-Another': 'another-value',
          }),
        })
      );
    });

    it('should use default_project when projectId not specified', async () => {
      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute('google_search', {}, context);

      expect(mockRegistry.getCapability).toHaveBeenCalledWith('default_project', 'google_search');
    });
  });

  describe('validate', () => {
    it('should return valid for existing capability', async () => {
      const result = await executor.validate('google_search', 'default_project');

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should return invalid for non-existent capability', async () => {
      (mockRegistry.getCapability as ReturnType<typeof vi.fn>).mockReturnValue(undefined);

      const result = await executor.validate('nonexistent', 'default_project');

      expect(result.valid).toBe(false);
      expect(result.errors).toContain("Capability 'nonexistent' not found");
    });

    it('should return invalid for capability without endpoint', async () => {
      const capabilityNoEndpoint: CapabilityExtended = {
        ...mockCapability,
        _internal: undefined,
      };
      (mockRegistry.getCapability as ReturnType<typeof vi.fn>).mockReturnValue(capabilityNoEndpoint);

      const result = await executor.validate('no_endpoint', 'default_project');

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.includes('endpoint'))).toBe(true);
    });

    it('should return invalid when URL resolution fails', async () => {
      (mockUrlResolver.resolveCapabilityUrl as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('No matching configuration')
      );

      const result = await executor.validate('google_search', 'default_project');

      expect(result.valid).toBe(false);
      expect(result.errors.some((e) => e.includes('URL resolution'))).toBe(true);
    });
  });
});

describe('createCapabilityExecutor factory', () => {
  it('should create a CapabilityExecutor instance', () => {
    const mockRegistry = {} as CapabilityRegistry;
    const mockUrlResolver = {} as URLResolver;

    const executor = createCapabilityExecutor(mockRegistry, mockUrlResolver);
    expect(executor).toBeInstanceOf(CapabilityExecutor);
  });
});
