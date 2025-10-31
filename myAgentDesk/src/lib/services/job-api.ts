/**
 * Job API Service - ジョブ作成と管理
 */

import type { JobCreationRequest, JobCreationResponse, RequirementState } from './types';
import { ServiceError } from './types';
import { fetchJson } from './http';

/**
 * ジョブを作成
 *
 * @param conversationId - 会話ID
 * @param requirements - 要求状態（completeness >= 0.8 が必要）
 * @returns ジョブ作成結果
 * @throws {ServiceError} - API呼び出し失敗時
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
