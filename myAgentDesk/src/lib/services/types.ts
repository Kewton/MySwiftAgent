/**
 * サービス層の型定義
 */

export interface Message {
	role: 'user' | 'assistant';
	content: string;
}

export interface RequirementState {
	data_source: string | null;
	process_description: string | null;
	output_format: string | null;
	schedule: string | null;
	completeness: number;
}

export interface JobResult {
	job_id: string;
	job_master_id: string;
	status: string;
	message: string;
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
