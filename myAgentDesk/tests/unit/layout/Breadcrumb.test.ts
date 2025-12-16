/**
 * Breadcrumb Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Breadcrumb from '$lib/components/layout/Breadcrumb.svelte';

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

describe('Breadcrumb', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render home breadcrumb item', () => {
		render(Breadcrumb);
		const homeLink = screen.getByRole('link', { name: /home/i });
		expect(homeLink).toBeDefined();
		expect(homeLink.getAttribute('href')).toBe('/');
	});

	it('should render proper navigation structure', () => {
		render(Breadcrumb);
		const nav = screen.getByRole('navigation', { name: /breadcrumb/i });
		expect(nav).toBeDefined();
	});

	it('should render breadcrumb list', () => {
		render(Breadcrumb);
		const list = screen.getByRole('list');
		expect(list).toBeDefined();
	});

	it('should have separator between items', () => {
		render(Breadcrumb);
		// Check for separator elements (typically / or >)
		const container = screen.getByRole('navigation', { name: /breadcrumb/i });
		expect(container.textContent).toContain('/');
	});
});
