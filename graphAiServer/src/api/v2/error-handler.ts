/**
 * Error Handler for v2 API
 *
 * Provides unified error handling and response formatting.
 * Hides sensitive information in production.
 *
 * @module api/v2/error-handler
 * @see Issue #348
 */

import type { Request, Response, NextFunction } from 'express';

// ============================================================
// Error Types
// ============================================================

/** API Error class */
export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: Record<string, unknown>;

  constructor(
    message: string,
    statusCode: number = 500,
    code: string = 'INTERNAL_ERROR',
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

/** Validation Error */
export class ValidationError extends ApiError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 400, 'VALIDATION_ERROR', details);
    this.name = 'ValidationError';
  }
}

/** Not Found Error */
export class NotFoundError extends ApiError {
  constructor(message: string) {
    super(message, 404, 'NOT_FOUND');
    this.name = 'NotFoundError';
  }
}

/** Unauthorized Error */
export class UnauthorizedError extends ApiError {
  constructor(message: string = 'Unauthorized') {
    super(message, 401, 'UNAUTHORIZED');
    this.name = 'UnauthorizedError';
  }
}

/** Forbidden Error */
export class ForbiddenError extends ApiError {
  constructor(message: string = 'Forbidden') {
    super(message, 403, 'FORBIDDEN');
    this.name = 'ForbiddenError';
  }
}

// ============================================================
// Error Response Format
// ============================================================

/** Standard error response */
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    timestamp: string;
  };
}

/**
 * Format error for API response
 * @param error - Error object
 * @param includeStack - Whether to include stack trace
 * @returns Formatted error response
 */
export function formatError(error: Error, includeStack: boolean = false): ErrorResponse {
  if (error instanceof ApiError) {
    return {
      error: {
        code: error.code,
        message: error.message,
        details: error.details,
        timestamp: new Date().toISOString(),
        ...(includeStack && { stack: error.stack }),
      },
    };
  }

  // Generic error
  return {
    error: {
      code: 'INTERNAL_ERROR',
      message: error.message || 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
      ...(includeStack && { stack: error.stack }),
    },
  };
}

/**
 * Get status code for an error
 * @param error - Error object
 * @returns HTTP status code
 */
export function getStatusCode(error: Error): number {
  if (error instanceof ApiError) {
    return error.statusCode;
  }

  // Check for common error types
  if (error.name === 'ValidationError' || error.message.includes('validation')) {
    return 400;
  }

  if (error.message.includes('not found')) {
    return 404;
  }

  if (error.message.includes('timeout')) {
    return 408;
  }

  return 500;
}

// ============================================================
// Express Middleware
// ============================================================

/**
 * Error handling middleware for Express
 */
export function errorHandler(
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const statusCode = getStatusCode(error);
  const isProduction = process.env.NODE_ENV === 'production';

  // Log error
  console.error(`[ErrorHandler] ${statusCode} ${req.method} ${req.path}:`, error.message);
  if (!isProduction && error.stack) {
    console.error(error.stack);
  }

  // Format response
  const response = formatError(error, !isProduction);

  // Send response
  res.status(statusCode).json(response);
}

/**
 * Async handler wrapper
 * Catches async errors and passes them to error middleware
 */
export function asyncHandler(
  fn: (req: Request, res: Response, next: NextFunction) => Promise<void>
): (req: Request, res: Response, next: NextFunction) => void {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

// ============================================================
// Security Logging
// ============================================================

/**
 * Log security-related events
 * @param event - Event type
 * @param details - Event details
 */
export function logSecurityEvent(
  event: string,
  details: Record<string, unknown>
): void {
  const logEntry = {
    type: 'SECURITY',
    event,
    timestamp: new Date().toISOString(),
    ...details,
  };

  console.warn('[SECURITY]', JSON.stringify(logEntry));
}
