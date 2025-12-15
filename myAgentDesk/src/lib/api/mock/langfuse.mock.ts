/**
 * @file LangfuseClient mock implementation
 * @description Mock client for Langfuse observability API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	LangfuseClient,
	TraceFilter,
	TraceResponse,
	TracesListResponse,
	SubmitScoreRequest,
	SubmitScoreResponse
} from '../clients/langfuse';

/**
 * Mock data for traces
 */
const mockTraces: TraceResponse[] = [
	{
		id: 'trace-1',
		name: 'Job Generator Execution',
		user_id: 'user-1',
		session_id: 'session-1',
		start_time: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
		end_time: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
		observations: [
			{
				id: 'obs-1',
				type: 'generation',
				name: 'LLM Call',
				start_time: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
				end_time: new Date(Date.now() - 4.5 * 60 * 1000).toISOString()
			}
		],
		input: { user_requirement: 'Create a daily report' },
		output: { status: 'completed', job_master_id: 'jm_123' }
	},
	{
		id: 'trace-2',
		name: 'Workflow Execution',
		user_id: 'user-1',
		session_id: 'session-2',
		start_time: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
		end_time: new Date(Date.now() - 9 * 60 * 1000).toISOString(),
		observations: [],
		input: { workflow: 'summarizer' },
		output: { result: 'Summary generated' }
	}
];

/**
 * Mock Langfuse client
 */
export class LangfuseClientMock implements Partial<LangfuseClient> {
	private traces: TraceResponse[] = [...mockTraces];
	private scoreIdCounter = 100;

	async getTraces(filter: TraceFilter): Promise<Result<TracesListResponse, ApiError>> {
		await this.delay(50);
		let result = [...this.traces];

		if (filter.name) {
			result = result.filter((t) => t.name?.includes(filter.name!));
		}
		if (filter.user_id) {
			result = result.filter((t) => t.user_id === filter.user_id);
		}
		if (filter.session_id) {
			result = result.filter((t) => t.session_id === filter.session_id);
		}

		const offset = filter.offset ?? 0;
		const limit = filter.limit ?? 10;
		const total = result.length;
		result = result.slice(offset, offset + limit);

		return ok({
			traces: result,
			total,
			limit,
			offset
		});
	}

	async getTrace(traceId: string): Promise<Result<TraceResponse, ApiError>> {
		await this.delay(50);
		const trace = this.traces.find((t) => t.id === traceId);
		if (trace) {
			return ok(trace);
		}
		return ok({
			id: traceId,
			name: 'Unknown Trace',
			observations: []
		});
	}

	async submitScore(request: SubmitScoreRequest): Promise<Result<SubmitScoreResponse, ApiError>> {
		await this.delay(100);
		return ok({
			success: true,
			score_id: `score-${++this.scoreIdCounter}`
		});
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
