/**
 * Catalog Types Unit Tests
 *
 * Issue #380: Capability Catalog type definitions
 * Tests for type exports and Zod schema validation
 */

import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import {
  ResponseSchemaPropertySchema,
  ResponseSchemaSchema,
  CatalogCapabilitySchema,
  CapabilityCatalogSchema,
  CatalogOptionsSchema,
  CatalogGenerationResultSchema,
  type ResponseSchemaProperty,
  type ResponseSchema,
  type CatalogCapability,
  type CapabilityCatalog,
  type CatalogOptions,
  type CatalogGenerationResult,
} from '../../../../src/capabilities/types/catalog.js';

describe('Catalog Types', () => {
  describe('ResponseSchemaPropertySchema', () => {
    it('should validate a simple property', () => {
      const property: ResponseSchemaProperty = {
        type: 'string',
        description: 'A simple string property',
      };

      const result = ResponseSchemaPropertySchema.safeParse(property);
      expect(result.success).toBe(true);
    });

    it('should validate an array property with items', () => {
      const property: ResponseSchemaProperty = {
        type: 'array',
        description: 'An array of items',
        items: {
          type: 'object',
          properties: {
            title: { type: 'string', description: 'Title' },
          },
        },
      };

      const result = ResponseSchemaPropertySchema.safeParse(property);
      expect(result.success).toBe(true);
    });

    it('should validate nested object property', () => {
      const property: ResponseSchemaProperty = {
        type: 'object',
        description: 'A nested object',
        properties: {
          name: { type: 'string', description: 'Name' },
          age: { type: 'integer', description: 'Age' },
        },
      };

      const result = ResponseSchemaPropertySchema.safeParse(property);
      expect(result.success).toBe(true);
    });

    it('should reject property without type', () => {
      const property = {
        description: 'Missing type',
      };

      const result = ResponseSchemaPropertySchema.safeParse(property);
      expect(result.success).toBe(false);
    });
  });

  describe('ResponseSchemaSchema', () => {
    it('should validate a complete response schema', () => {
      const schema: ResponseSchema = {
        search_results: {
          type: 'array',
          description: 'Search results',
          items: {
            type: 'object',
            properties: {
              title: { type: 'string', description: 'Result title' },
              link: { type: 'string', description: 'Result URL' },
            },
          },
        },
        count: {
          type: 'integer',
          description: 'Total count',
        },
      };

      const result = ResponseSchemaSchema.safeParse(schema);
      expect(result.success).toBe(true);
    });

    it('should validate an empty schema', () => {
      const schema: ResponseSchema = {};

      const result = ResponseSchemaSchema.safeParse(schema);
      expect(result.success).toBe(true);
    });
  });

  describe('CatalogCapabilitySchema', () => {
    it('should validate a capability with responseSchema', () => {
      const capability: CatalogCapability = {
        id: 'google_search',
        name: 'Google Search',
        description: 'Web search capability',
        version: '1.0.0',
        category: 'search',
        status: 'available',
        parameters: [
          {
            name: 'queries',
            type: 'array',
            required: true,
            description: 'Search queries',
          },
        ],
        responseSchema: {
          results: {
            type: 'array',
            description: 'Search results',
          },
        },
        tags: ['search', 'web'],
      };

      const result = CatalogCapabilitySchema.safeParse(capability);
      expect(result.success).toBe(true);
    });

    it('should validate capability without optional fields', () => {
      const capability = {
        id: 'simple_cap',
        name: 'Simple Capability',
        description: 'A simple capability',
        version: '1.0.0',
        category: 'utility',
        status: 'available',
        parameters: [],
      };

      const result = CatalogCapabilitySchema.safeParse(capability);
      expect(result.success).toBe(true);
    });

    it('should reject capability without required fields', () => {
      const capability = {
        id: 'incomplete',
        name: 'Incomplete',
        // Missing description, version, category, status, parameters
      };

      const result = CatalogCapabilitySchema.safeParse(capability);
      expect(result.success).toBe(false);
    });
  });

  describe('CapabilityCatalogSchema', () => {
    it('should validate a complete catalog', () => {
      const catalog: CapabilityCatalog = {
        version: '1.0.0',
        generatedAt: new Date().toISOString(),
        capabilities: [
          {
            id: 'test_cap',
            name: 'Test Capability',
            description: 'A test capability',
            version: '1.0.0',
            category: 'test',
            status: 'available',
            parameters: [],
          },
        ],
        summary: {
          total: 1,
          byCategory: { test: 1 },
          byStatus: { available: 1, unavailable: 0, deprecated: 0 },
          withResponseSchema: 0,
          withoutResponseSchema: 1,
        },
      };

      const result = CapabilityCatalogSchema.safeParse(catalog);
      expect(result.success).toBe(true);
    });
  });

  describe('CatalogOptionsSchema', () => {
    it('should validate default options', () => {
      const options: CatalogOptions = {
        outputFormats: ['json'],
        outputDir: './output',
      };

      const result = CatalogOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should validate options with all formats', () => {
      const options: CatalogOptions = {
        outputFormats: ['json', 'yaml', 'markdown'],
        outputDir: './output',
        includeExamples: true,
        includeMetadata: true,
      };

      const result = CatalogOptionsSchema.safeParse(options);
      expect(result.success).toBe(true);
    });

    it('should reject invalid output format', () => {
      const options = {
        outputFormats: ['xml'], // Invalid format
        outputDir: './output',
      };

      const result = CatalogOptionsSchema.safeParse(options);
      expect(result.success).toBe(false);
    });
  });

  describe('CatalogGenerationResultSchema', () => {
    it('should validate a successful result', () => {
      const result: CatalogGenerationResult = {
        success: true,
        catalogPath: '/path/to/catalog.json',
        catalog: {
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
        },
        generatedFiles: ['catalog.json'],
        warnings: [],
      };

      const parseResult = CatalogGenerationResultSchema.safeParse(result);
      expect(parseResult.success).toBe(true);
    });

    it('should validate a failed result with errors', () => {
      const result: CatalogGenerationResult = {
        success: false,
        catalogPath: '',
        generatedFiles: [],
        warnings: [],
        errors: ['Failed to read capability files'],
      };

      const parseResult = CatalogGenerationResultSchema.safeParse(result);
      expect(parseResult.success).toBe(true);
    });
  });

  describe('Type inference', () => {
    it('should correctly infer ResponseSchemaProperty type', () => {
      const prop: z.infer<typeof ResponseSchemaPropertySchema> = {
        type: 'string',
        description: 'Test',
      };
      expect(prop.type).toBe('string');
    });

    it('should correctly infer CatalogCapability type', () => {
      const cap: z.infer<typeof CatalogCapabilitySchema> = {
        id: 'test',
        name: 'Test',
        description: 'Test',
        version: '1.0.0',
        category: 'test',
        status: 'available',
        parameters: [],
      };
      expect(cap.id).toBe('test');
    });
  });
});
