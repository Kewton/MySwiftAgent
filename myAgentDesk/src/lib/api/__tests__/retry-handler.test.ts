/**
 * @file RetryHandler tests
 * @description TDD Phase 1: RED - Tests for exponential backoff retry logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { RetryHandler, type RetryConfig } from '../base/retry-handler';
import { err, ok } from '../result';
import { ApiErrorCode, createApiError } from '../errors';

describe('RetryHandler', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	describe('constructor', () => {
		it('should use default config values', () => {
			const handler = new RetryHandler();
			expect(handler.config.maxRetries).toBe(3);
			expect(handler.config.baseDelayMs).toBe(1000);
			expect(handler.config.maxDelayMs).toBe(30000);
		});

		it('should accept custom config', () => {
			const config: RetryConfig = {
				maxRetries: 5,
				baseDelayMs: 500,
				maxDelayMs: 10000
			};
			const handler = new RetryHandler(config);
			expect(handler.config.maxRetries).toBe(5);
			expect(handler.config.baseDelayMs).toBe(500);
			expect(handler.config.maxDelayMs).toBe(10000);
		});
	});

	describe('calculateDelay()', () => {
		it('should calculate exponential backoff delay', () => {
			const handler = new RetryHandler({ baseDelayMs: 1000, maxDelayMs: 30000, maxRetries: 3 });

			// 1st retry: 1000ms (baseDelay * 2^0)
			expect(handler.calculateDelay(0)).toBe(1000);

			// 2nd retry: 2000ms (baseDelay * 2^1)
			expect(handler.calculateDelay(1)).toBe(2000);

			// 3rd retry: 4000ms (baseDelay * 2^2)
			expect(handler.calculateDelay(2)).toBe(4000);
		});

		it('should cap delay at maxDelay', () => {
			const handler = new RetryHandler({ baseDelayMs: 1000, maxDelayMs: 3000, maxRetries: 5 });

			// Should be capped at 3000ms
			expect(handler.calculateDelay(3)).toBe(3000);
			expect(handler.calculateDelay(4)).toBe(3000);
		});
	});

	describe('shouldRetry()', () => {
		it('should retry on network errors', () => {
			const handler = new RetryHandler();
			const error = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});
			expect(handler.shouldRetry(error, 0)).toBe(true);
		});

		it('should retry on timeout errors', () => {
			const handler = new RetryHandler();
			const error = createApiError({
				code: ApiErrorCode.TIMEOUT,
				message: 'Request timeout'
			});
			expect(handler.shouldRetry(error, 0)).toBe(true);
		});

		it('should retry on 5xx server errors', () => {
			const handler = new RetryHandler();
			const error = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Internal server error',
				status: 500
			});
			expect(handler.shouldRetry(error, 0)).toBe(true);
		});

		it('should NOT retry on auth errors (401)', () => {
			const handler = new RetryHandler();
			const error = createApiError({
				code: ApiErrorCode.UNAUTHORIZED,
				message: 'Unauthorized',
				status: 401
			});
			expect(handler.shouldRetry(error, 0)).toBe(false);
		});

		it('should NOT retry on validation errors (400)', () => {
			const handler = new RetryHandler();
			const error = createApiError({
				code: ApiErrorCode.VALIDATION_ERROR,
				message: 'Bad request',
				status: 400
			});
			expect(handler.shouldRetry(error, 0)).toBe(false);
		});

		it('should NOT retry when max retries exceeded', () => {
			const handler = new RetryHandler({ maxRetries: 3, baseDelayMs: 1000, maxDelayMs: 30000 });
			const error = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});
			expect(handler.shouldRetry(error, 3)).toBe(false);
		});
	});

	describe('execute()', () => {
		it('should return success on first try', async () => {
			const handler = new RetryHandler();
			const operation = vi.fn().mockResolvedValue(ok('success'));

			const resultPromise = handler.execute(operation);
			await vi.runAllTimersAsync();
			const result = await resultPromise;

			expect(operation).toHaveBeenCalledTimes(1);
			expect(result.ok).toBe(true);
			if (result.ok) {
				expect(result.value).toBe('success');
			}
		});

		it('should retry on retryable error and succeed', async () => {
			const handler = new RetryHandler({
				maxRetries: 3,
				baseDelayMs: 100,
				maxDelayMs: 1000
			});
			const networkError = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});
			const operation = vi
				.fn()
				.mockResolvedValueOnce(err(networkError))
				.mockResolvedValueOnce(ok('success'));

			const resultPromise = handler.execute(operation);
			await vi.runAllTimersAsync();
			const result = await resultPromise;

			expect(operation).toHaveBeenCalledTimes(2);
			expect(result.ok).toBe(true);
		});

		it('should retry up to maxRetries times', async () => {
			const handler = new RetryHandler({
				maxRetries: 3,
				baseDelayMs: 100,
				maxDelayMs: 1000
			});
			const networkError = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});
			const operation = vi.fn().mockResolvedValue(err(networkError));

			const resultPromise = handler.execute(operation);
			await vi.runAllTimersAsync();
			const result = await resultPromise;

			// Initial call + 3 retries = 4 calls
			expect(operation).toHaveBeenCalledTimes(4);
			expect(result.ok).toBe(false);
		});

		it('should NOT retry on non-retryable error', async () => {
			const handler = new RetryHandler();
			const authError = createApiError({
				code: ApiErrorCode.UNAUTHORIZED,
				message: 'Unauthorized',
				status: 401
			});
			const operation = vi.fn().mockResolvedValue(err(authError));

			const result = await handler.execute(operation);

			expect(operation).toHaveBeenCalledTimes(1);
			expect(result.ok).toBe(false);
			if (!result.ok) {
				expect(result.error.code).toBe(ApiErrorCode.UNAUTHORIZED);
			}
		});

		it('should wait appropriate delay between retries', async () => {
			const handler = new RetryHandler({
				maxRetries: 2,
				baseDelayMs: 1000,
				maxDelayMs: 10000
			});
			const networkError = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});
			const operation = vi
				.fn()
				.mockResolvedValueOnce(err(networkError))
				.mockResolvedValueOnce(err(networkError))
				.mockResolvedValueOnce(ok('success'));

			const resultPromise = handler.execute(operation);

			// First call immediately
			expect(operation).toHaveBeenCalledTimes(1);

			// Wait 1000ms for first retry
			await vi.advanceTimersByTimeAsync(1000);
			expect(operation).toHaveBeenCalledTimes(2);

			// Wait 2000ms for second retry
			await vi.advanceTimersByTimeAsync(2000);
			expect(operation).toHaveBeenCalledTimes(3);

			const result = await resultPromise;
			expect(result.ok).toBe(true);
		});
	});
});
