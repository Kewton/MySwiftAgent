/**
 * @file MySchedulerClient implementation
 * @description Client for MyScheduler API (cron/interval/date scheduling)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';

/**
 * MyScheduler client configuration
 */
export interface MySchedulerClientConfig {
	baseUrl: string;
	apiToken: string;
}

/**
 * Schedule type
 */
export type ScheduleType = 'cron' | 'interval' | 'date';

/**
 * Create schedule request
 */
export interface CreateScheduleRequest {
	job_name: string;
	schedule_type: ScheduleType;
	cron_expression?: string;
	interval_seconds?: number;
	run_date?: string;
	url: string;
	method: string;
	headers?: Record<string, string>;
	body?: unknown;
}

/**
 * Schedule response
 */
export interface ScheduleResponse {
	job_id: string;
	job_name: string;
	schedule_type: ScheduleType;
	cron_expression?: string;
	interval_seconds?: number;
	run_date?: string;
	url?: string;
	method?: string;
	status?: string;
	next_run_time?: string;
}

/**
 * MyScheduler API client
 */
export class MySchedulerClient extends ApiClient {
	constructor(config: MySchedulerClientConfig) {
		super({
			baseUrl: config.baseUrl,
			serviceName: 'myAgentDesk',
			apiToken: config.apiToken,
			authType: 'api-token'
		});
	}

	/**
	 * Create a new schedule
	 */
	async createSchedule(request: CreateScheduleRequest): Promise<Result<ScheduleResponse, ApiError>> {
		return this.post<ScheduleResponse>('/api/v1/jobs', request);
	}

	/**
	 * Get list of schedules
	 */
	async getSchedules(): Promise<Result<ScheduleResponse[], ApiError>> {
		return this.get<ScheduleResponse[]>('/api/v1/jobs');
	}

	/**
	 * Get schedule by ID
	 */
	async getSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		return this.get<ScheduleResponse>(`/api/v1/jobs/${jobId}`);
	}

	/**
	 * Update schedule
	 */
	async updateSchedule(
		jobId: string,
		update: Partial<CreateScheduleRequest>
	): Promise<Result<ScheduleResponse, ApiError>> {
		return this.put<ScheduleResponse>(`/api/v1/jobs/${jobId}`, update);
	}

	/**
	 * Delete schedule
	 */
	async deleteSchedule(jobId: string): Promise<Result<void, ApiError>> {
		return this.delete(`/api/v1/jobs/${jobId}`);
	}

	/**
	 * Pause schedule
	 */
	async pauseSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		return this.post<ScheduleResponse>(`/api/v1/jobs/${jobId}/pause`);
	}

	/**
	 * Resume schedule
	 */
	async resumeSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		return this.post<ScheduleResponse>(`/api/v1/jobs/${jobId}/resume`);
	}
}
