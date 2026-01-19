/**
 * Metrics Types - Type definitions for generation metrics
 *
 * Issue #374: Metrics collection for feedback loop effectiveness
 */

import { z } from 'zod';
import type { ValidationError } from './generator.js';

/**
 * AttemptMetrics - Metrics for a single generation attempt
 */
export interface AttemptMetrics {
  attemptNumber: number;
  startTime: number;
  endTime: number;
  durationMs: number;
  tokenUsage: {
    prompt: number;
    completion: number;
    total: number;
  };
  validationErrors: ValidationError[];
  success: boolean;
}

/**
 * GenerationMetrics - Aggregated metrics for workflow generation
 */
export interface GenerationMetrics {
  /**
   * Initial success rate (1.0 = first attempt success, 0.0 = needed retry)
   */
  initialSuccessRate: number;

  /**
   * Average retry count to achieve success
   */
  averageRetryCount: number;

  /**
   * Token usage per attempt
   */
  tokenUsageByAttempt: number[];

  /**
   * Validation error types and their counts
   */
  validationErrorTypes: Record<string, number>;

  /**
   * Total processing duration in milliseconds
   */
  totalDurationMs: number;

  /**
   * Token savings from capability selection (optional)
   */
  tokenSavedBySelection?: number;
}

/**
 * MetricsSummary - Summary of generation metrics over time
 */
export interface MetricsSummary {
  count: number;
  avgInitialSuccessRate: number;
  avgRetryCount: number;
  totalTokens?: number;
  topErrorTypes?: [string, number][];
}

// Zod Schemas

export const AttemptMetricsSchema = z.object({
  attemptNumber: z.number().int().positive(),
  startTime: z.number(),
  endTime: z.number(),
  durationMs: z.number().nonnegative(),
  tokenUsage: z.object({
    prompt: z.number().nonnegative(),
    completion: z.number().nonnegative(),
    total: z.number().nonnegative(),
  }),
  validationErrors: z.array(z.object({
    code: z.string(),
    message: z.string(),
    path: z.string().optional(),
  })),
  success: z.boolean(),
});

export const GenerationMetricsSchema = z.object({
  initialSuccessRate: z.number().min(0).max(1),
  averageRetryCount: z.number().nonnegative(),
  tokenUsageByAttempt: z.array(z.number().nonnegative()),
  validationErrorTypes: z.record(z.string(), z.number().nonnegative()),
  totalDurationMs: z.number().nonnegative(),
  tokenSavedBySelection: z.number().optional(),
});

export const MetricsSummarySchema = z.object({
  count: z.number().int().nonnegative(),
  avgInitialSuccessRate: z.number().min(0).max(1),
  avgRetryCount: z.number().nonnegative(),
  totalTokens: z.number().optional(),
  topErrorTypes: z.array(z.tuple([z.string(), z.number()])).optional(),
});
