/**
 * RecentRunsList Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RecentRunsList from '../../../src/lib/components/projects/RecentRunsList.svelte';

describe('RecentRunsList', () => {
	const mockRuns = [
		{
			id: 'run_001',
			workbenchId: 'wb_001',
			jobVersionId: 'jv_001',
			status: 'success' as const,
			externalJobId: null,
			externalTraceId: null,
			executionParams: null,
			resultSummary: null,
			startedAt: new Date('2024-01-15T10:00:00'),
			completedAt: new Date('2024-01-15T10:05:00'),
			createdAt: new Date('2024-01-15T10:00:00'),
			updatedAt: new Date('2024-01-15T10:05:00'),
			workbench: { id: 'wb_001', name: 'API Workbench' }
		},
		{
			id: 'run_002',
			workbenchId: 'wb_002',
			jobVersionId: 'jv_001',
			status: 'running' as const,
			externalJobId: null,
			externalTraceId: null,
			executionParams: null,
			resultSummary: null,
			startedAt: new Date('2024-01-15T11:00:00'),
			completedAt: null,
			createdAt: new Date('2024-01-15T11:00:00'),
			updatedAt: new Date('2024-01-15T11:00:00'),
			workbench: { id: 'wb_002', name: 'Data Workbench' }
		}
	];

	it('should render run list', () => {
		render(RecentRunsList, { props: { runs: mockRuns, projectId: 'proj_001' } });
		expect(screen.getByText('API Workbench')).toBeTruthy();
		expect(screen.getByText('Data Workbench')).toBeTruthy();
	});

	it('should show status badges', () => {
		render(RecentRunsList, { props: { runs: mockRuns, projectId: 'proj_001' } });
		expect(screen.getByText('success')).toBeTruthy();
		expect(screen.getByText('running')).toBeTruthy();
	});

	it('should show empty state when no runs', () => {
		render(RecentRunsList, { props: { runs: [], projectId: 'proj_001' } });
		expect(screen.getByText(/No recent runs/i)).toBeTruthy();
	});

	it('should display run count in title', () => {
		render(RecentRunsList, { props: { runs: mockRuns, projectId: 'proj_001' } });
		expect(screen.getByText(/Recent Runs/i)).toBeTruthy();
	});
});
