/**
 * @file LangfuseClient implementation
 * @description Client for Langfuse observability API (traces, scores)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';

/**
 * Langfuse client configuration
 */
export interface LangfuseClientConfig {
	baseUrl: string;
	adminToken?: string;
}

/**
 * Trace filter
 */
export interface TraceFilter {
	limit?: number;
	offset?: number;
	name?: string;
	user_id?: string;
	session_id?: string;
}

/**
 * Trace observation
 */
export interface TraceObservation {
	id: string;
	type: string;
	name?: string;
	start_time?: string;
	end_time?: string;
	input?: unknown;
	output?: unknown;
}

/**
 * Trace response
 */
export interface TraceResponse {
	id: string;
	name?: string;
	user_id?: string;
	session_id?: string;
	start_time?: string;
	end_time?: string;
	observations?: TraceObservation[];
	input?: unknown;
	output?: unknown;
}

/**
 * Traces list response
 */
export interface TracesListResponse {
	traces: TraceResponse[];
	total: number;
	limit: number;
	offset: number;
}

/**
 * Submit score request
 */
export interface SubmitScoreRequest {
	trace_id: string;
	name: string;
	value: number;
	comment?: string;
}

/**
 * Submit score response
 */
export interface SubmitScoreResponse {
	success: boolean;
	score_id: string;
}

/**
 * Langfuse API client for observability
 */
export class LangfuseClient extends ApiClient {
	constructor(config: LangfuseClientConfig) {
		super({
			baseUrl: config.baseUrl,
			serviceName: 'myAgentDesk',
			adminToken: config.adminToken,
			authType: config.adminToken ? 'admin-token' : 'none'
		});
	}

	/**
	 * Get traces with optional filters
	 */
	async getTraces(filter: TraceFilter): Promise<Result<TracesListResponse, ApiError>> {
		const params: Record<string, string> = {};
		if (filter.limit) params.limit = String(filter.limit);
		if (filter.offset) params.offset = String(filter.offset);
		if (filter.name) params.name = filter.name;
		if (filter.user_id) params.user_id = filter.user_id;
		if (filter.session_id) params.session_id = filter.session_id;

		return this.get<TracesListResponse>(
			'/v1/langfuse/traces',
			Object.keys(params).length ? params : undefined
		);
	}

	/**
	 * Get a single trace by ID
	 */
	async getTrace(traceId: string): Promise<Result<TraceResponse, ApiError>> {
		return this.get<TraceResponse>(`/v1/langfuse/traces/${traceId}`);
	}

	/**
	 * Submit a feedback score for a trace
	 */
	async submitScore(request: SubmitScoreRequest): Promise<Result<SubmitScoreResponse, ApiError>> {
		return this.post<SubmitScoreResponse>('/v1/langfuse/scores', request);
	}
}
