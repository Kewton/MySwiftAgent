/**
 * Job API Service Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createJob } from './job-api';
import { ServiceError } from './types';
import type { RequirementState, JobCreationResponse } from './types';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('createJob', () => {
	const conversationId = 'test-conv-123';
	const requirements: RequirementState = {
		data_source: 'CSV file',
		process_description: 'データ分析',
		output_format: 'Excel',
		schedule: '毎日',
		completeness: 0.9
	};

	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('should successfully create a job', async () => {
		const mockResponse: JobCreationResponse = {
			job_id: 'job-123',
			job_master_id: 'master-456',
			status: 'created',
			message: 'Job created successfully'
		};

		mockFetch.mockResolvedValue({
			ok: true,
			json: async () => mockResponse
		});

		const result = await createJob(conversationId, requirements);

		expect(mockFetch).toHaveBeenCalledWith(
			'http://localhost:8104/aiagent-api/v1/chat/create-job',
			{
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					conversation_id: conversationId,
					requirements
				})
			}
		);

		expect(result).toEqual(mockResponse);
	});

	it('should throw ServiceError on network failure', async () => {
		mockFetch.mockRejectedValue(new Error('Network error'));

		await expect(createJob(conversationId, requirements)).rejects.toThrow(ServiceError);

		await expect(createJob(conversationId, requirements)).rejects.toThrow(
			'Failed to connect to job creation API'
		);
	});

	it('should throw ServiceError on HTTP 400 error', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 400,
			json: async () => ({ detail: 'Invalid requirements' })
		});

		await expect(createJob(conversationId, requirements)).rejects.toThrow(ServiceError);

		await expect(createJob(conversationId, requirements)).rejects.toThrow(
			'Job creation failed: Invalid requirements'
		);
	});

	it('should throw ServiceError on HTTP 500 error with unknown detail', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 500,
			json: async () => ({})
		});

		await expect(createJob(conversationId, requirements)).rejects.toThrow(ServiceError);

		await expect(createJob(conversationId, requirements)).rejects.toThrow(
			'Job creation failed: Unknown error'
		);
	});

	it('should throw ServiceError when JSON parsing fails', async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => {
				throw new Error('Invalid JSON');
			}
		});

		await expect(createJob(conversationId, requirements)).rejects.toThrow(ServiceError);

		await expect(createJob(conversationId, requirements)).rejects.toThrow(
			'Failed to parse job creation response'
		);
	});

	it('should include status code in ServiceError', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 403,
			json: async () => ({ detail: 'Forbidden' })
		});

		try {
			await createJob(conversationId, requirements);
			// Should not reach here
			expect(true).toBe(false);
		} catch (error) {
			expect(error).toBeInstanceOf(ServiceError);
			expect((error as ServiceError).statusCode).toBe(403);
			expect((error as ServiceError).message).toBe('Job creation failed: Forbidden');
		}
	});
});
