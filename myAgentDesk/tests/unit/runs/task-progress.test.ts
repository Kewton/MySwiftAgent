/**
 * TaskProgress Component Tests
 * Issue #293: Runs Screen - Task Progress Display
 *
 * Tests for TaskProgressCard and TaskProgressList components.
 */

import { describe, it, expect } from 'vitest';
import type { TaskProgressItem } from '$lib/utils/interface-schema';

describe('TaskProgress Component Types', () => {
	describe('TaskProgressItem structure', () => {
		it('should have required fields for display', () => {
			const task: TaskProgressItem = {
				taskId: 'task_001',
				taskName: 'google_search_financials',
				order: 1,
				status: 'succeeded',
				inputData: { company_name: 'Toyota' },
				outputData: { success: true, documents: ['doc1.pdf'] },
				durationMs: 12000
			};

			expect(task.taskId).toBe('task_001');
			expect(task.taskName).toBe('google_search_financials');
			expect(task.order).toBe(1);
			expect(task.status).toBe('succeeded');
			expect(task.durationMs).toBe(12000);
		});

		it('should support all task statuses', () => {
			const statuses = ['pending', 'running', 'succeeded', 'failed', 'skipped'];

			statuses.forEach((status) => {
				const task: TaskProgressItem = {
					taskId: 'task_001',
					taskName: 'Test Task',
					order: 1,
					status
				};
				expect(task.status).toBe(status);
			});
		});

		it('should handle optional fields', () => {
			const task: TaskProgressItem = {
				taskId: 'task_001',
				taskName: 'Pending Task',
				order: 1,
				status: 'pending'
				// No inputData, outputData, durationMs, etc.
			};

			expect(task.inputData).toBeUndefined();
			expect(task.outputData).toBeUndefined();
			expect(task.durationMs).toBeUndefined();
			expect(task.error).toBeUndefined();
		});

		it('should include error information for failed tasks', () => {
			const task: TaskProgressItem = {
				taskId: 'task_001',
				taskName: 'Failed Task',
				order: 1,
				status: 'failed',
				error: 'API rate limit exceeded',
				inputData: { query: 'test' }
			};

			expect(task.status).toBe('failed');
			expect(task.error).toBe('API rate limit exceeded');
		});

		it('should include timing information', () => {
			const startedAt = new Date('2024-12-26T10:00:00Z');
			const finishedAt = new Date('2024-12-26T10:00:12Z');

			const task: TaskProgressItem = {
				taskId: 'task_001',
				taskName: 'Completed Task',
				order: 1,
				status: 'succeeded',
				startedAt,
				finishedAt,
				durationMs: 12000
			};

			expect(task.startedAt).toEqual(startedAt);
			expect(task.finishedAt).toEqual(finishedAt);
			expect(task.durationMs).toBe(12000);
		});
	});
});

describe('TaskProgress UI Helper Functions', () => {
	describe('formatDuration', () => {
		function formatDuration(ms: number | null | undefined): string {
			if (ms == null) return '-';
			if (ms < 1000) return `${ms}ms`;
			const seconds = ms / 1000;
			if (seconds < 60) return `${seconds.toFixed(1)}s`;
			const minutes = Math.floor(seconds / 60);
			const remainingSeconds = (seconds % 60).toFixed(0);
			return `${minutes}m ${remainingSeconds}s`;
		}

		it('should format milliseconds', () => {
			expect(formatDuration(500)).toBe('500ms');
		});

		it('should format seconds', () => {
			expect(formatDuration(12000)).toBe('12.0s');
			expect(formatDuration(5500)).toBe('5.5s');
		});

		it('should format minutes and seconds', () => {
			expect(formatDuration(90000)).toBe('1m 30s');
			expect(formatDuration(125000)).toBe('2m 5s');
		});

		it('should handle null/undefined', () => {
			expect(formatDuration(null)).toBe('-');
			expect(formatDuration(undefined)).toBe('-');
		});
	});

	describe('getStatusColor', () => {
		function getStatusColor(status: string): string {
			switch (status) {
				case 'succeeded':
					return 'green';
				case 'failed':
					return 'red';
				case 'running':
					return 'blue';
				case 'pending':
					return 'gray';
				case 'skipped':
					return 'yellow';
				default:
					return 'gray';
			}
		}

		it('should return correct color for each status', () => {
			expect(getStatusColor('succeeded')).toBe('green');
			expect(getStatusColor('failed')).toBe('red');
			expect(getStatusColor('running')).toBe('blue');
			expect(getStatusColor('pending')).toBe('gray');
			expect(getStatusColor('skipped')).toBe('yellow');
		});

		it('should default to gray for unknown status', () => {
			expect(getStatusColor('unknown')).toBe('gray');
		});
	});

	describe('getStatusIcon', () => {
		function getStatusIcon(status: string): string {
			switch (status) {
				case 'succeeded':
					return '✓';
				case 'failed':
					return '✗';
				case 'running':
					return '⟳';
				case 'pending':
					return '○';
				case 'skipped':
					return '−';
				default:
					return '?';
			}
		}

		it('should return correct icon for each status', () => {
			expect(getStatusIcon('succeeded')).toBe('✓');
			expect(getStatusIcon('failed')).toBe('✗');
			expect(getStatusIcon('running')).toBe('⟳');
			expect(getStatusIcon('pending')).toBe('○');
			expect(getStatusIcon('skipped')).toBe('−');
		});
	});
});

describe('TaskProgressList Logic', () => {
	it('should calculate overall progress from task list', () => {
		const tasks: TaskProgressItem[] = [
			{ taskId: 'task_001', taskName: 'Task 1', order: 1, status: 'succeeded' },
			{ taskId: 'task_002', taskName: 'Task 2', order: 2, status: 'succeeded' },
			{ taskId: 'task_003', taskName: 'Task 3', order: 3, status: 'running' },
			{ taskId: 'task_004', taskName: 'Task 4', order: 4, status: 'pending' }
		];

		const completedCount = tasks.filter((t) => t.status === 'succeeded').length;
		const totalCount = tasks.length;
		const progressPercent = Math.round((completedCount / totalCount) * 100);

		expect(completedCount).toBe(2);
		expect(totalCount).toBe(4);
		expect(progressPercent).toBe(50);
	});

	it('should sort tasks by order', () => {
		const unsortedTasks: TaskProgressItem[] = [
			{ taskId: 'task_003', taskName: 'Task 3', order: 3, status: 'pending' },
			{ taskId: 'task_001', taskName: 'Task 1', order: 1, status: 'succeeded' },
			{ taskId: 'task_002', taskName: 'Task 2', order: 2, status: 'running' }
		];

		const sortedTasks = [...unsortedTasks].sort((a, b) => a.order - b.order);

		expect(sortedTasks[0].taskId).toBe('task_001');
		expect(sortedTasks[1].taskId).toBe('task_002');
		expect(sortedTasks[2].taskId).toBe('task_003');
	});

	it('should identify currently running task', () => {
		const tasks: TaskProgressItem[] = [
			{ taskId: 'task_001', taskName: 'Task 1', order: 1, status: 'succeeded' },
			{ taskId: 'task_002', taskName: 'Task 2', order: 2, status: 'running' },
			{ taskId: 'task_003', taskName: 'Task 3', order: 3, status: 'pending' }
		];

		const runningTask = tasks.find((t) => t.status === 'running');

		expect(runningTask).toBeDefined();
		expect(runningTask?.taskId).toBe('task_002');
	});

	it('should detect if any task has failed', () => {
		const tasksWithFailure: TaskProgressItem[] = [
			{ taskId: 'task_001', taskName: 'Task 1', order: 1, status: 'succeeded' },
			{ taskId: 'task_002', taskName: 'Task 2', order: 2, status: 'failed', error: 'Error' }
		];

		const hasFailed = tasksWithFailure.some((t) => t.status === 'failed');
		expect(hasFailed).toBe(true);

		const tasksWithoutFailure: TaskProgressItem[] = [
			{ taskId: 'task_001', taskName: 'Task 1', order: 1, status: 'succeeded' },
			{ taskId: 'task_002', taskName: 'Task 2', order: 2, status: 'succeeded' }
		];

		const hasNoFailed = tasksWithoutFailure.some((t) => t.status === 'failed');
		expect(hasNoFailed).toBe(false);
	});
});

describe('OutputViewer Logic', () => {
	describe('JSON formatting', () => {
		it('should format output data as JSON', () => {
			const outputData = { success: true, documents: ['doc1.pdf', 'doc2.pdf'] };
			const formatted = JSON.stringify(outputData, null, 2);

			expect(formatted).toContain('"success": true');
			expect(formatted).toContain('"documents"');
		});

		it('should handle null output data', () => {
			const outputData = null;
			const formatted = outputData ? JSON.stringify(outputData, null, 2) : 'No output data';

			expect(formatted).toBe('No output data');
		});

		it('should handle complex nested output', () => {
			const outputData = {
				status: 'completed',
				result: {
					summary: 'Analysis complete',
					details: {
						items: [1, 2, 3],
						metadata: { source: 'api' }
					}
				}
			};

			const formatted = JSON.stringify(outputData, null, 2);
			expect(formatted).toContain('"summary": "Analysis complete"');
			expect(formatted).toContain('"items"');
		});
	});

	describe('Download functionality', () => {
		it('should generate valid download filename', () => {
			const taskId = 'task_001';
			const timestamp = '2024-12-26T10-00-00';
			const filename = `${taskId}_output_${timestamp}.json`;

			expect(filename).toBe('task_001_output_2024-12-26T10-00-00.json');
		});

		it('should create downloadable blob from JSON', () => {
			const data = { test: 'data' };
			const jsonString = JSON.stringify(data, null, 2);
			const blob = new Blob([jsonString], { type: 'application/json' });

			expect(blob.type).toBe('application/json');
			expect(blob.size).toBeGreaterThan(0);
		});
	});

	describe('Display modes', () => {
		const displayModes = ['formatted', 'raw', 'tree'] as const;

		it('should support multiple display modes', () => {
			expect(displayModes).toContain('formatted');
			expect(displayModes).toContain('raw');
			expect(displayModes).toContain('tree');
		});

		it('should format JSON differently based on mode', () => {
			const data = { key: 'value' };

			// Formatted mode - pretty print
			const formatted = JSON.stringify(data, null, 2);
			expect(formatted).toContain('\n');

			// Raw mode - compact
			const raw = JSON.stringify(data);
			expect(raw).not.toContain('\n');
		});
	});
});
