/**
 * WorkflowTraceSummary Component Tests
 * Issue #305: Task Workflow Traces Summary Feature
 *
 * Tests for the main summary component that displays workflow generation results.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import WorkflowTraceSummary from '$lib/components/generation/WorkflowTraceSummary.svelte';
import type { WorkflowStatusItemExtended } from '$lib/types/workflow-summary';

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

describe('WorkflowTraceSummary', () => {
	const createSuccessItem = (): WorkflowStatusItemExtended => ({
		task_id: 'tm_001',
		task_name: 'Generate Audio Script',
		status: 'success',
		workflow_name: 'workflow_audio_script',
		generation_time_ms: 28500,
		error_message: null,
		langfuse_trace_id: 'trace_abc123',
		summary: {
			yaml_preview: 'version: 0.5\nnodes:\n  source: {}\n  build_prompt:\n    agent: stringTemplateAgent',
			sample_input: { title: 'Test Title', sections: ['section1', 'section2'] },
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
				strengths: ['Good API usage', 'Proper data flow'],
				weaknesses: ['Missing timeout config'],
				suggestions: ['Add retry logic', 'Consider error handling'],
				confidence: 0.92
			},
			retry_info: {
				retry_count: 1,
				max_retry: 3,
				generation_model: 'gpt-4o-mini'
			},
			failure_details: null
		}
	});

	const createFailedItem = (): WorkflowStatusItemExtended => ({
		task_id: 'tm_002',
		task_name: 'Upload to Google Drive',
		status: 'failed',
		workflow_name: null,
		generation_time_ms: 800,
		error_message: 'Invalid voice parameter',
		langfuse_trace_id: 'trace_def456',
		summary: {
			yaml_preview: 'version: 0.5\nnodes:\n  tts_drive_upload: {}',
			sample_input: { voice_id: 'ja-JP-Standard-A' },
			test_result: {
				http_status: 400,
				is_valid: false,
				validation_errors: ['Invalid voice parameter'],
				execution_time_ms: 500
			},
			evaluation: null,
			retry_info: {
				retry_count: 3,
				max_retry: 3,
				generation_model: 'gpt-4o-mini'
			},
			failure_details: {
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
					},
					{
						attempt: 3,
						error_message: 'Invalid voice parameter',
						model_used: 'gpt-4o-mini',
						timestamp: '2025-12-24T10:02:00Z'
					}
				]
			}
		}
	});

	describe('Compact View (Default)', () => {
		it('should render task name and status badge', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			expect(screen.getByText('Generate Audio Script')).toBeDefined();
			expect(screen.getByRole('status')).toBeDefined();
		});

		it('should display evaluation score for success status', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			// Score should be visible in compact view
			expect(screen.getByText('85')).toBeDefined();
		});

		it('should display generation time', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			// 28500ms = 28.5s
			expect(screen.getByText(/28\.5s/)).toBeDefined();
		});

		it('should display retry count when > 0', () => {
			const item = createSuccessItem();
			const { container } = render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			// Retry count should be visible in the metrics section
			const retryElement = container.querySelector('.metric.retry');
			expect(retryElement).not.toBeNull();
			expect(retryElement?.textContent).toContain('1');
		});

		it('should have expand button', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			const expandButton = screen.getByRole('button', { name: /show|expand/i });
			expect(expandButton).toBeDefined();
		});

		it('should render failed status with error indicator', () => {
			const item = createFailedItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			expect(screen.getByText('Upload to Google Drive')).toBeDefined();
			// Failed badge should be present
			const status = screen.getByRole('status');
			expect(status.textContent).toContain('Failed');
		});
	});

	describe('Expanded View', () => {
		it('should expand when expand button is clicked', async () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: false } });

			const expandButton = screen.getByRole('button', { name: /show|expand/i });
			await fireEvent.click(expandButton);

			// After clicking, should show YAML preview
			expect(screen.getByText(/version: 0\.5/)).toBeDefined();
		});

		it('should show YAML preview when expanded (success)', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: true } });

			expect(screen.getByText(/version: 0\.5/)).toBeDefined();
			expect(screen.getByText(/stringTemplateAgent/)).toBeDefined();
		});

		it('should show test data when expanded (success)', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: true } });

			// Sample input should be visible
			expect(screen.getByText(/Test Title/)).toBeDefined();
		});

		it('should show evaluation details when expanded (success)', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: true } });

			// Evaluation section should be visible - use getAllByText since there are multiple 85 values
			const scoreElements = screen.getAllByText('85');
			expect(scoreElements.length).toBeGreaterThan(0);
			expect(screen.getByText(/Good API usage/)).toBeDefined();
		});

		it('should show failure details when expanded (failed)', () => {
			const item = createFailedItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: true } });

			// Failure stage should be visible
			expect(screen.getByText(/workflow_execution/i)).toBeDefined();
			// Error message - multiple elements contain this
			const errorElements = screen.getAllByText(/Invalid voice parameter/);
			expect(errorElements.length).toBeGreaterThan(0);
		});

		it('should collapse when collapse button is clicked', async () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item, expanded: true } });

			// Initially expanded, should show YAML
			expect(screen.getByText(/version: 0\.5/)).toBeDefined();

			const collapseButton = screen.getByRole('button', { name: /hide/i });
			await fireEvent.click(collapseButton);

			// After collapsing, detailed content should be hidden
			expect(screen.queryByText(/stringTemplateAgent/)).toBeNull();
		});
	});

	describe('Langfuse Trace Link', () => {
		it('should show trace link when langfuse_trace_id is available', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			const link = screen.getByRole('link', { name: /trace/i });
			expect(link).toBeDefined();
			expect(link.getAttribute('href')).toContain('trace_abc123');
		});

		it('should not show trace link when langfuse_trace_id is null', () => {
			const item = createSuccessItem();
			item.langfuse_trace_id = null;
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			expect(screen.queryByRole('link', { name: /trace/i })).toBeNull();
		});
	});

	describe('Edge Cases', () => {
		it('should handle item without summary', () => {
			const item: WorkflowStatusItemExtended = {
				task_id: 'tm_003',
				task_name: 'Pending Task',
				status: 'pending',
				workflow_name: null,
				generation_time_ms: null,
				error_message: null,
				langfuse_trace_id: null,
				summary: null
			};
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			expect(screen.getByText('Pending Task')).toBeDefined();
			expect(screen.getByRole('status')).toBeDefined();
		});

		it('should handle generating status', () => {
			const item: WorkflowStatusItemExtended = {
				task_id: 'tm_004',
				task_name: 'Generating Task',
				status: 'generating',
				workflow_name: null,
				generation_time_ms: null,
				error_message: null,
				langfuse_trace_id: null,
				summary: null
			};
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			const status = screen.getByRole('status');
			expect(status.textContent).toContain('Generating');
		});
	});

	describe('Accessibility', () => {
		it('should have proper ARIA roles', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			expect(screen.getByRole('article')).toBeDefined();
			expect(screen.getByRole('status')).toBeDefined();
		});

		it('should have keyboard accessible expand button', () => {
			const item = createSuccessItem();
			render(WorkflowTraceSummary, { props: { workflowStatus: item } });

			const button = screen.getByRole('button', { name: /show|expand/i });
			expect(button.getAttribute('tabindex')).not.toBe('-1');
		});
	});
});
