/**
 * GlobalNav Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import GlobalNav from '$lib/components/layout/GlobalNav.svelte';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({ url: { pathname: '/' } });
			return () => {};
		})
	}
}));

describe('GlobalNav', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render the logo/home link', () => {
		render(GlobalNav);
		const logo = screen.getByRole('link', { name: /myagentdesk/i });
		expect(logo).toBeDefined();
		expect(logo.getAttribute('href')).toBe('/');
	});

	it('should render the projects navigation link', () => {
		render(GlobalNav);
		const projectsLink = screen.getByRole('link', { name: /projects/i });
		expect(projectsLink).toBeDefined();
		expect(projectsLink.getAttribute('href')).toBe('/projects');
	});

	it('should have proper navigation structure', () => {
		render(GlobalNav);
		const nav = screen.getByRole('navigation');
		expect(nav).toBeDefined();
	});

	it('should render settings link', () => {
		render(GlobalNav);
		const settingsLink = screen.getByRole('link', { name: /settings/i });
		expect(settingsLink).toBeDefined();
	});
});
