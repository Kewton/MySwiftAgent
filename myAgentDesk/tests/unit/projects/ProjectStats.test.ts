/**
 * ProjectStats Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ProjectStats from '../../../src/lib/components/projects/ProjectStats.svelte';

describe('ProjectStats', () => {
	const mockStats = {
		workbenchCount: 5,
		recentRunCount: 12,
		activeScheduleCount: 3
	};

	it('should render workbench count', () => {
		render(ProjectStats, { props: { stats: mockStats } });
		expect(screen.getByText('5')).toBeTruthy();
	});

	it('should render recent run count', () => {
		render(ProjectStats, { props: { stats: mockStats } });
		expect(screen.getByText('12')).toBeTruthy();
	});

	it('should render active schedule count', () => {
		render(ProjectStats, { props: { stats: mockStats } });
		expect(screen.getByText('3')).toBeTruthy();
	});

	it('should display labels for each stat', () => {
		render(ProjectStats, { props: { stats: mockStats } });
		expect(screen.getByText(/Workbenches/i)).toBeTruthy();
		expect(screen.getByText(/Recent Runs/i)).toBeTruthy();
		expect(screen.getByText(/Active Schedules/i)).toBeTruthy();
	});

	it('should handle zero counts', () => {
		const zeroStats = {
			workbenchCount: 0,
			recentRunCount: 0,
			activeScheduleCount: 0
		};
		render(ProjectStats, { props: { stats: zeroStats } });
		const zeroElements = screen.getAllByText('0');
		expect(zeroElements.length).toBe(3);
	});
});
