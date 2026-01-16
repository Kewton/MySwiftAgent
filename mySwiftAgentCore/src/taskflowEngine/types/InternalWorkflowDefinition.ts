/**
 * InternalWorkflowDefinition - Internal unified type definitions
 *
 * Issue #363: Internal workflow definition types
 * Extends WorkflowDefinition from shared/types with additional fields.
 */

import { z } from 'zod';
import type { RetryPolicy } from '../../shared/types/workflow.types.js';
import type { IOSchemaType, NodeType } from './TaskFlowDefinition.js';
import { IOSchemaTypeSchema } from './TaskFlowDefinition.js';

/**
 * Internal workflow step definition
 */
export interface InternalWorkflowStep {
  id: string;
  name: string;
  type: NodeType;
  config: Record<string, unknown>;
  params: Record<string, unknown>;
  dependsOn?: string[];
  retryPolicy?: RetryPolicy;
  timeout?: number;
}

/**
 * InternalWorkflowDefinition - Unified internal representation
 *
 * Extends the base WorkflowDefinition with:
 * - inputSchema / outputSchema from graphAiServer format
 * - outputMapping for result construction
 */
export interface InternalWorkflowDefinition {
  id: string;
  name: string;
  version: string;
  steps: InternalWorkflowStep[];
  inputSchema: IOSchemaType;
  outputSchema: IOSchemaType;
  outputMapping: Record<string, string>;
  timeout?: number;
  variables?: Record<string, unknown>;
}

// Zod Schemas for validation

export const RetryPolicySchema = z.object({
  maxRetries: z.number(),
  delayMs: z.number(),
  exponentialBackoff: z.boolean(),
});

export const InternalWorkflowStepSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['api_rest', 'code_js', 'transform', 'parallel', 'llm', 'action']),
  config: z.record(z.unknown()),
  params: z.record(z.unknown()),
  dependsOn: z.array(z.string()).optional(),
  retryPolicy: RetryPolicySchema.optional(),
  timeout: z.number().optional(),
});

export const InternalWorkflowDefinitionSchema = z.object({
  id: z.string(),
  name: z.string(),
  version: z.string(),
  steps: z.array(InternalWorkflowStepSchema),
  inputSchema: IOSchemaTypeSchema,
  outputSchema: IOSchemaTypeSchema,
  outputMapping: z.record(z.string()),
  timeout: z.number().optional(),
  variables: z.record(z.unknown()).optional(),
});
