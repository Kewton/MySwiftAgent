/**
 * API Types - HTTP API type definitions
 *
 * Issue #364: API request/response types
 */

import type { Context } from 'hono';
import type {
  BatchGenerationRequest,
  BatchGenerationResponse,
  GenerationStatusResponse,
  ErrorResponse,
} from './generator.js';

/**
 * API Context - Extended Hono context with typed variables
 */
export interface ApiContext {
  Variables: {
    requestId: string;
    userId?: string;
  };
}

/**
 * Typed Hono Context
 */
export type TypedContext = Context<ApiContext>;

/**
 * Health Check Response
 */
export interface HealthCheckResponse {
  status: 'healthy';
  version?: string;
  timestamp?: string;
}

/**
 * API Handler Result - Union of possible API responses
 */
export type BatchGenerationApiResult =
  | { status: 200; data: BatchGenerationResponse }
  | { status: 207; data: BatchGenerationResponse }
  | { status: 400; data: ErrorResponse }
  | { status: 500; data: ErrorResponse };

/**
 * Generation Status API Result
 */
export type GenerationStatusApiResult =
  | { status: 200; data: GenerationStatusResponse }
  | { status: 404; data: ErrorResponse };

/**
 * API Request Headers
 */
export interface ApiRequestHeaders {
  authorization?: string;
  'content-type'?: string;
  'x-request-id'?: string;
}

/**
 * Request with validated body
 */
export interface ValidatedRequest<T> {
  body: T;
  headers: ApiRequestHeaders;
  params: Record<string, string>;
  query: Record<string, string>;
}

// Re-export for convenience
export type {
  BatchGenerationRequest,
  BatchGenerationResponse,
  GenerationStatusResponse,
  ErrorResponse,
};
