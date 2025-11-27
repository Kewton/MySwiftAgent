/**
 * MLOps Types - TypeScript type definitions for MLOps UI components
 *
 * Includes types for:
 * - Candidates and selection
 * - Feedback and scoring
 * - Dashboard metrics
 * - Diagnostics
 * - Prompt management
 */

// ============================================================================
// Candidate Types (Issue #173)
// ============================================================================

/**
 * Represents a single candidate interpretation
 */
export interface Candidate {
	id: string;
	label: string;
	description: string;
	requirements: RequirementState;
	confidence: number;
}

/**
 * Response from candidate selection API
 */
export interface CandidateSelectionResponse {
	conversation_id: string;
	selected_candidate_id: string;
	requirements: RequirementState;
	message: string;
}

// ============================================================================
// Feedback Types (Issue #172)
// ============================================================================

/**
 * Feedback scores for a conversation
 */
export interface FeedbackScores {
	requirement_clarity?: number; // 1-5 scale
	interpretation_accuracy?: number; // 1-5 scale
	response_helpfulness?: number; // 1-5 scale
	overall_satisfaction?: number; // 1-5 scale
	comment?: string;
}

/**
 * Request body for feedback submission
 */
export interface FeedbackRequest {
	conversation_id: string;
	requirement_clarity?: number;
	interpretation_accuracy?: number;
	response_helpfulness?: number;
	overall_satisfaction?: number;
	comment?: string;
}

/**
 * Response from feedback submission API
 */
export interface FeedbackResponse {
	success: boolean;
	message: string;
	feedback_id: string | null;
	scores_submitted: number;
}

// ============================================================================
// Requirement Types
// ============================================================================

/**
 * Current state of requirements during clarification
 */
export interface RequirementState {
	data_source: string | null;
	process_description: string | null;
	output_format: string | null;
	schedule: string | null;
	completeness: number; // 0.0 to 1.0
}

/**
 * Creates an empty requirement state
 */
export function createEmptyRequirementState(): RequirementState {
	return {
		data_source: null,
		process_description: null,
		output_format: null,
		schedule: null,
		completeness: 0
	};
}

// ============================================================================
// Dashboard/Metrics Types (Issue #175, #176)
// ============================================================================

/**
 * Aggregated quality metrics
 */
export interface QualityMetrics {
	average_score: number;
	total_turns: number;
	success_rate: number;
	average_latency: number;
	total_sessions: number;
	completion_rate: number;
}

/**
 * Model usage statistics
 */
export interface ModelUsage {
	model: string;
	count: number;
	percentage: number;
}

/**
 * Response from metrics API
 */
export interface MetricsResponse {
	metrics: QualityMetrics;
	model_usage: ModelUsage[];
	period: {
		from_date: string;
		to_date: string;
	};
	cache_hit: boolean;
}

/**
 * SSE event for real-time dashboard updates
 */
export interface DashboardSSEEvent {
	event_type: 'connected' | 'metrics_update' | 'heartbeat' | 'error';
	timestamp: string;
	data: {
		client_id?: string;
		metrics?: QualityMetrics;
		model_usage?: ModelUsage[];
		is_full_snapshot?: boolean;
		error?: string;
	};
}

// ============================================================================
// Diagnostics Types (Issue #171)
// ============================================================================

/**
 * Message in a conversation
 */
export interface DiagnosticMessage {
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
}

/**
 * Full diagnostic information for a conversation
 */
export interface DiagnosticInfo {
	conversation_id: string;
	user_id: string;
	project_id: string;
	job_id: string | null;
	workflow_id: string | null;
	start_time: string;
	end_time: string | null;
	turn_count: number;
	messages: DiagnosticMessage[];
	langfuse_trace_url: string | null;
	metadata: Record<string, unknown>;
}

/**
 * Summary item for diagnostics list
 */
export interface DiagnosticSummary {
	conversation_id: string;
	user_id: string;
	start_time: string;
	turn_count: number;
}

/**
 * Response from diagnostics list API
 */
export interface DiagnosticsListResponse {
	items: DiagnosticSummary[];
	total: number;
	limit: number;
	offset: number;
}

/**
 * Query parameters for diagnostics list
 */
export interface DiagnosticsQuery {
	job_id?: string;
	user_id?: string;
	project_id?: string;
	workflow_id?: string;
	start_date?: string;
	end_date?: string;
	limit?: number;
	offset?: number;
}

// ============================================================================
// Prompt Management Types
// ============================================================================

/**
 * A single prompt version
 */
export interface PromptVersion {
	id: string;
	version: number;
	content: string;
	description: string;
	created_at: string;
	created_by: string;
	is_active: boolean;
	metadata: Record<string, unknown>;
}

/**
 * Prompt template with versions
 */
export interface PromptTemplate {
	id: string;
	name: string;
	description: string;
	category: string;
	current_version: number;
	versions: PromptVersion[];
	created_at: string;
	updated_at: string;
}

/**
 * Request to create a new prompt version
 */
export interface CreatePromptVersionRequest {
	prompt_id: string;
	content: string;
	description: string;
}

// ============================================================================
// AB Testing Types (Issue #178)
// ============================================================================

/**
 * AB Test variant configuration
 */
export interface ABTestVariant {
	name: string;
	weight: number;
}

/**
 * AB Test status
 */
export type ABTestStatus = 'draft' | 'running' | 'paused' | 'completed';

/**
 * AB Test configuration
 */
export interface ABTest {
	id: string;
	name: string;
	description: string;
	status: ABTestStatus;
	variants: ABTestVariant[];
	created_at: string;
	updated_at: string;
}

/**
 * AB Test assignment response
 */
export interface ABTestAssignment {
	test_id: string;
	session_id: string;
	variant_name: string;
	is_new: boolean;
	assigned_at: string;
}

/**
 * AB Test variant metrics
 */
export interface VariantMetrics {
	sample_size: number;
	mean: number;
	std: number;
	confidence_interval: [number, number];
}

/**
 * AB Test statistical report
 */
export interface ABTestReport {
	test_id: string;
	test_name: string;
	metric_name: string;
	metrics: Record<string, VariantMetrics>;
	t_test_result: {
		t_statistic: number;
		p_value: number;
		is_significant: boolean;
	};
	effect_size: {
		cohens_d: number;
		interpretation: 'negligible' | 'small' | 'medium' | 'large';
	};
	winner: string | null;
	recommendation: string;
}

// ============================================================================
// SSE/Chat Types
// ============================================================================

/**
 * SSE event types for requirement definition chat
 */
export type ChatSSEEventType =
	| 'message'
	| 'requirement_update'
	| 'candidate_selection'
	| 'requirements_ready'
	| 'done'
	| 'error';

/**
 * SSE event data
 */
export interface ChatSSEEvent {
	type: ChatSSEEventType;
	data?: {
		content?: string;
		requirements?: Partial<RequirementState>;
		candidates?: Candidate[];
		message?: string;
	};
}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * Loading state for async operations
 */
export interface LoadingState {
	isLoading: boolean;
	error: string | null;
}

/**
 * Toast notification type
 */
export interface ToastNotification {
	id: string;
	type: 'success' | 'error' | 'warning' | 'info';
	message: string;
	duration?: number;
}
