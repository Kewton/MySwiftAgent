/**
 * MetricsCollector - Generation metrics collection for feedback loop
 *
 * Issue #374: Tracks metrics for workflow generation including:
 * - Success rates
 * - Retry counts
 * - Token usage
 * - Validation error types
 */

import type {
  GenerationMetrics,
  MetricsSummary,
  ValidationError,
} from '../types/index.js';

/**
 * Attempt data for recording
 */
export interface AttemptData {
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
 * GenerationMetricsCollector - Collects metrics for a single generation
 *
 * Usage:
 * 1. Call startGeneration() when starting
 * 2. Call recordAttempt() after each attempt
 * 3. Call finalize() to get aggregated metrics
 */
export class GenerationMetricsCollector {
  private generationStartTime = 0;
  private attempts: AttemptData[] = [];

  /**
   * Start a new generation
   */
  startGeneration(): void {
    this.generationStartTime = Date.now();
    this.attempts = [];
  }

  /**
   * Record an attempt
   *
   * @param data - Attempt data
   */
  recordAttempt(data: AttemptData): void {
    this.attempts.push(data);
  }

  /**
   * Finalize and return aggregated metrics
   */
  finalize(): GenerationMetrics {
    const totalDurationMs = Date.now() - this.generationStartTime;

    // Calculate initial success rate
    const firstAttempt = this.attempts[0];
    const initialSuccessRate = this.attempts.length > 0 && firstAttempt?.success
      ? 1.0
      : 0.0;

    // Calculate average retry count
    const averageRetryCount = this.attempts.length;

    // Collect token usage by attempt
    const tokenUsageByAttempt = this.attempts.map(a => a.tokenUsage.total);

    // Aggregate validation error types
    const validationErrorTypes: Record<string, number> = {};
    for (const attempt of this.attempts) {
      for (const error of attempt.validationErrors) {
        validationErrorTypes[error.code] = (validationErrorTypes[error.code] ?? 0) + 1;
      }
    }

    return {
      initialSuccessRate,
      averageRetryCount,
      tokenUsageByAttempt,
      validationErrorTypes,
      totalDurationMs,
    };
  }
}

/**
 * MetricsAggregator - Aggregates metrics across multiple generations
 *
 * Usage:
 * 1. Call record() after each generation
 * 2. Call getSummary() to get aggregated summary
 * 3. Call reset() to clear recorded metrics
 */
export class MetricsAggregator {
  private metrics: GenerationMetrics[] = [];

  /**
   * Record metrics from a generation
   *
   * @param metrics - Generation metrics
   */
  record(metrics: GenerationMetrics): void {
    this.metrics.push(metrics);
  }

  /**
   * Get aggregated summary
   */
  getSummary(): MetricsSummary {
    if (this.metrics.length === 0) {
      return {
        count: 0,
        avgInitialSuccessRate: 0,
        avgRetryCount: 0,
      };
    }

    const count = this.metrics.length;

    // Calculate average initial success rate
    const avgInitialSuccessRate = this.metrics.reduce(
      (sum, m) => sum + m.initialSuccessRate, 0
    ) / count;

    // Calculate average retry count
    const avgRetryCount = this.metrics.reduce(
      (sum, m) => sum + m.averageRetryCount, 0
    ) / count;

    // Calculate total tokens
    const totalTokens = this.metrics.reduce(
      (sum, m) => sum + m.tokenUsageByAttempt.reduce((s, t) => s + t, 0), 0
    );

    // Aggregate error types
    const errorTypes: Record<string, number> = {};
    for (const m of this.metrics) {
      for (const [code, count] of Object.entries(m.validationErrorTypes)) {
        errorTypes[code] = (errorTypes[code] ?? 0) + count;
      }
    }

    // Get top 5 error types
    const topErrorTypes = Object.entries(errorTypes)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5) as [string, number][];

    return {
      count,
      avgInitialSuccessRate,
      avgRetryCount,
      totalTokens,
      topErrorTypes: topErrorTypes.length > 0 ? topErrorTypes : undefined,
    };
  }

  /**
   * Reset recorded metrics
   */
  reset(): void {
    this.metrics = [];
  }
}

/**
 * Factory function for GenerationMetricsCollector
 */
export function createMetricsCollector(): GenerationMetricsCollector {
  return new GenerationMetricsCollector();
}

/**
 * Factory function for MetricsAggregator
 */
export function createMetricsAggregator(): MetricsAggregator {
  return new MetricsAggregator();
}
