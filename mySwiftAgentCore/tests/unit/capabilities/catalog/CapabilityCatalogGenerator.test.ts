/**
 * CapabilityCatalogGenerator Unit Tests
 *
 * Issue #380: Capability Catalog generation tests
 * Tests YAML scanning, responseSchema extraction, and export functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import {
  CapabilityCatalogGenerator,
  createCapabilityCatalogGenerator,
} from '../../../../src/capabilities/catalog/CapabilityCatalogGenerator.js';
import type { CatalogOptions, CatalogCapability } from '../../../../src/capabilities/types/catalog.js';

// Mock fs/promises
vi.mock('fs/promises');
vi.mock('path', async (importOriginal) => {
  const actual = await importOriginal<typeof import('path')>();
  return {
    ...actual,
    default: actual,
  };
});

describe('CapabilityCatalogGenerator', () => {
  const mockCapabilityYaml = `
id: google_search
name: Google Search
description: Web search capability
version: "1.0.0"
status: available
category: search
parameters:
  - name: queries
    type: array
    required: true
    description: Search queries
returnType: object
responseSchema:
  search_results:
    type: array
    description: Search results list
    items:
      type: object
      properties:
        title:
          type: string
          description: Result title
        link:
          type: string
          description: Result URL
  count:
    type: integer
    description: Total count
tags:
  - search
  - web
`;

  const mockCapabilityWithoutSchema = `
id: simple_cap
name: Simple Capability
description: A simple capability without responseSchema
version: "1.0.0"
status: available
category: utility
parameters: []
returnType: string
`;

  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create instance with default base path', () => {
      const generator = new CapabilityCatalogGenerator();
      expect(generator).toBeInstanceOf(CapabilityCatalogGenerator);
    });

    it('should create instance with custom base path', () => {
      const generator = new CapabilityCatalogGenerator('/custom/path');
      expect(generator).toBeInstanceOf(CapabilityCatalogGenerator);
    });
  });

  describe('factory function', () => {
    it('should create generator instance', () => {
      const generator = createCapabilityCatalogGenerator();
      expect(generator).toBeInstanceOf(CapabilityCatalogGenerator);
    });

    it('should create generator with options', () => {
      const generator = createCapabilityCatalogGenerator('/custom/path');
      expect(generator).toBeInstanceOf(CapabilityCatalogGenerator);
    });
  });

  describe('scanCapabilities', () => {
    it('should scan and parse capability files', async () => {
      // Mock directory reading
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'google_search.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
        { name: 'simple_cap.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);

      // Mock file reading
      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        if (String(filePath).includes('google_search')) {
          return mockCapabilityYaml;
        }
        return mockCapabilityWithoutSchema;
      });

      const generator = new CapabilityCatalogGenerator('/test/config/capabilities');
      const result = await generator.scanCapabilities('default_project');

      expect(result.capabilities).toHaveLength(2);
      expect(result.warnings).toHaveLength(0);
    });

    it('should handle missing directory gracefully', async () => {
      vi.mocked(fs.readdir).mockRejectedValue(new Error('ENOENT: no such file or directory'));

      const generator = new CapabilityCatalogGenerator('/test/config');
      const result = await generator.scanCapabilities('nonexistent_project');

      expect(result.capabilities).toHaveLength(0);
      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it('should skip non-YAML files', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'google_search.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
        { name: 'readme.md', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
        { name: 'config.json', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);

      vi.mocked(fs.readFile).mockResolvedValue(mockCapabilityYaml);

      const generator = new CapabilityCatalogGenerator('/test/config');
      const result = await generator.scanCapabilities('default_project');

      // Should only process the YAML file
      expect(fs.readFile).toHaveBeenCalledTimes(1);
    });

    it('should add warning for YAML parse errors', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'invalid.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);

      vi.mocked(fs.readFile).mockResolvedValue('invalid: yaml: content: [');

      const generator = new CapabilityCatalogGenerator('/test/config');
      const result = await generator.scanCapabilities('default_project');

      expect(result.capabilities).toHaveLength(0);
      expect(result.warnings.length).toBeGreaterThan(0);
    });

    it('should skip index.yaml files', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'index.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
        { name: 'google_search.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);

      vi.mocked(fs.readFile).mockResolvedValue(mockCapabilityYaml);

      const generator = new CapabilityCatalogGenerator('/test/config');
      const result = await generator.scanCapabilities('default_project');

      // Should only process google_search.yaml
      expect(fs.readFile).toHaveBeenCalledTimes(1);
    });
  });

  describe('extractResponseSchema', () => {
    it('should extract responseSchema from capability', () => {
      const generator = new CapabilityCatalogGenerator();
      const capability: CatalogCapability = {
        id: 'test',
        name: 'Test',
        description: 'Test capability',
        version: '1.0.0',
        category: 'test',
        status: 'available',
        parameters: [],
        responseSchema: {
          result: {
            type: 'string',
            description: 'The result',
          },
        },
      };

      const schema = generator.extractResponseSchema(capability);
      expect(schema).toBeDefined();
      expect(schema?.result.type).toBe('string');
    });

    it('should return undefined when no responseSchema', () => {
      const generator = new CapabilityCatalogGenerator();
      const capability: CatalogCapability = {
        id: 'test',
        name: 'Test',
        description: 'Test capability',
        version: '1.0.0',
        category: 'test',
        status: 'available',
        parameters: [],
      };

      const schema = generator.extractResponseSchema(capability);
      expect(schema).toBeUndefined();
    });
  });

  describe('generateCatalog', () => {
    beforeEach(() => {
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'google_search.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);
      vi.mocked(fs.readFile).mockResolvedValue(mockCapabilityYaml);
      vi.mocked(fs.mkdir).mockResolvedValue(undefined);
      vi.mocked(fs.writeFile).mockResolvedValue(undefined);
    });

    it('should generate catalog with default options', async () => {
      const generator = new CapabilityCatalogGenerator('/test/config/capabilities');
      const options: CatalogOptions = {
        outputFormats: ['json'],
        outputDir: '/test/output',
      };

      const result = await generator.generateCatalog('default_project', options);

      expect(result.success).toBe(true);
      expect(result.catalog?.capabilities).toHaveLength(1);
      expect(result.catalog?.summary.total).toBe(1);
    });

    it('should generate JSON, YAML, and Markdown formats', async () => {
      const generator = new CapabilityCatalogGenerator('/test/config/capabilities');
      const options: CatalogOptions = {
        outputFormats: ['json', 'yaml', 'markdown'],
        outputDir: '/test/output',
      };

      const result = await generator.generateCatalog('default_project', options);

      expect(result.success).toBe(true);
      expect(result.generatedFiles).toContain('capabilities-catalog.json');
      expect(result.generatedFiles).toContain('capabilities-catalog.yaml');
      expect(result.generatedFiles).toContain('capabilities-catalog.md');
    });

    it('should calculate summary statistics correctly', async () => {
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'cap1.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
        { name: 'cap2.yaml', isFile: () => true, isDirectory: () => false } as unknown as fs.Dirent,
      ]);

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        if (String(filePath).includes('cap1')) {
          return mockCapabilityYaml;
        }
        return mockCapabilityWithoutSchema;
      });

      const generator = new CapabilityCatalogGenerator('/test/config/capabilities');
      const options: CatalogOptions = {
        outputFormats: ['json'],
        outputDir: '/test/output',
      };

      const result = await generator.generateCatalog('default_project', options);

      expect(result.catalog?.summary.total).toBe(2);
      expect(result.catalog?.summary.withResponseSchema).toBe(1);
      expect(result.catalog?.summary.withoutResponseSchema).toBe(1);
    });

    it('should handle write errors gracefully', async () => {
      vi.mocked(fs.writeFile).mockRejectedValue(new Error('Write permission denied'));

      const generator = new CapabilityCatalogGenerator('/test/config/capabilities');
      const options: CatalogOptions = {
        outputFormats: ['json'],
        outputDir: '/test/output',
      };

      const result = await generator.generateCatalog('default_project', options);

      expect(result.success).toBe(false);
      expect(result.errors?.length).toBeGreaterThan(0);
    });
  });

  describe('exportToJson', () => {
    it('should export catalog to JSON format', async () => {
      vi.mocked(fs.mkdir).mockResolvedValue(undefined);
      vi.mocked(fs.writeFile).mockResolvedValue(undefined);

      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [],
        summary: {
          total: 0,
          byCategory: {},
          byStatus: { available: 0, unavailable: 0, deprecated: 0 },
          withResponseSchema: 0,
          withoutResponseSchema: 0,
        },
      };

      await generator.exportToJson(catalog, '/test/output');

      expect(fs.writeFile).toHaveBeenCalledWith(
        expect.stringContaining('capabilities-catalog.json'),
        expect.any(String),
        'utf-8'
      );
    });
  });

  describe('exportToYaml', () => {
    it('should export catalog to YAML format', async () => {
      vi.mocked(fs.mkdir).mockResolvedValue(undefined);
      vi.mocked(fs.writeFile).mockResolvedValue(undefined);

      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [],
        summary: {
          total: 0,
          byCategory: {},
          byStatus: { available: 0, unavailable: 0, deprecated: 0 },
          withResponseSchema: 0,
          withoutResponseSchema: 0,
        },
      };

      await generator.exportToYaml(catalog, '/test/output');

      expect(fs.writeFile).toHaveBeenCalledWith(
        expect.stringContaining('capabilities-catalog.yaml'),
        expect.any(String),
        'utf-8'
      );
    });
  });

  describe('exportToMarkdown', () => {
    it('should export catalog to Markdown format', async () => {
      vi.mocked(fs.mkdir).mockResolvedValue(undefined);
      vi.mocked(fs.writeFile).mockResolvedValue(undefined);

      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [
          {
            id: 'test',
            name: 'Test Capability',
            description: 'A test capability',
            version: '1.0.0',
            category: 'test',
            status: 'available' as const,
            parameters: [],
            responseSchema: {
              result: { type: 'string', description: 'Result' },
            },
          },
        ],
        summary: {
          total: 1,
          byCategory: { test: 1 },
          byStatus: { available: 1, unavailable: 0, deprecated: 0 },
          withResponseSchema: 1,
          withoutResponseSchema: 0,
        },
      };

      await generator.exportToMarkdown(catalog, '/test/output');

      expect(fs.writeFile).toHaveBeenCalledWith(
        expect.stringContaining('capabilities-catalog.md'),
        expect.stringContaining('# Capability Catalog'),
        'utf-8'
      );
    });

    it('should include responseSchema in Markdown', async () => {
      vi.mocked(fs.mkdir).mockResolvedValue(undefined);
      let writtenContent = '';
      vi.mocked(fs.writeFile).mockImplementation(async (_path, content) => {
        writtenContent = content as string;
      });

      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [
          {
            id: 'test',
            name: 'Test',
            description: 'Test',
            version: '1.0.0',
            category: 'test',
            status: 'available' as const,
            parameters: [],
            responseSchema: {
              result: { type: 'string', description: 'The result' },
            },
          },
        ],
        summary: {
          total: 1,
          byCategory: { test: 1 },
          byStatus: { available: 1, unavailable: 0, deprecated: 0 },
          withResponseSchema: 1,
          withoutResponseSchema: 0,
        },
      };

      await generator.exportToMarkdown(catalog, '/test/output');

      expect(writtenContent).toContain('Response Schema');
      expect(writtenContent).toContain('result');
    });
  });

  describe('formatForAIPrompt', () => {
    it('should format catalog for AI prompt injection', () => {
      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [
          {
            id: 'google_search',
            name: 'Google Search',
            description: 'Web search',
            version: '1.0.0',
            category: 'search',
            status: 'available' as const,
            parameters: [
              { name: 'queries', type: 'array', required: true, description: 'Search queries' },
            ],
            responseSchema: {
              search_results: { type: 'array', description: 'Results' },
            },
          },
        ],
        summary: {
          total: 1,
          byCategory: { search: 1 },
          byStatus: { available: 1, unavailable: 0, deprecated: 0 },
          withResponseSchema: 1,
          withoutResponseSchema: 0,
        },
      };

      const formatted = generator.formatForAIPrompt(catalog);

      expect(formatted).toContain('google_search');
      expect(formatted).toContain('Google Search');
      expect(formatted).toContain('search_results');
    });

    it('should only include available capabilities', () => {
      const generator = new CapabilityCatalogGenerator();
      const catalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [
          {
            id: 'available_cap',
            name: 'Available',
            description: 'Available capability',
            version: '1.0.0',
            category: 'test',
            status: 'available' as const,
            parameters: [],
          },
          {
            id: 'unavailable_cap',
            name: 'Unavailable',
            description: 'Unavailable capability',
            version: '1.0.0',
            category: 'test',
            status: 'unavailable' as const,
            parameters: [],
          },
        ],
        summary: {
          total: 2,
          byCategory: { test: 2 },
          byStatus: { available: 1, unavailable: 1, deprecated: 0 },
          withResponseSchema: 0,
          withoutResponseSchema: 2,
        },
      };

      const formatted = generator.formatForAIPrompt(catalog);

      expect(formatted).toContain('available_cap');
      expect(formatted).not.toContain('unavailable_cap');
    });
  });
});
