/**
 * Generation Components Tests
 * Issue #305: Workflow Generation Progress Display
 *
 * Tests for PhaseFlow, TaskBreakdownList, WorkflowStatusBadge, and GenerationSummary components.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import PhaseFlow from '$lib/components/generation/PhaseFlow.svelte';
import TaskBreakdownList from '$lib/components/generation/TaskBreakdownList.svelte';
import WorkflowStatusBadge from '$lib/components/generation/WorkflowStatusBadge.svelte';
import GenerationSummary from '$lib/components/generation/GenerationSummary.svelte';
import type { TaskBreakdownItem, WorkflowStatusItem } from '$lib/api/clients/expert-agent';

// Mock $app/stores for components that might need it
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

describe('PhaseFlow', () => {
	it('should render idle state correctly', () => {
		render(PhaseFlow, { props: { phase: 'idle', progress: 0 } });

		const phaseGroup = screen.getByRole('group', { name: /generation progress phases/i });
		expect(phaseGroup).toBeDefined();
	});

	it('should render task_analysis phase as active', () => {
		render(PhaseFlow, { props: { phase: 'task_analysis', progress: 35 } });

		// Progress bar should be visible
		const progressBar = screen.getByRole('progressbar');
		expect(progressBar).toBeDefined();
		expect(progressBar.getAttribute('aria-valuenow')).toBe('35');
	});

	it('should render workflow_generation phase as active', () => {
		render(PhaseFlow, { props: { phase: 'workflow_generation', progress: 80 } });

		const progressBar = screen.getByRole('progressbar');
		expect(progressBar.getAttribute('aria-valuenow')).toBe('80');
	});

	it('should render complete phase', () => {
		render(PhaseFlow, { props: { phase: 'complete', progress: 100 } });

		const progressBar = screen.getByRole('progressbar');
		expect(progressBar.getAttribute('aria-valuenow')).toBe('100');
	});

	it('should show warning style when hasFailures is true', () => {
		render(PhaseFlow, { props: { phase: 'complete', progress: 100, hasFailures: true } });

		// The component should render with hasFailures
		const phaseGroup = screen.getByRole('group');
		expect(phaseGroup).toBeDefined();
	});
});

describe('WorkflowStatusBadge', () => {
	it('should render pending status', () => {
		render(WorkflowStatusBadge, { props: { status: 'pending' } });

		const badge = screen.getByRole('status');
		expect(badge.textContent).toContain('Pending');
	});

	it('should render generating status with spinner', () => {
		render(WorkflowStatusBadge, { props: { status: 'generating' } });

		const badge = screen.getByRole('status');
		expect(badge.textContent).toContain('Generating');
	});

	it('should render success status', () => {
		render(WorkflowStatusBadge, {
			props: {
				status: 'success',
				workflowName: 'workflow_test',
				generationTimeMs: 28500
			}
		});

		const badge = screen.getByRole('status');
		expect(badge.textContent).toContain('Workflow OK');
	});

	it('should render failed status', () => {
		render(WorkflowStatusBadge, {
			props: {
				status: 'failed',
				errorMessage: 'API rate limit exceeded'
			}
		});

		const badge = screen.getByRole('status');
		expect(badge.textContent).toContain('Failed');
	});

	it('should have correct aria-label', () => {
		render(WorkflowStatusBadge, { props: { status: 'success' } });

		const badge = screen.getByRole('status');
		expect(badge.getAttribute('aria-label')).toContain('Workflow status: Workflow OK');
	});
});

describe('TaskBreakdownList', () => {
	const mockTasks: TaskBreakdownItem[] = [
		{
			task_id: 'tm_001',
			name: 'Gmail取得',
			description: 'Gmail APIで未読メール取得',
			recommended_apis: ['Gmail API']
		},
		{
			task_id: 'tm_002',
			name: 'Claude要約',
			description: 'Claude APIで要約生成',
			recommended_apis: ['Anthropic API']
		}
	];

	const mockWorkflowStatuses: WorkflowStatusItem[] = [
		{
			task_id: 'tm_001',
			status: 'success',
			workflow_name: 'workflow_gmail',
			generation_time_ms: 28500,
			error_message: null
		},
		{
			task_id: 'tm_002',
			status: 'generating',
			workflow_name: null,
			generation_time_ms: null,
			error_message: null
		}
	];

	it('should render task breakdown list', () => {
		render(TaskBreakdownList, { props: { tasks: mockTasks } });

		const region = screen.getByRole('region', { name: /task breakdown results/i });
		expect(region).toBeDefined();
	});

	it('should display task count', () => {
		render(TaskBreakdownList, { props: { tasks: mockTasks } });

		expect(screen.getByText('2 tasks')).toBeDefined();
	});

	it('should display task names', () => {
		render(TaskBreakdownList, { props: { tasks: mockTasks } });

		expect(screen.getByText('Gmail取得')).toBeDefined();
		expect(screen.getByText('Claude要約')).toBeDefined();
	});

	it('should display task descriptions', () => {
		render(TaskBreakdownList, { props: { tasks: mockTasks } });

		expect(screen.getByText('Gmail APIで未読メール取得')).toBeDefined();
	});

	it('should display recommended APIs as tags', () => {
		render(TaskBreakdownList, { props: { tasks: mockTasks } });

		expect(screen.getByText('Gmail API')).toBeDefined();
		expect(screen.getByText('Anthropic API')).toBeDefined();
	});

	it('should display workflow statuses when provided', () => {
		render(TaskBreakdownList, {
			props: { tasks: mockTasks, workflowStatuses: mockWorkflowStatuses }
		});

		// Should have status badges
		const badges = screen.getAllByRole('status');
		expect(badges.length).toBe(2);
	});

	it('should display workflow result for successful tasks', () => {
		render(TaskBreakdownList, {
			props: { tasks: mockTasks, workflowStatuses: mockWorkflowStatuses }
		});

		expect(screen.getByText('workflow_gmail.yaml')).toBeDefined();
		expect(screen.getByText('28.5s')).toBeDefined();
	});
});

describe('GenerationSummary', () => {
	it('should render summary section', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 3, failedCount: 0 }
		});

		const region = screen.getByRole('region', { name: /generation summary/i });
		expect(region).toBeDefined();
	});

	it('should display success count', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 2, failedCount: 1 }
		});

		// Use getAllByText since there are multiple '2' elements (section icon and stat value)
		const twoElements = screen.getAllByText('2');
		expect(twoElements.length).toBeGreaterThanOrEqual(1);
		expect(screen.getByText('Workflow Generated')).toBeDefined();
	});

	it('should display failed count when there are failures', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 2, failedCount: 1 }
		});

		expect(screen.getByText('1')).toBeDefined();
		expect(screen.getByText('Failed')).toBeDefined();
	});

	it('should not display failed section when no failures', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 3, failedCount: 0 }
		});

		expect(screen.queryByText('Failed')).toBeNull();
	});

	it('should display total tasks', () => {
		render(GenerationSummary, {
			props: { totalTasks: 5, successCount: 4, failedCount: 1 }
		});

		expect(screen.getByText('5')).toBeDefined();
		expect(screen.getByText('Total Tasks')).toBeDefined();
	});

	it('should display trace link when traceId is provided', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 3, failedCount: 0, traceId: 'trace_123' }
		});

		const link = screen.getByRole('link', { name: /view in langfuse/i });
		expect(link).toBeDefined();
		expect(link.getAttribute('href')).toBe('http://localhost:3001/trace/trace_123');
	});

	it('should not display trace link when traceId is not provided', () => {
		render(GenerationSummary, {
			props: { totalTasks: 3, successCount: 3, failedCount: 0 }
		});

		expect(screen.queryByRole('link', { name: /view in langfuse/i })).toBeNull();
	});
});
