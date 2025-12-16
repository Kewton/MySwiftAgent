/**
 * @file ApiError type implementation
 * @description API error types and classification utilities
 */

/**
 * API error codes enum
 */
export enum ApiErrorCode {
	// Authentication errors
	UNAUTHORIZED = 'UNAUTHORIZED',
	FORBIDDEN = 'FORBIDDEN',

	// Client errors
	VALIDATION_ERROR = 'VALIDATION_ERROR',
	NOT_FOUND = 'NOT_FOUND',

	// Server errors
	SERVER_ERROR = 'SERVER_ERROR',

	// Network errors
	NETWORK_ERROR = 'NETWORK_ERROR',
	TIMEOUT = 'TIMEOUT',

	// Circuit breaker
	CIRCUIT_OPEN = 'CIRCUIT_OPEN',

	// Unknown
	UNKNOWN = 'UNKNOWN'
}

/**
 * API error interface
 */
export interface ApiError {
	code: ApiErrorCode;
	message: string;
	status?: number;
	details?: Record<string, unknown>;
	timestamp: number;
}

/**
 * Input for creating an API error
 */
export interface CreateApiErrorInput {
	code: ApiErrorCode;
	message: string;
	status?: number;
	details?: Record<string, unknown>;
}

/**
 * Create an API error with automatic timestamp
 */
export function createApiError(input: CreateApiErrorInput): ApiError {
	return {
		code: input.code,
		message: input.message,
		status: input.status,
		details: input.details,
		timestamp: Date.now()
	};
}

/**
 * Check if error is an authentication error (401 or 403)
 */
export function isAuthError(error: ApiError): boolean {
	return error.code === ApiErrorCode.UNAUTHORIZED || error.code === ApiErrorCode.FORBIDDEN;
}

/**
 * Check if error is a network error
 */
export function isNetworkError(error: ApiError): boolean {
	return error.code === ApiErrorCode.NETWORK_ERROR;
}

/**
 * Check if error is a timeout error
 */
export function isTimeoutError(error: ApiError): boolean {
	return error.code === ApiErrorCode.TIMEOUT;
}

/**
 * Check if error is a server error (5xx)
 */
export function isServerError(error: ApiError): boolean {
	return error.status !== undefined && error.status >= 500 && error.status < 600;
}

/**
 * Check if error is a validation error (400, 422)
 */
export function isValidationError(error: ApiError): boolean {
	return error.code === ApiErrorCode.VALIDATION_ERROR;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: ApiError): boolean {
	return (
		isNetworkError(error) ||
		isTimeoutError(error) ||
		isServerError(error) ||
		error.code === ApiErrorCode.SERVER_ERROR
	);
}

/**
 * Classify HTTP status code to ApiError
 */
export function classifyHttpError(status: number, message: string): ApiError {
	let code: ApiErrorCode;

	switch (status) {
		case 401:
			code = ApiErrorCode.UNAUTHORIZED;
			break;
		case 403:
			code = ApiErrorCode.FORBIDDEN;
			break;
		case 404:
			code = ApiErrorCode.NOT_FOUND;
			break;
		case 400:
		case 422:
			code = ApiErrorCode.VALIDATION_ERROR;
			break;
		default:
			if (status >= 500 && status < 600) {
				code = ApiErrorCode.SERVER_ERROR;
			} else {
				code = ApiErrorCode.UNKNOWN;
			}
	}

	return createApiError({ code, message, status });
}
