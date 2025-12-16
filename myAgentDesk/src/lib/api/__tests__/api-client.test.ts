/**
 * @file ApiClient base class tests
 * @description TDD Phase 1: RED - Tests for base ApiClient with Service Token auth
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiClient } from '../base/api-client';
import { isOk, isErr } from '../result';
import { ApiErrorCode } from '../errors';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('ApiClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('constructor', () => {
		it('should create client with required config', () => {
			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'test-service'
			});

			expect(client).toBeDefined();
		});

		it('should accept optional service token', () => {
			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'test-service',
				serviceToken: 'secret-token'
			});

			expect(client).toBeDefined();
		});

		it('should accept timeout configuration', () => {
			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'test-service',
				timeout: 5000
			});

			expect(client).toBeDefined();
		});
	});

	describe('request()', () => {
		it('should make GET request with proper headers', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({ data: 'test' })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'test-token'
			});

			const result = await client.get<{ data: string }>('/api/test');

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8000/api/test',
				expect.objectContaining({
					method: 'GET',
					headers: expect.objectContaining({
						'X-Service': 'myAgentDesk',
						'X-Token': 'test-token',
						'Content-Type': 'application/json'
					})
				})
			);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.data).toBe('test');
			}
		});

		it('should make POST request with body', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 201,
				json: async () => ({ id: 1 })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'test-token'
			});

			const body = { name: 'test' };
			const result = await client.post<{ id: number }>('/api/items', body);

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8000/api/items',
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify(body)
				})
			);

			expect(isOk(result)).toBe(true);
		});

		it('should make PUT request', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({ updated: true })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'test-token'
			});

			const result = await client.put<{ updated: boolean }>('/api/items/1', { name: 'updated' });

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8000/api/items/1',
				expect.objectContaining({
					method: 'PUT'
				})
			);

			expect(isOk(result)).toBe(true);
		});

		it('should make DELETE request', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 204,
				json: async () => ({})
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'test-token'
			});

			const result = await client.delete('/api/items/1');

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8000/api/items/1',
				expect.objectContaining({
					method: 'DELETE'
				})
			);

			expect(isOk(result)).toBe(true);
		});

		it('should handle query parameters', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({ items: [] })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk'
			});

			await client.get('/api/items', { status: 'pending', limit: '10' });

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8000/api/items?status=pending&limit=10',
				expect.any(Object)
			);
		});
	});

	describe('Error handling', () => {
		it('should classify 401 error correctly', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 401,
				json: async () => ({ detail: 'Unauthorized' })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'invalid-token'
			});

			const result = await client.get('/api/protected');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.UNAUTHORIZED);
				expect(result.error.status).toBe(401);
			}
		});

		it('should classify 403 error correctly', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 403,
				json: async () => ({ detail: 'Forbidden' })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk'
			});

			const result = await client.get('/api/admin');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.FORBIDDEN);
			}
		});

		it('should classify 404 error correctly', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 404,
				json: async () => ({ detail: 'Not found' })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk'
			});

			const result = await client.get('/api/nonexistent');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.NOT_FOUND);
			}
		});

		it('should classify 500 error correctly', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 500,
				json: async () => ({ detail: 'Internal server error' })
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk'
			});

			const result = await client.get('/api/error');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.SERVER_ERROR);
			}
		});

		it('should handle network errors', async () => {
			mockFetch.mockRejectedValue(new Error('Network error'));

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk'
			});

			const result = await client.get('/api/test');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.NETWORK_ERROR);
			}
		});

		it('should handle timeout errors', async () => {
			const abortError = new Error('The operation was aborted');
			abortError.name = 'AbortError';
			mockFetch.mockRejectedValue(abortError);

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				timeout: 1000
			});

			const result = await client.get('/api/slow');

			expect(isErr(result)).toBe(true);
			if (isErr(result)) {
				expect(result.error.code).toBe(ApiErrorCode.TIMEOUT);
			}
		});
	});

	describe('Custom headers', () => {
		it('should merge custom headers', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({})
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				serviceToken: 'token'
			});

			await client.get('/api/test', undefined, {
				headers: { 'X-Custom-Header': 'custom-value' }
			});

			expect(mockFetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({
					headers: expect.objectContaining({
						'X-Custom-Header': 'custom-value',
						'X-Service': 'myAgentDesk'
					})
				})
			);
		});
	});

	describe('API Token authentication', () => {
		it('should use X-API-Token header when specified', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({})
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				apiToken: 'api-token-123',
				authType: 'api-token'
			});

			await client.get('/api/test');

			expect(mockFetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({
					headers: expect.objectContaining({
						'X-API-Token': 'api-token-123'
					})
				})
			);
		});
	});

	describe('Admin Token authentication', () => {
		it('should use X-Admin-Token header when specified', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({})
			});

			const client = new ApiClient({
				baseUrl: 'http://localhost:8000',
				serviceName: 'myAgentDesk',
				adminToken: 'admin-token-abc',
				authType: 'admin-token'
			});

			await client.get('/api/admin/test');

			expect(mockFetch).toHaveBeenCalledWith(
				expect.any(String),
				expect.objectContaining({
					headers: expect.objectContaining({
						'X-Admin-Token': 'admin-token-abc'
					})
				})
			);
		});
	});
});
