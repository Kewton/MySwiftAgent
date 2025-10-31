/**
 * RequirementCard Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import RequirementCard from './RequirementCard.svelte';
import type { RequirementState } from '$lib/stores/conversations';

describe('RequirementCard', () => {
	const mockRequirements: RequirementState = {
		data_source: 'CSV file',
		process_description: 'データ分析',
		output_format: 'Excel',
		schedule: '毎日',
		completeness: 0.5
	};

	it('should render with initial requirements', () => {
		const { getByText } = render(RequirementCard, {
			props: {
				requirements: mockRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		expect(getByText('CSV file')).toBeTruthy();
		expect(getByText('データ分析')).toBeTruthy();
		expect(getByText('Excel')).toBeTruthy();
		expect(getByText('毎日')).toBeTruthy();
	});

	it('should show completeness percentage', () => {
		const { getByText } = render(RequirementCard, {
			props: {
				requirements: mockRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		expect(getByText('50%')).toBeTruthy();
	});

	it('should disable create button when completeness < 0.8', () => {
		const { container } = render(RequirementCard, {
			props: {
				requirements: mockRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		const button = container.querySelector('button[type="button"]') as HTMLButtonElement;
		expect(button).toBeTruthy();
		expect(button.hasAttribute('disabled')).toBe(true);
	});

	it('should enable create button when completeness >= 0.8', () => {
		const readyRequirements: RequirementState = {
			...mockRequirements,
			completeness: 0.9
		};

		const { container } = render(RequirementCard, {
			props: {
				requirements: readyRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		const button = container.querySelector('button[type="button"]') as HTMLButtonElement;
		expect(button).toBeTruthy();
		expect(button.hasAttribute('disabled')).toBe(false);
	});

	it('should call onCreateJob when button is clicked', async () => {
		const onCreateJob = vi.fn();
		const readyRequirements: RequirementState = {
			...mockRequirements,
			completeness: 0.9
		};

		const { container } = render(RequirementCard, {
			props: {
				requirements: readyRequirements,
				isCreatingJob: false,
				onCreateJob
			}
		});

		const button = container.querySelector('button[type="button"]') as HTMLButtonElement;
		expect(button).toBeTruthy();
		await fireEvent.click(button);

		expect(onCreateJob).toHaveBeenCalledTimes(1);
	});

	it('should disable button when isCreatingJob is true', () => {
		const readyRequirements: RequirementState = {
			...mockRequirements,
			completeness: 0.9
		};

		const { container } = render(RequirementCard, {
			props: {
				requirements: readyRequirements,
				isCreatingJob: true,
				onCreateJob: vi.fn()
			}
		});

		const button = container.querySelector('button[type="button"]') as HTMLButtonElement;
		expect(button).toBeTruthy();
		expect(button.hasAttribute('disabled')).toBe(true);
	});

	it('should toggle details when collapse button is clicked', async () => {
		const { getByLabelText, queryByText } = render(RequirementCard, {
			props: {
				requirements: mockRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		// Initially expanded
		expect(queryByText('CSV file')).toBeTruthy();

		// Click collapse button
		const collapseButton = getByLabelText(/折りたたむ/i);
		await fireEvent.click(collapseButton);

		// Details should be hidden
		expect(queryByText('CSV file')).toBeNull();

		// Click expand button
		const expandButton = getByLabelText(/展開/i);
		await fireEvent.click(expandButton);

		// Details should be visible again
		expect(queryByText('CSV file')).toBeTruthy();
	});

	it('should show "未定" for null requirement fields', () => {
		const emptyRequirements: RequirementState = {
			data_source: null,
			process_description: null,
			output_format: null,
			schedule: null,
			completeness: 0
		};

		const { getAllByText } = render(RequirementCard, {
			props: {
				requirements: emptyRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		const undefinedElements = getAllByText('未定');
		expect(undefinedElements.length).toBeGreaterThan(0);
	});

	it('should show green color when completeness >= 0.8', () => {
		const readyRequirements: RequirementState = {
			...mockRequirements,
			completeness: 0.9
		};

		const { container } = render(RequirementCard, {
			props: {
				requirements: readyRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		const percentage = container.querySelector('.text-green-600');
		expect(percentage).toBeTruthy();
	});

	it('should show purple color when completeness < 0.8', () => {
		const { container } = render(RequirementCard, {
			props: {
				requirements: mockRequirements,
				isCreatingJob: false,
				onCreateJob: vi.fn()
			}
		});

		const percentage = container.querySelector('.text-purple-600');
		expect(percentage).toBeTruthy();
	});
});
