/**
 * RetryStrategy Unit Tests
 *
 * Issue #364: Retry logic with exponential backoff
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  RetryStrategy,
  createRetryStrategy,
  type RetryConfig,
} from '../../../../src/taskflowGeneratorAgent/recovery/RetryStrategy.js';

describe('RetryStrategy', () => {
  describe('constructor', () => {
    it('should use default config', () => {
      const strategy = new RetryStrategy();

      expect(strategy.getConfig().maxAttempts).toBe(3);
      expect(strategy.getConfig().initialDelayMs).toBe(1000);
      expect(strategy.getConfig().maxDelayMs).toBe(10000);
      expect(strategy.getConfig().backoffFactor).toBe(2);
    });

    it('should accept custom config', () => {
      const config: RetryConfig = {
        maxAttempts: 5,
        initialDelayMs: 500,
        maxDelayMs: 5000,
        backoffFactor: 1.5,
      };

      const strategy = new RetryStrategy(config);

      expect(strategy.getConfig()).toEqual(config);
    });
  });

  describe('execute', () => {
    it('should succeed on first attempt', async () => {
      const strategy = new RetryStrategy();
      const fn = vi.fn().mockResolvedValue('success');

      const result = await strategy.execute(fn);

      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should retry on failure and succeed', async () => {
      const strategy = new RetryStrategy({
        maxAttempts: 3,
        initialDelayMs: 10,
        maxDelayMs: 100,
        backoffFactor: 2,
      });

      const fn = vi
        .fn()
        .mockRejectedValueOnce(new Error('First fail'))
        .mockRejectedValueOnce(new Error('Second fail'))
        .mockResolvedValue('success');

      const result = await strategy.execute(fn);

      expect(result).toBe('success');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should throw after max attempts', async () => {
      const strategy = new RetryStrategy({
        maxAttempts: 3,
        initialDelayMs: 10,
        maxDelayMs: 100,
        backoffFactor: 2,
      });

      const fn = vi.fn().mockRejectedValue(new Error('Always fail'));

      await expect(strategy.execute(fn)).rejects.toThrow('Always fail');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should pass attempt number to function', async () => {
      const strategy = new RetryStrategy({
        maxAttempts: 3,
        initialDelayMs: 10,
        maxDelayMs: 100,
        backoffFactor: 2,
      });

      const attempts: number[] = [];
      const fn = vi.fn().mockImplementation((attempt: number) => {
        attempts.push(attempt);
        if (attempt < 3) {
          throw new Error('Retry needed');
        }
        return 'success';
      });

      await strategy.execute(fn);

      expect(attempts).toEqual([1, 2, 3]);
    });

    it('should respect shouldRetry predicate', async () => {
      const strategy = new RetryStrategy({
        maxAttempts: 5,
        initialDelayMs: 10,
        maxDelayMs: 100,
        backoffFactor: 2,
      });

      const authError = new Error('Unauthorized');
      authError.name = 'AuthError';

      const fn = vi.fn().mockRejectedValue(authError);

      const shouldRetry = (error: Error) => error.name !== 'AuthError';

      await expect(strategy.execute(fn, shouldRetry)).rejects.toThrow('Unauthorized');
      expect(fn).toHaveBeenCalledTimes(1); // No retry for auth errors
    });

    it('should call onRetry callback', async () => {
      const strategy = new RetryStrategy({
        maxAttempts: 3,
        initialDelayMs: 10,
        maxDelayMs: 100,
        backoffFactor: 2,
      });

      const fn = vi
        .fn()
        .mockRejectedValueOnce(new Error('First fail'))
        .mockResolvedValue('success');

      const onRetry = vi.fn();

      await strategy.execute(fn, undefined, onRetry);

      expect(onRetry).toHaveBeenCalledTimes(1);
      expect(onRetry).toHaveBeenCalledWith(
        expect.any(Error),
        1,
        expect.any(Number)
      );
    });
  });

  describe('calculateDelay', () => {
    it('should calculate exponential backoff', () => {
      const strategy = new RetryStrategy({
        maxAttempts: 5,
        initialDelayMs: 1000,
        maxDelayMs: 10000,
        backoffFactor: 2,
      });

      // Attempt 1: 1000ms
      // Attempt 2: 2000ms
      // Attempt 3: 4000ms
      // Attempt 4: 8000ms
      // Attempt 5: 10000ms (capped)

      expect(strategy.calculateDelay(1)).toBe(1000);
      expect(strategy.calculateDelay(2)).toBe(2000);
      expect(strategy.calculateDelay(3)).toBe(4000);
      expect(strategy.calculateDelay(4)).toBe(8000);
      expect(strategy.calculateDelay(5)).toBe(10000); // Capped at max
    });

    it('should respect maxDelay', () => {
      const strategy = new RetryStrategy({
        maxAttempts: 10,
        initialDelayMs: 1000,
        maxDelayMs: 5000,
        backoffFactor: 3,
      });

      // Attempt 3: 1000 * 3^2 = 9000 -> capped to 5000
      expect(strategy.calculateDelay(3)).toBe(5000);
    });
  });

  describe('shouldRetryDefault', () => {
    it('should return true for generic errors', () => {
      const strategy = new RetryStrategy();

      expect(strategy.shouldRetryDefault(new Error('Generic error'))).toBe(true);
    });
  });
});

describe('createRetryStrategy', () => {
  it('should create RetryStrategy instance', () => {
    const strategy = createRetryStrategy();

    expect(strategy).toBeInstanceOf(RetryStrategy);
  });

  it('should accept config', () => {
    const config: RetryConfig = {
      maxAttempts: 5,
      initialDelayMs: 500,
      maxDelayMs: 5000,
      backoffFactor: 1.5,
    };

    const strategy = createRetryStrategy(config);

    expect(strategy.getConfig()).toEqual(config);
  });
});
