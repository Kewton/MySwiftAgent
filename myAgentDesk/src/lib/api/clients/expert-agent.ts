/**
 * @file ExpertAgentClient implementation
 * @description Client for ExpertAgent API (job generation, workflows, LLM)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';
import type { WorkflowGenerationSummary } from '$lib/types/workflow-summary';

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
 * Task breakdown item from job generation
 * Issue #305: Structured task data for UI display
 */
export interface TaskBreakdownItem {
	task_id: string;
	name: string;
	description: string;
	recommended_apis: string[];
}

/**
 * Workflow status item for each task
 * Issue #305: Tracks workflow generation status per task
 * Issue #305: Added langfuse_trace_id for per-task trace links
 * Issue #305: Added task_name for human-readable display
 */
export interface WorkflowStatusItem {
	task_id: string;
	task_name: string | null;
	status: 'pending' | 'generating' | 'success' | 'failed';
	workflow_name: string | null;
	generation_time_ms: number | null;
	error_message: string | null;
	langfuse_trace_id: string | null;
	/** Issue #305 Extension: Detailed workflow generation summary */
	summary: WorkflowGenerationSummary | null;
}

/**
 * Job generation result (nested in status response)
 * Issue #310: Added interface_definitions field
 */
export interface JobGenerationResult {
	status: string;
	job_id: string | null;
	job_master_id: string | null;
	task_breakdown: TaskBreakdownItem[];
	/** Issue #310: Interface definitions from job generation */
	interface_definitions: Record<string, unknown> | null;
	error_message: string | null;
	langfuse_trace_id: string | null;
	/** Issue #396: Workflow generation statuses */
	workflow_statuses: WorkflowStatusItem[] | null;
}

/**
 * Job generation phase
 * Issue #305: Two-phase progress tracking
 */
export type JobPhase = 'task_analysis' | 'workflow_generation' | 'complete';

/**
 * Job status response
 * Issue #305: Extended with phase, task_breakdown, and workflow_statuses
 */
export interface JobStatusResponse {
	job_id: string;
	status: string;
	progress: number;
	job_master_id: string | null;
	error_message: string | null;
	result: JobGenerationResult | null;
	/** Current generation phase */
	phase: JobPhase | null;
	/** Task breakdown from phase 1 */
	task_breakdown: TaskBreakdownItem[] | null;
	/** Workflow generation status per task */
	workflow_statuses: WorkflowStatusItem[] | null;
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
