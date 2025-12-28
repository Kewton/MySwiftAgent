/**
 * JobQueueClient Extended Methods Tests
 * Issue #293: JobQueue Integration for Runs
 *
 * Tests for new methods: createJobFromMaster, getJobTasks, getJobResult, cancelJob, retryTask
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { JobQueueClient } from '$lib/api/clients/job-queue';
import type {
	JobCreateFromMasterRequest,
	TaskList,
	JobResultResponse
} from '$lib/api/clients/job-queue';
import { isOk, isErr } from '$lib/api/result';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('JobQueueClient Extended Methods', () => {
	let client: JobQueueClient;

	beforeEach(() => {
		mockFetch.mockReset();
		client = new JobQueueClient({
			baseUrl: 'http://localhost:8001',
			apiToken: 'test-token'
		});
	});

	describe('createJobFromMaster', () => {
		it('should create a job from master with body parameters', async () => {
			const masterId = 'jm_12345';
			const request: JobCreateFromMasterRequest = {
				name: 'Test Job',
				body: {
					company_name: 'Toyota',
					target_years: '2020-2024'
				},
				tags: ['test']
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: async () => ({
					job_id: 'job_67890',
					status: 'queued'
				})
			});

			const result = await client.createJobFromMaster(masterId, request);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.job_id).toBe('job_67890');
				expect(result.value.status).toBe('queued');
			}

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8001/api/v1/jobs/from-master/jm_12345',
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify(request)
				})
			);
		});

		it('should handle validation errors', async () => {
			const masterId = 'jm_invalid';
			const request: JobCreateFromMasterRequest = {};

			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: async () => ({
					detail: 'Job master not found'
				})
			});

			const result = await client.createJobFromMaster(masterId, request);

			expect(isErr(result)).toBe(true);
		});
	});

	describe('getJobTasks', () => {
		it('should return task list for a job', async () => {
			const jobId = 'job_12345';
			const mockTaskList: TaskList = {
				job_id: jobId,
				tasks: [
					{
						id: 'task_001',
						job_id: jobId,
						master_id: 'tm_001',
						master_version: 1,
						order: 1,
						status: 'succeeded',
						input_data: { query: 'test' },
						output_data: { result: 'success' },
						attempt: 1,
						error: null,
						started_at: '2024-12-26T10:00:00Z',
						finished_at: '2024-12-26T10:00:12Z',
						duration_ms: 12000,
						created_at: '2024-12-26T10:00:00Z',
						updated_at: '2024-12-26T10:00:12Z'
					},
					{
						id: 'task_002',
						job_id: jobId,
						master_id: 'tm_002',
						master_version: 1,
						order: 2,
						status: 'running',
						input_data: null,
						output_data: null,
						attempt: 1,
						error: null,
						started_at: '2024-12-26T10:00:12Z',
						finished_at: null,
						duration_ms: null,
						created_at: '2024-12-26T10:00:12Z',
						updated_at: '2024-12-26T10:00:15Z'
					}
				],
				total: 2
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: async () => mockTaskList
			});

			const result = await client.getJobTasks(jobId);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.job_id).toBe(jobId);
				expect(result.value.tasks).toHaveLength(2);
				expect(result.value.tasks[0].status).toBe('succeeded');
				expect(result.value.tasks[0].output_data).toEqual({ result: 'success' });
				expect(result.value.tasks[1].status).toBe('running');
			}

			expect(mockFetch).toHaveBeenCalledWith(
				`http://localhost:8001/api/v1/jobs/${jobId}/tasks`,
				expect.objectContaining({
					method: 'GET'
				})
			);
		});

		it('should handle job not found', async () => {
			const jobId = 'job_notfound';

			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: async () => ({ detail: 'Job not found' })
			});

			const result = await client.getJobTasks(jobId);

			expect(isErr(result)).toBe(true);
		});
	});

	describe('getJobResult', () => {
		it('should return job result', async () => {
			const jobId = 'job_12345';
			const mockResult: JobResultResponse = {
				job_id: jobId,
				status: 'succeeded',
				result: {
					final_output: { report: 'Generated report content...' }
				},
				error: null,
				finished_at: '2024-12-26T10:05:00Z'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: async () => mockResult
			});

			const result = await client.getJobResult(jobId);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.job_id).toBe(jobId);
				expect(result.value.status).toBe('succeeded');
				expect(result.value.result).toEqual({
					final_output: { report: 'Generated report content...' }
				});
			}
		});
	});

	describe('cancelJob', () => {
		it('should cancel a running job', async () => {
			const jobId = 'job_12345';

			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: async () => ({
					job_id: jobId,
					status: 'canceled'
				})
			});

			const result = await client.cancelJob(jobId);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.status).toBe('canceled');
			}

			expect(mockFetch).toHaveBeenCalledWith(
				`http://localhost:8001/api/v1/jobs/${jobId}/cancel`,
				expect.objectContaining({
					method: 'POST'
				})
			);
		});
	});

	describe('retryTask', () => {
		it('should retry a failed task', async () => {
			const taskId = 'task_12345';

			mockFetch.mockResolvedValueOnce({
				ok: true,
				status: 200,
				json: async () => ({
					task_id: taskId,
					status: 'queued',
					message: 'Task retry scheduled'
				})
			});

			const result = await client.retryTask(taskId);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.task_id).toBe(taskId);
				expect(result.value.status).toBe('queued');
			}

			expect(mockFetch).toHaveBeenCalledWith(
				`http://localhost:8001/api/v1/tasks/${taskId}/retry`,
				expect.objectContaining({
					method: 'POST'
				})
			);
		});
	});
});

describe('TaskStatus Types', () => {
	it('should have correct task status values', () => {
		const validStatuses = ['pending', 'running', 'succeeded', 'failed', 'skipped'];
		expect(validStatuses).toContain('pending');
		expect(validStatuses).toContain('running');
		expect(validStatuses).toContain('succeeded');
		expect(validStatuses).toContain('failed');
		expect(validStatuses).toContain('skipped');
	});
});
