import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import ScheduleSelector from './ScheduleSelector.svelte';

describe('ScheduleSelector', () => {
	it('should render with default execution mode', () => {
		const { container } = render(ScheduleSelector, { props: { onChange: vi.fn() } });
		const apiOnlyRadio = container.querySelector('input[value="api_only"]') as HTMLInputElement;
		expect(apiOnlyRadio.checked).toBe(true);
	});

	it('should render all three options', () => {
		const { getByText } = render(ScheduleSelector, { props: { onChange: vi.fn() } });
		expect(getByText('API公開のみ')).toBeTruthy();
		expect(getByText('スケジュール実行')).toBeTruthy();
		expect(getByText('両方')).toBeTruthy();
	});

	it('should call onChange when execution mode changes', async () => {
		const onChange = vi.fn();
		const { container } = render(ScheduleSelector, { props: { onChange } });

		const scheduleRadio = container.querySelector('input[value="schedule"]') as HTMLInputElement;
		await fireEvent.click(scheduleRadio);

		expect(onChange).toHaveBeenCalledWith('schedule');
	});

	it('should allow switching between modes', async () => {
		const onChange = vi.fn();
		const { container } = render(ScheduleSelector, {
			props: { executionMode: 'api_only', onChange }
		});

		const bothRadio = container.querySelector('input[value="both"]') as HTMLInputElement;
		await fireEvent.click(bothRadio);

		expect(onChange).toHaveBeenCalledWith('both');
	});

	it('should display descriptions for each option', () => {
		const { getByText } = render(ScheduleSelector, { props: { onChange: vi.fn() } });
		expect(getByText(/手動実行のみ/i)).toBeTruthy();
		expect(getByText(/定期実行のみ/i)).toBeTruthy();
		expect(getByText(/手動実行とスケジュール実行の両方/i)).toBeTruthy();
	});
});
