/**
 * EndpointConfigManager Unit Tests
 *
 * Issue #372: Tests for endpoint configuration management
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  EndpointConfigManager,
  createEndpointConfigManager,
} from '../../../../src/capabilityManagement/endpoint/EndpointConfigManager.js';
import type { ApiEndpointsConfig } from '../../../../src/capabilityManagement/endpoint/types.js';

// Mock fs/promises
vi.mock('fs/promises', () => ({
  readFile: vi.fn(),
}));

// Mock js-yaml
vi.mock('js-yaml', () => ({
  default: {
    load: vi.fn(),
    JSON_SCHEMA: {},
  },
}));

import * as fs from 'fs/promises';
import yaml from 'js-yaml';

describe('EndpointConfigManager', () => {
  let configManager: EndpointConfigManager;
  const basePath = '/test/config';

  beforeEach(() => {
    configManager = new EndpointConfigManager({ basePath });
    vi.clearAllMocks();
    // Clear any cached environment variables
    delete process.env.TEST_VAR;
    delete process.env.EXPERT_AGENT_BASE_URL;
  });

  afterEach(() => {
    configManager.clearCache();
  });

  describe('constructor', () => {
    it('should create instance with basePath', () => {
      expect(configManager).toBeInstanceOf(EndpointConfigManager);
    });

    it('should enable cache by default', () => {
      const manager = new EndpointConfigManager({ basePath });
      expect(manager).toBeDefined();
    });

    it('should allow disabling cache', () => {
      const manager = new EndpointConfigManager({ basePath, enableCache: false });
      expect(manager).toBeDefined();
    });
  });

  describe('resolveEnvVars', () => {
    it('should resolve simple environment variable', () => {
      process.env.TEST_VAR = 'test_value';
      const result = configManager.resolveEnvVars('${TEST_VAR}');
      expect(result).toBe('test_value');
    });

    it('should resolve environment variable with default value when not set', () => {
      delete process.env.UNSET_VAR;
      const result = configManager.resolveEnvVars('${UNSET_VAR:-default_value}');
      expect(result).toBe('default_value');
    });

    it('should use environment value over default', () => {
      process.env.TEST_VAR = 'env_value';
      const result = configManager.resolveEnvVars('${TEST_VAR:-default_value}');
      expect(result).toBe('env_value');
    });

    it('should resolve multiple variables in one string', () => {
      process.env.HOST = 'localhost';
      process.env.PORT = '8004';
      const result = configManager.resolveEnvVars('http://${HOST}:${PORT}/api');
      expect(result).toBe('http://localhost:8004/api');
    });

    it('should leave unmatched patterns unchanged', () => {
      const result = configManager.resolveEnvVars('no variables here');
      expect(result).toBe('no variables here');
    });

    it('should handle empty default value', () => {
      delete process.env.EMPTY_VAR;
      const result = configManager.resolveEnvVars('${EMPTY_VAR:-}');
      expect(result).toBe('');
    });

    it('should handle complex patterns with colons', () => {
      delete process.env.URL_VAR;
      const result = configManager.resolveEnvVars('${URL_VAR:-http://localhost:8004}');
      expect(result).toBe('http://localhost:8004');
    });

    it('should handle nested pattern (no nesting support)', () => {
      process.env.OUTER = 'outer_value';
      const result = configManager.resolveEnvVars('prefix_${OUTER}_suffix');
      expect(result).toBe('prefix_outer_value_suffix');
    });
  });

  describe('loadProjectEndpoints', () => {
    it('should load and parse index.yaml with api_endpoints', async () => {
      const mockYamlContent = `
        capabilities:
          - google_search
        api_endpoints:
          expert_agent:
            base_url: "http://localhost:8004"
            description: "AI Agent API"
            endpoint_prefix: "/v1/"
      `;

      const mockParsed = {
        capabilities: ['google_search'],
        api_endpoints: {
          expert_agent: {
            base_url: 'http://localhost:8004',
            description: 'AI Agent API',
            endpoint_prefix: '/v1/',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue(mockYamlContent);
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      const result = await configManager.loadProjectEndpoints('default_project');

      expect(result).toEqual({
        expert_agent: {
          base_url: 'http://localhost:8004',
          description: 'AI Agent API',
          endpoint_prefix: '/v1/',
        },
      });
    });

    it('should resolve environment variables in base_url', async () => {
      process.env.EXPERT_AGENT_BASE_URL = 'http://staging.example.com:8004';

      const mockParsed = {
        api_endpoints: {
          expert_agent: {
            base_url: '${EXPERT_AGENT_BASE_URL:-http://localhost:8004}',
            description: 'AI Agent API',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      const result = await configManager.loadProjectEndpoints('default_project');

      expect(result.expert_agent?.base_url).toBe('http://staging.example.com:8004');
    });

    it('should use default value when environment variable not set', async () => {
      delete process.env.EXPERT_AGENT_BASE_URL;

      const mockParsed = {
        api_endpoints: {
          expert_agent: {
            base_url: '${EXPERT_AGENT_BASE_URL:-http://localhost:8004}',
            description: 'AI Agent API',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      const result = await configManager.loadProjectEndpoints('default_project');

      expect(result.expert_agent?.base_url).toBe('http://localhost:8004');
    });

    it('should return empty object when no api_endpoints in index', async () => {
      const mockParsed = {
        capabilities: ['google_search'],
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      const result = await configManager.loadProjectEndpoints('default_project');

      expect(result).toEqual({});
    });

    it('should throw error when index.yaml cannot be read', async () => {
      (fs.readFile as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('ENOENT: no such file or directory')
      );

      await expect(configManager.loadProjectEndpoints('nonexistent')).rejects.toThrow(
        'Failed to load endpoint configuration'
      );
    });

    it('should cache loaded configurations', async () => {
      const mockParsed = {
        api_endpoints: {
          expert_agent: {
            base_url: 'http://localhost:8004',
            description: 'AI Agent API',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      // First call
      await configManager.loadProjectEndpoints('default_project');
      // Second call should use cache
      await configManager.loadProjectEndpoints('default_project');

      // fs.readFile should only be called once due to caching
      expect(fs.readFile).toHaveBeenCalledTimes(1);
    });

    it('should bypass cache when disabled', async () => {
      const managerNoCache = new EndpointConfigManager({
        basePath,
        enableCache: false,
      });

      const mockParsed = {
        api_endpoints: {
          expert_agent: {
            base_url: 'http://localhost:8004',
            description: 'AI Agent API',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      await managerNoCache.loadProjectEndpoints('default_project');
      await managerNoCache.loadProjectEndpoints('default_project');

      // fs.readFile should be called twice when cache is disabled
      expect(fs.readFile).toHaveBeenCalledTimes(2);
    });
  });

  describe('clearCache', () => {
    it('should clear cached configurations', async () => {
      const mockParsed = {
        api_endpoints: {
          expert_agent: {
            base_url: 'http://localhost:8004',
            description: 'AI Agent API',
          },
        },
      };

      (fs.readFile as ReturnType<typeof vi.fn>).mockResolvedValue('');
      (yaml.load as ReturnType<typeof vi.fn>).mockReturnValue(mockParsed);

      // First call
      await configManager.loadProjectEndpoints('default_project');
      // Clear cache
      configManager.clearCache();
      // Second call should reload
      await configManager.loadProjectEndpoints('default_project');

      expect(fs.readFile).toHaveBeenCalledTimes(2);
    });
  });
});

describe('createEndpointConfigManager factory', () => {
  it('should create an EndpointConfigManager instance', () => {
    const manager = createEndpointConfigManager('/test/path');
    expect(manager).toBeInstanceOf(EndpointConfigManager);
  });
});
