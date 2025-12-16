/**
 * @file ApiError type tests
 * @description TDD Phase 1: RED - Tests for API error types and classification
 */

import { describe, it, expect } from 'vitest';
import {
	createApiError,
	isAuthError,
	isNetworkError,
	isTimeoutError,
	isServerError,
	isValidationError,
	classifyHttpError,
	ApiErrorCode
} from '../errors';

describe('ApiError', () => {
	describe('createApiError()', () => {
		it('should create an ApiError with all fields', () => {
			const error = createApiError({
				code: ApiErrorCode.UNAUTHORIZED,
				message: 'Authentication failed',
				status: 401,
				details: { reason: 'invalid_token' }
			});

			expect(error.code).toBe(ApiErrorCode.UNAUTHORIZED);
			expect(error.message).toBe('Authentication failed');
			expect(error.status).toBe(401);
			expect(error.details).toEqual({ reason: 'invalid_token' });
		});

		it('should create an ApiError with optional fields', () => {
			const error = createApiError({
				code: ApiErrorCode.NETWORK_ERROR,
				message: 'Network error'
			});

			expect(error.code).toBe(ApiErrorCode.NETWORK_ERROR);
			expect(error.message).toBe('Network error');
			expect(error.status).toBeUndefined();
			expect(error.details).toBeUndefined();
		});

		it('should set timestamp automatically', () => {
			const before = Date.now();
			const error = createApiError({
				code: ApiErrorCode.UNKNOWN,
				message: 'Unknown error'
			});
			const after = Date.now();

			expect(error.timestamp).toBeGreaterThanOrEqual(before);
			expect(error.timestamp).toBeLessThanOrEqual(after);
		});
	});

	describe('Error classification functions', () => {
		describe('isAuthError()', () => {
			it('should return true for 401 errors', () => {
				const error = createApiError({
					code: ApiErrorCode.UNAUTHORIZED,
					message: 'Unauthorized',
					status: 401
				});
				expect(isAuthError(error)).toBe(true);
			});

			it('should return true for 403 errors', () => {
				const error = createApiError({
					code: ApiErrorCode.FORBIDDEN,
					message: 'Forbidden',
					status: 403
				});
				expect(isAuthError(error)).toBe(true);
			});

			it('should return false for other errors', () => {
				const error = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Server error',
					status: 500
				});
				expect(isAuthError(error)).toBe(false);
			});
		});

		describe('isNetworkError()', () => {
			it('should return true for network errors', () => {
				const error = createApiError({
					code: ApiErrorCode.NETWORK_ERROR,
					message: 'Network error'
				});
				expect(isNetworkError(error)).toBe(true);
			});

			it('should return false for other errors', () => {
				const error = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Server error',
					status: 500
				});
				expect(isNetworkError(error)).toBe(false);
			});
		});

		describe('isTimeoutError()', () => {
			it('should return true for timeout errors', () => {
				const error = createApiError({
					code: ApiErrorCode.TIMEOUT,
					message: 'Request timeout'
				});
				expect(isTimeoutError(error)).toBe(true);
			});

			it('should return false for other errors', () => {
				const error = createApiError({
					code: ApiErrorCode.NETWORK_ERROR,
					message: 'Network error'
				});
				expect(isTimeoutError(error)).toBe(false);
			});
		});

		describe('isServerError()', () => {
			it('should return true for 5xx errors', () => {
				const error500 = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Internal error',
					status: 500
				});
				expect(isServerError(error500)).toBe(true);

				const error502 = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Bad gateway',
					status: 502
				});
				expect(isServerError(error502)).toBe(true);

				const error503 = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Service unavailable',
					status: 503
				});
				expect(isServerError(error503)).toBe(true);
			});

			it('should return false for 4xx errors', () => {
				const error = createApiError({
					code: ApiErrorCode.VALIDATION_ERROR,
					message: 'Bad request',
					status: 400
				});
				expect(isServerError(error)).toBe(false);
			});
		});

		describe('isValidationError()', () => {
			it('should return true for validation errors', () => {
				const error = createApiError({
					code: ApiErrorCode.VALIDATION_ERROR,
					message: 'Invalid input',
					status: 400
				});
				expect(isValidationError(error)).toBe(true);

				const error422 = createApiError({
					code: ApiErrorCode.VALIDATION_ERROR,
					message: 'Unprocessable entity',
					status: 422
				});
				expect(isValidationError(error422)).toBe(true);
			});

			it('should return false for other errors', () => {
				const error = createApiError({
					code: ApiErrorCode.SERVER_ERROR,
					message: 'Server error',
					status: 500
				});
				expect(isValidationError(error)).toBe(false);
			});
		});
	});

	describe('classifyHttpError()', () => {
		it('should classify 401 as UNAUTHORIZED', () => {
			const error = classifyHttpError(401, 'Unauthorized');
			expect(error.code).toBe(ApiErrorCode.UNAUTHORIZED);
			expect(error.status).toBe(401);
		});

		it('should classify 403 as FORBIDDEN', () => {
			const error = classifyHttpError(403, 'Forbidden');
			expect(error.code).toBe(ApiErrorCode.FORBIDDEN);
			expect(error.status).toBe(403);
		});

		it('should classify 404 as NOT_FOUND', () => {
			const error = classifyHttpError(404, 'Not found');
			expect(error.code).toBe(ApiErrorCode.NOT_FOUND);
			expect(error.status).toBe(404);
		});

		it('should classify 400 as VALIDATION_ERROR', () => {
			const error = classifyHttpError(400, 'Bad request');
			expect(error.code).toBe(ApiErrorCode.VALIDATION_ERROR);
			expect(error.status).toBe(400);
		});

		it('should classify 422 as VALIDATION_ERROR', () => {
			const error = classifyHttpError(422, 'Unprocessable entity');
			expect(error.code).toBe(ApiErrorCode.VALIDATION_ERROR);
			expect(error.status).toBe(422);
		});

		it('should classify 5xx as SERVER_ERROR', () => {
			const error500 = classifyHttpError(500, 'Internal server error');
			expect(error500.code).toBe(ApiErrorCode.SERVER_ERROR);

			const error502 = classifyHttpError(502, 'Bad gateway');
			expect(error502.code).toBe(ApiErrorCode.SERVER_ERROR);

			const error503 = classifyHttpError(503, 'Service unavailable');
			expect(error503.code).toBe(ApiErrorCode.SERVER_ERROR);
		});

		it('should classify unknown status as UNKNOWN', () => {
			const error = classifyHttpError(418, "I'm a teapot");
			expect(error.code).toBe(ApiErrorCode.UNKNOWN);
			expect(error.status).toBe(418);
		});
	});
});
