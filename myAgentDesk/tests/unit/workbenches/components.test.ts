/**
 * Workbench Component Tests
 * Issue #289: Workbench List/Detail Screens
 *
 * Tests for workbench-related Svelte components.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import WorkbenchCard from '$lib/components/workbenches/WorkbenchCard.svelte';
import WorkbenchStats from '$lib/components/workbenches/WorkbenchStats.svelte';
import CreateWorkbenchModal from '$lib/components/workbenches/CreateWorkbenchModal.svelte';
import type { WorkbenchListItem, WorkbenchStats as WorkbenchStatsType } from '$lib/types/workbench';

// Mock $app/stores for page context
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: new URL('http://localhost/projects/proj_001/workbenches?status=all'),
				params: { projectId: 'proj_001' }
			});
			return () => {};
		})
	}
}));

// Mock $app/navigation
vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

describe('WorkbenchCard', () => {
	const mockWorkbench: WorkbenchListItem = {
		id: 'wb_001',
		name: 'Test Workbench',
		description: 'A test workbench description',
		status: 'active',
		activeRequirementVersionId: 'rv_001',
		runCount: 10,
		lastRunAt: new Date('2024-01-15T10:00:00Z'),
		lastRunStatus: 'success',
		scheduleCount: 2,
		createdAt: new Date('2024-01-01'),
		updatedAt: new Date('2024-01-15')
	};

	it('should render workbench name', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		expect(screen.getByText('Test Workbench')).toBeTruthy();
	});

	it('should render workbench description', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		expect(screen.getByText('A test workbench description')).toBeTruthy();
	});

	it('should display status badge with correct class', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		const badge = screen.getByTestId('status-badge');
		expect(badge).toBeTruthy();
		expect(badge.textContent).toBe('active');
		expect(badge.classList.contains('badge-active')).toBe(true);
	});

	it('should display run count', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		const runCount = screen.getByTestId('run-count');
		expect(runCount.textContent).toContain('10');
	});

	it('should display schedule count', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		const scheduleCount = screen.getByTestId('schedule-count');
		expect(scheduleCount.textContent).toContain('2');
	});

	it('should link to workbench detail page', () => {
		render(WorkbenchCard, { props: { workbench: mockWorkbench, projectId: 'proj_001' } });

		const link = screen.getByTestId('workbench-card');
		expect(link.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_001');
	});

	it('should render draft status badge correctly', () => {
		const draftWorkbench: WorkbenchListItem = {
			...mockWorkbench,
			status: 'draft'
		};
		render(WorkbenchCard, { props: { workbench: draftWorkbench, projectId: 'proj_001' } });

		const badge = screen.getByTestId('status-badge');
		expect(badge.classList.contains('badge-draft')).toBe(true);
	});

	it('should render archived status badge correctly', () => {
		const archivedWorkbench: WorkbenchListItem = {
			...mockWorkbench,
			status: 'archived'
		};
		render(WorkbenchCard, { props: { workbench: archivedWorkbench, projectId: 'proj_001' } });

		const badge = screen.getByTestId('status-badge');
		expect(badge.classList.contains('badge-archived')).toBe(true);
	});
});

describe('WorkbenchStats', () => {
	const mockStats: WorkbenchStatsType = {
		totalRuns: 100,
		successfulRuns: 85,
		failedRuns: 15,
		successRate: 85,
		lastRunAt: new Date('2024-01-15T10:00:00Z'),
		activeSchedules: 3,
		pendingRuns: 2
	};

	it('should display total runs', () => {
		render(WorkbenchStats, { props: { stats: mockStats } });

		const totalRuns = screen.getByTestId('stat-total-runs');
		expect(totalRuns.textContent).toContain('100');
	});

	it('should display success rate with correct color', () => {
		render(WorkbenchStats, { props: { stats: mockStats } });

		const successRate = screen.getByTestId('stat-success-rate');
		expect(successRate.textContent).toContain('85%');
	});

	it('should display active schedules', () => {
		render(WorkbenchStats, { props: { stats: mockStats } });

		const schedules = screen.getByTestId('stat-active-schedules');
		expect(schedules.textContent).toContain('3');
	});

	it('should display pending runs', () => {
		render(WorkbenchStats, { props: { stats: mockStats } });

		const pending = screen.getByTestId('stat-pending-runs');
		expect(pending.textContent).toContain('2');
	});

	it('should apply warning color for medium success rate', () => {
		const mediumStats: WorkbenchStatsType = {
			...mockStats,
			successRate: 60
		};
		render(WorkbenchStats, { props: { stats: mediumStats } });

		const successRate = screen.getByTestId('stat-success-rate');
		expect(successRate.querySelector('.text-warning')).toBeTruthy();
	});

	it('should apply danger color for low success rate', () => {
		const lowStats: WorkbenchStatsType = {
			...mockStats,
			successRate: 30
		};
		render(WorkbenchStats, { props: { stats: lowStats } });

		const successRate = screen.getByTestId('stat-success-rate');
		expect(successRate.querySelector('.text-danger')).toBeTruthy();
	});
});

describe('CreateWorkbenchModal', () => {
	it('should not render when closed', () => {
		render(CreateWorkbenchModal, {
			props: { open: false, onClose: vi.fn() }
		});

		expect(screen.queryByTestId('create-workbench-modal')).toBeNull();
	});

	it('should render when open', () => {
		render(CreateWorkbenchModal, {
			props: { open: true, onClose: vi.fn() }
		});

		expect(screen.getByTestId('create-workbench-modal')).toBeTruthy();
	});

	it('should display modal title', () => {
		render(CreateWorkbenchModal, {
			props: { open: true, onClose: vi.fn() }
		});

		expect(screen.getByText('Create New Workbench')).toBeTruthy();
	});

	it('should have disabled submit button when name is empty', () => {
		render(CreateWorkbenchModal, {
			props: { open: true, onClose: vi.fn() }
		});

		const submitButton = screen.getByTestId('submit-button');
		expect(submitButton.hasAttribute('disabled')).toBe(true);
	});

	it('should enable submit button when name is provided', async () => {
		render(CreateWorkbenchModal, {
			props: { open: true, onClose: vi.fn() }
		});

		const nameInput = screen.getByTestId('input-name');
		await fireEvent.input(nameInput, { target: { value: 'New Workbench' } });

		const submitButton = screen.getByTestId('submit-button');
		expect(submitButton.hasAttribute('disabled')).toBe(false);
	});

	it('should call onClose when cancel button is clicked', async () => {
		const onClose = vi.fn();
		render(CreateWorkbenchModal, {
			props: { open: true, onClose }
		});

		const cancelButton = screen.getByText('Cancel');
		await fireEvent.click(cancelButton);

		expect(onClose).toHaveBeenCalled();
	});

	it('should call onCreate with form data when submitted', async () => {
		const onCreate = vi.fn();
		const onClose = vi.fn();
		render(CreateWorkbenchModal, {
			props: { open: true, onClose, onCreate }
		});

		const nameInput = screen.getByTestId('input-name');
		const descInput = screen.getByTestId('input-description');

		await fireEvent.input(nameInput, { target: { value: 'New Workbench' } });
		await fireEvent.input(descInput, { target: { value: 'A description' } });

		const submitButton = screen.getByTestId('submit-button');
		await fireEvent.click(submitButton);

		expect(onCreate).toHaveBeenCalledWith({
			name: 'New Workbench',
			description: 'A description'
		});
		expect(onClose).toHaveBeenCalled();
	});
});
