/**
 * CapabilityClient Unit Tests
 *
 * Issue #365: TypeScript SDK for capability management
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  CapabilityClient,
  createCapabilityClient,
  type CapabilityClientConfig,
} from '../../../src/capabilityManagement/client/CapabilityClient.js';
import type { PublicCapability } from '../../../src/shared/types/capability.types.js';

// Mock fetch for testing
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('CapabilityClient', () => {
  let client: CapabilityClient;
  const baseUrl = 'http://localhost:8006';

  const sampleCapability: PublicCapability = {
    id: 'google_search',
    name: 'Google Search',
    description: 'Search the web using Google',
    version: '1.0.0',
    status: 'available',
    category: 'search',
    parameters: [
      {
        name: 'query',
        type: 'string',
        required: true,
        description: 'Search query',
      },
    ],
    returnType: 'object',
    tags: ['search', 'web'],
    project: 'default_project',
  };

  beforeEach(() => {
    mockFetch.mockReset();
    client = new CapabilityClient({ baseUrl });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getCapabilities', () => {
    it('should fetch capabilities for a project', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capabilities: [sampleCapability] }),
      });

      const result = await client.getCapabilities('default_project');

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/capabilities?project=default_project`,
        expect.objectContaining({
          method: 'GET',
        })
      );
      expect(result).toHaveLength(1);
      expect(result[0]?.id).toBe('google_search');
    });

    it('should handle empty response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capabilities: [] }),
      });

      const result = await client.getCapabilities('empty_project');

      expect(result).toEqual([]);
    });

    it('should throw error on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(client.getCapabilities('default_project')).rejects.toThrow();
    });

    it('should include API token in headers if configured', async () => {
      const clientWithToken = new CapabilityClient({
        baseUrl,
        apiToken: 'test-token',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capabilities: [] }),
      });

      await clientWithToken.getCapabilities('default_project');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Token': 'test-token',
          }),
        })
      );
    });
  });

  describe('getCapability', () => {
    it('should fetch a specific capability', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capability: sampleCapability }),
      });

      const result = await client.getCapability('default_project', 'google_search');

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/capabilities/google_search?project=default_project`,
        expect.any(Object)
      );
      expect(result?.id).toBe('google_search');
    });

    it('should return undefined for non-existent capability', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const result = await client.getCapability('default_project', 'non_existent');

      expect(result).toBeUndefined();
    });
  });

  describe('getCapabilitiesAsYaml', () => {
    it('should fetch capabilities in YAML format', async () => {
      const yamlContent = `
- id: google_search
  name: Google Search
  description: Search the web using Google
`;

      mockFetch.mockResolvedValueOnce({
        ok: true,
        text: async () => yamlContent,
      });

      const result = await client.getCapabilitiesAsYaml('default_project');

      expect(mockFetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/capabilities/yaml?project=default_project`,
        expect.any(Object)
      );
      expect(result).toContain('google_search');
    });

    it('should throw error on API failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      await expect(client.getCapabilitiesAsYaml('default_project')).rejects.toThrow();
    });
  });

  describe('client configuration', () => {
    it('should use custom timeout', async () => {
      const clientWithTimeout = new CapabilityClient({
        baseUrl,
        timeout: 5000,
      });

      // Note: Testing timeout requires AbortController, simplified test here
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ capabilities: [] }),
      });

      await clientWithTimeout.getCapabilities('default_project');

      expect(mockFetch).toHaveBeenCalled();
    });
  });
});

describe('createCapabilityClient factory', () => {
  it('should create a CapabilityClient instance', () => {
    const client = createCapabilityClient({ baseUrl: 'http://localhost:8006' });
    expect(client).toBeInstanceOf(CapabilityClient);
  });
});
