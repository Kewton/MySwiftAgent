/**
 * Metrics Types Unit Tests
 *
 * Issue #374: Generation metrics for feedback loop effectiveness
 */

import { describe, it, expect } from 'vitest';
import {
  AttemptMetricsSchema,
  GenerationMetricsSchema,
  MetricsSummarySchema,
  type AttemptMetrics,
  type GenerationMetrics,
  type MetricsSummary,
} from '../../../../src/taskflowGeneratorAgent/types/metrics.js';

describe('AttemptMetrics', () => {
  describe('type structure', () => {
    it('should define all required fields', () => {
      const metrics: AttemptMetrics = {
        attemptNumber: 1,
        startTime: Date.now(),
        endTime: Date.now() + 1000,
        durationMs: 1000,
        tokenUsage: {
          prompt: 500,
          completion: 200,
          total: 700,
        },
        validationErrors: [],
        success: true,
      };

      expect(metrics.attemptNumber).toBe(1);
      expect(metrics.durationMs).toBe(1000);
      expect(metrics.tokenUsage.total).toBe(700);
      expect(metrics.success).toBe(true);
    });

    it('should support validation errors array', () => {
      const metrics: AttemptMetrics = {
        attemptNumber: 1,
        startTime: Date.now(),
        endTime: Date.now() + 1000,
        durationMs: 1000,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [
          { code: 'ERROR_1', message: 'Error 1', path: 'path.to.error' },
          { code: 'ERROR_2', message: 'Error 2' },
        ],
        success: false,
      };

      expect(metrics.validationErrors).toHaveLength(2);
      expect(metrics.success).toBe(false);
    });
  });

  describe('AttemptMetricsSchema validation', () => {
    it('should validate correct metrics', () => {
      const validMetrics = {
        attemptNumber: 1,
        startTime: Date.now(),
        endTime: Date.now() + 1000,
        durationMs: 1000,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      };

      const result = AttemptMetricsSchema.safeParse(validMetrics);
      expect(result.success).toBe(true);
    });

    it('should reject negative attempt number', () => {
      const invalidMetrics = {
        attemptNumber: -1,
        startTime: Date.now(),
        endTime: Date.now() + 1000,
        durationMs: 1000,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      };

      const result = AttemptMetricsSchema.safeParse(invalidMetrics);
      expect(result.success).toBe(false);
    });

    it('should reject negative duration', () => {
      const invalidMetrics = {
        attemptNumber: 1,
        startTime: Date.now(),
        endTime: Date.now() - 1000,
        durationMs: -1000,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      };

      const result = AttemptMetricsSchema.safeParse(invalidMetrics);
      expect(result.success).toBe(false);
    });
  });
});

describe('GenerationMetrics', () => {
  describe('type structure', () => {
    it('should define all required fields', () => {
      const metrics: GenerationMetrics = {
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [700],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      };

      expect(metrics.initialSuccessRate).toBe(1.0);
      expect(metrics.averageRetryCount).toBe(1.0);
      expect(metrics.tokenUsageByAttempt).toHaveLength(1);
      expect(metrics.totalDurationMs).toBe(1000);
    });

    it('should track validation error types', () => {
      const metrics: GenerationMetrics = {
        initialSuccessRate: 0.0,
        averageRetryCount: 2.5,
        tokenUsageByAttempt: [500, 600, 700],
        validationErrorTypes: {
          'MISSING_REQUIRED_PARAM': 3,
          'PARAM_TYPE_MISMATCH': 2,
          'UNKNOWN_PARAM': 1,
        },
        totalDurationMs: 5000,
      };

      expect(metrics.validationErrorTypes['MISSING_REQUIRED_PARAM']).toBe(3);
      expect(Object.keys(metrics.validationErrorTypes)).toHaveLength(3);
    });

    it('should support optional token savings', () => {
      const metricsWithSavings: GenerationMetrics = {
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [500],
        validationErrorTypes: {},
        totalDurationMs: 1000,
        tokenSavedBySelection: 200,
      };

      expect(metricsWithSavings.tokenSavedBySelection).toBe(200);
    });
  });

  describe('GenerationMetricsSchema validation', () => {
    it('should validate correct metrics', () => {
      const validMetrics = {
        initialSuccessRate: 0.5,
        averageRetryCount: 1.5,
        tokenUsageByAttempt: [500, 600],
        validationErrorTypes: { 'ERROR': 2 },
        totalDurationMs: 3000,
      };

      const result = GenerationMetricsSchema.safeParse(validMetrics);
      expect(result.success).toBe(true);
    });

    it('should reject success rate > 1', () => {
      const invalidMetrics = {
        initialSuccessRate: 1.5,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [500],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      };

      const result = GenerationMetricsSchema.safeParse(invalidMetrics);
      expect(result.success).toBe(false);
    });

    it('should reject negative success rate', () => {
      const invalidMetrics = {
        initialSuccessRate: -0.1,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [500],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      };

      const result = GenerationMetricsSchema.safeParse(invalidMetrics);
      expect(result.success).toBe(false);
    });
  });
});

describe('MetricsSummary', () => {
  describe('type structure', () => {
    it('should define summary fields', () => {
      const summary: MetricsSummary = {
        count: 10,
        avgInitialSuccessRate: 0.8,
        avgRetryCount: 1.2,
      };

      expect(summary.count).toBe(10);
      expect(summary.avgInitialSuccessRate).toBe(0.8);
      expect(summary.avgRetryCount).toBe(1.2);
    });

    it('should support optional fields', () => {
      const fullSummary: MetricsSummary = {
        count: 100,
        avgInitialSuccessRate: 0.75,
        avgRetryCount: 1.3,
        totalTokens: 50000,
        topErrorTypes: [
          ['MISSING_REQUIRED_PARAM', 25],
          ['PARAM_TYPE_MISMATCH', 15],
          ['UNKNOWN_PARAM', 10],
        ],
      };

      expect(fullSummary.totalTokens).toBe(50000);
      expect(fullSummary.topErrorTypes).toHaveLength(3);
      expect(fullSummary.topErrorTypes?.[0]).toEqual(['MISSING_REQUIRED_PARAM', 25]);
    });
  });

  describe('MetricsSummarySchema validation', () => {
    it('should validate correct summary', () => {
      const validSummary = {
        count: 10,
        avgInitialSuccessRate: 0.8,
        avgRetryCount: 1.2,
      };

      const result = MetricsSummarySchema.safeParse(validSummary);
      expect(result.success).toBe(true);
    });

    it('should validate summary with optional fields', () => {
      const validSummary = {
        count: 100,
        avgInitialSuccessRate: 0.75,
        avgRetryCount: 1.3,
        totalTokens: 50000,
        topErrorTypes: [['ERROR', 10]],
      };

      const result = MetricsSummarySchema.safeParse(validSummary);
      expect(result.success).toBe(true);
    });

    it('should reject negative count', () => {
      const invalidSummary = {
        count: -1,
        avgInitialSuccessRate: 0.8,
        avgRetryCount: 1.2,
      };

      const result = MetricsSummarySchema.safeParse(invalidSummary);
      expect(result.success).toBe(false);
    });
  });
});
