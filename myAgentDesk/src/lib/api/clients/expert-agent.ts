/**
 * @file ExpertAgentClient implementation
 * @description Client for ExpertAgent API (job generation, workflows, LLM)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';

/**
 * ExpertAgent client configuration
 */
export interface ExpertAgentClientConfig {
	baseUrl: string;
	adminToken?: string;
}

/**
 * Job generation request
 */
export interface GenerateJobRequest {
	user_requirement: string;
	max_retry?: number;
}

/**
 * Job generation response
 * Issue #305: Added langfuse_trace_id for immediate trace link availability
 */
export interface GenerateJobResponse {
	status: string;
	job_id: string;
	job_master_id: string | null;
	task_breakdown: unknown | null;
	langfuse_trace_id: string | null;
}

/**
 * Job generation result (nested in status response)
 */
export interface JobGenerationResult {
	status: string;
	job_id: string | null;
	job_master_id: string | null;
	task_breakdown: unknown[];
	error_message: string | null;
	langfuse_trace_id: string | null;
}

/**
 * Job status response
 */
export interface JobStatusResponse {
	job_id: string;
	status: string;
	progress: number;
	job_master_id: string | null;
	error_message: string | null;
	result: JobGenerationResult | null;
}

/**
 * Health check response
 */
export interface HealthResponse {
	status: string;
	service: string;
}

/**
 * ExpertAgent API client
 */
export class ExpertAgentClient extends ApiClient {
	constructor(config: ExpertAgentClientConfig) {
		super({
			baseUrl: config.baseUrl,
			serviceName: 'myAgentDesk',
			adminToken: config.adminToken,
			authType: config.adminToken ? 'admin-token' : 'none'
		});
	}

	/**
	 * Generate a job from user requirement
	 */
	async generateJob(request: GenerateJobRequest): Promise<Result<GenerateJobResponse, ApiError>> {
		return this.post<GenerateJobResponse>('/v1/job-generator', request);
	}

	/**
	 * Get job generation status
	 */
	async getJobStatus(jobId: string): Promise<Result<JobStatusResponse, ApiError>> {
		return this.get<JobStatusResponse>(`/v1/jobs/${jobId}/status`);
	}

	/**
	 * Health check
	 */
	async health(): Promise<Result<HealthResponse, ApiError>> {
		return this.get<HealthResponse>('/health');
	}
}
