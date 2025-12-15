/**
 * WorkbenchTabs Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import WorkbenchTabs from '$lib/components/layout/WorkbenchTabs.svelte';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches/wb_abc123/requirements' },
				params: { projectId: 'proj_001', workbenchId: 'wb_abc123' }
			});
			return () => {};
		})
	}
}));

describe('WorkbenchTabs', () => {
	const mockWorkbench = {
		id: 'wb_abc123',
		name: 'Test Workbench',
		projectId: 'proj_001'
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render tab navigation', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const nav = screen.getByRole('navigation', { name: /workbench/i });
		expect(nav).toBeDefined();
	});

	it('should render requirements tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /requirements/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/requirements');
	});

	it('should render generate tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /generate/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/generate');
	});

	it('should render review tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /review/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/review');
	});

	it('should render runs tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /runs/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/runs');
	});

	it('should render analyze tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /analyze/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/analyze');
	});

	it('should render improve tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /improve/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/improve');
	});

	it('should render schedule tab', () => {
		render(WorkbenchTabs, { props: { workbench: mockWorkbench } });
		const tab = screen.getByRole('link', { name: /schedule/i });
		expect(tab).toBeDefined();
		expect(tab.getAttribute('href')).toBe('/projects/proj_001/workbenches/wb_abc123/schedule');
	});
});
