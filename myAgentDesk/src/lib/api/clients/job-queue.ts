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

// =============================================================================
// Issue #293: Extended Types for Run Execution
// =============================================================================

/**
 * Task status enumeration
 */
export type TaskStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'skipped';

/**
 * Job status enumeration
 */
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled';

/**
 * Request for creating a job from a master template
 */
export interface JobCreateFromMasterRequest {
	name?: string;
	headers?: Record<string, string>;
	params?: Record<string, unknown>;
	body?: Record<string, unknown>;
	timeout_sec?: number;
	priority?: number;
	scheduled_at?: string;
	max_attempts?: number;
	tags?: string[];
	validate_interfaces?: boolean;
}

/**
 * Response for job creation from master
 */
export interface JobCreateFromMasterResponse {
	job_id: string;
	status: JobStatus;
}

/**
 * Task detail from JobQueue API
 */
export interface TaskDetail {
	id: string;
	job_id: string;
	master_id: string;
	master_version: number | null;
	order: number;
	status: TaskStatus | string;
	input_data: Record<string, unknown> | null;
	output_data: Record<string, unknown> | null;
	attempt: number;
	error: string | null;
	started_at: string | null;
	finished_at: string | null;
	duration_ms: number | null;
	created_at: string;
	updated_at: string;
}

/**
 * Task list response from JobQueue API
 */
export interface TaskList {
	job_id: string;
	tasks: TaskDetail[];
	total: number;
}

/**
 * Job result response from JobQueue API
 */
export interface JobResultResponse {
	job_id: string;
	status: JobStatus | string;
	result: Record<string, unknown> | null;
	error: string | null;
	finished_at: string | null;
}

/**
 * Task retry response
 */
export interface TaskRetryResponse {
	task_id: string;
	status: string;
	message: string;
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

	// =========================================================================
	// Issue #293: Extended Methods for Run Execution
	// =========================================================================

	/**
	 * Create a job from a master template.
	 * This is used when starting a Run from a JobVersion.
	 *
	 * @param masterId - The job master ID (externalJobMasterId from JobVersion)
	 * @param request - Job creation parameters including input data in body
	 * @returns Created job response with job_id and status
	 */
	async createJobFromMaster(
		masterId: string,
		request: JobCreateFromMasterRequest
	): Promise<Result<JobCreateFromMasterResponse, ApiError>> {
		return this.post<JobCreateFromMasterResponse>(`/api/v1/jobs/from-master/${masterId}`, request);
	}

	/**
	 * Get task list for a job.
	 * Returns all tasks with their current status, input/output data.
	 *
	 * @param jobId - The job ID
	 * @returns Task list with details for each task
	 */
	async getJobTasks(jobId: string): Promise<Result<TaskList, ApiError>> {
		return this.get<TaskList>(`/api/v1/jobs/${jobId}/tasks`);
	}

	/**
	 * Get the result of a completed job.
	 *
	 * @param jobId - The job ID
	 * @returns Job result with final output data
	 */
	async getJobResult(jobId: string): Promise<Result<JobResultResponse, ApiError>> {
		return this.get<JobResultResponse>(`/api/v1/jobs/${jobId}/result`);
	}

	/**
	 * Cancel a running job.
	 *
	 * @param jobId - The job ID to cancel
	 * @returns Updated job response with canceled status
	 */
	async cancelJob(jobId: string): Promise<Result<JobCreateFromMasterResponse, ApiError>> {
		return this.post<JobCreateFromMasterResponse>(`/api/v1/jobs/${jobId}/cancel`, {});
	}

	/**
	 * Retry a failed task.
	 *
	 * @param taskId - The task ID to retry
	 * @returns Task retry response
	 */
	async retryTask(taskId: string): Promise<Result<TaskRetryResponse, ApiError>> {
		return this.post<TaskRetryResponse>(`/api/v1/tasks/${taskId}/retry`, {});
	}
}
