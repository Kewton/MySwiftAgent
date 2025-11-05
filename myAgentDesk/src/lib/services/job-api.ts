/**
 * Job API Service - ジョブ作成と管理
 */

import type { RequirementState } from '$lib/domain/types';
import type { JobCreationRequest, JobCreationResponse } from './types';
import { ServiceError } from './types';
import { fetchJson } from './http';

/**
 * ジョブ作成ステータス
 */
export interface JobStatus {
	job_id: string;
	status: 'creating' | 'completed' | 'failed';
	progress: number; // 0-100
	start_time: string;
	end_time?: string;
	job_master_id?: string;
	error_message?: string;
	result?: JobCreationResponse;
}

/**
 * ジョブを作成 (非同期)
 *
 * @param conversationId - 会話ID
 * @param requirements - 要求状態（completeness >= 0.8 が必要）
 * @returns ジョブID (即座に返却)
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function createJobAsync(
	conversationId: string,
	requirements: RequirementState
): Promise<{ job_id: string }> {
	const userRequirement = `データソース: ${requirements.data_source || '未定'}
処理内容: ${requirements.process_description || '未定'}
出力形式: ${requirements.output_format || '未定'}
スケジュール: ${requirements.schedule || '未定'}`;

	try {
		const response = await fetchJson<JobCreationResponse>({
			path: '/job-generator',
			method: 'POST',
			body: {
				user_requirement: userRequirement,
				max_retry: 5
			}
		});

		if (!response.job_id) {
			throw new ServiceError('Job ID not returned from API');
		}

		return { job_id: response.job_id };
	} catch (error) {
		if (error instanceof ServiceError) {
			throw error;
		}
		throw new ServiceError('Failed to start job creation', undefined, error);
	}
}

/**
 * ジョブ作成ステータスを取得
 *
 * @param jobId - ジョブID
 * @returns ジョブ作成ステータス
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
	try {
		return await fetchJson<JobStatus>({
			path: `/jobs/${jobId}/status`,
			method: 'GET'
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			throw error;
		}
		throw new ServiceError('Failed to get job status', undefined, error);
	}
}

/**
 * ジョブを作成 (旧同期版 - 後方互換性のため残す)
 *
 * @param conversationId - 会話ID
 * @param requirements - 要求状態（completeness >= 0.8 が必要）
 * @returns ジョブ作成結果
 * @throws {ServiceError} - API呼び出し失敗時
 * @deprecated Use createJobAsync() and getJobStatus() for async job creation
 */
export async function createJob(
	conversationId: string,
	requirements: RequirementState
): Promise<JobCreationResponse> {
	const request: JobCreationRequest = {
		conversation_id: conversationId,
		requirements
	};

	try {
		return await fetchJson<JobCreationResponse>({
			path: '/chat/create-job',
			method: 'POST',
			body: request
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			const isConnectionFailure = !error.statusCode && error.message.startsWith('Failed to fetch');
			if (isConnectionFailure) {
				throw new ServiceError('Failed to connect to job creation API', undefined, error);
			}

			if (error.statusCode && error.message === 'Failed to parse JSON response') {
				throw new ServiceError(
					'Failed to parse job creation response',
					error.statusCode,
					error.originalError
				);
			}

			if (error.statusCode) {
				const detail =
					(error.originalError as { detail?: string } | undefined)?.detail || 'Unknown error';
				throw new ServiceError(
					`Job creation failed: ${detail}`,
					error.statusCode,
					error.originalError
				);
			}

			throw error;
		}
		throw new ServiceError('Job creation failed', undefined, error);
	}
}
