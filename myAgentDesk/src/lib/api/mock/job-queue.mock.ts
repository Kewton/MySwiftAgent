/**
 * @file JobQueueClient mock implementation
 * @description Mock client for JobQueue API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	JobQueueClient,
	CreateJobRequest,
	JobResponse,
	JobListFilter,
	JobMasterResponse
} from '../clients/job-queue';

/**
 * Mock data for jobs
 */
const mockJobs: JobResponse[] = [
	{ id: 'job-1', status: 'completed', url: 'http://example.com/api1', method: 'POST' },
	{ id: 'job-2', status: 'pending', url: 'http://example.com/api2', method: 'GET' },
	{ id: 'job-3', status: 'running', url: 'http://example.com/api3', method: 'POST' }
];

/**
 * Mock data for job masters
 */
const mockJobMasters: JobMasterResponse[] = [
	{
		id: 'jm-1',
		name: 'Daily Report Generator',
		description: 'Generate daily reports from Gmail',
		tasks: [
			{ id: 'tm-1', name: 'Fetch Emails', order: 1 },
			{ id: 'tm-2', name: 'Summarize Content', order: 2 },
			{ id: 'tm-3', name: 'Send to Slack', order: 3 }
		]
	},
	{
		id: 'jm-2',
		name: 'Weekly Backup',
		description: 'Backup database weekly',
		tasks: [{ id: 'tm-4', name: 'Run Backup', order: 1 }]
	}
];

/**
 * Mock JobQueue client
 */
export class JobQueueClientMock implements Partial<JobQueueClient> {
	private jobs: JobResponse[] = [...mockJobs];
	private jobIdCounter = 100;

	async createJob(request: CreateJobRequest): Promise<Result<JobResponse, ApiError>> {
		await this.delay(100);
		const newJob: JobResponse = {
			id: `job-${++this.jobIdCounter}`,
			status: 'pending',
			url: request.url,
			method: request.method
		};
		this.jobs.push(newJob);
		return ok(newJob);
	}

	async getJobs(filter?: JobListFilter): Promise<Result<JobResponse[], ApiError>> {
		await this.delay(50);
		let result = [...this.jobs];
		if (filter?.status) {
			result = result.filter((j) => j.status === filter.status);
		}
		if (filter?.limit) {
			result = result.slice(0, filter.limit);
		}
		return ok(result);
	}

	async getJob(jobId: string): Promise<Result<JobResponse, ApiError>> {
		await this.delay(50);
		const job = this.jobs.find((j) => j.id === jobId);
		if (job) {
			return ok(job);
		}
		return ok({ id: jobId, status: 'not_found' });
	}

	async updateJob(
		jobId: string,
		update: Partial<JobResponse>
	): Promise<Result<JobResponse, ApiError>> {
		await this.delay(50);
		const idx = this.jobs.findIndex((j) => j.id === jobId);
		if (idx >= 0) {
			this.jobs[idx] = { ...this.jobs[idx], ...update };
			return ok(this.jobs[idx]);
		}
		return ok({ id: jobId, status: 'not_found', ...update });
	}

	async deleteJob(_jobId: string): Promise<Result<void, ApiError>> {
		await this.delay(50);
		return ok(undefined);
	}

	async getJobMasters(): Promise<Result<JobMasterResponse[], ApiError>> {
		await this.delay(50);
		return ok(mockJobMasters);
	}

	async createJobMaster(
		request: Omit<JobMasterResponse, 'id'>
	): Promise<Result<JobMasterResponse, ApiError>> {
		await this.delay(100);
		return ok({
			id: `jm-${Date.now()}`,
			...request
		});
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
