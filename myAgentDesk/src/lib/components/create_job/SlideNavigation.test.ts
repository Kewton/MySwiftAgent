import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SlideNavigation from './SlideNavigation.svelte';

describe('SlideNavigation', () => {
	it('should call onPrev when prev button is clicked', async () => {
		const onPrev = vi.fn();
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 2,
				totalSlides: 5,
				onPrev,
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		const prevButton = getByLabelText('前のスライド');
		await fireEvent.click(prevButton);

		expect(onPrev).toHaveBeenCalledTimes(1);
	});

	it('should call onNext when next button is clicked', async () => {
		const onNext = vi.fn();
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 2,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext,
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		const nextButton = getByLabelText('次のスライド');
		await fireEvent.click(nextButton);

		expect(onNext).toHaveBeenCalledTimes(1);
	});

	it('should disable prev button on first slide', () => {
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 1,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		const prevButton = getByLabelText('前のスライド') as HTMLButtonElement;
		expect(prevButton.disabled).toBe(true);
	});

	it('should disable next button on last slide', () => {
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 5,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		const nextButton = getByLabelText('次のスライド') as HTMLButtonElement;
		expect(nextButton.disabled).toBe(true);
	});

	it('should call onFullscreen when fullscreen button is clicked', async () => {
		const onFullscreen = vi.fn();
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 2,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen,
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		const fullscreenButton = getByLabelText('全画面表示');
		await fireEvent.click(fullscreenButton);

		expect(onFullscreen).toHaveBeenCalledTimes(1);
	});

	it('should call onExportPdf when PDF export button is clicked', async () => {
		const onExportPdf = vi.fn();
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 2,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf,
				onExportPng: vi.fn()
			}
		});

		const pdfButton = getByLabelText('PDFでエクスポート');
		await fireEvent.click(pdfButton);

		expect(onExportPdf).toHaveBeenCalledTimes(1);
	});

	it('should call onExportPng when PNG export button is clicked', async () => {
		const onExportPng = vi.fn();
		const { getByLabelText } = render(SlideNavigation, {
			props: {
				currentSlide: 2,
				totalSlides: 5,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng
			}
		});

		const pngButton = getByLabelText('PNGでエクスポート');
		await fireEvent.click(pngButton);

		expect(onExportPng).toHaveBeenCalledTimes(1);
	});

	it('should display correct slide count', () => {
		const { getByText } = render(SlideNavigation, {
			props: {
				currentSlide: 3,
				totalSlides: 10,
				onPrev: vi.fn(),
				onNext: vi.fn(),
				onFullscreen: vi.fn(),
				onExportPdf: vi.fn(),
				onExportPng: vi.fn()
			}
		});

		expect(getByText('3 / 10')).toBeTruthy();
	});
});
