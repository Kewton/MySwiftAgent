/**
 * Error Types - Standardized error handling types
 *
 * This module provides a consistent error type system
 * for the entire mySwiftAgentCore service.
 */

import { z } from 'zod';

/**
 * Error severity levels
 */
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

/**
 * Error category for classification
 */
export type ErrorCategory =
  | 'validation'
  | 'authentication'
  | 'authorization'
  | 'execution'
  | 'timeout'
  | 'network'
  | 'configuration'
  | 'internal';

/**
 * Base error structure
 */
export interface CoreError {
  code: string;
  message: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  timestamp: Date;
  requestId?: string;
  details?: Record<string, unknown>;
  stack?: string;
}

/**
 * Validation error with field-level details
 */
export interface ValidationError extends CoreError {
  category: 'validation';
  fieldErrors: FieldError[];
}

/**
 * Field-level validation error
 */
export interface FieldError {
  field: string;
  message: string;
  value?: unknown;
  constraint?: string;
}

/**
 * HTTP error response format
 */
export interface HttpErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    requestId?: string;
  };
  timestamp: string;
}

// Zod schemas for validation

export const FieldErrorSchema = z.object({
  field: z.string(),
  message: z.string(),
  value: z.unknown().optional(),
  constraint: z.string().optional(),
});

export const CoreErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  category: z.enum([
    'validation',
    'authentication',
    'authorization',
    'execution',
    'timeout',
    'network',
    'configuration',
    'internal',
  ]),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  timestamp: z.date(),
  requestId: z.string().optional(),
  details: z.record(z.unknown()).optional(),
  stack: z.string().optional(),
});

export const ValidationErrorSchema = CoreErrorSchema.extend({
  category: z.literal('validation'),
  fieldErrors: z.array(FieldErrorSchema),
});

export const HttpErrorResponseSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.unknown()).optional(),
    requestId: z.string().optional(),
  }),
  timestamp: z.string(),
});

/**
 * Error codes enumeration
 */
export const ErrorCodes = {
  // Validation errors (VAL_*)
  VAL_INVALID_INPUT: 'VAL_INVALID_INPUT',
  VAL_MISSING_REQUIRED: 'VAL_MISSING_REQUIRED',
  VAL_TYPE_MISMATCH: 'VAL_TYPE_MISMATCH',

  // Authentication errors (AUTH_*)
  AUTH_MISSING_TOKEN: 'AUTH_MISSING_TOKEN',
  AUTH_INVALID_TOKEN: 'AUTH_INVALID_TOKEN',
  AUTH_TOKEN_EXPIRED: 'AUTH_TOKEN_EXPIRED',

  // Authorization errors (AUTHZ_*)
  AUTHZ_PERMISSION_DENIED: 'AUTHZ_PERMISSION_DENIED',
  AUTHZ_RESOURCE_FORBIDDEN: 'AUTHZ_RESOURCE_FORBIDDEN',

  // Execution errors (EXEC_*)
  EXEC_WORKFLOW_FAILED: 'EXEC_WORKFLOW_FAILED',
  EXEC_STEP_FAILED: 'EXEC_STEP_FAILED',
  EXEC_TIMEOUT: 'EXEC_TIMEOUT',

  // Configuration errors (CFG_*)
  CFG_MISSING_REQUIRED: 'CFG_MISSING_REQUIRED',
  CFG_INVALID_VALUE: 'CFG_INVALID_VALUE',

  // Internal errors (INT_*)
  INT_UNEXPECTED: 'INT_UNEXPECTED',
  INT_SERVICE_UNAVAILABLE: 'INT_SERVICE_UNAVAILABLE',
} as const;

export type ErrorCode = (typeof ErrorCodes)[keyof typeof ErrorCodes];

/**
 * Create a CoreError instance
 */
export function createCoreError(
  code: ErrorCode,
  message: string,
  category: ErrorCategory,
  severity: ErrorSeverity,
  details?: Record<string, unknown>
): CoreError {
  return {
    code,
    message,
    category,
    severity,
    timestamp: new Date(),
    details,
  };
}

/**
 * Create an HTTP error response
 */
export function createHttpErrorResponse(error: CoreError, requestId?: string): HttpErrorResponse {
  return {
    error: {
      code: error.code,
      message: error.message,
      details: error.details,
      requestId,
    },
    timestamp: error.timestamp.toISOString(),
  };
}
