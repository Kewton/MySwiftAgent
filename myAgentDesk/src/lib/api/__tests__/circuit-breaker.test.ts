/**
 * @file CircuitBreaker tests
 * @description TDD Phase 1: RED - Tests for circuit breaker pattern
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { CircuitBreaker, CircuitState, type CircuitBreakerConfig } from '../base/circuit-breaker';
import { err, ok } from '../result';
import { ApiErrorCode, createApiError } from '../errors';

describe('CircuitBreaker', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	describe('constructor', () => {
		it('should use default config values', () => {
			const breaker = new CircuitBreaker();
			expect(breaker.config.failureThreshold).toBe(5);
			expect(breaker.config.resetTimeoutMs).toBe(30000);
			expect(breaker.config.halfOpenMaxAttempts).toBe(3);
		});

		it('should accept custom config', () => {
			const config: CircuitBreakerConfig = {
				failureThreshold: 3,
				resetTimeoutMs: 10000,
				halfOpenMaxAttempts: 1
			};
			const breaker = new CircuitBreaker(config);
			expect(breaker.config.failureThreshold).toBe(3);
			expect(breaker.config.resetTimeoutMs).toBe(10000);
			expect(breaker.config.halfOpenMaxAttempts).toBe(1);
		});
	});

	describe('initial state', () => {
		it('should start in CLOSED state', () => {
			const breaker = new CircuitBreaker();
			expect(breaker.state).toBe(CircuitState.CLOSED);
		});

		it('should have zero failure count initially', () => {
			const breaker = new CircuitBreaker();
			expect(breaker.failureCount).toBe(0);
		});
	});

	describe('CLOSED state behavior', () => {
		it('should allow execution in CLOSED state', async () => {
			const breaker = new CircuitBreaker();
			const operation = vi.fn().mockResolvedValue(ok('success'));

			const result = await breaker.execute(operation);

			expect(operation).toHaveBeenCalled();
			expect(result.ok).toBe(true);
		});

		it('should increment failure count on error', async () => {
			const breaker = new CircuitBreaker();
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});
			const operation = vi.fn().mockResolvedValue(err(serverError));

			await breaker.execute(operation);

			expect(breaker.failureCount).toBe(1);
			expect(breaker.state).toBe(CircuitState.CLOSED);
		});

		it('should reset failure count on success', async () => {
			const breaker = new CircuitBreaker();
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// First, fail some requests
			const failOp = vi.fn().mockResolvedValue(err(serverError));
			await breaker.execute(failOp);
			await breaker.execute(failOp);
			expect(breaker.failureCount).toBe(2);

			// Then succeed
			const successOp = vi.fn().mockResolvedValue(ok('success'));
			await breaker.execute(successOp);

			expect(breaker.failureCount).toBe(0);
		});

		it('should transition to OPEN when failure threshold reached', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 3,
				resetTimeoutMs: 30000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});
			const operation = vi.fn().mockResolvedValue(err(serverError));

			await breaker.execute(operation);
			await breaker.execute(operation);
			expect(breaker.state).toBe(CircuitState.CLOSED);

			await breaker.execute(operation);
			expect(breaker.state).toBe(CircuitState.OPEN);
		});
	});

	describe('OPEN state behavior', () => {
		it('should reject execution in OPEN state without calling operation', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 30000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			const failOp = vi.fn().mockResolvedValue(err(serverError));
			await breaker.execute(failOp);
			expect(breaker.state).toBe(CircuitState.OPEN);

			// Attempt to execute - should be rejected
			const newOp = vi.fn().mockResolvedValue(ok('success'));
			const result = await breaker.execute(newOp);

			expect(newOp).not.toHaveBeenCalled();
			expect(result.ok).toBe(false);
			if (!result.ok) {
				expect(result.error.code).toBe(ApiErrorCode.CIRCUIT_OPEN);
			}
		});

		it('should transition to HALF_OPEN after reset timeout', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 10000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			const failOp = vi.fn().mockResolvedValue(err(serverError));
			await breaker.execute(failOp);
			expect(breaker.state).toBe(CircuitState.OPEN);

			// Advance time past reset timeout
			vi.advanceTimersByTime(10001);

			// Next execution should transition to HALF_OPEN
			const successOp = vi.fn().mockResolvedValue(ok('success'));
			await breaker.execute(successOp);

			// After success in HALF_OPEN, should go to CLOSED
			expect(breaker.state).toBe(CircuitState.CLOSED);
		});
	});

	describe('HALF_OPEN state behavior', () => {
		it('should allow limited executions in HALF_OPEN state', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 10000,
				halfOpenMaxAttempts: 2
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			await breaker.execute(vi.fn().mockResolvedValue(err(serverError)));
			expect(breaker.state).toBe(CircuitState.OPEN);

			// Advance time past reset timeout
			vi.advanceTimersByTime(10001);

			// Should allow 2 attempts in HALF_OPEN
			const op1 = vi.fn().mockResolvedValue(err(serverError));
			await breaker.execute(op1);
			expect(op1).toHaveBeenCalled();
			expect(breaker.state).toBe(CircuitState.OPEN); // Failed, back to OPEN
		});

		it('should transition to CLOSED on success in HALF_OPEN', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 10000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			await breaker.execute(vi.fn().mockResolvedValue(err(serverError)));
			vi.advanceTimersByTime(10001);

			// Success should close circuit
			const successOp = vi.fn().mockResolvedValue(ok('success'));
			await breaker.execute(successOp);

			expect(breaker.state).toBe(CircuitState.CLOSED);
			expect(breaker.failureCount).toBe(0);
		});

		it('should transition back to OPEN on failure in HALF_OPEN', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 10000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			await breaker.execute(vi.fn().mockResolvedValue(err(serverError)));
			vi.advanceTimersByTime(10001);

			// Failure should re-open circuit
			const failOp = vi.fn().mockResolvedValue(err(serverError));
			await breaker.execute(failOp);

			expect(breaker.state).toBe(CircuitState.OPEN);
		});
	});

	describe('reset()', () => {
		it('should reset breaker to initial state', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 1,
				resetTimeoutMs: 30000,
				halfOpenMaxAttempts: 1
			});
			const serverError = createApiError({
				code: ApiErrorCode.SERVER_ERROR,
				message: 'Server error',
				status: 500
			});

			// Trip the circuit
			await breaker.execute(vi.fn().mockResolvedValue(err(serverError)));
			expect(breaker.state).toBe(CircuitState.OPEN);

			// Reset
			breaker.reset();

			expect(breaker.state).toBe(CircuitState.CLOSED);
			expect(breaker.failureCount).toBe(0);
		});
	});

	describe('Non-retryable errors', () => {
		it('should NOT count auth errors towards failure threshold', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 2,
				resetTimeoutMs: 30000,
				halfOpenMaxAttempts: 1
			});
			const authError = createApiError({
				code: ApiErrorCode.UNAUTHORIZED,
				message: 'Unauthorized',
				status: 401
			});
			const operation = vi.fn().mockResolvedValue(err(authError));

			await breaker.execute(operation);
			await breaker.execute(operation);
			await breaker.execute(operation);

			// Auth errors should not trip the circuit
			expect(breaker.state).toBe(CircuitState.CLOSED);
			expect(breaker.failureCount).toBe(0);
		});

		it('should NOT count validation errors towards failure threshold', async () => {
			const breaker = new CircuitBreaker({
				failureThreshold: 2,
				resetTimeoutMs: 30000,
				halfOpenMaxAttempts: 1
			});
			const validationError = createApiError({
				code: ApiErrorCode.VALIDATION_ERROR,
				message: 'Bad request',
				status: 400
			});
			const operation = vi.fn().mockResolvedValue(err(validationError));

			await breaker.execute(operation);
			await breaker.execute(operation);
			await breaker.execute(operation);

			// Validation errors should not trip the circuit
			expect(breaker.state).toBe(CircuitState.CLOSED);
			expect(breaker.failureCount).toBe(0);
		});
	});
});
