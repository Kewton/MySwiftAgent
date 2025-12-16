/**
 * @file ApiClient base class implementation
 * @description Base HTTP client with authentication and error handling
 */

import { type Result, ok, err } from '../result';
import { type ApiError, ApiErrorCode, classifyHttpError, createApiError } from '../errors';

/**
 * Authentication type
 */
export type AuthType = 'service-token' | 'api-token' | 'admin-token' | 'none';

/**
 * API client configuration
 */
export interface ApiClientConfig {
	/** Base URL for the API */
	baseUrl: string;
	/** Service name for X-Service header */
	serviceName: string;
	/** Service token for X-Token header (service-token auth) */
	serviceToken?: string;
	/** API token for X-API-Token header (api-token auth) */
	apiToken?: string;
	/** Admin token for X-Admin-Token header (admin-token auth) */
	adminToken?: string;
	/** Authentication type */
	authType?: AuthType;
	/** Request timeout in milliseconds */
	timeout?: number;
}

/**
 * Request options
 */
export interface RequestOptions {
	headers?: Record<string, string>;
	timeout?: number;
}

/**
 * Base API client class
 */
export class ApiClient {
	protected readonly baseUrl: string;
	protected readonly serviceName: string;
	protected readonly serviceToken?: string;
	protected readonly apiToken?: string;
	protected readonly adminToken?: string;
	protected readonly authType: AuthType;
	protected readonly timeout: number;

	constructor(config: ApiClientConfig) {
		this.baseUrl = config.baseUrl;
		this.serviceName = config.serviceName;
		this.serviceToken = config.serviceToken;
		this.apiToken = config.apiToken;
		this.adminToken = config.adminToken;
		this.authType = config.authType ?? 'service-token';
		this.timeout = config.timeout ?? 30000;
	}

	/**
	 * Build headers for request
	 */
	protected buildHeaders(customHeaders?: Record<string, string>): Record<string, string> {
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			...customHeaders
		};

		// Add authentication headers based on auth type
		switch (this.authType) {
			case 'service-token':
				headers['X-Service'] = this.serviceName;
				if (this.serviceToken) {
					headers['X-Token'] = this.serviceToken;
				}
				break;
			case 'api-token':
				if (this.apiToken) {
					headers['X-API-Token'] = this.apiToken;
				}
				break;
			case 'admin-token':
				if (this.adminToken) {
					headers['X-Admin-Token'] = this.adminToken;
				}
				break;
		}

		return headers;
	}

	/**
	 * Build full URL with query parameters
	 */
	protected buildUrl(path: string, params?: Record<string, string>): string {
		// Ensure baseUrl ends without slash and path starts with slash
		const base = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
		const normalizedPath = path.startsWith('/') ? path : `/${path}`;
		const fullUrl = `${base}${normalizedPath}`;

		const url = new URL(fullUrl);
		if (params) {
			Object.entries(params).forEach(([key, value]) => {
				url.searchParams.append(key, value);
			});
		}
		return url.toString();
	}

	/**
	 * Make an HTTP request
	 */
	protected async request<T>(
		method: string,
		path: string,
		body?: unknown,
		params?: Record<string, string>,
		options?: RequestOptions
	): Promise<Result<T, ApiError>> {
		const url = this.buildUrl(path, params);
		const headers = this.buildHeaders(options?.headers);
		const timeout = options?.timeout ?? this.timeout;

		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), timeout);

		try {
			const response = await fetch(url, {
				method,
				headers,
				body: body ? JSON.stringify(body) : undefined,
				signal: controller.signal
			});

			clearTimeout(timeoutId);

			if (!response.ok) {
				const errorBody = await response.json().catch(() => ({}));
				const message = (errorBody as { detail?: string }).detail ?? response.statusText;
				return err(classifyHttpError(response.status, message));
			}

			const data = await response.json();
			return ok(data as T);
		} catch (error) {
			clearTimeout(timeoutId);

			if (error instanceof Error) {
				if (error.name === 'AbortError') {
					return err(
						createApiError({
							code: ApiErrorCode.TIMEOUT,
							message: 'Request timed out'
						})
					);
				}

				return err(
					createApiError({
						code: ApiErrorCode.NETWORK_ERROR,
						message: error.message
					})
				);
			}

			return err(
				createApiError({
					code: ApiErrorCode.UNKNOWN,
					message: 'Unknown error occurred'
				})
			);
		}
	}

	/**
	 * HTTP GET request
	 */
	async get<T>(
		path: string,
		params?: Record<string, string>,
		options?: RequestOptions
	): Promise<Result<T, ApiError>> {
		return this.request<T>('GET', path, undefined, params, options);
	}

	/**
	 * HTTP POST request
	 */
	async post<T>(
		path: string,
		body?: unknown,
		options?: RequestOptions
	): Promise<Result<T, ApiError>> {
		return this.request<T>('POST', path, body, undefined, options);
	}

	/**
	 * HTTP PUT request
	 */
	async put<T>(
		path: string,
		body?: unknown,
		options?: RequestOptions
	): Promise<Result<T, ApiError>> {
		return this.request<T>('PUT', path, body, undefined, options);
	}

	/**
	 * HTTP PATCH request
	 */
	async patch<T>(
		path: string,
		body?: unknown,
		options?: RequestOptions
	): Promise<Result<T, ApiError>> {
		return this.request<T>('PATCH', path, body, undefined, options);
	}

	/**
	 * HTTP DELETE request
	 */
	async delete<T = void>(path: string, options?: RequestOptions): Promise<Result<T, ApiError>> {
		return this.request<T>('DELETE', path, undefined, undefined, options);
	}
}
