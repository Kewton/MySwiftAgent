/**
 * ProjectSidebar Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ProjectSidebar from '$lib/components/layout/ProjectSidebar.svelte';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches' },
				params: { projectId: 'proj_001' }
			});
			return () => {};
		})
	}
}));

describe('ProjectSidebar', () => {
	const mockProject = {
		id: 'proj_001',
		name: 'Test Project'
	};

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render sidebar navigation', () => {
		render(ProjectSidebar, { props: { project: mockProject } });
		const nav = screen.getByRole('navigation', { name: /project/i });
		expect(nav).toBeDefined();
	});

	it('should render overview link', () => {
		render(ProjectSidebar, { props: { project: mockProject } });
		const overviewLink = screen.getByRole('link', { name: /overview/i });
		expect(overviewLink).toBeDefined();
		expect(overviewLink.getAttribute('href')).toBe('/projects/proj_001');
	});

	it('should render workbenches link', () => {
		render(ProjectSidebar, { props: { project: mockProject } });
		const workbenchesLink = screen.getByRole('link', { name: /workbenches/i });
		expect(workbenchesLink).toBeDefined();
		expect(workbenchesLink.getAttribute('href')).toBe('/projects/proj_001/workbenches');
	});

	it('should render vault link', () => {
		render(ProjectSidebar, { props: { project: mockProject } });
		const vaultLink = screen.getByRole('link', { name: /vault/i });
		expect(vaultLink).toBeDefined();
		expect(vaultLink.getAttribute('href')).toBe('/projects/proj_001/vault');
	});

	it('should display project name', () => {
		render(ProjectSidebar, { props: { project: mockProject } });
		expect(screen.getByText('Test Project')).toBeDefined();
	});
});
