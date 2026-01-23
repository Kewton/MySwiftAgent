/**
 * Generator Types - Type definitions for taskflowGeneratorAgent
 *
 * Issue #364: Types aligned with OpenAPI specification
 * Source of Truth: docs/spec/api/taskflow-generator-api.yaml
 */

import { z } from 'zod';

/**
 * Recovery Strategy enum - Unified recovery strategies for error handling
 *
 * Strategy Selection Guide:
 * - RETRY_CURRENT: Transient errors (timeout, rate limit)
 * - RETRY_WITH_FEEDBACK: Validation errors that can be corrected with LLM feedback
 * - ROLLBACK_TO_ANALYSIS: Structural issues requiring re-analysis
 * - UPDATE_CAPABILITIES: Missing or incorrect capability definitions
 * - MANUAL_INTERVENTION: Unrecoverable errors requiring human decision
 */
export enum RecoveryStrategy {
  RETRY_CURRENT = 'RETRY_CURRENT',
  RETRY_WITH_FEEDBACK = 'RETRY_WITH_FEEDBACK',
  ROLLBACK_TO_ANALYSIS = 'ROLLBACK_TO_ANALYSIS',
  UPDATE_CAPABILITIES = 'UPDATE_CAPABILITIES',
  MANUAL_INTERVENTION = 'MANUAL_INTERVENTION',
}

/**
 * Error Type enum - Classification for recovery decisions
 */
export enum ErrorType {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  LLM_ERROR = 'LLM_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  REGISTRATION_ERROR = 'REGISTRATION_ERROR',
  CAPABILITY_NOT_FOUND = 'CAPABILITY_NOT_FOUND',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
}

// Zod Schemas

export const RecoveryStrategySchema = z.enum([
  'RETRY_CURRENT',
  'RETRY_WITH_FEEDBACK',
  'ROLLBACK_TO_ANALYSIS',
  'UPDATE_CAPABILITIES',
  'MANUAL_INTERVENTION',
]);

export const ErrorTypeSchema = z.enum([
  'VALIDATION_ERROR',
  'LLM_ERROR',
  'TIMEOUT_ERROR',
  'REGISTRATION_ERROR',
  'CAPABILITY_NOT_FOUND',
  'INTERNAL_ERROR',
]);

/**
 * Interface Definition - Input/Output schema for tasks
 */
export const InterfaceDefinitionSchema = z.object({
  input: z.record(z.string()).optional(),
  output: z.record(z.string()).optional(),
});

export type InterfaceDefinition = z.infer<typeof InterfaceDefinitionSchema>;

/**
 * Task Generation Request - Request to generate a single workflow
 */
export const TaskGenerationRequestSchema = z.object({
  task_id: z.string(),
  task_master_id: z.string().optional(),
  name: z.string(),
  description: z.string(),
  dependencies: z.array(z.string()).optional(),
  interface: InterfaceDefinitionSchema,
});

export type TaskGenerationRequest = z.infer<typeof TaskGenerationRequestSchema>;

/**
 * Parameter Validation Schema - Constraints for parameter values
 * Issue #374: Extended validation for capability parameters
 */
export const ParameterValidationSchema = z.object({
  min: z.number().optional(),
  max: z.number().optional(),
  pattern: z.string().optional(),
  enum: z.array(z.unknown()).optional(),
});

export type ParameterValidation = z.infer<typeof ParameterValidationSchema>;

/**
 * Capability Parameter - Parameter definition for capabilities
 * Issue #374: Extended with defaultValue and validation constraints
 */
export const CapabilityParameterSchema = z.object({
  name: z.string(),
  type: z.string(),
  required: z.boolean().optional(),
  description: z.string().optional(),
  defaultValue: z.unknown().optional(),
  validation: ParameterValidationSchema.optional(),
});

export type CapabilityParameter = z.infer<typeof CapabilityParameterSchema>;

/**
 * Capability - Available capability definition
 */
export const CapabilitySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  // Issue #396: Extended category enum to match actual capability categories
  category: z.enum(['api', 'llm', 'transform', 'utility', 'search', 'ai_agent']),
  status: z.enum(['available', 'unavailable', 'deprecated']),
  parameters: z.array(CapabilityParameterSchema).optional(),
});

export type Capability = z.infer<typeof CapabilitySchema>;

/**
 * Trace Context - Langfuse trace context for observability
 */
export const TraceContextSchema = z.object({
  trace_id: z.string().optional(),
  parent_span_id: z.string().optional(),
  user_id: z.string().optional(),
  session_id: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type TraceContext = z.infer<typeof TraceContextSchema>;

/**
 * Generation Options - Configuration for workflow generation
 */
export const GenerationOptionsSchema = z.object({
  max_concurrency: z.number().int().min(1).max(20).optional().default(5),
  timeout_per_task_ms: z.number().int().min(1000).max(120000).optional().default(30000),
  validate_before_register: z.boolean().optional().default(true),
  max_retries: z.number().int().min(0).max(5).optional().default(3),
});

export type GenerationOptions = z.infer<typeof GenerationOptionsSchema>;

/**
 * Batch Generation Request - Request to generate multiple workflows
 */
export const BatchGenerationRequestSchema = z.object({
  tasks: z.array(TaskGenerationRequestSchema),
  capabilities: z.array(CapabilitySchema),
  project_id: z.string(),
  options: GenerationOptionsSchema.optional(),
  trace_context: TraceContextSchema.optional(),
});

export type BatchGenerationRequest = z.infer<typeof BatchGenerationRequestSchema>;

/**
 * Validation Error - Error from validation pipeline
 */
export const ValidationErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  path: z.string().optional(),
});

export type ValidationError = z.infer<typeof ValidationErrorSchema>;

/**
 * Validation Warning - Warning from validation pipeline
 */
export const ValidationWarningSchema = z.object({
  code: z.string(),
  message: z.string(),
});

export type ValidationWarning = z.infer<typeof ValidationWarningSchema>;

/**
 * Validation Result - Result from validation pipeline
 */
export const ValidationResultSchema = z.object({
  isValid: z.boolean(),
  errors: z.array(ValidationErrorSchema).optional(),
  warnings: z.array(ValidationWarningSchema).optional(),
});

export type ValidationResult = z.infer<typeof ValidationResultSchema>;

/**
 * Workflow Generation Result - Result for a single task
 */
export const WorkflowGenerationResultSchema = z.object({
  workflow_name: z.string(),
  registered: z.boolean(),
  workflow_id: z.string().optional(),
  validation_result: ValidationResultSchema.optional(),
});

export type WorkflowGenerationResult = z.infer<typeof WorkflowGenerationResultSchema>;

/**
 * Task Error - Error details for failed tasks
 */
export const TaskErrorSchema = z.object({
  task_id: z.string(),
  error_type: ErrorTypeSchema,
  message: z.string(),
  recoverable: z.boolean(),
  recovery_suggestion: RecoveryStrategySchema.optional(),
  details: z.record(z.unknown()).optional(),
});

export type TaskError = z.infer<typeof TaskErrorSchema>;

/**
 * Batch Generation Response - Response from batch generation
 */
export const BatchGenerationResponseSchema = z.object({
  success: z.boolean(),
  workflows: z.record(WorkflowGenerationResultSchema),
  failed_tasks: z.array(TaskErrorSchema),
  trace_url: z.string().url().optional(),
});

export type BatchGenerationResponse = z.infer<typeof BatchGenerationResponseSchema>;

/**
 * Generation Status Response - Status of generation operation
 */
export const GenerationStatusResponseSchema = z.object({
  trace_id: z.string(),
  status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  total_tasks: z.number().int(),
  completed_tasks: z.number().int(),
  failed_tasks: z.number().int(),
  duration_ms: z.number().int().optional(),
});

export type GenerationStatusResponse = z.infer<typeof GenerationStatusResponseSchema>;

/**
 * Error Response - Generic error response
 */
export const ErrorResponseSchema = z.object({
  error: z.string(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
});

export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;

// ==================================================
// Issue #374: Enhanced Capability Types for Prompts
// ==================================================

/**
 * TaskFlow Step Example - Example step for capability documentation
 */
export interface TaskFlowStepExample {
  id: string;
  type: string;
  config: Record<string, unknown>;
  params: Record<string, unknown>;
}

/**
 * Capability Example for Prompt - Example with TaskFlow step
 */
export interface CapabilityPromptExample {
  description: string;
  taskflow_step: TaskFlowStepExample;
}

/**
 * Response Schema - Schema definition for API responses
 */
export interface ResponseSchema {
  type: string;
  properties?: Record<string, { type: string; description?: string }>;
  items?: { type: string };
}

/**
 * Capability Metadata - Additional metadata for capabilities
 */
export interface CapabilityMetadata {
  use_cases?: string[];
  tags?: string[];
  [key: string]: unknown;
}

/**
 * CapabilityForPrompt - Extended capability type for prompt generation
 *
 * Issue #374: This type extends Capability with:
 * - Examples with TaskFlow step format
 * - Response schema for output documentation
 * - Rich metadata including use_cases
 *
 * Used by PromptBuilder to create context-rich prompts
 */
export const CapabilityForPromptSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  category: z.string(),
  status: z.enum(['available', 'unavailable', 'deprecated']),
  parameters: z.array(CapabilityParameterSchema).optional(),
  examples: z.array(z.object({
    description: z.string(),
    taskflow_step: z.object({
      id: z.string(),
      type: z.string(),
      config: z.record(z.unknown()),
      params: z.record(z.unknown()),
    }),
  })).optional(),
  responseSchema: z.object({
    type: z.string(),
    properties: z.record(z.object({
      type: z.string(),
      description: z.string().optional(),
    })).optional(),
    items: z.object({ type: z.string() }).optional(),
  }).optional(),
  metadata: z.object({
    use_cases: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
  }).passthrough().optional(),
});

export type CapabilityForPrompt = z.infer<typeof CapabilityForPromptSchema>;
