/**
 * Workflow Summary Type Definitions
 * Issue #305: Task Workflow Traces Summary Feature
 *
 * Type definitions for workflow generation summary display.
 */

/**
 * Test execution summary for workflow validation
 */
export interface TestExecutionSummary {
	http_status: number | null;
	is_valid: boolean;
	validation_errors: string[];
	execution_time_ms: number | null;
}

/**
 * LLM evaluation summary with 5 component scores
 */
export interface EvaluationSummary {
	score: number | null;
	structural_score: number | null;
	requirement_score: number | null;
	output_quality_score: number | null;
	error_handling_score: number | null;
	test_data_quality_score: number | null;
	strengths: string[];
	weaknesses: string[];
	suggestions: string[];
	confidence: number | null;
}

/**
 * Retry information for workflow generation
 */
export interface RetryInfo {
	retry_count: number;
	max_retry: number;
	generation_model: string | null;
}

/**
 * Retry history entry for tracking generation attempts
 */
export interface RetryHistoryEntry {
	attempt: number;
	error_message: string;
	model_used: string | null;
	timestamp: string;
}

/**
 * Cause analysis for failure diagnosis
 */
export interface CauseAnalysis {
	category: string;
	problem_location: string | null;
	problem_field: string | null;
	actual_value: string | null;
	expected_value: string | null;
}

/**
 * Error summary for failure details
 */
export interface ErrorSummary {
	http_status: number | null;
	error_code: string | null;
	error_message: string;
	error_detail: string | null;
}

/**
 * Failure stage types
 */
export type FailureStage =
	| 'yaml_generation'
	| 'schema_validation'
	| 'workflow_registration'
	| 'workflow_execution'
	| 'node_error'
	| 'output_validation'
	| 'quality_evaluation';

/**
 * Detailed failure information for error diagnosis
 */
export interface FailureDetails {
	failure_stage: FailureStage;
	error_summary: ErrorSummary;
	cause_analysis: CauseAnalysis | null;
	recommendations: string[];
	retry_history: RetryHistoryEntry[];
}

/**
 * Complete workflow generation summary
 */
export interface WorkflowGenerationSummary {
	yaml_preview: string | null;
	yaml_content: string | null; // Full YAML for expansion
	sample_input: Record<string, unknown> | null;
	test_result: TestExecutionSummary | null;
	evaluation: EvaluationSummary | null;
	retry_info: RetryInfo | null;
	failure_details: FailureDetails | null;
}

/**
 * Extended workflow status item with summary
 */
export interface WorkflowStatusItemExtended {
	task_id: string;
	task_name: string | null;
	status: 'pending' | 'generating' | 'success' | 'failed';
	workflow_name: string | null;
	generation_time_ms: number | null;
	error_message: string | null;
	langfuse_trace_id: string | null;
	summary: WorkflowGenerationSummary | null;
}

/**
 * Score range configuration for color coding
 */
export const SCORE_RANGES = {
	excellent: { min: 90, max: 100, color: 'green', label: 'Excellent' },
	good: { min: 70, max: 89, color: 'blue', label: 'Good' },
	fair: { min: 50, max: 69, color: 'yellow', label: 'Fair' },
	poor: { min: 0, max: 49, color: 'red', label: 'Poor' }
} as const;

/**
 * Get score range for a given score
 */
export function getScoreRange(
	score: number | null
): (typeof SCORE_RANGES)[keyof typeof SCORE_RANGES] | null {
	if (score === null) return null;
	if (score >= 90) return SCORE_RANGES.excellent;
	if (score >= 70) return SCORE_RANGES.good;
	if (score >= 50) return SCORE_RANGES.fair;
	return SCORE_RANGES.poor;
}

/**
 * Failure stage display configuration
 */
export const FAILURE_STAGE_CONFIG: Record<
	FailureStage,
	{ label: string; description: string; color: string }
> = {
	yaml_generation: {
		label: 'YAML Generation',
		description: 'Failed to generate valid YAML',
		color: 'red'
	},
	schema_validation: {
		label: 'Schema Validation',
		description: 'Input validation failed',
		color: 'orange'
	},
	workflow_registration: {
		label: 'Workflow Registration',
		description: 'Failed to register with GraphAI',
		color: 'orange'
	},
	workflow_execution: {
		label: 'Workflow Execution',
		description: 'API execution failed',
		color: 'red'
	},
	node_error: {
		label: 'Node Error',
		description: 'Individual node failed',
		color: 'red'
	},
	output_validation: {
		label: 'Output Validation',
		description: 'Output schema mismatch',
		color: 'orange'
	},
	quality_evaluation: {
		label: 'Quality Evaluation',
		description: 'Quality threshold not met',
		color: 'yellow'
	}
};
