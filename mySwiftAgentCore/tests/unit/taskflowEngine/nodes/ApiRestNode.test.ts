/**
 * ApiRestNode Unit Tests
 *
 * Issue #363: REST API node executor
 * Issue #372: Extended with capability_id support
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  ApiRestNodeExecutor,
  createApiRestNodeExecutor,
} from '../../../../src/taskflowEngine/nodes/ApiRestNode.js';
import type { ExtendedNodeExecutionContext } from '../../../../src/taskflowEngine/nodes/ApiRestNode.js';
import type { NodeConfig, ExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';
import type { CapabilityExecutor } from '../../../../src/taskflowEngine/nodes/CapabilityExecutor.js';

// Mock fetch
global.fetch = vi.fn();

describe('ApiRestNodeExecutor', () => {
  let executor: ApiRestNodeExecutor;
  let context: ExecutionContext;

  beforeEach(() => {
    executor = new ApiRestNodeExecutor();
    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {},
    };
    vi.clearAllMocks();
  });

  describe('type', () => {
    it('should have type api_rest', () => {
      expect(executor.type).toBe('api_rest');
    });
  });

  describe('validate', () => {
    it('should validate valid config', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/data',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(true);
    });

    it('should require either url or capability_id', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Either url or capability_id is required');
    });

    it('should require method when using url', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          url: 'https://api.example.com',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('method is required when using url');
    });

    it('should not require method when using capability_id', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          capability_id: 'google_search',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(true);
    });

    it('should validate with capability_id and optional method', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          capability_id: 'google_search',
          method: 'POST',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(true);
    });

    it('should validate method value', () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'INVALID',
          url: 'https://api.example.com',
        },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors[0]).toContain('Invalid method');
    });
  });

  describe('execute', () => {
    it('should execute GET request', async () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/users/123',
        },
      };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: 123, name: 'Test User' }),
      });

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ id: 123, name: 'Test User' });
      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/users/123',
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('should execute POST request with body', async () => {
      const config: NodeConfig = {
        nodeId: 'create_user',
        type: 'api_rest',
        config: {
          method: 'POST',
          url: 'https://api.example.com/users',
          headers: { 'Content-Type': 'application/json' },
        },
      };
      const params = { body: { name: 'New User' } };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => ({ id: 456, name: 'New User' }),
      });

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'New User' }),
        })
      );
    });

    it('should handle request errors', async () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/error',
        },
      };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ error: 'Server error' }),
      });

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('HTTP_ERROR');
    });

    it('should handle network errors', async () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/data',
        },
      };

      (fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('NETWORK_ERROR');
    });

    it('should interpolate URL variables', async () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/users/${user_id}',
        },
      };
      const params = { user_id: '123' };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ id: 123 }),
      });

      await executor.execute(config, params, context);

      expect(fetch).toHaveBeenCalledWith(
        'https://api.example.com/users/123',
        expect.anything()
      );
    });

    it('should use auth header from secrets', async () => {
      const config: NodeConfig = {
        nodeId: 'fetch_data',
        type: 'api_rest',
        config: {
          method: 'GET',
          url: 'https://api.example.com/data',
          auth: {
            type: 'bearer',
            secret_key: 'API_TOKEN',
          },
        },
      };
      const contextWithSecrets: ExecutionContext = {
        ...context,
        secrets: { API_TOKEN: 'secret_token_123' },
      };

      (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      await executor.execute(config, {}, contextWithSecrets);

      expect(fetch).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer secret_token_123',
          }),
        })
      );
    });
  });
});

describe('createApiRestNodeExecutor factory', () => {
  it('should create an ApiRestNodeExecutor instance', () => {
    const executor = createApiRestNodeExecutor();
    expect(executor).toBeInstanceOf(ApiRestNodeExecutor);
  });
});

/**
 * Issue #372: capability_id execution mode tests
 */
describe('ApiRestNodeExecutor capability_id mode', () => {
  let executor: ApiRestNodeExecutor;
  let mockCapabilityExecutor: CapabilityExecutor;
  let extendedContext: ExtendedNodeExecutionContext;

  beforeEach(() => {
    vi.clearAllMocks();
    executor = new ApiRestNodeExecutor();
    mockCapabilityExecutor = {
      execute: vi.fn().mockResolvedValue({
        success: true,
        output: { results: ['test result'] },
        metadata: { capabilityId: 'google_search' },
      }),
      validate: vi.fn(),
    } as unknown as CapabilityExecutor;

    extendedContext = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: { API_KEY: 'test-key' },
      capabilityExecutor: mockCapabilityExecutor,
    };
  });

  it('should delegate to CapabilityExecutor when capability_id is specified', async () => {
    const config: NodeConfig = {
      nodeId: 'search_node',
      type: 'api_rest',
      config: {
        capability_id: 'google_search',
      },
    };

    const result = await executor.execute(
      config,
      { queries: ['test query'] },
      extendedContext
    );

    expect(result.success).toBe(true);
    expect(mockCapabilityExecutor.execute).toHaveBeenCalledWith(
      'google_search',
      { queries: ['test query'] },
      extendedContext,
      'default_project'
    );
  });

  it('should use specified project_id', async () => {
    const config: NodeConfig = {
      nodeId: 'search_node',
      type: 'api_rest',
      config: {
        capability_id: 'google_search',
        project_id: 'custom_project',
      },
    };

    await executor.execute(config, {}, extendedContext);

    expect(mockCapabilityExecutor.execute).toHaveBeenCalledWith(
      'google_search',
      {},
      extendedContext,
      'custom_project'
    );
  });

  it('should return error when CapabilityExecutor is not available', async () => {
    const config: NodeConfig = {
      nodeId: 'search_node',
      type: 'api_rest',
      config: {
        capability_id: 'google_search',
      },
    };

    const contextWithoutExecutor: ExecutionContext = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {},
    };

    const result = await executor.execute(config, {}, contextWithoutExecutor);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe('EXECUTOR_NOT_AVAILABLE');
  });

  it('should return error when neither url nor capability_id is specified', async () => {
    const config: NodeConfig = {
      nodeId: 'bad_config',
      type: 'api_rest',
      config: {
        method: 'GET',
      },
    };

    const result = await executor.execute(config, {}, extendedContext);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe('CONFIGURATION_ERROR');
    expect(result.error?.message).toContain('Either url or capability_id must be specified');
  });

  it('should prefer capability_id when both url and capability_id are specified', async () => {
    const config: NodeConfig = {
      nodeId: 'mixed_config',
      type: 'api_rest',
      config: {
        url: 'https://api.example.com',
        capability_id: 'google_search',
        method: 'POST',
      },
    };

    await executor.execute(config, {}, extendedContext);

    // Should use CapabilityExecutor, not direct URL
    expect(mockCapabilityExecutor.execute).toHaveBeenCalled();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('should forward capability execution errors', async () => {
    (mockCapabilityExecutor.execute as ReturnType<typeof vi.fn>).mockResolvedValue({
      success: false,
      output: null,
      error: {
        code: 'CAPABILITY_NOT_FOUND',
        message: "Capability 'nonexistent' not found",
      },
    });

    const config: NodeConfig = {
      nodeId: 'search_node',
      type: 'api_rest',
      config: {
        capability_id: 'nonexistent',
      },
    };

    const result = await executor.execute(config, {}, extendedContext);

    expect(result.success).toBe(false);
    expect(result.error?.code).toBe('CAPABILITY_NOT_FOUND');
  });
});
