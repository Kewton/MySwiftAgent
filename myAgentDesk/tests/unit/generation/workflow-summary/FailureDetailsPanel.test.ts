/**
 * FailureDetailsPanel Component Tests
 * Issue #305: Task Workflow Traces Summary Feature
 *
 * Tests for the failure details panel that shows error information.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import FailureDetailsPanel from '$lib/components/generation/FailureDetailsPanel.svelte';
import type { FailureDetails } from '$lib/types/workflow-summary';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches/wb_001/generate' },
				params: { projectId: 'proj_001', workbenchId: 'wb_001' }
			});
			return () => {};
		})
	}
}));

describe('FailureDetailsPanel', () => {
	const createWorkflowExecutionFailure = (): FailureDetails => ({
		failure_stage: 'workflow_execution',
		error_summary: {
			http_status: 400,
			error_code: 'INVALID_PARAMETER',
			error_message: 'Invalid voice parameter',
			error_detail: '"ja-JP-Standard-A" is not valid. Expected one of: alloy, echo, fable, onyx, nova, shimmer'
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
			},
			{
				attempt: 3,
				error_message: 'Invalid voice parameter',
				model_used: 'gpt-4o-mini',
				timestamp: '2025-12-24T10:02:00Z'
			}
		]
	});

	const createYamlGenerationFailure = (): FailureDetails => ({
		failure_stage: 'yaml_generation',
		error_summary: {
			http_status: null,
			error_code: 'PARSE_ERROR',
			error_message: 'Failed to parse YAML output',
			error_detail: 'Syntax error at line 15: unexpected indent'
		},
		cause_analysis: null,
		recommendations: ['Retry with different model', 'Check prompt template'],
		retry_history: []
	});

	describe('Failure Stage Badge', () => {
		it('should display workflow_execution stage', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/workflow_execution/i)).toBeDefined();
		});

		it('should display yaml_generation stage', () => {
			const failure = createYamlGenerationFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/yaml_generation/i)).toBeDefined();
		});

		it('should have appropriate styling for failure stage', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// The stage badge should be visible and styled
			const badge = screen.getByText(/workflow_execution/i);
			expect(badge).toBeDefined();
		});
	});

	describe('Error Summary Card', () => {
		it('should display HTTP status', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/400/)).toBeDefined();
		});

		it('should display error code', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/INVALID_PARAMETER/)).toBeDefined();
		});

		it('should display error message', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Multiple elements contain this text, so use getAllByText
			const elements = screen.getAllByText(/Invalid voice parameter/);
			expect(elements.length).toBeGreaterThan(0);
		});

		it('should display error detail', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/Expected one of: alloy, echo, fable/)).toBeDefined();
		});

		it('should handle null HTTP status', () => {
			const failure = createYamlGenerationFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Should not show HTTP status section or show "N/A"
			expect(screen.queryByText(/HTTP Status:/)).toBeNull();
		});
	});

	describe('Cause Analysis Card', () => {
		it('should display cause category', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/API parameter/)).toBeDefined();
		});

		it('should display problem location', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/tts_drive_upload/)).toBeDefined();
		});

		it('should display problem field', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/body\.voice/)).toBeDefined();
		});

		it('should display actual vs expected values', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Multiple elements contain the value, use getAllByText
			const actualValueElements = screen.getAllByText(/ja-JP-Standard-A/);
			expect(actualValueElements.length).toBeGreaterThan(0);
			// Expected value is separated, so check for parts
			const expectedValueElements = screen.getAllByText(/alloy/);
			expect(expectedValueElements.length).toBeGreaterThan(0);
		});

		it('should not show cause analysis when null', () => {
			const failure = createYamlGenerationFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.queryByText(/Problem Location/)).toBeNull();
		});
	});

	describe('Recommendations List', () => {
		it('should display all recommendations', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/Update voice parameter to use OpenAI TTS format/)).toBeDefined();
			expect(screen.getByText(/Regenerate workflow with corrected parameter/)).toBeDefined();
		});

		it('should show recommendations in a list format', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			const list = screen.getByRole('list', { name: /recommendations/i });
			expect(list).toBeDefined();
			const items = list.querySelectorAll('li');
			expect(items.length).toBe(2);
		});

		it('should handle empty recommendations', () => {
			const failure: FailureDetails = {
				...createYamlGenerationFailure(),
				recommendations: []
			};
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Should not crash, might show "No recommendations" or hide section
			expect(screen.queryByRole('list', { name: /recommendations/i })).toBeNull();
		});
	});

	describe('Retry History Timeline', () => {
		it('should display retry count', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/3.*attempts/i)).toBeDefined();
		});

		it('should display each retry attempt', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			expect(screen.getByText(/gemini-2.5-flash/)).toBeDefined();
			// Multiple gpt-4o-mini entries exist
			const gptElements = screen.getAllByText(/gpt-4o-mini/);
			expect(gptElements.length).toBeGreaterThan(0);
		});

		it('should display timestamps', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Timestamps are shown - the format depends on locale, but should show time
			// The timestamps 10:00, 10:01, 10:02 UTC will be localized
			const container = document.body;
			expect(container.textContent).toMatch(/\d{1,2}:\d{2}/);
		});

		it('should handle empty retry history', () => {
			const failure = createYamlGenerationFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Should not show retry history section
			expect(screen.queryByText(/attempts/i)).toBeNull();
		});
	});

	describe('Accessibility', () => {
		it('should have proper ARIA roles', () => {
			const failure = createWorkflowExecutionFailure();
			const { container } = render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Section with aria-label is implicitly a region
			const section = container.querySelector('section[aria-label*="Failure"]');
			expect(section).not.toBeNull();
		});

		it('should use semantic heading structure', () => {
			const failure = createWorkflowExecutionFailure();
			render(FailureDetailsPanel, { props: { failureDetails: failure } });

			// Should have headings for each section
			const headings = screen.getAllByRole('heading');
			expect(headings.length).toBeGreaterThanOrEqual(1);
		});
	});

	describe('All Failure Stages', () => {
		const stages = [
			'yaml_generation',
			'schema_validation',
			'workflow_registration',
			'workflow_execution',
			'node_error',
			'output_validation',
			'quality_evaluation'
		] as const;

		stages.forEach((stage) => {
			it(`should handle ${stage} failure stage`, () => {
				const failure: FailureDetails = {
					failure_stage: stage,
					error_summary: {
						http_status: null,
						error_code: null,
						error_message: `Error in stage: ${stage.replace(/_/g, ' ')}`,
						error_detail: null
					},
					cause_analysis: null,
					recommendations: [],
					retry_history: []
				};
				const { container } = render(FailureDetailsPanel, { props: { failureDetails: failure } });

				// The stage badge should contain the stage name with underscores
				const badge = container.querySelector('.stage-badge');
				expect(badge).not.toBeNull();
				expect(badge?.textContent).toContain(stage);
			});
		});
	});
});
