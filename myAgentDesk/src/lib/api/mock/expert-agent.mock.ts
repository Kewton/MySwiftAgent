/**
 * @file ExpertAgentClient mock implementation
 * @description Mock client for ExpertAgent API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	ExpertAgentClient,
	GenerateJobRequest,
	GenerateJobResponse,
	JobStatusResponse,
	HealthResponse,
	TaskBreakdownItem,
	WorkflowStatusItem
} from '../clients/expert-agent';

/**
 * Mock data for job generation
 * Issue #305: Added langfuse_trace_id
 */
const mockJobResponse: GenerateJobResponse = {
	status: 'creating',
	job_id: 'mock-job-' + Date.now(),
	job_master_id: null,
	task_breakdown: null,
	langfuse_trace_id: 'mock-langfuse-trace-' + Date.now()
};

/**
 * Mock task breakdown data
 * Issue #305: Structured task data for UI display
 */
const mockTaskBreakdown: TaskBreakdownItem[] = [
	{
		task_id: 'tm_001',
		name: 'Gmail未読メール取得',
		description: 'Gmail APIを使用して未読メールを最大10件取得する',
		recommended_apis: ['Gmail API (users.messages.list)']
	},
	{
		task_id: 'tm_002',
		name: 'Claude要約生成',
		description: '取得したメール内容をClaude APIで要約する',
		recommended_apis: ['Anthropic API (messages)']
	},
	{
		task_id: 'tm_003',
		name: 'Slack投稿',
		description: '要約結果をSlackチャンネルに投稿する',
		recommended_apis: ['Slack API (chat.postMessage)']
	}
];

/**
 * Mock workflow statuses
 * Issue #305: Workflow generation status per task
 */
const mockWorkflowStatuses: WorkflowStatusItem[] = [
	{
		task_id: 'tm_001',
		task_name: 'Gmail未読メール取得',
		status: 'success',
		workflow_name: 'workflow_gmail_fetch',
		generation_time_ms: 28500,
		error_message: null,
		langfuse_trace_id: 'trace_mock_001',
		summary: null
	},
	{
		task_id: 'tm_002',
		task_name: 'Claude要約生成',
		status: 'success',
		workflow_name: 'workflow_claude_summarize',
		generation_time_ms: 32100,
		error_message: null,
		langfuse_trace_id: 'trace_mock_002',
		summary: null
	},
	{
		task_id: 'tm_003',
		task_name: 'Slack投稿',
		status: 'success',
		workflow_name: 'workflow_slack_post',
		generation_time_ms: 25300,
		error_message: null,
		langfuse_trace_id: 'trace_mock_003',
		summary: null
	}
];

/**
 * Mock interface definitions
 * Issue #310: Interface definitions for each task
 */
const mockInterfaceDefinitions: Record<string, unknown> = {
	tm_001: {
		interface_master_id: 'im_mock_001',
		interface_name: 'GmailFetchInterface',
		input_schema: { type: 'object', properties: { max_results: { type: 'integer' } } },
		output_schema: { type: 'object', properties: { messages: { type: 'array' } } }
	},
	tm_002: {
		interface_master_id: 'im_mock_002',
		interface_name: 'ClaudeSummarizeInterface',
		input_schema: { type: 'object', properties: { text: { type: 'string' } } },
		output_schema: { type: 'object', properties: { summary: { type: 'string' } } }
	}
};

/**
 * Mock data for job status
 * Issue #305: Extended with phase, task_breakdown, workflow_statuses
 * Issue #310: Added interface_definitions
 */
const mockJobStatus: JobStatusResponse = {
	job_id: 'mock-job-id',
	status: 'completed',
	progress: 100,
	job_master_id: 'jm_mock_123',
	error_message: null,
	phase: 'complete',
	task_breakdown: mockTaskBreakdown,
	workflow_statuses: mockWorkflowStatuses,
	result: {
		status: 'success',
		job_id: 'mock-job-id',
		job_master_id: 'jm_mock_123',
		task_breakdown: mockTaskBreakdown,
		interface_definitions: mockInterfaceDefinitions,
		error_message: null,
		langfuse_trace_id: 'mock-langfuse-trace-id'
	}
};

/**
 * Mock ExpertAgent client
 */
export class ExpertAgentClientMock implements Partial<ExpertAgentClient> {
	async generateJob(_request: GenerateJobRequest): Promise<Result<GenerateJobResponse, ApiError>> {
		// Simulate API delay
		await this.delay(100);
		const timestamp = Date.now();
		return ok({
			...mockJobResponse,
			job_id: 'mock-job-' + timestamp,
			langfuse_trace_id: 'mock-langfuse-trace-' + timestamp
		});
	}

	async getJobStatus(jobId: string): Promise<Result<JobStatusResponse, ApiError>> {
		await this.delay(50);
		return ok({
			...mockJobStatus,
			job_id: jobId
		});
	}

	async health(): Promise<Result<HealthResponse, ApiError>> {
		return ok({
			status: 'healthy',
			service: 'expertAgent (mock)'
		});
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
