/**
 * サービス層の型定義
 */

import type { JobResult, RequirementState } from '$lib/domain/types';

export interface Message {
	role: 'user' | 'assistant';
	content: string;
}

// Chat API Request/Response Types
export interface ChatRequest {
	conversation_id: string;
	user_message: string;
	context: {
		previous_messages: Message[];
		current_requirements: RequirementState;
	};
}

export interface ChatMessageEvent {
	type: 'message';
	data: {
		content: string;
	};
}

export interface RequirementUpdateEvent {
	type: 'requirement_update';
	data: {
		requirements: RequirementState;
	};
}

export type ChatStreamEvent = ChatMessageEvent | RequirementUpdateEvent;

// Job Creation API Request/Response Types
export interface JobCreationRequest {
	conversation_id: string;
	requirements: RequirementState;
}

export interface JobCreationResponse extends JobResult {}

// Service Error Types
export class ServiceError extends Error {
	constructor(
		message: string,
		public readonly statusCode?: number,
		public readonly originalError?: unknown
	) {
		super(message);
		this.name = 'ServiceError';
	}
}
