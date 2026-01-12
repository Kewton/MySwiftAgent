/* Auto-generated from JSON Schema. DO NOT EDIT. */
/* Source: shared/schemas/taskflow/v1/workflow.schema.json */

/**
 * Simple type for I/O schema fields.
 */
export type SimpleType = "string" | "number" | "boolean" | "array" | "object" | "null";

/**
 * TaskFlow V2 workflow definition schema. This is the Single Source of Truth for workflow definitions used by both ExpertAgent (Python/Pydantic) and GraphAiServer (TypeScript/Zod).
 */
export interface TaskFlowWorkflowDefinition {
  /**
   * Unique workflow name. Must start with a letter or underscore, followed by letters, numbers, underscores, or hyphens.
   */
  workflow_name: string;
  /**
   * Human-readable description of the workflow.
   */
  description?: string;
  input_schema: IOSchema;
  output_schema: IOSchema1;
  /**
   * Workflow steps executed in order.
   *
   * @minItems 1
   */
  steps: [Step, ...Step[]];
  /**
   * Output field mappings. Maps output field names to step output references (e.g., ${step_001.output.data}).
   */
  output: {
    [k: string]: string;
  };
  [k: string]: unknown;
}
/**
 * Input field definitions. Maps field names to their types.
 */
export interface IOSchema {
  [k: string]: SimpleType;
}
/**
 * Output field definitions. Maps field names to their types.
 */
export interface IOSchema1 {
  [k: string]: SimpleType;
}
export interface Step {
  /**
   * Unique step identifier. Must start with a letter or underscore.
   */
  id: string;
  /**
   * Step type.
   */
  type: "api_rest" | "code_js" | "transform";
  /**
   * Human-readable description of the step.
   */
  description?: string;
  /**
   * Step-specific configuration.
   */
  config: ApiRestConfig | CodeJsConfig | TransformConfig;
  /**
   * Additional parameters for variable substitution.
   */
  params?: {
    [k: string]: unknown;
  };
  input_schema?: IOSchema2;
  output_schema?: IOSchema3;
  [k: string]: unknown;
}
export interface ApiRestConfig {
  /**
   * Step type discriminator for api_rest.
   */
  step_type?: "api_rest";
  /**
   * HTTP method.
   */
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  /**
   * API endpoint URL. Must use HTTPS for external URLs. Supports variable references like ${inputs.url}.
   */
  url: string;
  /**
   * HTTP headers as key-value pairs.
   */
  headers?: {
    [k: string]: string;
  };
  /**
   * Request body. Can be a JSON object or string.
   */
  body?: {
    [k: string]: unknown;
  };
  /**
   * Request timeout in milliseconds.
   */
  timeout_ms?: number;
  /**
   * Whether to verify SSL certificates.
   */
  verify_ssl?: boolean;
  [k: string]: unknown;
}
export interface CodeJsConfig {
  /**
   * Step type discriminator for code_js.
   */
  step_type?: "code_js";
  /**
   * Path to the JavaScript file.
   */
  path: string;
  /**
   * Name of the function to execute.
   */
  function_name?: string;
  [k: string]: unknown;
}
export interface TransformConfig {
  /**
   * Step type discriminator for transform.
   */
  step_type?: "transform";
  /**
   * Transform mode.
   */
  mode?: "template" | "concat" | "map" | "merge";
  /**
   * Template string for 'template' mode.
   */
  template?: string;
  /**
   * Separator for 'concat' mode.
   */
  separator?: string;
  /**
   * Field list for 'map' or 'merge' mode.
   */
  fields?: string[];
  /**
   * Source field for transformation.
   */
  source_field?: string;
  /**
   * Merge strategy for 'merge' mode.
   */
  strategy?: "shallow" | "deep";
  [k: string]: unknown;
}
/**
 * Step-level input schema.
 */
export interface IOSchema2 {
  [k: string]: SimpleType;
}
/**
 * Step-level output schema.
 */
export interface IOSchema3 {
  [k: string]: SimpleType;
}
