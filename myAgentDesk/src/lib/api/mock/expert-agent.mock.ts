/**
 * @file ExpertAgentClient mock implementation
 * @description Mock client for ExpertAgent API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	ExpertAgentClient,
	GenerateJobRequest,
	GenerateJobResponse,
	JobStatusResponse,
	HealthResponse
} from '../clients/expert-agent';

/**
 * Mock data for job generation
 */
const mockJobResponse: GenerateJobResponse = {
	status: 'creating',
	job_id: 'mock-job-' + Date.now(),
	job_master_id: null,
	task_breakdown: null
};

/**
 * Mock data for job status
 */
const mockJobStatus: JobStatusResponse = {
	job_id: 'mock-job-id',
	status: 'completed',
	progress: 100,
	job_master_id: 'jm_mock_123'
};

/**
 * Mock ExpertAgent client
 */
export class ExpertAgentClientMock implements Partial<ExpertAgentClient> {
	async generateJob(_request: GenerateJobRequest): Promise<Result<GenerateJobResponse, ApiError>> {
		// Simulate API delay
		await this.delay(100);
		return ok({
			...mockJobResponse,
			job_id: 'mock-job-' + Date.now()
		});
	}

	async getJobStatus(jobId: string): Promise<Result<JobStatusResponse, ApiError>> {
		await this.delay(50);
		return ok({
			...mockJobStatus,
			job_id: jobId
		});
	}

	async health(): Promise<Result<HealthResponse, ApiError>> {
		return ok({
			status: 'healthy',
			service: 'expertAgent (mock)'
		});
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
