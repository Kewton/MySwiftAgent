import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createSchedule, getScheduleHistory, deleteSchedule } from './schedule-api';
import { ServiceError } from './types';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('schedule-api', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe('createSchedule', () => {
		it('should create a schedule successfully', async () => {
			const mockResponse = {
				schedule_id: 'schedule-123',
				job_id: 'job-456',
				cron_expression: '0 9 * * *',
				timezone: 'Asia/Tokyo',
				next_execution: '2025-11-03T09:00:00+09:00',
				status: 'active',
				created_at: '2025-11-02T14:00:00+09:00'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockResponse)
			});

			const result = await createSchedule({
				job_id: 'job-456',
				cron_expression: '0 9 * * *',
				timezone: 'Asia/Tokyo'
			});

			expect(result).toEqual(mockResponse);
		});

		it('should throw ServiceError on network failure', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			await expect(
				createSchedule({
					job_id: 'job-456',
					cron_expression: '0 9 * * *',
					timezone: 'Asia/Tokyo'
				})
			).rejects.toThrow(ServiceError);
		});

		it('should throw ServiceError on HTTP 400 error', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 400,
				text: async () => JSON.stringify({ detail: 'Invalid cron expression' })
			});

			await expect(
				createSchedule({
					job_id: 'job-456',
					cron_expression: 'invalid',
					timezone: 'Asia/Tokyo'
				})
			).rejects.toThrow(ServiceError);
		});
	});

	describe('getScheduleHistory', () => {
		it('should get schedule history successfully', async () => {
			const mockHistory = [
				{
					execution_id: 'exec-1',
					schedule_id: 'schedule-123',
					executed_at: '2025-11-02T09:00:00+09:00',
					status: 'success',
					error_message: null
				}
			];

			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify(mockHistory)
			});

			const result = await getScheduleHistory('job-456');

			expect(result).toEqual(mockHistory);
		});

		it('should throw ServiceError on HTTP 404 error', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				text: async () => JSON.stringify({ detail: 'Job not found' })
			});

			await expect(getScheduleHistory('job-456')).rejects.toThrow(ServiceError);
		});
	});

	describe('deleteSchedule', () => {
		it('should delete schedule successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				text: async () => JSON.stringify({})
			});

			await expect(deleteSchedule('schedule-123')).resolves.not.toThrow();
		});
	});
});
