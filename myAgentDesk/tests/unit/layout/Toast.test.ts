/**
 * Toast Component Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import Toast from '$lib/components/ui/Toast.svelte';

describe('Toast', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should render toast container', () => {
		render(Toast, { props: { message: 'Test message', type: 'info', visible: true } });
		expect(screen.getByText('Test message')).toBeDefined();
	});

	it('should not be visible when visible prop is false', () => {
		render(Toast, { props: { message: 'Test message', type: 'info', visible: false } });
		const toast = screen.queryByText('Test message');
		expect(toast).toBeNull();
	});

	it('should apply success style for success type', () => {
		render(Toast, { props: { message: 'Success!', type: 'success', visible: true } });
		const toast = screen.getByText('Success!');
		expect(toast.closest('[data-type="success"]')).toBeDefined();
	});

	it('should apply error style for error type', () => {
		render(Toast, { props: { message: 'Error!', type: 'error', visible: true } });
		const toast = screen.getByText('Error!');
		expect(toast.closest('[data-type="error"]')).toBeDefined();
	});

	it('should apply warning style for warning type', () => {
		render(Toast, { props: { message: 'Warning!', type: 'warning', visible: true } });
		const toast = screen.getByText('Warning!');
		expect(toast.closest('[data-type="warning"]')).toBeDefined();
	});
});
