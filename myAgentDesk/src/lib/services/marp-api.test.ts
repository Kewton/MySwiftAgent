import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getMarpReport, getMarpMarkdown, getMarpPdfUrl, getMarpPngUrls } from './marp-api';
import { ServiceError } from './types';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('marp-api', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('getMarpReport', () => {
		it('should get HTML format report successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview\n\n## Task 1\n...',
				html: '<div class="marp"><section>Slide 1</section></div>',
				pdf_url: null,
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpReport('job-123', 'html');

			expect(result).toEqual(mockResponse);
			expect(mockFetch).toHaveBeenCalledWith(
				expect.stringContaining('/marp-report/job-123?format=html'),
				expect.any(Object)
			);
		});

		it('should get PDF format report successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div class="marp">...</div>',
				pdf_url: 'http://localhost:8104/aiagent-api/v1/reports/job-123.pdf',
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpReport('job-123', 'pdf');

			expect(result).toEqual(mockResponse);
			expect(result.pdf_url).toBeTruthy();
		});

		it('should get PNG format report successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div class="marp">...</div>',
				pdf_url: null,
				png_urls: [
					'http://localhost:8104/aiagent-api/v1/reports/job-123-slide-1.png',
					'http://localhost:8104/aiagent-api/v1/reports/job-123-slide-2.png'
				],
				slide_count: 2
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpReport('job-123', 'png');

			expect(result).toEqual(mockResponse);
			expect(result.png_urls).toHaveLength(2);
		});

		it('should throw ServiceError on HTTP 404 error (job not found)', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				text: async () => JSON.stringify({ detail: 'Job not found' })
			});

			await expect(getMarpReport('job-999', 'html')).rejects.toThrow(ServiceError);
		});

		it('should throw ServiceError on HTTP 500 error (Marp generation failed)', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				text: async () => JSON.stringify({ detail: 'Marp generation failed' })
			});

			await expect(getMarpReport('job-123', 'html')).rejects.toThrow(ServiceError);
		});

		it('should throw ServiceError on network failure', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			await expect(getMarpReport('job-123', 'html')).rejects.toThrow(ServiceError);
		});
	});

	describe('getMarpMarkdown', () => {
		it('should get markdown successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview\n\n## Task 1',
				html: '<div>...</div>',
				pdf_url: null,
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpMarkdown('job-123');

			expect(result).toBe('# Job Overview\n\n## Task 1');
		});
	});

	describe('getMarpPdfUrl', () => {
		it('should get PDF URL successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div>...</div>',
				pdf_url: 'http://localhost:8104/aiagent-api/v1/reports/job-123.pdf',
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpPdfUrl('job-123');

			expect(result).toBe('http://localhost:8104/aiagent-api/v1/reports/job-123.pdf');
		});

		it('should throw error when PDF URL is not available', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div>...</div>',
				pdf_url: null,
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			await expect(getMarpPdfUrl('job-123')).rejects.toThrow('PDF URL not available');
		});
	});

	describe('getMarpPngUrls', () => {
		it('should get PNG URLs successfully', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div>...</div>',
				pdf_url: null,
				png_urls: [
					'http://localhost:8104/aiagent-api/v1/reports/job-123-slide-1.png',
					'http://localhost:8104/aiagent-api/v1/reports/job-123-slide-2.png'
				],
				slide_count: 2
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await getMarpPngUrls('job-123');

			expect(result).toHaveLength(2);
			expect(result[0]).toContain('slide-1.png');
		});

		it('should throw error when PNG URLs are not available', async () => {
			const mockResponse = {
				job_id: 'job-123',
				markdown: '# Job Overview',
				html: '<div>...</div>',
				pdf_url: null,
				png_urls: null,
				slide_count: 5
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			await expect(getMarpPngUrls('job-123')).rejects.toThrow('PNG URLs not available');
		});
	});
});
