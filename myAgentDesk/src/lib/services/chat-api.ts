/**
 * Chat API Service - チャットストリーミングと要求定義支援
 */

import type { RequirementState } from '$lib/domain/types';
import type { ChatRequest, ChatStreamEvent, Message } from './types';
import { ServiceError } from './types';
import { streamSse } from './http';

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

	try {
		await streamSse<ChatStreamEvent>({
			path: '/chat/requirement-definition',
			body: request,
			onEvent: (event) => {
				if (event.type === 'message') {
					onMessage(event.data.content);
					return;
				}
				if (event.type === 'requirement_update') {
					onRequirementUpdate(event.data.requirements);
					return;
				}
				console.warn('Unhandled stream event type', event);
			}
		});
	} catch (error) {
		if (error instanceof ServiceError) {
			const isConnectionFailure =
				!error.statusCode && error.message.startsWith('Failed to connect');
			if (isConnectionFailure) {
				throw new ServiceError('Failed to connect to chat API', undefined, error);
			}
			throw error;
		}
		throw new ServiceError('Error processing stream data', undefined, error);
	}
}
