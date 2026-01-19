/**
 * Catalog Types - Type definitions for capability catalog generation
 *
 * Issue #380: Capability Catalog type definitions
 * Defines types for responseSchema, catalog entries, and generation options
 */

import { z } from 'zod';

// ============================================
// ResponseSchema Types
// ============================================

/**
 * ResponseSchemaProperty - Individual property in a response schema
 * Supports nested objects and arrays
 */
export const ResponseSchemaPropertySchema: z.ZodType<ResponseSchemaProperty> = z.lazy(() =>
  z.object({
    type: z.string(),
    description: z.string().optional(),
    items: ResponseSchemaPropertySchema.optional(),
    properties: z.record(ResponseSchemaPropertySchema).optional(),
    required: z.array(z.string()).optional(),
    format: z.string().optional(),
    minimum: z.number().optional(),
    maximum: z.number().optional(),
    pattern: z.string().optional(),
    enum: z.array(z.unknown()).optional(),
  })
);

export interface ResponseSchemaProperty {
  type: string;
  description?: string;
  items?: ResponseSchemaProperty;
  properties?: Record<string, ResponseSchemaProperty>;
  required?: string[];
  format?: string;
  minimum?: number;
  maximum?: number;
  pattern?: string;
  enum?: unknown[];
}

/**
 * ResponseSchema - Complete response schema definition
 * Maps field names to their schema definitions
 */
export const ResponseSchemaSchema = z.record(ResponseSchemaPropertySchema);

export type ResponseSchema = Record<string, ResponseSchemaProperty>;

// ============================================
// Capability Parameter Types
// ============================================

/**
 * CapabilityParameter - Parameter definition for capabilities
 */
export const CatalogParameterSchema = z.object({
  name: z.string(),
  type: z.string(),
  required: z.boolean().optional().default(false),
  description: z.string().optional(),
  defaultValue: z.unknown().optional(),
  validation: z
    .object({
      pattern: z.string().optional(),
      min: z.number().optional(),
      max: z.number().optional(),
      enum: z.array(z.unknown()).optional(),
    })
    .optional(),
});

export type CatalogParameter = z.infer<typeof CatalogParameterSchema>;

// ============================================
// Catalog Capability Types
// ============================================

/**
 * CatalogCapability - Capability entry in the catalog
 * Includes responseSchema for output documentation
 */
export const CatalogCapabilitySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.string(),
  category: z.string(),
  status: z.enum(['available', 'unavailable', 'deprecated']),
  parameters: z.array(CatalogParameterSchema),
  returnType: z.string().optional(),
  responseSchema: ResponseSchemaSchema.optional(),
  tags: z.array(z.string()).optional(),
  examples: z
    .array(
      z.object({
        description: z.string(),
        input: z.record(z.unknown()).optional(),
        expectedOutput: z.unknown().optional(),
        taskflow_step: z
          .object({
            id: z.string(),
            type: z.string(),
            config: z.record(z.unknown()),
            params: z.record(z.unknown()),
          })
          .optional(),
        output_mapping: z.record(z.string()).optional(),
      })
    )
    .optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type CatalogCapability = z.infer<typeof CatalogCapabilitySchema>;

// ============================================
// Catalog Summary Types
// ============================================

/**
 * CatalogSummary - Summary statistics for the catalog
 */
export const CatalogSummarySchema = z.object({
  total: z.number(),
  byCategory: z.record(z.number()),
  byStatus: z.object({
    available: z.number(),
    unavailable: z.number(),
    deprecated: z.number(),
  }),
  withResponseSchema: z.number(),
  withoutResponseSchema: z.number(),
});

export type CatalogSummary = z.infer<typeof CatalogSummarySchema>;

// ============================================
// Capability Catalog Types
// ============================================

/**
 * CapabilityCatalog - Complete catalog of capabilities
 */
export const CapabilityCatalogSchema = z.object({
  version: z.string(),
  generatedAt: z.string(),
  capabilities: z.array(CatalogCapabilitySchema),
  summary: CatalogSummarySchema,
});

export type CapabilityCatalog = z.infer<typeof CapabilityCatalogSchema>;

// ============================================
// Catalog Options Types
// ============================================

/**
 * CatalogOutputFormat - Supported output formats
 */
export const CatalogOutputFormatSchema = z.enum(['json', 'yaml', 'markdown']);

export type CatalogOutputFormat = z.infer<typeof CatalogOutputFormatSchema>;

/**
 * CatalogOptions - Options for catalog generation
 */
export const CatalogOptionsSchema = z.object({
  outputFormats: z.array(CatalogOutputFormatSchema),
  outputDir: z.string(),
  includeExamples: z.boolean().optional().default(true),
  includeMetadata: z.boolean().optional().default(true),
  filterCategories: z.array(z.string()).optional(),
  filterStatus: z.array(z.enum(['available', 'unavailable', 'deprecated'])).optional(),
});

export type CatalogOptions = z.infer<typeof CatalogOptionsSchema>;

// ============================================
// Catalog Generation Result Types
// ============================================

/**
 * CatalogGenerationResult - Result of catalog generation
 */
export const CatalogGenerationResultSchema = z.object({
  success: z.boolean(),
  catalogPath: z.string(),
  catalog: CapabilityCatalogSchema.optional(),
  generatedFiles: z.array(z.string()),
  warnings: z.array(z.string()),
  errors: z.array(z.string()).optional(),
});

export type CatalogGenerationResult = z.infer<typeof CatalogGenerationResultSchema>;

// ============================================
// Scan Result Types
// ============================================

/**
 * CapabilityScanResult - Result of scanning capability files
 */
export const CapabilityScanResultSchema = z.object({
  capabilities: z.array(CatalogCapabilitySchema),
  warnings: z.array(z.string()),
  errors: z.array(z.string()).optional(),
});

export type CapabilityScanResult = z.infer<typeof CapabilityScanResultSchema>;
