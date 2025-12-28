/**
 * Run Type Tests
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Tests for Run type definitions, status utilities, and constants.
 */
import { describe, it, expect } from 'vitest';
import {
	RUN_STATUS_CONFIG,
	TERMINAL_STATUSES,
	isTerminalStatus,
	calculateProgress,
	getRunDuration,
	type RunListItem,
	type RunDetail,
	type RunStatusUpdate
} from '$lib/types/run';

describe('Run Type Definitions', () => {
	describe('RUN_STATUS_CONFIG', () => {
		it('should have configuration for all run statuses', () => {
			const expectedStatuses = ['queued', 'running', 'success', 'failed', 'canceled', 'timeout'];
			expectedStatuses.forEach((status) => {
				expect(RUN_STATUS_CONFIG[status as keyof typeof RUN_STATUS_CONFIG]).toBeDefined();
				expect(RUN_STATUS_CONFIG[status as keyof typeof RUN_STATUS_CONFIG].label).toBeDefined();
				expect(RUN_STATUS_CONFIG[status as keyof typeof RUN_STATUS_CONFIG].color).toBeDefined();
				expect(RUN_STATUS_CONFIG[status as keyof typeof RUN_STATUS_CONFIG].bgColor).toBeDefined();
			});
		});

		it('should have correct label for queued status', () => {
			expect(RUN_STATUS_CONFIG.queued.label).toBe('Queued');
		});

		it('should have correct label for running status', () => {
			expect(RUN_STATUS_CONFIG.running.label).toBe('Running');
		});

		it('should have correct label for success status', () => {
			expect(RUN_STATUS_CONFIG.success.label).toBe('Success');
		});

		it('should have correct label for failed status', () => {
			expect(RUN_STATUS_CONFIG.failed.label).toBe('Failed');
		});

		it('should have correct label for canceled status', () => {
			expect(RUN_STATUS_CONFIG.canceled.label).toBe('Canceled');
		});

		it('should have correct label for timeout status', () => {
			expect(RUN_STATUS_CONFIG.timeout.label).toBe('Timeout');
		});
	});

	describe('TERMINAL_STATUSES', () => {
		it('should include success, failed, canceled, timeout', () => {
			expect(TERMINAL_STATUSES).toContain('success');
			expect(TERMINAL_STATUSES).toContain('failed');
			expect(TERMINAL_STATUSES).toContain('canceled');
			expect(TERMINAL_STATUSES).toContain('timeout');
		});

		it('should not include queued or running', () => {
			expect(TERMINAL_STATUSES).not.toContain('queued');
			expect(TERMINAL_STATUSES).not.toContain('running');
		});
	});

	describe('isTerminalStatus', () => {
		it('should return true for terminal statuses', () => {
			expect(isTerminalStatus('success')).toBe(true);
			expect(isTerminalStatus('failed')).toBe(true);
			expect(isTerminalStatus('canceled')).toBe(true);
			expect(isTerminalStatus('timeout')).toBe(true);
		});

		it('should return false for non-terminal statuses', () => {
			expect(isTerminalStatus('queued')).toBe(false);
			expect(isTerminalStatus('running')).toBe(false);
		});
	});

	describe('calculateProgress', () => {
		it('should return 0 when no tasks completed', () => {
			expect(calculateProgress(0, 10)).toBe(0);
		});

		it('should return 100 when all tasks completed', () => {
			expect(calculateProgress(10, 10)).toBe(100);
		});

		it('should return correct percentage', () => {
			expect(calculateProgress(5, 10)).toBe(50);
			expect(calculateProgress(3, 12)).toBe(25);
		});

		it('should return 0 when total is 0', () => {
			expect(calculateProgress(0, 0)).toBe(0);
		});

		it('should handle undefined completed', () => {
			expect(calculateProgress(undefined, 10)).toBe(0);
		});

		it('should handle undefined total', () => {
			expect(calculateProgress(5, undefined)).toBe(0);
		});
	});

	describe('getRunDuration', () => {
		it('should return null when startedAt is null', () => {
			expect(getRunDuration(null, new Date())).toBeNull();
		});

		it('should return null when startedAt is undefined', () => {
			expect(getRunDuration(undefined, new Date())).toBeNull();
		});

		it('should calculate duration between startedAt and completedAt', () => {
			const start = new Date('2024-01-15T15:00:00Z');
			const end = new Date('2024-01-15T15:02:34Z');
			expect(getRunDuration(start, end)).toBe('2m 34s');
		});

		it('should calculate duration to now when completedAt is null', () => {
			const start = new Date(Date.now() - 60000); // 1 minute ago
			const duration = getRunDuration(start, null);
			expect(duration).toMatch(/^1m \d+s$|^0m \d+s$/);
		});

		it('should format hours correctly', () => {
			const start = new Date('2024-01-15T15:00:00Z');
			const end = new Date('2024-01-15T17:30:45Z');
			expect(getRunDuration(start, end)).toBe('2h 30m 45s');
		});

		it('should format seconds only for short durations', () => {
			const start = new Date('2024-01-15T15:00:00Z');
			const end = new Date('2024-01-15T15:00:45Z');
			expect(getRunDuration(start, end)).toBe('45s');
		});
	});

	describe('RunListItem interface', () => {
		it('should have required properties', () => {
			const runListItem: RunListItem = {
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				jobVersionLabel: 'v1.2',
				status: 'running',
				tasksCompleted: 3,
				totalTasks: 10,
				startedAt: new Date(),
				completedAt: null,
				createdAt: new Date()
			};

			expect(runListItem.id).toBeDefined();
			expect(runListItem.workbenchId).toBeDefined();
			expect(runListItem.jobVersionId).toBeDefined();
			expect(runListItem.jobVersionLabel).toBeDefined();
			expect(runListItem.status).toBeDefined();
		});
	});

	describe('RunDetail interface', () => {
		it('should have all detail properties', () => {
			const runDetail: RunDetail = {
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				jobVersionLabel: 'v1.2',
				status: 'success',
				externalJobId: 'ext_job_123',
				externalTraceId: 'trace_123',
				executionParams: '{"key": "value"}',
				resultSummary: 'All tasks completed',
				tasksCompleted: 10,
				totalTasks: 10,
				startedAt: new Date(),
				completedAt: new Date(),
				createdAt: new Date(),
				updatedAt: new Date()
			};

			expect(runDetail.id).toBeDefined();
			expect(runDetail.externalJobId).toBeDefined();
			expect(runDetail.externalTraceId).toBeDefined();
			expect(runDetail.executionParams).toBeDefined();
			expect(runDetail.resultSummary).toBeDefined();
		});
	});

	describe('RunStatusUpdate interface', () => {
		it('should have polling response properties', () => {
			const statusUpdate: RunStatusUpdate = {
				runId: 'run_001',
				status: 'running',
				tasksCompleted: 5,
				totalTasks: 10,
				externalTraceId: 'trace_123'
			};

			expect(statusUpdate.runId).toBeDefined();
			expect(statusUpdate.status).toBeDefined();
			expect(statusUpdate.tasksCompleted).toBeDefined();
			expect(statusUpdate.totalTasks).toBeDefined();
		});
	});
});
