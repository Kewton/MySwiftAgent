/**
 * RecentSchedulesList Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RecentSchedulesList from '../../../src/lib/components/projects/RecentSchedulesList.svelte';

describe('RecentSchedulesList', () => {
	const mockSchedules = [
		{
			id: 'sched_001',
			workbenchId: 'wb_001',
			targetJobVersionId: 'jv_001',
			name: 'Daily Report',
			cronExpression: '0 0 * * *',
			isEnabled: true,
			externalSchedulerId: null,
			executionParams: null,
			nextRunAt: new Date('2024-01-16T00:00:00'),
			lastRunAt: new Date('2024-01-15T00:00:00'),
			createdAt: new Date('2024-01-01'),
			updatedAt: new Date('2024-01-15'),
			workbench: { id: 'wb_001', name: 'API Workbench' }
		},
		{
			id: 'sched_002',
			workbenchId: 'wb_002',
			targetJobVersionId: 'jv_001',
			name: 'Weekly Cleanup',
			cronExpression: '0 0 * * 0',
			isEnabled: false,
			externalSchedulerId: null,
			executionParams: null,
			nextRunAt: null,
			lastRunAt: new Date('2024-01-07T00:00:00'),
			createdAt: new Date('2024-01-01'),
			updatedAt: new Date('2024-01-07'),
			workbench: { id: 'wb_002', name: 'Data Workbench' }
		}
	];

	it('should render schedule list', () => {
		render(RecentSchedulesList, { props: { schedules: mockSchedules, projectId: 'proj_001' } });
		expect(screen.getByText('Daily Report')).toBeTruthy();
		expect(screen.getByText('Weekly Cleanup')).toBeTruthy();
	});

	it('should show enabled/disabled status', () => {
		render(RecentSchedulesList, { props: { schedules: mockSchedules, projectId: 'proj_001' } });
		expect(screen.getByText('Enabled')).toBeTruthy();
		expect(screen.getByText('Disabled')).toBeTruthy();
	});

	it('should display cron expressions', () => {
		render(RecentSchedulesList, { props: { schedules: mockSchedules, projectId: 'proj_001' } });
		expect(screen.getByText('0 0 * * *')).toBeTruthy();
		expect(screen.getByText('0 0 * * 0')).toBeTruthy();
	});

	it('should show empty state when no schedules', () => {
		render(RecentSchedulesList, { props: { schedules: [], projectId: 'proj_001' } });
		expect(screen.getByText(/No schedules/i)).toBeTruthy();
	});

	it('should display workbench names', () => {
		render(RecentSchedulesList, { props: { schedules: mockSchedules, projectId: 'proj_001' } });
		expect(screen.getByText('API Workbench')).toBeTruthy();
		expect(screen.getByText('Data Workbench')).toBeTruthy();
	});
});
