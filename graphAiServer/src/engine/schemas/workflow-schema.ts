/**
 * Zod Schema Definitions for TaskFlow Engine
 *
 * This file defines Zod schemas for validating workflow definitions.
 * All schemas enforce security constraints including HTTPS requirements.
 *
 * @module engine/schemas/workflow-schema
 * @see Issue #348
 * @see Issue #352 - URL variable reference validation fix
 */

import { z } from 'zod';

import {
  startsWithValidVariable,
  URL_VALIDATION_SHORT_MESSAGE,
} from '../constants/variable-patterns.js';

// ============================================================
// Basic Type Schemas
// ============================================================

/** HTTP Methods */
export const HttpMethodSchema = z.enum(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']);

/** Node Types */
export const NodeTypeSchema = z.enum(['api_rest', 'code_js', 'transform']);

/** Simple Types for I/O Schema */
export const SimpleTypeSchema = z.enum([
  'string',
  'number',
  'boolean',
  'array',
  'object',
  'null',
]);

/** I/O Schema - maps field names to simple types */
export const IOSchema = z.record(z.string(), SimpleTypeSchema);

// ============================================================
// URL Validation Pattern
// ============================================================

/**
 * Check if HTTP and local IPs are allowed (development mode)
 * Controlled by environment variables:
 * - TASKFLOW_ALLOW_HTTP=true - Allow HTTP protocol
 * - TASKFLOW_ALLOW_LOCAL=true - Allow localhost and private IPs
 */
function isDevModeEnabled(): boolean {
  return (
    process.env.TASKFLOW_ALLOW_HTTP === 'true' &&
    process.env.TASKFLOW_ALLOW_LOCAL === 'true'
  );
}

/**
 * URL validation for TaskFlow V2
 *
 * Allows:
 * - https:// URLs
 * - http:// URLs (only in dev mode)
 * - All TaskFlow variable references: ${inputs.*}, ${step_id.output.*}, ${env.*}, ${secrets.*}
 * - Combinations like ${inputs.base_url}/api/v1/endpoint
 *
 * @see Issue #352 - Fixed to allow all TaskFlow variable types
 */

/** Custom URL validator with HTTPS enforcement (relaxed in dev mode) */
const httpsUrlSchema = z.string().refine(
  (url) => {
    // Issue #352: Allow all valid TaskFlow variable references
    // Supports: ${inputs.*}, ${step_id.output.*}, ${env.*}, ${secrets.*}
    // Also supports trailing paths like ${inputs.url}/api/v1/endpoint
    if (startsWithValidVariable(url)) {
      return true;
    }
    // In dev mode, allow both HTTP and HTTPS
    if (isDevModeEnabled()) {
      return url.startsWith('https://') || url.startsWith('http://');
    }
    // Otherwise, must start with https://
    return url.startsWith('https://');
  },
  {
    message: URL_VALIDATION_SHORT_MESSAGE,
  }
);

// ============================================================
// Node Configuration Schemas
// ============================================================

/** REST API Node Configuration */
export const ApiRestConfigSchema = z.object({
  step_type: z.literal('api_rest').optional(), // For compatibility with expertAgent schema
  method: HttpMethodSchema,
  url: httpsUrlSchema,
  headers: z.record(z.string(), z.string()).optional(),
  body: z.unknown().optional(),
  timeout_ms: z.number().int().positive().default(30000),
  verify_ssl: z.boolean().default(true),
});

/** JavaScript Node Configuration */
export const CodeJsConfigSchema = z.object({
  step_type: z.literal('code_js').optional(), // For compatibility with expertAgent schema
  path: z
    .string()
    .min(1)
    .refine((p) => !p.includes('..'), {
      message: 'Path must not contain ".." (path traversal)',
    }),
  function_name: z.string().min(1).default('main'),
});

/** Transform Node Configuration */
export const TransformConfigSchema = z.object({
  step_type: z.literal('transform').optional(), // For compatibility with expertAgent schema
  mode: z.enum(['template', 'concat', 'map', 'merge']).default('template'),
  template: z.string().optional(),
  separator: z.string().optional(),
  fields: z.array(z.string()).optional(),
  source_field: z.string().optional(),
  strategy: z.enum(['shallow', 'deep']).optional(),
});

// ============================================================
// Step Schemas
// ============================================================

/** Base Step Schema (without type-specific config) */
const BaseStepFieldsSchema = z.object({
  id: z
    .string()
    .min(1)
    .regex(/^[a-zA-Z_][a-zA-Z0-9_-]*$/, {
      message: 'Step ID must start with a letter or underscore and contain only alphanumeric characters, underscores, and hyphens',
    }),
  description: z.string().optional(),
  params: z.record(z.string(), z.unknown()).default({}),
  input_schema: IOSchema.optional(),
  output_schema: IOSchema.optional(),
});

/** API REST Step Schema */
export const ApiRestStepSchema = BaseStepFieldsSchema.extend({
  type: z.literal('api_rest'),
  config: ApiRestConfigSchema,
});

/** Code JS Step Schema */
export const CodeJsStepSchema = BaseStepFieldsSchema.extend({
  type: z.literal('code_js'),
  config: CodeJsConfigSchema,
});

/** Transform Step Schema */
export const TransformStepSchema = BaseStepFieldsSchema.extend({
  type: z.literal('transform'),
  config: TransformConfigSchema,
});

/** Single Step Schema (union of all step types) */
export const SingleStepSchema = z.discriminatedUnion('type', [
  ApiRestStepSchema,
  CodeJsStepSchema,
  TransformStepSchema,
]);

/** Parallel Block Schema - uses lazy evaluation for recursive structure */
export const ParallelBlockSchema = z.object({
  type: z.literal('parallel'),
  steps: z.array(z.lazy(() => SingleStepSchema)).min(1, {
    message: 'Parallel block must contain at least one step',
  }),
});

// ============================================================
// Condition Expression Schema (for conditional blocks)
// ============================================================

/**
 * Condition expression format: ${variable.path} OPERATOR VALUE
 * Security: Uses whitelist approach - only primitives allowed
 */
export const ConditionExpressionSchema = z.string().refine(
  (expr) => {
    // Pattern: ${var.path} OPERATOR VALUE
    // VALUE must be: string literal, number, boolean, or null
    const pattern = /^\$\{[a-zA-Z_][a-zA-Z0-9_.]*\}\s*(==|!=|>|<|>=|<=)\s*('[^']*'|"[^"]*"|-?\d+(\.\d+)?|true|false|null)$/;
    return pattern.test(expr.trim());
  },
  {
    message: "Invalid condition expression format. Use: ${var.path} == 'value' or ${var} > 10",
  }
);

// Forward declare StepSchema type for recursive use
type StepSchemaType = z.ZodUnion<[typeof SingleStepSchema, typeof ParallelBlockSchema, z.ZodObject<any>]>;

/** Conditional Block Schema */
export const ConditionalBlockSchema = z.object({
  type: z.literal('conditional'),
  condition: ConditionExpressionSchema,
  then: z.array(z.lazy((): StepSchemaType => StepSchema)).min(1, {
    message: 'Conditional block must have at least one step in then branch',
  }),
  else: z.array(z.lazy((): StepSchemaType => StepSchema)).optional(),
});

/** Step Schema (single step, parallel block, or conditional block) */
export const StepSchema = z.union([SingleStepSchema, ParallelBlockSchema, ConditionalBlockSchema]);

// ============================================================
// Workflow Definition Schema
// ============================================================

/** Complete Workflow Definition Schema */
export const WorkflowDefinitionSchema = z.object({
  workflow_name: z
    .string()
    .min(1)
    .regex(/^[a-zA-Z_][a-zA-Z0-9_-]*$/, {
      message:
        'Workflow name must start with a letter or underscore and contain only alphanumeric characters, underscores, and hyphens',
    }),
  description: z.string().optional(),
  input_schema: IOSchema,
  output_schema: IOSchema,
  steps: z.array(StepSchema).min(1, {
    message: 'Workflow must contain at least one step',
  }),
  output: z.record(z.string(), z.string()),
});

// ============================================================
// API Request Schemas
// ============================================================

/** Workflow Execution Request Schema */
export const WorkflowExecutionRequestSchema = z.object({
  workflow_name: z.string().optional(),
  definition: WorkflowDefinitionSchema.optional(),
  inputs: z.record(z.string(), z.unknown()),
  project: z.string().optional(),
}).refine(
  (data) => data.workflow_name !== undefined || data.definition !== undefined,
  {
    message: 'Either workflow_name or definition must be provided',
  }
);

/** Workflow Validation Request Schema */
export const WorkflowValidationRequestSchema = z.object({
  definition: WorkflowDefinitionSchema,
});

// ============================================================
// Inferred Types
// ============================================================

export type HttpMethod = z.infer<typeof HttpMethodSchema>;
export type NodeType = z.infer<typeof NodeTypeSchema>;
export type SimpleType = z.infer<typeof SimpleTypeSchema>;
export type IOSchemaType = z.infer<typeof IOSchema>;
export type ApiRestConfig = z.infer<typeof ApiRestConfigSchema>;
export type CodeJsConfig = z.infer<typeof CodeJsConfigSchema>;
export type TransformConfig = z.infer<typeof TransformConfigSchema>;
export type ApiRestStep = z.infer<typeof ApiRestStepSchema>;
export type CodeJsStep = z.infer<typeof CodeJsStepSchema>;
export type TransformStep = z.infer<typeof TransformStepSchema>;
export type SingleStep = z.infer<typeof SingleStepSchema>;
export type ParallelBlock = z.infer<typeof ParallelBlockSchema>;
export type ConditionalBlock = z.infer<typeof ConditionalBlockSchema>;
export type Step = z.infer<typeof StepSchema>;
export type WorkflowDefinition = z.infer<typeof WorkflowDefinitionSchema>;
export type WorkflowExecutionRequest = z.infer<typeof WorkflowExecutionRequestSchema>;
export type WorkflowValidationRequest = z.infer<typeof WorkflowValidationRequestSchema>;

// ============================================================
// Validation Helper Functions
// ============================================================

/**
 * Validate a workflow definition
 * @param definition - The workflow definition to validate
 * @returns Validation result with parsed data or errors
 */
export function validateWorkflowDefinition(
  definition: unknown
): { success: true; data: WorkflowDefinition } | { success: false; errors: z.ZodError } {
  const result = WorkflowDefinitionSchema.safeParse(definition);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return { success: false, errors: result.error };
}

/**
 * Validate a single step
 * @param step - The step to validate
 * @returns Validation result with parsed data or errors
 */
export function validateStep(
  step: unknown
): { success: true; data: Step } | { success: false; errors: z.ZodError } {
  const result = StepSchema.safeParse(step);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return { success: false, errors: result.error };
}

/**
 * Convert Zod errors to validation errors
 * @param zodError - Zod error object
 * @returns Array of validation errors
 */
export function zodErrorToValidationErrors(
  zodError: z.ZodError
): Array<{ path: string; message: string; code: string }> {
  return zodError.errors.map((err) => ({
    path: err.path.join('.'),
    message: err.message,
    code: err.code,
  }));
}
