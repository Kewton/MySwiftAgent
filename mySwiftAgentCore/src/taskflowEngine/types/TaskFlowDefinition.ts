/**
 * TaskFlowDefinition - graphAiServer compatible type definitions
 *
 * Issue #363: External TaskFlow definition types
 * Issue #396: Updated to match graphAiServer's expected format (simple type mapping)
 * These types are compatible with graphAiServer workflow definitions.
 */

import { z } from 'zod';

/**
 * Supported node types
 */
export const NodeTypes = ['api_rest', 'code_js', 'transform', 'parallel', 'llm', 'action'] as const;
export type NodeType = (typeof NodeTypes)[number];

/**
 * Simple type values for IO schema
 * Issue #396: graphAiServer uses simple type mapping {field: "type"}
 */
export const SimpleTypes = ['string', 'number', 'boolean', 'array', 'object', 'null'] as const;
export type SimpleType = (typeof SimpleTypes)[number];

/**
 * IO Schema type definition (graphAiServer format)
 * Issue #396: Simple mapping of field names to type strings
 */
export type IOSchemaType = Record<string, SimpleType>;

/**
 * TaskFlow step definition (graphAiServer format)
 */
export interface TaskFlowStep {
  id: string;
  type: NodeType;
  description?: string;
  config: Record<string, unknown>;
  params?: Record<string, unknown>;
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

/**
 * Simple type schema for IO schema values
 * Issue #396: graphAiServer uses simple type strings
 */
export const SimpleTypeSchema = z.enum(SimpleTypes);

/**
 * IO Schema - maps field names to simple type strings
 * Issue #396: graphAiServer format {field: "type"}
 */
export const IOSchemaTypeSchema = z.record(z.string(), SimpleTypeSchema);

export const TaskFlowStepSchema = z.object({
  id: z.string(),
  type: z.enum(NodeTypes),
  description: z.string().optional(),
  config: z.record(z.unknown()),
  params: z.record(z.unknown()).optional().default({}),
});

export const TaskFlowDefinitionSchema = z.object({
  workflow_name: z.string(),
  description: z.string().optional(),
  input_schema: IOSchemaTypeSchema,
  output_schema: IOSchemaTypeSchema,
  steps: z.array(TaskFlowStepSchema),
  output: z.record(z.string()),
});
