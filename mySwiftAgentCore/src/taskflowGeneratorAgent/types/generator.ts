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
 * Capability Parameter - Parameter definition for capabilities
 */
export const CapabilityParameterSchema = z.object({
  name: z.string(),
  type: z.string(),
  required: z.boolean().optional(),
  description: z.string().optional(),
});

export type CapabilityParameter = z.infer<typeof CapabilityParameterSchema>;

/**
 * Capability - Available capability definition
 */
export const CapabilitySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().optional(),
  category: z.enum(['api', 'llm', 'transform', 'utility']),
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
