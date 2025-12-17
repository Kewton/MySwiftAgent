/**
 * Requirements Component Tests
 * Issue #290: Requirements List and Version Management
 *
 * Tests for requirement-related Svelte components.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RequirementVersionCard from '$lib/components/requirements/RequirementVersionCard.svelte';
import DiffViewer from '$lib/components/markdown/DiffViewer.svelte';
import type { RequirementVersionStatus } from '$lib/server/db/schema';

// Mock $app/stores for page context
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: new URL('http://localhost/projects/proj_001/workbenches/wb_001/requirements'),
				params: { projectId: 'proj_001', workbenchId: 'wb_001' }
			});
			return () => {};
		})
	}
}));

// Mock $app/environment
vi.mock('$app/environment', () => ({
	browser: true
}));

describe('RequirementVersionCard', () => {
	const createMockVersion = (
		overrides: Partial<{
			id: string;
			version: number;
			status: RequirementVersionStatus;
			changeSummary: string | null;
			createdAt: Date;
			updatedAt: Date;
		}> = {}
	) => ({
		id: 'rv_001',
		version: 1,
		status: 'draft' as RequirementVersionStatus,
		changeSummary: 'Initial version',
		createdAt: new Date('2024-01-15'),
		updatedAt: new Date('2024-01-15'),
		...overrides
	});

	it('should render version number', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ version: 3 }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		expect(screen.getByTestId('version-number').textContent).toContain('v3');
	});

	it('should render status badge with correct label', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ status: 'active' }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const badge = screen.getByTestId('status-badge');
		expect(badge.textContent).toBe('Active');
	});

	it('should render draft status', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ status: 'draft' }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const badge = screen.getByTestId('status-badge');
		expect(badge.textContent).toBe('Draft');
	});

	it('should render deprecated status', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ status: 'deprecated' }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const badge = screen.getByTestId('status-badge');
		expect(badge.textContent).toBe('Deprecated');
	});

	it('should render submitted status', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ status: 'submitted' }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const badge = screen.getByTestId('status-badge');
		expect(badge.textContent).toBe('Submitted');
	});

	it('should show active indicator when isActive is true', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion(),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: true
			}
		});

		expect(screen.getByTestId('active-indicator')).toBeTruthy();
		expect(screen.getByTestId('active-indicator').textContent).toBe('Current');
	});

	it('should not show active indicator when isActive is false', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion(),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		expect(screen.queryByTestId('active-indicator')).toBeNull();
	});

	it('should render change summary when present', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ changeSummary: 'Added new feature' }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const summary = screen.getByTestId('change-summary');
		expect(summary.textContent).toBe('Added new feature');
	});

	it('should not render change summary when null', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ changeSummary: null }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		expect(screen.queryByTestId('change-summary')).toBeNull();
	});

	it('should link to correct detail page', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ id: 'rv_123' }),
				projectId: 'proj_abc',
				workbenchId: 'wb_xyz',
				isActive: false
			}
		});

		const card = screen.getByTestId('version-card');
		expect(card.getAttribute('href')).toBe(
			'/projects/proj_abc/workbenches/wb_xyz/requirements/rv_123'
		);
	});

	it('should render created date', () => {
		render(RequirementVersionCard, {
			props: {
				version: createMockVersion({ createdAt: new Date('2024-03-15') }),
				projectId: 'proj_001',
				workbenchId: 'wb_001',
				isActive: false
			}
		});

		const date = screen.getByTestId('created-date');
		expect(date.textContent).toContain('2024');
	});
});

describe('DiffViewer', () => {
	it('should render diff header with version numbers', () => {
		render(DiffViewer, {
			props: {
				diffs: [{ operation: 0 as const, text: 'Hello' }],
				fromVersion: 1,
				toVersion: 2
			}
		});

		const header = screen.getByTestId('diff-header');
		expect(header.textContent).toContain('v1');
		expect(header.textContent).toContain('v2');
	});

	it('should render equal text without highlighting', () => {
		render(DiffViewer, {
			props: {
				diffs: [{ operation: 0 as const, text: 'unchanged text' }],
				fromVersion: 1,
				toVersion: 2
			}
		});

		const segment = screen.getByTestId('diff-segment-0');
		expect(segment.textContent).toBe('unchanged text');
		expect(segment.getAttribute('data-operation')).toBe('0');
	});

	it('should highlight insertions', () => {
		render(DiffViewer, {
			props: {
				diffs: [{ operation: 1 as const, text: 'new text' }],
				fromVersion: 1,
				toVersion: 2
			}
		});

		const segment = screen.getByTestId('diff-segment-0');
		expect(segment.textContent).toBe('new text');
		expect(segment.getAttribute('data-operation')).toBe('1');
		expect(segment.classList.contains('diff-insertion')).toBe(true);
	});

	it('should highlight deletions', () => {
		render(DiffViewer, {
			props: {
				diffs: [{ operation: -1 as const, text: 'removed text' }],
				fromVersion: 1,
				toVersion: 2
			}
		});

		const segment = screen.getByTestId('diff-segment-0');
		expect(segment.textContent).toBe('removed text');
		expect(segment.getAttribute('data-operation')).toBe('-1');
		expect(segment.classList.contains('diff-deletion')).toBe(true);
	});

	it('should render multiple diff segments', () => {
		render(DiffViewer, {
			props: {
				diffs: [
					{ operation: 0 as const, text: 'Hello ' },
					{ operation: -1 as const, text: 'world' },
					{ operation: 1 as const, text: 'there' }
				],
				fromVersion: 1,
				toVersion: 2
			}
		});

		expect(screen.getByTestId('diff-segment-0').textContent).toBe('Hello ');
		expect(screen.getByTestId('diff-segment-1').textContent).toBe('world');
		expect(screen.getByTestId('diff-segment-2').textContent).toBe('there');
	});

	it('should render legend items', () => {
		render(DiffViewer, {
			props: {
				diffs: [],
				fromVersion: 1,
				toVersion: 2
			}
		});

		expect(screen.getByTestId('legend-deletion')).toBeTruthy();
		expect(screen.getByTestId('legend-insertion')).toBeTruthy();
	});
});
