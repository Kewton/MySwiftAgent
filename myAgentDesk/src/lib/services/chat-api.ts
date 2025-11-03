/**
 * Chat API Service - チャットストリーミングと要求定義支援
 */

import type { ChatRequest, ChatStreamEvent, RequirementState, Message } from './types';
import { ServiceError } from './types';

const API_BASE = 'http://localhost:8104/aiagent-api/v1';

/**
 * SSE ストリーミングで要求定義チャットを実行
 *
 * @param conversationId - 会話ID
 * @param userMessage - ユーザーメッセージ
 * @param previousMessages - 過去のメッセージ履歴
 * @param currentRequirements - 現在の要求状態
 * @param onMessage - メッセージチャンク受信時のコールバック
 * @param onRequirementUpdate - 要求状態更新時のコールバック
 * @throws {ServiceError} - API呼び出し失敗時
 */
export async function streamChatRequirementDefinition(
	conversationId: string,
	userMessage: string,
	previousMessages: Message[],
	currentRequirements: RequirementState,
	onMessage: (content: string) => void,
	onRequirementUpdate: (requirements: RequirementState) => void
): Promise<void> {
	const request: ChatRequest = {
		conversation_id: conversationId,
		user_message: userMessage,
		context: {
			previous_messages: previousMessages,
			current_requirements: currentRequirements
		}
	};

	let response: Response;

	try {
		response = await fetch(`${API_BASE}/chat/requirement-definition`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(request)
		});
	} catch (error) {
		throw new ServiceError('Failed to connect to chat API', undefined, error);
	}

	if (!response.ok) {
		throw new ServiceError(`HTTP ${response.status}: ${response.statusText}`, response.status);
	}

	const reader = response.body?.getReader();
	if (!reader) {
		throw new ServiceError('Response body is not readable');
	}

	const decoder = new TextDecoder();

	try {
		// eslint-disable-next-line no-constant-condition
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			const chunk = decoder.decode(value, { stream: true });
			const lines = chunk.split('\n');

			for (const line of lines) {
				if (line.startsWith('data: ')) {
					const event: ChatStreamEvent = JSON.parse(line.substring(6));

					if (event.type === 'message') {
						onMessage(event.data.content);
					} else if (event.type === 'requirement_update') {
						onRequirementUpdate(event.data.requirements);
					}
				}
			}
		}
	} catch (error) {
		throw new ServiceError('Error processing stream data', undefined, error);
	}
}
