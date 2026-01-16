/**
 * TaskFlowDefinition - graphAiServer compatible type definitions
 *
 * Issue #363: External TaskFlow definition types
 * These types are compatible with graphAiServer workflow definitions.
 */

import { z } from 'zod';

/**
 * Supported node types
 */
export const NodeTypes = ['api_rest', 'code_js', 'transform', 'parallel', 'llm', 'action'] as const;
export type NodeType = (typeof NodeTypes)[number];

/**
 * IO Schema property type
 */
export interface IOSchemaProperty {
  type: string;
  description?: string;
  items?: IOSchemaProperty;
  properties?: Record<string, IOSchemaProperty>;
  required?: string[];
  enum?: string[];
  default?: unknown;
}

/**
 * IO Schema type definition
 */
export interface IOSchemaType {
  type: string;
  properties?: Record<string, IOSchemaProperty>;
  required?: string[];
  items?: IOSchemaProperty;
  description?: string;
}

/**
 * TaskFlow step definition (graphAiServer format)
 */
export interface TaskFlowStep {
  id: string;
  type: NodeType;
  description?: string;
  config: Record<string, unknown>;
  params: Record<string, unknown>;
}

/**
 * TaskFlowDefinition - graphAiServer compatible workflow definition
 */
export interface TaskFlowDefinition {
  workflow_name: string;
  description?: string;
  input_schema: IOSchemaType;
  output_schema: IOSchemaType;
  steps: TaskFlowStep[];
  output: Record<string, string>;
}

// Zod Schemas for validation

export const IOSchemaPropertySchema: z.ZodType<IOSchemaProperty> = z.lazy(() =>
  z.object({
    type: z.string(),
    description: z.string().optional(),
    items: IOSchemaPropertySchema.optional(),
    properties: z.record(IOSchemaPropertySchema).optional(),
    required: z.array(z.string()).optional(),
    enum: z.array(z.string()).optional(),
    default: z.unknown().optional(),
  })
);

export const IOSchemaTypeSchema = z.object({
  type: z.string(),
  properties: z.record(IOSchemaPropertySchema).optional(),
  required: z.array(z.string()).optional(),
  items: IOSchemaPropertySchema.optional(),
  description: z.string().optional(),
});

export const TaskFlowStepSchema = z.object({
  id: z.string(),
  type: z.enum(NodeTypes),
  description: z.string().optional(),
  config: z.record(z.unknown()),
  params: z.record(z.unknown()),
});

export const TaskFlowDefinitionSchema = z.object({
  workflow_name: z.string(),
  description: z.string().optional(),
  input_schema: IOSchemaTypeSchema,
  output_schema: IOSchemaTypeSchema,
  steps: z.array(TaskFlowStepSchema),
  output: z.record(z.string()),
});
