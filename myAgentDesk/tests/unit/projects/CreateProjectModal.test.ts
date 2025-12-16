/**
 * CreateProjectModal Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CreateProjectModal from '../../../src/lib/components/projects/CreateProjectModal.svelte';

describe('CreateProjectModal', () => {
	it('should not render when closed', () => {
		render(CreateProjectModal, { props: { isOpen: false } });
		expect(screen.queryByRole('dialog')).toBeNull();
	});

	it('should render when open', () => {
		render(CreateProjectModal, { props: { isOpen: true } });
		expect(screen.getByRole('dialog')).toBeTruthy();
	});

	it('should show form fields', () => {
		render(CreateProjectModal, { props: { isOpen: true } });
		expect(screen.getByLabelText(/Project Name/i)).toBeTruthy();
		expect(screen.getByLabelText(/Description/i)).toBeTruthy();
	});

	it('should have submit button', () => {
		render(CreateProjectModal, { props: { isOpen: true } });
		expect(screen.getByRole('button', { name: /Create/i })).toBeTruthy();
	});

	it('should have cancel button', () => {
		render(CreateProjectModal, { props: { isOpen: true } });
		expect(screen.getByRole('button', { name: /Cancel/i })).toBeTruthy();
	});

	it('should show title', () => {
		render(CreateProjectModal, { props: { isOpen: true } });
		expect(screen.getByText(/New Project/i)).toBeTruthy();
	});
});
