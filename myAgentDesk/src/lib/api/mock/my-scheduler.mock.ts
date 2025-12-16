/**
 * @file MySchedulerClient mock implementation
 * @description Mock client for MyScheduler API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	MySchedulerClient,
	CreateScheduleRequest,
	ScheduleResponse
} from '../clients/my-scheduler';

/**
 * Mock data for schedules
 */
const mockSchedules: ScheduleResponse[] = [
	{
		job_id: 'schedule-1',
		job_name: 'Daily Report',
		schedule_type: 'cron',
		cron_expression: '0 9 * * *',
		url: 'http://localhost:8101/api/v1/jobs',
		method: 'POST',
		status: 'active',
		next_run_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
	},
	{
		job_id: 'schedule-2',
		job_name: 'Health Check',
		schedule_type: 'interval',
		interval_seconds: 300,
		url: 'http://localhost:8103/health',
		method: 'GET',
		status: 'active',
		next_run_time: new Date(Date.now() + 5 * 60 * 1000).toISOString()
	}
];

/**
 * Mock MyScheduler client
 */
export class MySchedulerClientMock implements Partial<MySchedulerClient> {
	private schedules: ScheduleResponse[] = [...mockSchedules];
	private scheduleIdCounter = 100;

	async createSchedule(
		request: CreateScheduleRequest
	): Promise<Result<ScheduleResponse, ApiError>> {
		await this.delay(100);
		const newSchedule: ScheduleResponse = {
			job_id: `schedule-${++this.scheduleIdCounter}`,
			job_name: request.job_name,
			schedule_type: request.schedule_type,
			cron_expression: request.cron_expression,
			interval_seconds: request.interval_seconds,
			run_date: request.run_date,
			url: request.url,
			method: request.method,
			status: 'active',
			next_run_time: new Date(Date.now() + 60 * 60 * 1000).toISOString()
		};
		this.schedules.push(newSchedule);
		return ok(newSchedule);
	}

	async getSchedules(): Promise<Result<ScheduleResponse[], ApiError>> {
		await this.delay(50);
		return ok([...this.schedules]);
	}

	async getSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		await this.delay(50);
		const schedule = this.schedules.find((s) => s.job_id === jobId);
		if (schedule) {
			return ok(schedule);
		}
		return ok({
			job_id: jobId,
			job_name: 'Unknown',
			schedule_type: 'cron',
			status: 'not_found'
		});
	}

	async updateSchedule(
		jobId: string,
		update: Partial<CreateScheduleRequest>
	): Promise<Result<ScheduleResponse, ApiError>> {
		await this.delay(50);
		const idx = this.schedules.findIndex((s) => s.job_id === jobId);
		if (idx >= 0) {
			this.schedules[idx] = { ...this.schedules[idx], ...update };
			return ok(this.schedules[idx]);
		}
		return ok({
			job_id: jobId,
			job_name: update.job_name ?? 'Unknown',
			schedule_type: update.schedule_type ?? 'cron'
		});
	}

	async deleteSchedule(_jobId: string): Promise<Result<void, ApiError>> {
		await this.delay(50);
		return ok(undefined);
	}

	async pauseSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		await this.delay(50);
		const schedule = this.schedules.find((s) => s.job_id === jobId);
		if (schedule) {
			schedule.status = 'paused';
			return ok(schedule);
		}
		return ok({
			job_id: jobId,
			job_name: 'Unknown',
			schedule_type: 'cron',
			status: 'paused'
		});
	}

	async resumeSchedule(jobId: string): Promise<Result<ScheduleResponse, ApiError>> {
		await this.delay(50);
		const schedule = this.schedules.find((s) => s.job_id === jobId);
		if (schedule) {
			schedule.status = 'active';
			return ok(schedule);
		}
		return ok({
			job_id: jobId,
			job_name: 'Unknown',
			schedule_type: 'cron',
			status: 'active'
		});
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
