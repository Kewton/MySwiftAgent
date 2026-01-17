/**
 * URLResolver Unit Tests
 *
 * Issue #372: Tests for URL resolution from capabilities
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { URLResolver, createURLResolver } from '../../../../src/capabilityManagement/endpoint/URLResolver.js';
import type {
  IEndpointConfigManager,
  ApiEndpointsConfig,
} from '../../../../src/capabilityManagement/endpoint/types.js';
import { EndpointResolutionError } from '../../../../src/capabilityManagement/endpoint/types.js';
import type { CapabilityExtended } from '../../../../src/shared/types/capability.types.js';

describe('URLResolver', () => {
  let urlResolver: URLResolver;
  let mockConfigManager: IEndpointConfigManager;
  let mockEndpoints: ApiEndpointsConfig;

  beforeEach(() => {
    mockEndpoints = {
      expert_agent: {
        base_url: 'http://localhost:8004',
        description: 'AI Agent API',
        endpoint_prefix: '/v1/',
      },
      google_apis: {
        base_url: 'https://www.googleapis.com',
        description: 'Google APIs',
      },
      graphai_server: {
        base_url: 'http://localhost:8005',
        description: 'GraphAI Server',
        endpoint_prefix: '/api/',
      },
    };

    mockConfigManager = {
      loadProjectEndpoints: vi.fn().mockResolvedValue(mockEndpoints),
      resolveEnvVars: vi.fn((v) => v),
      clearCache: vi.fn(),
    };

    urlResolver = new URLResolver({
      configManager: mockConfigManager,
      defaultProjectId: 'default_project',
    });
  });

  describe('constructor', () => {
    it('should create instance with configManager', () => {
      expect(urlResolver).toBeInstanceOf(URLResolver);
    });

    it('should use default project ID when not specified', () => {
      const resolver = new URLResolver({
        configManager: mockConfigManager,
      });
      expect(resolver).toBeInstanceOf(URLResolver);
    });
  });

  describe('resolveCapabilityUrl', () => {
    it('should resolve URL for capability with api_source matching endpoint key', async () => {
      const capability: CapabilityExtended = {
        id: 'google_search',
        name: 'Google Search',
        description: 'Search using Google',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/utility/google_search',
          method: 'POST',
          auth_type: 'api_key',
          secret_key: 'SERPER_API_KEY',
        },
      };

      // Mock a scenario where capability has api_source
      const capabilityWithSource: CapabilityExtended = {
        ...capability,
        _internal: {
          ...capability._internal,
          config: { api_source: 'expert_agent' },
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capabilityWithSource);

      expect(result.url).toBe('http://localhost:8004/v1/utility/google_search');
    });

    it('should resolve URL using endpoint_prefix fallback when no api_source', async () => {
      const capability: CapabilityExtended = {
        id: 'google_search',
        name: 'Google Search',
        description: 'Search using Google',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/utility/google_search',
          method: 'POST',
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capability);

      // Should match expert_agent because endpoint starts with /v1/
      expect(result.url).toBe('http://localhost:8004/v1/utility/google_search');
    });

    it('should include auth configuration from capability', async () => {
      const capability: CapabilityExtended = {
        id: 'google_search',
        name: 'Google Search',
        description: 'Search using Google',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/utility/google_search',
          method: 'POST',
          auth_type: 'bearer_token',
          secret_key: 'API_TOKEN',
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capability);

      expect(result.auth).toEqual({
        type: 'bearer',
        secret_key: 'API_TOKEN',
      });
    });

    it('should include timeout from capability', async () => {
      const capability: CapabilityExtended = {
        id: 'slow_api',
        name: 'Slow API',
        description: 'A slow API',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/slow',
          method: 'GET',
          timeout_ms: 30000,
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capability);

      expect(result.timeout_ms).toBe(30000);
    });

    it('should include headers from capability', async () => {
      const capability: CapabilityExtended = {
        id: 'custom_api',
        name: 'Custom API',
        description: 'API with custom headers',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/custom',
          method: 'POST',
          headers: {
            'X-Custom-Header': 'custom-value',
          },
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capability);

      expect(result.headers).toEqual({
        'X-Custom-Header': 'custom-value',
      });
    });

    it('should throw EndpointResolutionError when capability has no endpoint', async () => {
      const capability: CapabilityExtended = {
        id: 'no_endpoint',
        name: 'No Endpoint',
        description: 'Capability without endpoint',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        // No _internal section
      };

      await expect(urlResolver.resolveCapabilityUrl(capability)).rejects.toThrow(
        EndpointResolutionError
      );
    });

    it('should throw EndpointResolutionError when no matching base URL found', async () => {
      // Create resolver with empty endpoints
      mockConfigManager.loadProjectEndpoints = vi.fn().mockResolvedValue({});
      const resolver = new URLResolver({ configManager: mockConfigManager });

      const capability: CapabilityExtended = {
        id: 'orphan_capability',
        name: 'Orphan',
        description: 'Capability with no matching endpoint',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/unknown/endpoint',
          method: 'GET',
        },
      };

      await expect(resolver.resolveCapabilityUrl(capability)).rejects.toThrow(
        EndpointResolutionError
      );
    });

    it('should use specified projectId over default', async () => {
      const capability: CapabilityExtended = {
        id: 'project_specific',
        name: 'Project Specific',
        description: 'Capability for specific project',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/specific',
          method: 'GET',
        },
      };

      await urlResolver.resolveCapabilityUrl(capability, 'custom_project');

      expect(mockConfigManager.loadProjectEndpoints).toHaveBeenCalledWith('custom_project');
    });

    it('should handle api_key auth type mapping', async () => {
      const capability: CapabilityExtended = {
        id: 'api_key_auth',
        name: 'API Key Auth',
        description: 'Capability with API key auth',
        version: '1.0.0',
        status: 'available',
        category: 'utility',
        parameters: [],
        returnType: 'object',
        _internal: {
          endpoint: '/v1/protected',
          method: 'GET',
          auth_type: 'api_key',
          secret_key: 'MY_API_KEY',
        },
      };

      const result = await urlResolver.resolveCapabilityUrl(capability);

      expect(result.auth).toEqual({
        type: 'api_key',
        secret_key: 'MY_API_KEY',
      });
    });
  });

  describe('findMatchingConfig', () => {
    it('should find config by endpoint_prefix match', () => {
      const result = urlResolver.findMatchingConfig('/v1/utility/search', mockEndpoints);

      expect(result).toBeDefined();
      expect(result?.base_url).toBe('http://localhost:8004');
    });

    it('should find config by /api/ prefix', () => {
      const result = urlResolver.findMatchingConfig('/api/workflows/run', mockEndpoints);

      expect(result).toBeDefined();
      expect(result?.base_url).toBe('http://localhost:8005');
    });

    it('should return undefined when no match found', () => {
      const result = urlResolver.findMatchingConfig('/unknown/path', mockEndpoints);

      expect(result).toBeUndefined();
    });

    it('should match the most specific prefix', () => {
      const endpoints: ApiEndpointsConfig = {
        general: {
          base_url: 'http://general.example.com',
          description: 'General API',
          endpoint_prefix: '/api/',
        },
        specific: {
          base_url: 'http://specific.example.com',
          description: 'Specific API',
          endpoint_prefix: '/api/v2/',
        },
      };

      const result = urlResolver.findMatchingConfig('/api/v2/endpoint', endpoints);

      expect(result?.base_url).toBe('http://specific.example.com');
    });
  });
});

describe('createURLResolver factory', () => {
  it('should create a URLResolver instance', () => {
    const mockConfigManager: IEndpointConfigManager = {
      loadProjectEndpoints: vi.fn(),
      resolveEnvVars: vi.fn(),
      clearCache: vi.fn(),
    };

    const resolver = createURLResolver(mockConfigManager);
    expect(resolver).toBeInstanceOf(URLResolver);
  });

  it('should accept default project ID', () => {
    const mockConfigManager: IEndpointConfigManager = {
      loadProjectEndpoints: vi.fn(),
      resolveEnvVars: vi.fn(),
      clearCache: vi.fn(),
    };

    const resolver = createURLResolver(mockConfigManager, 'my_project');
    expect(resolver).toBeInstanceOf(URLResolver);
  });
});
