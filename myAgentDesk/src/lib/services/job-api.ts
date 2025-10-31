/**
 * Job API Service - ジョブ作成と管理
 */

import type { JobCreationRequest, JobCreationResponse, RequirementState } from './types';
import { ServiceError } from './types';

const API_BASE = 'http://localhost:8104/aiagent-api/v1';

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

	let response: Response;

	try {
		response = await fetch(`${API_BASE}/chat/create-job`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(request)
		});
	} catch (error) {
		throw new ServiceError('Failed to connect to job creation API', undefined, error);
	}

	let result: unknown;

	try {
		result = await response.json();
	} catch (error) {
		throw new ServiceError('Failed to parse job creation response', response.status, error);
	}

	if (!response.ok) {
		const errorDetail = (result as { detail?: string }).detail || 'Unknown error';
		throw new ServiceError(`Job creation failed: ${errorDetail}`, response.status);
	}

	return result as JobCreationResponse;
}
