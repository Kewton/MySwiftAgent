/**
 * NextActionBar Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import NextActionBar from '$lib/components/layout/NextActionBar.svelte';

describe('NextActionBar', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render the action bar container', () => {
		render(NextActionBar, {
			props: { message: 'Click to continue', actionLabel: 'Continue', actionHref: '/next' }
		});
		const container = screen.getByRole('region', { name: /next action/i });
		expect(container).toBeDefined();
	});

	it('should display the action message', () => {
		render(NextActionBar, {
			props: { message: 'Ready to generate', actionLabel: 'Generate', actionHref: '/generate' }
		});
		expect(screen.getByText('Ready to generate')).toBeDefined();
	});

	it('should render action button with correct href', () => {
		render(NextActionBar, {
			props: { message: 'Review complete', actionLabel: 'Start Run', actionHref: '/runs' }
		});
		const button = screen.getByRole('link', { name: /start run/i });
		expect(button).toBeDefined();
		expect(button.getAttribute('href')).toBe('/runs');
	});

	it('should hide when visible is false', () => {
		render(NextActionBar, {
			props: { message: 'Test', actionLabel: 'Test', actionHref: '/test', visible: false }
		});
		const container = screen.queryByRole('region', { name: /next action/i });
		expect(container).toBeNull();
	});

	it('should show when visible is true', () => {
		render(NextActionBar, {
			props: { message: 'Test', actionLabel: 'Test', actionHref: '/test', visible: true }
		});
		const container = screen.getByRole('region', { name: /next action/i });
		expect(container).toBeDefined();
	});
});
