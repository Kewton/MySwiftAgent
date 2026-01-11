/**
 * TaskFlow Engine Type Definitions
 *
 * This file defines all TypeScript types for the TaskFlow Engine.
 * These types support the modular task definition and parallel API execution engine.
 *
 * @module types/taskflow
 * @see Issue #348
 */

// ============================================================
// Basic Type Definitions
// ============================================================

/** HTTP Methods supported by REST API Node */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/** Node type identifiers */
export type NodeType = 'api_rest' | 'code_js' | 'transform';

/** Node execution states */
export type NodeState = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

/** Simple type schema for I/O validation */
export type SimpleType = 'string' | 'number' | 'boolean' | 'array' | 'object' | 'null';

/** I/O Schema type - maps field names to simple types */
export type IOSchemaType = Record<string, SimpleType>;

// ============================================================
// Node Configuration Types
// ============================================================

/** REST API Node configuration */
export interface ApiRestConfig {
  /** HTTP method */
  method: HttpMethod;
  /** Request URL (must be HTTPS, supports variable references) */
  url: string;
  /** Optional request headers (supports variable references) */
  headers?: Record<string, string>;
  /** Optional request body (supports variable references) */
  body?: unknown;
  /** Timeout in milliseconds (default: 30000) */
  timeout_ms?: number;
  /** SSL certificate verification (default: true, must be true in production) */
  verify_ssl?: boolean;
}

/** JavaScript Node configuration */
export interface CodeJsConfig {
  /** Path to JavaScript file (relative to scripts directory) */
  path: string;
  /** Function name to execute (default: 'main') */
  function_name?: string;
}

/** Transform Node configuration */
export interface TransformConfig {
  /** Transform mode */
  mode: 'template' | 'concat' | 'map' | 'merge';
  /** Handlebars template (for template and map modes) */
  template?: string;
  /** Separator for concat mode (default: ', ') */
  separator?: string;
  /** Fields to concat (for concat mode) */
  fields?: string[];
  /** Source field for map mode */
  source_field?: string;
  /** Merge strategy (for merge mode) */
  strategy?: 'shallow' | 'deep';
}

/** Union type for all node configurations */
export type NodeConfig = ApiRestConfig | CodeJsConfig | TransformConfig;

// ============================================================
// Step Definitions
// ============================================================

/** Base step interface */
export interface BaseStep {
  /** Unique step identifier */
  id: string;
  /** Step type */
  type: NodeType;
  /** Optional description */
  description?: string;
  /** Node configuration */
  config: NodeConfig;
  /** Input parameters (supports variable references) */
  params?: Record<string, unknown>;
  /** Input schema for validation */
  input_schema?: IOSchemaType;
  /** Output schema for validation */
  output_schema?: IOSchemaType;
}

/** API REST Step with typed config */
export interface ApiRestStep extends BaseStep {
  type: 'api_rest';
  config: ApiRestConfig;
}

/** Code JS Step with typed config */
export interface CodeJsStep extends BaseStep {
  type: 'code_js';
  config: CodeJsConfig;
}

/** Transform Step with typed config */
export interface TransformStep extends BaseStep {
  type: 'transform';
  config: TransformConfig;
}

/** Parallel block containing multiple steps */
export interface ParallelBlock {
  /** Parallel block type identifier */
  type: 'parallel';
  /** Steps to execute in parallel */
  steps: Step[];
}

/** Conditional block for if/else branching */
export interface ConditionalBlock {
  /** Conditional block type identifier */
  type: 'conditional';
  /** Condition expression (e.g., "${step.output.status} == 'active'") */
  condition: string;
  /** Steps to execute if condition is true */
  then: Step[];
  /** Steps to execute if condition is false */
  else?: Step[];
}

/** Union type for all step types */
export type Step = ApiRestStep | CodeJsStep | TransformStep | ParallelBlock | ConditionalBlock;

// ============================================================
// Workflow Definition
// ============================================================

/** Complete workflow definition */
export interface WorkflowDefinition {
  /** Workflow name */
  workflow_name: string;
  /** Optional description */
  description?: string;
  /** Input schema for workflow inputs */
  input_schema: IOSchemaType;
  /** Output schema for workflow outputs */
  output_schema: IOSchemaType;
  /** Array of steps to execute */
  steps: Step[];
  /** Output mapping (field name to variable reference) */
  output: Record<string, string>;
}

// ============================================================
// Execution Context Types
// ============================================================

/** Variable reference source types */
export type ReferenceSource = 'inputs' | 'env' | 'secrets' | 'output';

/** Parsed variable reference */
export interface ParsedReference {
  /** Source type */
  source: ReferenceSource;
  /** Node ID (for output references) */
  nodeId?: string;
  /** Field path */
  path: string[];
  /** Default value (for ?? operator) */
  defaultValue?: unknown;
  /** Original reference string */
  original: string;
}

/** Execution context data */
export interface ExecutionContext {
  /** Workflow inputs */
  inputs: Record<string, unknown>;
  /** Environment variables */
  env: Record<string, string>;
  /** Secrets from MyVault or environment */
  secrets: Record<string, string>;
  /** Node outputs keyed by node ID */
  outputs: Map<string, unknown>;
  /** Node errors keyed by node ID */
  errors: Map<string, NodeError>;
}

// ============================================================
// Execution Result Types
// ============================================================

/** Node error details */
export interface NodeError {
  /** Error message */
  message: string;
  /** Error stack trace (optional) */
  stack?: string;
  /** Error code */
  code?: string;
  /** Additional error details */
  details?: Record<string, unknown>;
}

/** Node execution log entry */
export interface NodeLog {
  /** Node ID */
  nodeId: string;
  /** Execution state */
  state: NodeState;
  /** Start timestamp (milliseconds) */
  startTime: number;
  /** End timestamp (milliseconds) */
  endTime: number;
  /** Number of retry attempts */
  retryCount: number;
  /** Error details (if failed) */
  error?: {
    message: string;
    stack?: string;
  };
}

/** Node execution result */
export interface NodeResult {
  /** Whether execution was successful */
  success: boolean;
  /** Output data (if successful) */
  output?: unknown;
  /** Error details (if failed) */
  error?: NodeError;
  /** Execution log */
  log: NodeLog;
}

/** Workflow execution result (matches existing GraphAI response format) */
export interface WorkflowResult {
  /** Results keyed by node ID, plus 'inputs' and '_output' */
  results: Record<string, unknown>;
  /** Errors keyed by node ID */
  errors: Record<string, NodeError>;
  /** Execution logs */
  logs: NodeLog[];
}

// ============================================================
// Validation Types
// ============================================================

/** Validation result */
export interface ValidationResult {
  /** Whether validation passed */
  valid: boolean;
  /** Validation errors */
  errors: ValidationError[];
}

/** Validation error */
export interface ValidationError {
  /** Error type */
  type: 'schema' | 'type' | 'required' | 'format' | 'security';
  /** Field path */
  path: string;
  /** Error message */
  message: string;
  /** Expected value/type */
  expected?: string;
  /** Actual value/type */
  actual?: string;
}

// ============================================================
// URL Validation Types (SSRF Protection)
// ============================================================

/** URL validation result */
export interface UrlValidationResult {
  /** Whether URL is valid and safe */
  valid: boolean;
  /** Error message if invalid */
  error?: string;
  /** Security violation type (if any) */
  securityIssue?: 'private_ip' | 'blocked_host' | 'http_not_allowed' | 'domain_not_whitelisted';
}

// ============================================================
// API Request/Response Types
// ============================================================

/** Workflow execution request */
export interface WorkflowExecutionRequest {
  /** Workflow name (for registered workflows) */
  workflow_name?: string;
  /** Inline workflow definition */
  definition?: WorkflowDefinition;
  /** Workflow inputs */
  inputs: Record<string, unknown>;
  /** Project for secrets resolution */
  project?: string;
}

/** Workflow validation request */
export interface WorkflowValidationRequest {
  /** Workflow definition to validate */
  definition: WorkflowDefinition;
}

/** Workflow validation response */
export interface WorkflowValidationResponse {
  /** Whether definition is valid */
  valid: boolean;
  /** Validation errors */
  errors: ValidationError[];
}

// ============================================================
// Type Guards
// ============================================================

/** Type guard for ParallelBlock */
export function isParallelBlock(step: Step): step is ParallelBlock {
  return step.type === 'parallel';
}

/** Type guard for ConditionalBlock */
export function isConditionalBlock(step: Step): step is ConditionalBlock {
  return step.type === 'conditional';
}

/** Type guard for BaseStep (non-parallel, non-conditional) */
export function isBaseStep(step: Step): step is ApiRestStep | CodeJsStep | TransformStep {
  return step.type !== 'parallel' && step.type !== 'conditional';
}

/** Type guard for ApiRestStep */
export function isApiRestStep(step: Step): step is ApiRestStep {
  return step.type === 'api_rest';
}

/** Type guard for CodeJsStep */
export function isCodeJsStep(step: Step): step is CodeJsStep {
  return step.type === 'code_js';
}

/** Type guard for TransformStep */
export function isTransformStep(step: Step): step is TransformStep {
  return step.type === 'transform';
}
