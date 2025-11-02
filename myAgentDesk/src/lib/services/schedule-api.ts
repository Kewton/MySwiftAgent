/**
 * Schedule API Service - myScheduler連携
 */

import { fetchJson } from './http';
import { ServiceError } from './types';

const MYSCHEDULER_API_BASE = import.meta.env.VITE_MYSCHEDULER_API_BASE || 'http://localhost:8102';

export interface ScheduleRequest {
	job_id: string;
	cron_expression: string;
	timezone: string;
}

export interface ScheduleResponse {
	schedule_id: string;
	job_id: string;
	cron_expression: string;
	timezone: string;
	next_execution: string;
	status: 'active' | 'paused' | 'disabled';
	created_at: string;
}

export interface ScheduleHistoryItem {
	execution_id: string;
	schedule_id: string;
	executed_at: string;
	status: 'success' | 'failed';
	error_message: string | null;
}

/**
 * スケジュールを作成
 *
 * @param request - スケジュール作成リクエスト
 * @returns スケジュール作成レスポンス
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function createSchedule(request: ScheduleRequest): Promise<ScheduleResponse> {
	try {
		return await fetchJson<ScheduleResponse>({
			path: '/schedule/create',
			method: 'POST',
			body: request,
			baseUrl: MYSCHEDULER_API_BASE
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			const detail = (error.originalError as { detail?: string })?.detail || error.message;
			throw new ServiceError(`Schedule creation failed: ${detail}`, error.statusCode, error);
		}
		throw new ServiceError('Schedule creation failed', undefined, error);
	}
}

/**
 * スケジュール履歴を取得
 *
 * @param jobId - ジョブID
 * @returns スケジュール履歴
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getScheduleHistory(jobId: string): Promise<ScheduleHistoryItem[]> {
	try {
		return await fetchJson<ScheduleHistoryItem[]>({
			path: `/schedule/history/${jobId}`,
			method: 'GET',
			baseUrl: MYSCHEDULER_API_BASE
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(
				`Failed to get schedule history: ${error.message}`,
				error.statusCode,
				error
			);
		}
		throw new ServiceError('Failed to get schedule history', undefined, error);
	}
}

/**
 * スケジュールを削除
 *
 * @param scheduleId - スケジュールID
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function deleteSchedule(scheduleId: string): Promise<void> {
	try {
		await fetchJson<void>({
			path: `/schedule/${scheduleId}`,
			method: 'DELETE',
			baseUrl: MYSCHEDULER_API_BASE
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(
				`Failed to delete schedule: ${error.message}`,
				error.statusCode,
				error
			);
		}
		throw new ServiceError('Failed to delete schedule', undefined, error);
	}
}

/**
 * スケジュールを一時停止/再開
 *
 * @param scheduleId - スケジュールID
 * @param status - 変更後のステータス
 * @returns 更新後のスケジュール情報
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function toggleSchedule(
	scheduleId: string,
	status: 'paused' | 'active'
): Promise<ScheduleResponse> {
	try {
		return await fetchJson<ScheduleResponse>({
			path: `/schedule/${scheduleId}/status`,
			method: 'PUT',
			body: { status },
			baseUrl: MYSCHEDULER_API_BASE
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			throw new ServiceError(
				`Failed to toggle schedule: ${error.message}`,
				error.statusCode,
				error
			);
		}
		throw new ServiceError('Failed to toggle schedule', undefined, error);
	}
}
