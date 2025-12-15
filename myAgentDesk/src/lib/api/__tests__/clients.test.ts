/**
 * @file API Client implementations tests
 * @description TDD Phase 1: RED - Tests for specific API clients (ExpertAgent, JobQueue, etc.)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ExpertAgentClient } from '../clients/expert-agent';
import { JobQueueClient } from '../clients/job-queue';
import { MySchedulerClient } from '../clients/my-scheduler';
import { MyVaultClient } from '../clients/my-vault';
import { LangfuseClient } from '../clients/langfuse';
import { isOk, isErr } from '../result';
import { ApiErrorCode } from '../errors';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('ExpertAgentClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('generateJob()', () => {
		it('should call job-generator endpoint with user requirement', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					status: 'creating',
					job_id: 'test-job-id',
					job_master_id: null,
					task_breakdown: null
				})
			});

			const client = new ExpertAgentClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.generateJob({
				user_requirement: 'Create a daily report',
				max_retry: 3
			});

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8104/aiagent-api/v1/job-generator',
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify({
						user_requirement: 'Create a daily report',
						max_retry: 3
					})
				})
			);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.job_id).toBe('test-job-id');
			}
		});

		it('should handle job generation errors', async () => {
			mockFetch.mockResolvedValue({
				ok: false,
				status: 500,
				json: async () => ({ detail: 'ANTHROPIC_API_KEY not configured' })
			});

			const client = new ExpertAgentClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.generateJob({
				user_requirement: 'Create a job'
			});

			expect(isErr(result)).toBe(true);
		});
	});

	describe('getJobStatus()', () => {
		it('should get job status by ID', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					job_id: 'test-job-id',
					status: 'completed',
					progress: 100,
					job_master_id: 'jm_123'
				})
			});

			const client = new ExpertAgentClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.getJobStatus('test-job-id');

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8104/aiagent-api/v1/jobs/test-job-id/status',
				expect.any(Object)
			);

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.status).toBe('completed');
			}
		});
	});

	describe('health()', () => {
		it('should check service health', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({ status: 'healthy', service: 'expertAgent' })
			});

			const client = new ExpertAgentClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.health();

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.status).toBe('healthy');
			}
		});
	});
});

describe('JobQueueClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('createJob()', () => {
		it('should create a new job', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 201,
				json: async () => ({
					id: 'job-123',
					status: 'pending'
				})
			});

			const client = new JobQueueClient({
				baseUrl: 'http://localhost:8101',
				apiToken: 'test-token'
			});

			const result = await client.createJob({
				url: 'http://example.com/api',
				method: 'POST',
				body: { key: 'value' },
				timeout_sec: 30,
				max_retries: 3
			});

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8101/api/v1/jobs',
				expect.objectContaining({
					method: 'POST',
					headers: expect.objectContaining({
						'X-API-Token': 'test-token'
					})
				})
			);

			expect(isOk(result)).toBe(true);
		});
	});

	describe('getJobs()', () => {
		it('should list jobs with filters', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ([
					{ id: 'job-1', status: 'pending' },
					{ id: 'job-2', status: 'pending' }
				])
			});

			const client = new JobQueueClient({
				baseUrl: 'http://localhost:8101',
				apiToken: 'test-token'
			});

			const result = await client.getJobs({ status: 'pending', limit: 10 });

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8101/api/v1/jobs?status=pending&limit=10',
				expect.any(Object)
			);

			expect(isOk(result)).toBe(true);
		});
	});

	describe('getJobMasters()', () => {
		it('should list job masters', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ([
					{ id: 'jm-1', name: 'Job Master 1' },
					{ id: 'jm-2', name: 'Job Master 2' }
				])
			});

			const client = new JobQueueClient({
				baseUrl: 'http://localhost:8101',
				apiToken: 'test-token'
			});

			const result = await client.getJobMasters();

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value).toHaveLength(2);
			}
		});
	});
});

describe('MySchedulerClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('createSchedule()', () => {
		it('should create a cron schedule', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 201,
				json: async () => ({
					job_id: 'schedule-123',
					job_name: 'daily_report',
					schedule_type: 'cron'
				})
			});

			const client = new MySchedulerClient({
				baseUrl: 'http://localhost:8102',
				apiToken: 'test-token'
			});

			const result = await client.createSchedule({
				job_name: 'daily_report',
				schedule_type: 'cron',
				cron_expression: '0 9 * * *',
				url: 'http://localhost:8101/api/v1/jobs',
				method: 'POST'
			});

			expect(isOk(result)).toBe(true);
		});
	});

	describe('getSchedules()', () => {
		it('should list schedules', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ([
					{ job_id: 's-1', job_name: 'Schedule 1' }
				])
			});

			const client = new MySchedulerClient({
				baseUrl: 'http://localhost:8102',
				apiToken: 'test-token'
			});

			const result = await client.getSchedules();

			expect(isOk(result)).toBe(true);
		});
	});

	describe('pauseSchedule()', () => {
		it('should pause a schedule', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({ status: 'paused' })
			});

			const client = new MySchedulerClient({
				baseUrl: 'http://localhost:8102',
				apiToken: 'test-token'
			});

			const result = await client.pauseSchedule('schedule-123');

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8102/api/v1/jobs/schedule-123/pause',
				expect.objectContaining({ method: 'POST' })
			);

			expect(isOk(result)).toBe(true);
		});
	});
});

describe('MyVaultClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('getSecret()', () => {
		it('should get a secret by project and key', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					key: 'ANTHROPIC_API_KEY',
					value: 'sk-ant-xxx',
					project: 'default_project'
				})
			});

			const client = new MyVaultClient({
				baseUrl: 'http://localhost:8103',
				serviceName: 'myAgentDesk',
				serviceToken: 'vault-token'
			});

			const result = await client.getSecret('default_project', 'ANTHROPIC_API_KEY');

			expect(mockFetch).toHaveBeenCalledWith(
				'http://localhost:8103/api/secrets/default_project/ANTHROPIC_API_KEY',
				expect.objectContaining({
					headers: expect.objectContaining({
						'X-Service': 'myAgentDesk',
						'X-Token': 'vault-token'
					})
				})
			);

			expect(isOk(result)).toBe(true);
		});
	});

	describe('listSecrets()', () => {
		it('should list all secrets', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ([
					{ key: 'KEY_1', project: 'default_project' },
					{ key: 'KEY_2', project: 'default_project' }
				])
			});

			const client = new MyVaultClient({
				baseUrl: 'http://localhost:8103',
				serviceName: 'myAgentDesk',
				serviceToken: 'vault-token'
			});

			const result = await client.listSecrets();

			expect(isOk(result)).toBe(true);
		});
	});

	describe('createSecret()', () => {
		it('should create a new secret', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 201,
				json: async () => ({
					key: 'NEW_KEY',
					project: 'default_project'
				})
			});

			const client = new MyVaultClient({
				baseUrl: 'http://localhost:8103',
				serviceName: 'myAgentDesk',
				serviceToken: 'vault-token'
			});

			const result = await client.createSecret({
				project: 'default_project',
				key: 'NEW_KEY',
				value: 'secret-value',
				description: 'A new secret'
			});

			expect(isOk(result)).toBe(true);
		});
	});
});

describe('LangfuseClient', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	describe('getTraces()', () => {
		it('should get traces with filters', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					traces: [
						{ id: 'trace-1', name: 'Job Generator Execution' }
					],
					total: 1,
					limit: 10,
					offset: 0
				})
			});

			const client = new LangfuseClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.getTraces({ limit: 10 });

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.traces).toHaveLength(1);
			}
		});
	});

	describe('getTrace()', () => {
		it('should get a single trace by ID', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					id: 'trace-123',
					name: 'Test Trace',
					observations: []
				})
			});

			const client = new LangfuseClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.getTrace('trace-123');

			expect(isOk(result)).toBe(true);
		});
	});

	describe('submitScore()', () => {
		it('should submit a feedback score', async () => {
			mockFetch.mockResolvedValue({
				ok: true,
				status: 200,
				json: async () => ({
					success: true,
					score_id: 'score-123'
				})
			});

			const client = new LangfuseClient({
				baseUrl: 'http://localhost:8104/aiagent-api'
			});

			const result = await client.submitScore({
				trace_id: 'trace-123',
				name: 'user_rating',
				value: 0.9,
				comment: 'Great response'
			});

			expect(isOk(result)).toBe(true);
		});
	});
});
