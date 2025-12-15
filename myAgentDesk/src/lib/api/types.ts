/**
 * @file Common API types
 * @description Shared types used across API clients
 */

/**
 * HTTP method types
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/**
 * Job status types
 */
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

/**
 * Schedule type
 */
export type ScheduleType = 'cron' | 'interval' | 'date';

/**
 * Health check response
 */
export interface HealthCheckResponse {
	status: 'healthy' | 'unhealthy';
	service: string;
	version?: string;
	timestamp?: string;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
	limit?: number;
	offset?: number;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	limit: number;
	offset: number;
}

/**
 * API response with metadata
 */
export interface ApiResponse<T> {
	data: T;
	meta?: {
		timestamp: string;
		request_id?: string;
	};
}

/**
 * Service error response from backends
 */
export interface ServiceErrorResponse {
	detail: string;
	code?: string;
	errors?: Array<{
		field: string;
		message: string;
	}>;
}
