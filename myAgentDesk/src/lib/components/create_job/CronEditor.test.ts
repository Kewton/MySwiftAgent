import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import CronEditor from './CronEditor.svelte';

describe('CronEditor', () => {
	it('should render with default cron expression', () => {
		const { container } = render(CronEditor, { props: { onCronChange: vi.fn() } });
		const input = container.querySelector('input[type="text"]') as HTMLInputElement;
		expect(input.value).toBe('0 9 * * *');
	});

	it('should display next execution preview', () => {
		const { getByText } = render(CronEditor, { props: { onCronChange: vi.fn() } });
		expect(getByText(/毎日 9:00/i)).toBeTruthy();
	});

	it('should call onCronChange when cron expression changes', async () => {
		const onCronChange = vi.fn();
		const { container } = render(CronEditor, { props: { onCronChange } });

		const input = container.querySelector('input[type="text"]') as HTMLInputElement;
		input.value = '0 12 * * *';
		await fireEvent.input(input);

		expect(onCronChange).toHaveBeenCalledWith('0 12 * * *');
	});

	it('should allow selecting preset schedules', async () => {
		const onCronChange = vi.fn();
		const { getByText } = render(CronEditor, { props: { onCronChange } });

		const presetButton = getByText('6時間ごと');
		await fireEvent.click(presetButton);

		expect(onCronChange).toHaveBeenCalledWith('0 */6 * * *');
	});

	it('should validate cron expression format', async () => {
		const { container, getByText } = render(CronEditor, { props: { onCronChange: vi.fn() } });

		const input = container.querySelector('input[type="text"]') as HTMLInputElement;
		input.value = 'invalid cron';
		await fireEvent.input(input);

		expect(getByText(/Cron式は5つのフィールドが必要/i)).toBeTruthy();
	});

	it('should display error message for invalid cron', async () => {
		const { container, getByText } = render(CronEditor, { props: { onCronChange: vi.fn() } });

		const input = container.querySelector('input[type="text"]') as HTMLInputElement;
		input.value = '0 9';
		await fireEvent.input(input);

		expect(getByText(/Cron式は5つのフィールドが必要/i)).toBeTruthy();
	});

	it('should allow changing timezone', async () => {
		const { container } = render(CronEditor, {
			props: { timezone: 'UTC', onCronChange: vi.fn() }
		});

		const select = container.querySelector('select') as HTMLSelectElement;
		expect(select.value).toBe('UTC');
	});

	it('should update preview when timezone changes', async () => {
		const { container, getByText } = render(CronEditor, { props: { onCronChange: vi.fn() } });

		const select = container.querySelector('select') as HTMLSelectElement;
		select.value = 'UTC';
		await fireEvent.change(select);

		// Check that the preview shows the timezone (e.g., "毎日 9:00 (UTC)")
		expect(getByText(/毎日 9:00 \(UTC\)/i)).toBeTruthy();
	});
});
