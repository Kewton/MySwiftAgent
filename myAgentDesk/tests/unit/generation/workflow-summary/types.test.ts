/**
 * Workflow Summary Type Tests
 * Issue #305: Task Workflow Traces Summary Feature
 *
 * Tests for TypeScript type definitions to ensure proper type structure.
 */
import { describe, it, expect } from 'vitest';
import type {
	TestExecutionSummary,
	EvaluationSummary,
	RetryInfo,
	FailureDetails,
	WorkflowGenerationSummary,
	WorkflowStatusItemExtended
} from '$lib/types/workflow-summary';

describe('Workflow Summary Type Definitions', () => {
	describe('TestExecutionSummary', () => {
		it('should have correct structure for success case', () => {
			const summary: TestExecutionSummary = {
				http_status: 200,
				is_valid: true,
				validation_errors: [],
				execution_time_ms: 1500
			};

			expect(summary.http_status).toBe(200);
			expect(summary.is_valid).toBe(true);
			expect(summary.validation_errors).toEqual([]);
			expect(summary.execution_time_ms).toBe(1500);
		});

		it('should allow null values where appropriate', () => {
			const summary: TestExecutionSummary = {
				http_status: null,
				is_valid: false,
				validation_errors: ['Error 1', 'Error 2'],
				execution_time_ms: null
			};

			expect(summary.http_status).toBeNull();
			expect(summary.execution_time_ms).toBeNull();
		});
	});

	describe('EvaluationSummary', () => {
		it('should have correct structure with all scores', () => {
			const evaluation: EvaluationSummary = {
				score: 85,
				structural_score: 90,
				requirement_score: 85,
				output_quality_score: 80,
				error_handling_score: 75,
				test_data_quality_score: 88,
				strengths: ['Good API usage', 'Proper error handling'],
				weaknesses: ['Missing timeout config'],
				suggestions: ['Add retry logic'],
				confidence: 0.92
			};

			expect(evaluation.score).toBe(85);
			expect(evaluation.structural_score).toBe(90);
			expect(evaluation.strengths).toHaveLength(2);
			expect(evaluation.weaknesses).toHaveLength(1);
			expect(evaluation.suggestions).toHaveLength(1);
			expect(evaluation.confidence).toBe(0.92);
		});

		it('should allow null scores', () => {
			const evaluation: EvaluationSummary = {
				score: null,
				structural_score: null,
				requirement_score: null,
				output_quality_score: null,
				error_handling_score: null,
				test_data_quality_score: null,
				strengths: [],
				weaknesses: [],
				suggestions: [],
				confidence: null
			};

			expect(evaluation.score).toBeNull();
			expect(evaluation.confidence).toBeNull();
		});
	});

	describe('RetryInfo', () => {
		it('should have correct retry information', () => {
			const retryInfo: RetryInfo = {
				retry_count: 2,
				max_retry: 3,
				generation_model: 'gpt-4o-mini'
			};

			expect(retryInfo.retry_count).toBe(2);
			expect(retryInfo.max_retry).toBe(3);
			expect(retryInfo.generation_model).toBe('gpt-4o-mini');
		});

		it('should allow null generation_model', () => {
			const retryInfo: RetryInfo = {
				retry_count: 0,
				max_retry: 3,
				generation_model: null
			};

			expect(retryInfo.generation_model).toBeNull();
		});
	});

	describe('FailureDetails', () => {
		it('should have correct structure for workflow execution failure', () => {
			const failure: FailureDetails = {
				failure_stage: 'workflow_execution',
				error_summary: {
					http_status: 400,
					error_code: 'INVALID_PARAMETER',
					error_message: 'Invalid voice parameter',
					error_detail: 'Expected one of: alloy, echo, fable'
				},
				cause_analysis: {
					category: 'API parameter',
					problem_location: 'node: tts_drive_upload',
					problem_field: 'body.voice',
					actual_value: 'ja-JP-Standard-A',
					expected_value: 'alloy | echo | fable | onyx | nova | shimmer'
				},
				recommendations: [
					'Update voice parameter to use OpenAI TTS format',
					'Regenerate workflow with corrected parameter'
				],
				retry_history: [
					{
						attempt: 1,
						error_message: 'Invalid voice parameter',
						model_used: 'gemini-2.5-flash',
						timestamp: '2025-12-24T10:00:00Z'
					},
					{
						attempt: 2,
						error_message: 'Invalid voice parameter',
						model_used: 'gpt-4o-mini',
						timestamp: '2025-12-24T10:01:00Z'
					}
				]
			};

			expect(failure.failure_stage).toBe('workflow_execution');
			expect(failure.error_summary.http_status).toBe(400);
			expect(failure.cause_analysis?.category).toBe('API parameter');
			expect(failure.recommendations).toHaveLength(2);
			expect(failure.retry_history).toHaveLength(2);
		});

		it('should allow null cause_analysis', () => {
			const failure: FailureDetails = {
				failure_stage: 'yaml_generation',
				error_summary: {
					http_status: null,
					error_code: null,
					error_message: 'Failed to generate valid YAML',
					error_detail: null
				},
				cause_analysis: null,
				recommendations: ['Retry with different model'],
				retry_history: []
			};

			expect(failure.cause_analysis).toBeNull();
		});
	});

	describe('WorkflowGenerationSummary', () => {
		it('should have correct structure for success case', () => {
			const summary: WorkflowGenerationSummary = {
				yaml_preview: 'version: 0.5\nnodes:\n  source: {}',
				sample_input: { title: 'Test', sections: ['s1', 's2'] },
				test_result: {
					http_status: 200,
					is_valid: true,
					validation_errors: [],
					execution_time_ms: 1200
				},
				evaluation: {
					score: 85,
					structural_score: 90,
					requirement_score: 85,
					output_quality_score: 80,
					error_handling_score: 75,
					test_data_quality_score: 88,
					strengths: ['Good structure'],
					weaknesses: [],
					suggestions: [],
					confidence: 0.9
				},
				retry_info: {
					retry_count: 1,
					max_retry: 3,
					generation_model: 'gpt-4o-mini'
				},
				failure_details: null
			};

			expect(summary.yaml_preview).toBeDefined();
			expect(summary.sample_input).toBeDefined();
			expect(summary.test_result?.is_valid).toBe(true);
			expect(summary.evaluation?.score).toBe(85);
			expect(summary.failure_details).toBeNull();
		});

		it('should have correct structure for failure case', () => {
			const summary: WorkflowGenerationSummary = {
				yaml_preview: null,
				sample_input: null,
				test_result: null,
				evaluation: null,
				retry_info: {
					retry_count: 3,
					max_retry: 3,
					generation_model: 'gpt-4o-mini'
				},
				failure_details: {
					failure_stage: 'yaml_generation',
					error_summary: {
						http_status: null,
						error_code: null,
						error_message: 'Failed to generate YAML',
						error_detail: null
					},
					cause_analysis: null,
					recommendations: [],
					retry_history: []
				}
			};

			expect(summary.yaml_preview).toBeNull();
			expect(summary.failure_details).toBeDefined();
		});
	});

	describe('WorkflowStatusItemExtended', () => {
		it('should extend base WorkflowStatusItem with summary', () => {
			const item: WorkflowStatusItemExtended = {
				task_id: 'tm_001',
				task_name: 'Generate Audio Script',
				status: 'success',
				workflow_name: 'workflow_audio_script',
				generation_time_ms: 28500,
				error_message: null,
				langfuse_trace_id: 'trace_abc123',
				summary: {
					yaml_preview: 'version: 0.5\nnodes: {}',
					sample_input: { text: 'sample' },
					test_result: {
						http_status: 200,
						is_valid: true,
						validation_errors: [],
						execution_time_ms: 1000
					},
					evaluation: {
						score: 90,
						structural_score: 95,
						requirement_score: 90,
						output_quality_score: 85,
						error_handling_score: 80,
						test_data_quality_score: 92,
						strengths: ['Excellent'],
						weaknesses: [],
						suggestions: [],
						confidence: 0.95
					},
					retry_info: {
						retry_count: 0,
						max_retry: 3,
						generation_model: 'gemini-2.5-flash'
					},
					failure_details: null
				}
			};

			expect(item.task_id).toBe('tm_001');
			expect(item.status).toBe('success');
			expect(item.summary).toBeDefined();
			expect(item.summary?.evaluation?.score).toBe(90);
		});

		it('should allow null summary', () => {
			const item: WorkflowStatusItemExtended = {
				task_id: 'tm_002',
				task_name: 'Upload to Drive',
				status: 'pending',
				workflow_name: null,
				generation_time_ms: null,
				error_message: null,
				langfuse_trace_id: null,
				summary: null
			};

			expect(item.summary).toBeNull();
		});
	});
});
