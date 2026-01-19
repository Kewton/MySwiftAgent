/**
 * MetricsCollector Unit Tests
 *
 * Issue #374: Generation metrics collection for feedback loop
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  GenerationMetricsCollector,
  MetricsAggregator,
  createMetricsCollector,
  createMetricsAggregator,
} from '../../../../src/taskflowGeneratorAgent/generator/MetricsCollector.js';
import type { AttemptMetrics, GenerationMetrics } from '../../../../src/taskflowGeneratorAgent/types/metrics.js';

describe('GenerationMetricsCollector', () => {
  let collector: GenerationMetricsCollector;

  beforeEach(() => {
    collector = new GenerationMetricsCollector();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('startGeneration', () => {
    it('should record start time', () => {
      const startTime = Date.now();
      collector.startGeneration();

      // Can check indirectly through finalize
      vi.advanceTimersByTime(1000);
      const metrics = collector.finalize();

      expect(metrics.totalDurationMs).toBeGreaterThanOrEqual(1000);
    });

    it('should reset attempts', () => {
      // Record some attempts
      collector.startGeneration();
      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      // Start new generation - should reset
      collector.startGeneration();
      const metrics = collector.finalize();

      expect(metrics.tokenUsageByAttempt).toHaveLength(0);
    });
  });

  describe('recordAttempt', () => {
    it('should record successful attempt', () => {
      collector.startGeneration();

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 500,
        durationMs: 500,
        tokenUsage: { prompt: 200, completion: 100, total: 300 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.tokenUsageByAttempt).toHaveLength(1);
      expect(metrics.tokenUsageByAttempt[0]).toBe(300);
      expect(metrics.initialSuccessRate).toBe(1.0);
    });

    it('should record failed attempt with errors', () => {
      collector.startGeneration();

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 500,
        durationMs: 500,
        tokenUsage: { prompt: 200, completion: 100, total: 300 },
        validationErrors: [
          { code: 'MISSING_REQUIRED_PARAM', message: 'Missing param' },
          { code: 'PARAM_TYPE_MISMATCH', message: 'Type mismatch' },
        ],
        success: false,
      });

      const metrics = collector.finalize();

      expect(metrics.initialSuccessRate).toBe(0.0);
      expect(metrics.validationErrorTypes['MISSING_REQUIRED_PARAM']).toBe(1);
      expect(metrics.validationErrorTypes['PARAM_TYPE_MISMATCH']).toBe(1);
    });

    it('should track multiple attempts', () => {
      collector.startGeneration();

      // First attempt fails
      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 500,
        durationMs: 500,
        tokenUsage: { prompt: 200, completion: 100, total: 300 },
        validationErrors: [
          { code: 'MISSING_REQUIRED_PARAM', message: 'Error 1' },
        ],
        success: false,
      });

      // Second attempt fails
      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 600,
        durationMs: 600,
        tokenUsage: { prompt: 300, completion: 150, total: 450 },
        validationErrors: [
          { code: 'MISSING_REQUIRED_PARAM', message: 'Error 1' },
        ],
        success: false,
      });

      // Third attempt succeeds
      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 700,
        durationMs: 700,
        tokenUsage: { prompt: 400, completion: 200, total: 600 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.tokenUsageByAttempt).toHaveLength(3);
      expect(metrics.tokenUsageByAttempt).toEqual([300, 450, 600]);
      expect(metrics.validationErrorTypes['MISSING_REQUIRED_PARAM']).toBe(2);
      expect(metrics.averageRetryCount).toBe(3);
    });

    it('should auto-increment attempt number', () => {
      collector.startGeneration();

      // Record without explicit attempt number
      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: false,
      });

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();
      expect(metrics.tokenUsageByAttempt).toHaveLength(2);
    });
  });

  describe('finalize', () => {
    it('should calculate initial success rate correctly', () => {
      collector.startGeneration();

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.initialSuccessRate).toBe(1.0);
    });

    it('should calculate zero initial success rate when first fails', () => {
      collector.startGeneration();

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [{ code: 'ERROR', message: 'Failed' }],
        success: false,
      });

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.initialSuccessRate).toBe(0.0);
    });

    it('should calculate average retry count', () => {
      collector.startGeneration();

      // 3 attempts, 1 success
      for (let i = 0; i < 2; i++) {
        collector.recordAttempt({
          startTime: Date.now(),
          endTime: Date.now() + 100,
          durationMs: 100,
          tokenUsage: { prompt: 100, completion: 50, total: 150 },
          validationErrors: [{ code: 'ERROR', message: 'Failed' }],
          success: false,
        });
      }

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.averageRetryCount).toBe(3);
    });

    it('should aggregate validation error types', () => {
      collector.startGeneration();

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [
          { code: 'ERROR_A', message: 'A' },
          { code: 'ERROR_B', message: 'B' },
          { code: 'ERROR_A', message: 'A again' },
        ],
        success: false,
      });

      collector.recordAttempt({
        startTime: Date.now(),
        endTime: Date.now() + 100,
        durationMs: 100,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [
          { code: 'ERROR_A', message: 'A third time' },
        ],
        success: false,
      });

      const metrics = collector.finalize();

      expect(metrics.validationErrorTypes['ERROR_A']).toBe(3);
      expect(metrics.validationErrorTypes['ERROR_B']).toBe(1);
    });

    it('should calculate total duration', () => {
      collector.startGeneration();

      vi.advanceTimersByTime(2000);

      collector.recordAttempt({
        startTime: Date.now() - 1000,
        endTime: Date.now(),
        durationMs: 1000,
        tokenUsage: { prompt: 100, completion: 50, total: 150 },
        validationErrors: [],
        success: true,
      });

      const metrics = collector.finalize();

      expect(metrics.totalDurationMs).toBeGreaterThanOrEqual(2000);
    });

    it('should handle empty attempts', () => {
      collector.startGeneration();
      const metrics = collector.finalize();

      expect(metrics.initialSuccessRate).toBe(0.0);
      expect(metrics.averageRetryCount).toBe(0);
      expect(metrics.tokenUsageByAttempt).toHaveLength(0);
      expect(metrics.validationErrorTypes).toEqual({});
    });
  });
});

describe('MetricsAggregator', () => {
  let aggregator: MetricsAggregator;

  beforeEach(() => {
    aggregator = new MetricsAggregator();
  });

  describe('record', () => {
    it('should record metrics', () => {
      const metrics: GenerationMetrics = {
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      };

      aggregator.record(metrics);

      const summary = aggregator.getSummary();
      expect(summary.count).toBe(1);
    });

    it('should record multiple metrics', () => {
      aggregator.record({
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      });

      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 2.0,
        tokenUsageByAttempt: [300, 400],
        validationErrorTypes: { 'ERROR': 1 },
        totalDurationMs: 2000,
      });

      const summary = aggregator.getSummary();
      expect(summary.count).toBe(2);
    });
  });

  describe('getSummary', () => {
    it('should return zero summary for empty aggregator', () => {
      const summary = aggregator.getSummary();

      expect(summary.count).toBe(0);
      expect(summary.avgInitialSuccessRate).toBe(0);
      expect(summary.avgRetryCount).toBe(0);
    });

    it('should calculate average initial success rate', () => {
      aggregator.record({
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      });

      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 3.0,
        tokenUsageByAttempt: [300, 400, 500],
        validationErrorTypes: {},
        totalDurationMs: 3000,
      });

      const summary = aggregator.getSummary();

      expect(summary.avgInitialSuccessRate).toBe(0.5);
    });

    it('should calculate average retry count', () => {
      aggregator.record({
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      });

      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 3.0,
        tokenUsageByAttempt: [300, 400, 500],
        validationErrorTypes: {},
        totalDurationMs: 3000,
      });

      const summary = aggregator.getSummary();

      expect(summary.avgRetryCount).toBe(2.0);
    });

    it('should calculate total tokens', () => {
      aggregator.record({
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      });

      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 2.0,
        tokenUsageByAttempt: [300, 400],
        validationErrorTypes: {},
        totalDurationMs: 2000,
      });

      const summary = aggregator.getSummary();

      expect(summary.totalTokens).toBe(1000); // 300 + 300 + 400
    });

    it('should aggregate top error types', () => {
      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 2.0,
        tokenUsageByAttempt: [300, 400],
        validationErrorTypes: {
          'MISSING_REQUIRED_PARAM': 2,
          'PARAM_TYPE_MISMATCH': 1,
        },
        totalDurationMs: 2000,
      });

      aggregator.record({
        initialSuccessRate: 0.0,
        averageRetryCount: 3.0,
        tokenUsageByAttempt: [300, 400, 500],
        validationErrorTypes: {
          'MISSING_REQUIRED_PARAM': 3,
          'UNKNOWN_PARAM': 2,
        },
        totalDurationMs: 3000,
      });

      const summary = aggregator.getSummary();

      expect(summary.topErrorTypes).toBeDefined();
      expect(summary.topErrorTypes?.[0]).toEqual(['MISSING_REQUIRED_PARAM', 5]);
    });

    it('should limit top error types to 5', () => {
      const metrics: GenerationMetrics = {
        initialSuccessRate: 0.0,
        averageRetryCount: 5.0,
        tokenUsageByAttempt: [100, 200, 300, 400, 500],
        validationErrorTypes: {
          'ERROR_1': 10,
          'ERROR_2': 9,
          'ERROR_3': 8,
          'ERROR_4': 7,
          'ERROR_5': 6,
          'ERROR_6': 5,
          'ERROR_7': 4,
        },
        totalDurationMs: 5000,
      };

      aggregator.record(metrics);

      const summary = aggregator.getSummary();

      expect(summary.topErrorTypes).toHaveLength(5);
      expect(summary.topErrorTypes?.[0][0]).toBe('ERROR_1');
    });
  });

  describe('reset', () => {
    it('should clear recorded metrics', () => {
      aggregator.record({
        initialSuccessRate: 1.0,
        averageRetryCount: 1.0,
        tokenUsageByAttempt: [300],
        validationErrorTypes: {},
        totalDurationMs: 1000,
      });

      aggregator.reset();

      const summary = aggregator.getSummary();
      expect(summary.count).toBe(0);
    });
  });
});

describe('Factory functions', () => {
  it('should create GenerationMetricsCollector', () => {
    const collector = createMetricsCollector();
    expect(collector).toBeInstanceOf(GenerationMetricsCollector);
  });

  it('should create MetricsAggregator', () => {
    const aggregator = createMetricsAggregator();
    expect(aggregator).toBeInstanceOf(MetricsAggregator);
  });
});
