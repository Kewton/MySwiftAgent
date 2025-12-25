/**
 * TaskAccordion Component Tests
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Tests for the task accordion component that displays task breakdown.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import TaskAccordion from '$lib/components/job-version/TaskAccordion.svelte';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches/wb_001/job-versions/jv_001' },
				params: { projectId: 'proj_001', workbenchId: 'wb_001', jobVersionId: 'jv_001' }
			});
			return () => {};
		})
	}
}));

describe('TaskAccordion Component', () => {
	const createTask = (overrides = {}) => ({
		task_id: 'tm_001',
		name: 'Fetch User Data',
		description: 'Retrieve user information from the database',
		recommended_apis: ['GET /api/users', 'GET /api/users/:id'],
		inputInterface: {
			type: 'object',
			properties: {
				userId: { type: 'string', description: 'The user ID to fetch' }
			},
			required: ['userId']
		},
		outputInterface: {
			type: 'object',
			properties: {
				user: { type: 'object', description: 'The fetched user data' }
			}
		},
		...overrides
	});

	describe('Collapsed State (Default)', () => {
		it('should render task name', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			expect(screen.getByText('Fetch User Data')).toBeDefined();
		});

		it('should render task index number', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			expect(screen.getByText('1')).toBeDefined();
		});

		it('should render task description', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			expect(screen.getByText('Retrieve user information from the database')).toBeDefined();
		});

		it('should render recommended APIs as tags', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			expect(screen.getByText('GET /api/users')).toBeDefined();
			expect(screen.getByText('GET /api/users/:id')).toBeDefined();
		});

		it('should have expand button', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			const expandButton = screen.getByRole('button', { name: /expand|show|details/i });
			expect(expandButton).toBeDefined();
		});

		it('should not show interfaces when collapsed', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			// Interface details should not be visible
			expect(screen.queryByText(/inputInterface/i)).toBeNull();
			expect(screen.queryByText(/outputInterface/i)).toBeNull();
		});
	});

	describe('Expanded State', () => {
		it('should expand when expand button is clicked', async () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			const expandButton = screen.getByRole('button', { name: /expand|show|details/i });
			await fireEvent.click(expandButton);

			// Should now show interface sections
			expect(screen.getByText(/Input Interface/i)).toBeDefined();
			expect(screen.getByText(/Output Interface/i)).toBeDefined();
		});

		it('should show input interface when expanded', async () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0, expanded: true } });

			expect(screen.getByText(/Input Interface/i)).toBeDefined();
			expect(screen.getByText(/userId/)).toBeDefined();
		});

		it('should show output interface when expanded', async () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0, expanded: true } });

			expect(screen.getByText(/Output Interface/i)).toBeDefined();
		});

		it('should format JSON Schema as readable JSON', async () => {
			const task = createTask();
			const { container } = render(TaskAccordion, {
				props: { task, index: 0, expanded: true }
			});

			// Should have pre or code element for JSON display
			const codeElements = container.querySelectorAll('pre, code');
			expect(codeElements.length).toBeGreaterThan(0);
		});

		it('should collapse when collapse button is clicked', async () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0, expanded: true } });

			const collapseButton = screen.getByRole('button', { name: /collapse|hide/i });
			await fireEvent.click(collapseButton);

			// Interfaces should be hidden
			expect(screen.queryByText(/Input Interface/i)).toBeNull();
		});
	});

	describe('Edge Cases', () => {
		it('should handle task without recommended APIs', () => {
			const task = createTask({ recommended_apis: [] });
			render(TaskAccordion, { props: { task, index: 0 } });

			expect(screen.getByText('Fetch User Data')).toBeDefined();
			// No API tags should be rendered
			expect(screen.queryByText('GET /api/users')).toBeNull();
		});

		it('should handle task without interfaces', async () => {
			const task = createTask({
				inputInterface: null,
				outputInterface: null
			});
			render(TaskAccordion, { props: { task, index: 0, expanded: true } });

			// Should still render without errors
			expect(screen.getByText('Fetch User Data')).toBeDefined();
		});

		it('should handle different task indices', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 7 } });

			expect(screen.getByText('8')).toBeDefined(); // 0-indexed to 1-indexed
		});
	});

	describe('Accessibility', () => {
		it('should have proper ARIA roles', () => {
			const task = createTask();
			const { container } = render(TaskAccordion, { props: { task, index: 0 } });

			// Should have accordion structure
			const regionOrArticle =
				container.querySelector('[role="region"]') || container.querySelector('article');
			expect(regionOrArticle).not.toBeNull();
		});

		it('should have accessible button', () => {
			const task = createTask();
			render(TaskAccordion, { props: { task, index: 0 } });

			const button = screen.getByRole('button', { name: /expand|show|details/i });
			expect(button.getAttribute('tabindex')).not.toBe('-1');
		});
	});
});
