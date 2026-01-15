/**
 * Workflow Types - Core type definitions for workflow execution
 *
 * This module defines the type system for TaskFlow workflow execution,
 * including partial success models and recovery actions.
 */

import { z } from 'zod';

/**
 * Execution status with partial success support
 */
export type ExecutionStatus = 'success' | 'partial_success' | 'failed';

/**
 * Step error representation
 */
export interface StepError {
  stepId: string;
  stepName: string;
  errorCode: string;
  errorMessage: string;
  timestamp: Date;
  recoverable: boolean;
  context?: Record<string, unknown>;
}

/**
 * Recovery action types
 */
export type RecoveryActionType = 'retry' | 'skip' | 'fallback' | 'abort';

/**
 * Recovery action definition
 */
export interface RecoveryAction {
  type: RecoveryActionType;
  stepId: string;
  maxRetries?: number;
  fallbackValue?: unknown;
  reason: string;
}

/**
 * Workflow step result
 */
export interface StepResult {
  stepId: string;
  stepName: string;
  status: ExecutionStatus;
  output?: unknown;
  error?: StepError;
  startTime: Date;
  endTime: Date;
  durationMs: number;
}

/**
 * Workflow execution result with partial success support
 */
export interface WorkflowExecutionResult {
  workflowId: string;
  workflowName: string;
  status: ExecutionStatus;
  stepResults: StepResult[];
  errors: StepError[];
  recoveryActions: RecoveryAction[];
  startTime: Date;
  endTime: Date;
  durationMs: number;
  metadata?: Record<string, unknown>;
}

/**
 * Workflow definition
 */
export interface WorkflowDefinition {
  id: string;
  name: string;
  version: string;
  steps: WorkflowStep[];
  variables?: Record<string, unknown>;
  timeout?: number;
}

/**
 * Workflow step definition
 */
export interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  dependsOn?: string[];
  retryPolicy?: RetryPolicy;
  timeout?: number;
}

/**
 * Retry policy configuration
 */
export interface RetryPolicy {
  maxRetries: number;
  delayMs: number;
  exponentialBackoff: boolean;
}

// Zod schemas for validation

export const StepErrorSchema = z.object({
  stepId: z.string(),
  stepName: z.string(),
  errorCode: z.string(),
  errorMessage: z.string(),
  timestamp: z.date(),
  recoverable: z.boolean(),
  context: z.record(z.unknown()).optional(),
});

export const RecoveryActionSchema = z.object({
  type: z.enum(['retry', 'skip', 'fallback', 'abort']),
  stepId: z.string(),
  maxRetries: z.number().optional(),
  fallbackValue: z.unknown().optional(),
  reason: z.string(),
});

export const StepResultSchema = z.object({
  stepId: z.string(),
  stepName: z.string(),
  status: z.enum(['success', 'partial_success', 'failed']),
  output: z.unknown().optional(),
  error: StepErrorSchema.optional(),
  startTime: z.date(),
  endTime: z.date(),
  durationMs: z.number(),
});

export const WorkflowExecutionResultSchema = z.object({
  workflowId: z.string(),
  workflowName: z.string(),
  status: z.enum(['success', 'partial_success', 'failed']),
  stepResults: z.array(StepResultSchema),
  errors: z.array(StepErrorSchema),
  recoveryActions: z.array(RecoveryActionSchema),
  startTime: z.date(),
  endTime: z.date(),
  durationMs: z.number(),
  metadata: z.record(z.unknown()).optional(),
});
