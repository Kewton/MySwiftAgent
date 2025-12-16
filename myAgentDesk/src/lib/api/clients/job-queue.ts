/**
 * @file JobQueueClient implementation
 * @description Client for JobQueue API (job management, task execution)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';

/**
 * JobQueue client configuration
 */
export interface JobQueueClientConfig {
	baseUrl: string;
	apiToken: string;
}

/**
 * Create job request
 */
export interface CreateJobRequest {
	url: string;
	method: string;
	headers?: Record<string, string>;
	body?: unknown;
	timeout_sec?: number;
	max_retries?: number;
	retry_backoff_sec?: number;
}

/**
 * Job response
 */
export interface JobResponse {
	id: string;
	status: string;
	url?: string;
	method?: string;
	result?: unknown;
	error_message?: string;
}

/**
 * Job list filter
 */
export interface JobListFilter {
	status?: string;
	limit?: number;
	offset?: number;
}

/**
 * Job master response
 */
export interface JobMasterResponse {
	id: string;
	name: string;
	description?: string;
	tasks?: TaskMasterResponse[];
}

/**
 * Task master response
 */
export interface TaskMasterResponse {
	id: string;
	name: string;
	description?: string;
	order?: number;
}

/**
 * JobQueue API client
 */
export class JobQueueClient extends ApiClient {
	constructor(config: JobQueueClientConfig) {
		super({
			baseUrl: config.baseUrl,
			serviceName: 'myAgentDesk',
			apiToken: config.apiToken,
			authType: 'api-token'
		});
	}

	/**
	 * Create a new job
	 */
	async createJob(request: CreateJobRequest): Promise<Result<JobResponse, ApiError>> {
		return this.post<JobResponse>('/api/v1/jobs', request);
	}

	/**
	 * Get list of jobs
	 */
	async getJobs(filter?: JobListFilter): Promise<Result<JobResponse[], ApiError>> {
		const params: Record<string, string> = {};
		if (filter?.status) params.status = filter.status;
		if (filter?.limit) params.limit = String(filter.limit);
		if (filter?.offset) params.offset = String(filter.offset);

		return this.get<JobResponse[]>('/api/v1/jobs', Object.keys(params).length ? params : undefined);
	}

	/**
	 * Get job by ID
	 */
	async getJob(jobId: string): Promise<Result<JobResponse, ApiError>> {
		return this.get<JobResponse>(`/api/v1/jobs/${jobId}`);
	}

	/**
	 * Update job status
	 */
	async updateJob(
		jobId: string,
		update: Partial<JobResponse>
	): Promise<Result<JobResponse, ApiError>> {
		return this.patch<JobResponse>(`/api/v1/jobs/${jobId}`, update);
	}

	/**
	 * Delete a job
	 */
	async deleteJob(jobId: string): Promise<Result<void, ApiError>> {
		return this.delete(`/api/v1/jobs/${jobId}`);
	}

	/**
	 * Get job masters
	 */
	async getJobMasters(): Promise<Result<JobMasterResponse[], ApiError>> {
		return this.get<JobMasterResponse[]>('/api/v1/job-masters');
	}

	/**
	 * Create job master
	 */
	async createJobMaster(
		request: Omit<JobMasterResponse, 'id'>
	): Promise<Result<JobMasterResponse, ApiError>> {
		return this.post<JobMasterResponse>('/api/v1/job-masters', request);
	}
}
