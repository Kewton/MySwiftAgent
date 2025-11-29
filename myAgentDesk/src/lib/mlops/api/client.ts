/**
 * MLOps API Client - Unified API client for MLOps operations
 *
 * Provides methods for:
 * - Candidate selection
 * - Feedback submission
 * - Dashboard metrics
 * - Diagnostics
 * - Prompt management
 */

import { getApiBase } from '$lib/services/config';
import type {
	CandidateSelectionResponse,
	FeedbackRequest,
	FeedbackResponse,
	MetricsResponse,
	DiagnosticInfo,
	DiagnosticsListResponse,
	DiagnosticsQuery,
	DashboardSSEEvent,
	PromptTemplate,
	CreatePromptVersionRequest,
	ABTest,
	ABTestAssignment,
	ABTestReport
} from '../types';

// ============================================================================
// HTTP Helper
// ============================================================================

/**
 * Base HTTP client with error handling
 */
async function fetchWithError<T>(url: string, options?: RequestInit): Promise<T> {
	const response = await fetch(url, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options?.headers
		}
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	return response.json();
}

// ============================================================================
// Candidate Selection API (Issue #173)
// ============================================================================

/**
 * Select a candidate interpretation
 */
export async function selectCandidate(
	conversationId: string,
	candidateId: string
): Promise<CandidateSelectionResponse> {
	const baseUrl = getApiBase();
	return fetchWithError<CandidateSelectionResponse>(`${baseUrl}/chat/select-candidate`, {
		method: 'POST',
		body: JSON.stringify({
			conversation_id: conversationId,
			selected_candidate_id: candidateId
		})
	});
}

// ============================================================================
// Feedback API (Issue #172)
// ============================================================================

/**
 * Submit feedback scores for a conversation
 */
export async function submitFeedback(feedback: FeedbackRequest): Promise<FeedbackResponse> {
	const baseUrl = getApiBase();
	return fetchWithError<FeedbackResponse>(`${baseUrl}/chat/feedback`, {
		method: 'POST',
		body: JSON.stringify(feedback)
	});
}

// ============================================================================
// Dashboard/Metrics API (Issue #175, #176)
// ============================================================================

/**
 * Get aggregated quality metrics
 */
export async function getMetrics(fromDate?: string, toDate?: string): Promise<MetricsResponse> {
	const baseUrl = getApiBase();
	const params = new URLSearchParams();
	if (fromDate) params.set('from_date', fromDate);
	if (toDate) params.set('to_date', toDate);

	const queryString = params.toString();
	const url = `${baseUrl}/observability/requirement-definition-metrics${queryString ? `?${queryString}` : ''}`;

	return fetchWithError<MetricsResponse>(url);
}

/**
 * Subscribe to real-time dashboard metrics via SSE
 */
export function subscribeToDashboard(
	onEvent: (event: DashboardSSEEvent) => void,
	onError?: (error: Error) => void
): () => void {
	const baseUrl = getApiBase();
	const eventSource = new EventSource(`${baseUrl}/observability/dashboard/stream`);

	eventSource.onmessage = (event) => {
		try {
			const data = JSON.parse(event.data) as DashboardSSEEvent;
			onEvent(data);
		} catch (error) {
			onError?.(new Error('Failed to parse SSE event'));
		}
	};

	eventSource.onerror = () => {
		onError?.(new Error('SSE connection error'));
	};

	// Return cleanup function
	return () => {
		eventSource.close();
	};
}

// ============================================================================
// Diagnostics API (Issue #171)
// ============================================================================

/**
 * Get diagnostic info for a single conversation
 */
export async function getDiagnosticInfo(conversationId: string): Promise<DiagnosticInfo> {
	const baseUrl = getApiBase();
	return fetchWithError<DiagnosticInfo>(`${baseUrl}/chat/diagnostics/${conversationId}`);
}

/**
 * List diagnostics with optional filtering
 */
export async function listDiagnostics(query?: DiagnosticsQuery): Promise<DiagnosticsListResponse> {
	const baseUrl = getApiBase();
	const params = new URLSearchParams();

	if (query) {
		if (query.job_id) params.set('job_id', query.job_id);
		if (query.user_id) params.set('user_id', query.user_id);
		if (query.project_id) params.set('project_id', query.project_id);
		if (query.workflow_id) params.set('workflow_id', query.workflow_id);
		if (query.start_date) params.set('start_date', query.start_date);
		if (query.end_date) params.set('end_date', query.end_date);
		if (query.limit) params.set('limit', query.limit.toString());
		if (query.offset) params.set('offset', query.offset.toString());
	}

	const queryString = params.toString();
	const url = `${baseUrl}/chat/diagnostics${queryString ? `?${queryString}` : ''}`;

	return fetchWithError<DiagnosticsListResponse>(url);
}

// ============================================================================
// Prompt Management API
// ============================================================================

/**
 * List all prompt templates
 */
export async function listPrompts(): Promise<PromptTemplate[]> {
	const baseUrl = getApiBase();
	return fetchWithError<PromptTemplate[]>(`${baseUrl}/prompts`);
}

/**
 * Get a single prompt template
 */
export async function getPrompt(promptId: string): Promise<PromptTemplate> {
	const baseUrl = getApiBase();
	return fetchWithError<PromptTemplate>(`${baseUrl}/prompts/${promptId}`);
}

/**
 * Create a new prompt version
 */
export async function createPromptVersion(
	request: CreatePromptVersionRequest
): Promise<PromptTemplate> {
	const baseUrl = getApiBase();
	return fetchWithError<PromptTemplate>(`${baseUrl}/prompts/${request.prompt_id}/versions`, {
		method: 'POST',
		body: JSON.stringify({
			content: request.content,
			description: request.description
		})
	});
}

/**
 * Activate a specific prompt version
 */
export async function activatePromptVersion(
	promptId: string,
	versionId: string
): Promise<PromptTemplate> {
	const baseUrl = getApiBase();
	return fetchWithError<PromptTemplate>(
		`${baseUrl}/prompts/${promptId}/versions/${versionId}/activate`,
		{
			method: 'POST'
		}
	);
}

// ============================================================================
// AB Testing API (Issue #178)
// ============================================================================

/**
 * List all AB tests
 */
export async function listABTests(status?: string): Promise<{ items: ABTest[]; total: number }> {
	const baseUrl = getApiBase();
	const params = new URLSearchParams();
	if (status) params.set('status', status);

	const queryString = params.toString();
	const url = `${baseUrl}/ab-tests${queryString ? `?${queryString}` : ''}`;

	return fetchWithError<{ items: ABTest[]; total: number }>(url);
}

/**
 * Get a single AB test
 */
export async function getABTest(testId: string): Promise<ABTest> {
	const baseUrl = getApiBase();
	return fetchWithError<ABTest>(`${baseUrl}/ab-tests/${testId}`);
}

/**
 * Assign a variant to a session
 */
export async function assignVariant(testId: string, sessionId: string): Promise<ABTestAssignment> {
	const baseUrl = getApiBase();
	return fetchWithError<ABTestAssignment>(`${baseUrl}/ab-tests/${testId}/assignment`, {
		method: 'POST',
		body: JSON.stringify({ session_id: sessionId })
	});
}

/**
 * Generate an AB test report
 */
export async function generateABTestReport(
	testId: string,
	metricName?: string,
	confidenceLevel?: number
): Promise<ABTestReport> {
	const baseUrl = getApiBase();
	return fetchWithError<ABTestReport>(`${baseUrl}/ab-tests/${testId}/report`, {
		method: 'POST',
		body: JSON.stringify({
			metric_name: metricName || 'quality_score',
			confidence_level: confidenceLevel || 0.95
		})
	});
}

// ============================================================================
// Export all functions as a unified API client
// ============================================================================

export const mlopsApi = {
	// Candidate selection
	selectCandidate,

	// Feedback
	submitFeedback,

	// Dashboard/Metrics
	getMetrics,
	subscribeToDashboard,

	// Diagnostics
	getDiagnosticInfo,
	listDiagnostics,

	// Prompts
	listPrompts,
	getPrompt,
	createPromptVersion,
	activatePromptVersion,

	// AB Testing
	listABTests,
	getABTest,
	assignVariant,
	generateABTestReport
};

export default mlopsApi;
