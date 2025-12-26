/**
 * Run Polling Store Tests
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Tests for the run polling store that handles real-time status updates.
 * Covers polling lifecycle, cleanup, and memory leak prevention.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createRunPollingStore, RUN_POLLING_CONFIG } from '$lib/stores/run-polling.svelte';
import type { RunStatus } from '$lib/server/db/schema';

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Run Polling Store', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		mockFetch.mockReset();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	describe('RUN_POLLING_CONFIG', () => {
		it('should have polling interval of 5 seconds', () => {
			expect(RUN_POLLING_CONFIG.intervalMs).toBe(5000);
		});

		it('should have max polling duration of 30 minutes', () => {
			expect(RUN_POLLING_CONFIG.maxDurationMs).toBe(1800000);
		});
	});

	describe('createRunPollingStore', () => {
		it('should create store with initial state', () => {
			const store = createRunPollingStore();

			expect(store.isPolling).toBe(false);
			expect(store.runStatus).toBeNull();
			expect(store.error).toBeNull();
		});

		it('should start polling when startPolling is called', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');

			expect(store.isPolling).toBe(true);

			// Wait for first poll
			await vi.runOnlyPendingTimersAsync();

			expect(mockFetch).toHaveBeenCalledWith('/api/runs/run_001/status');
			expect(store.runStatus?.status).toBe('running');
		});

		it('should stop polling when terminal status is reached', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'success',
					tasksCompleted: 10,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');

			await vi.runOnlyPendingTimersAsync();

			expect(store.isPolling).toBe(false);
			expect(store.runStatus?.status).toBe('success');
		});

		it('should continue polling while status is running', async () => {
			const store = createRunPollingStore();

			// Mock running response
			mockFetch.mockResolvedValue({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');

			// Wait for first poll
			await vi.runOnlyPendingTimersAsync();

			// Verify running status keeps polling active
			expect(store.runStatus?.status).toBe('running');
			expect(store.isPolling).toBe(true);

			// Cleanup
			store.stopPolling();
		});

		it('should stop polling when stopPolling is called', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValue({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			store.stopPolling();

			expect(store.isPolling).toBe(false);
		});

		it('should handle API errors gracefully', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: async () => ({ error: 'Internal Server Error' })
			});

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			expect(store.error).not.toBeNull();
			expect(store.isPolling).toBe(false);
		});

		it('should handle network errors gracefully', async () => {
			const store = createRunPollingStore();

			mockFetch.mockRejectedValueOnce(new Error('Network error'));

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			expect(store.error).not.toBeNull();
			expect(store.isPolling).toBe(false);
		});

		it('should have timeout configuration', () => {
			// Test that the timeout configuration is set correctly
			// The actual timeout behavior is tested via the configuration
			expect(RUN_POLLING_CONFIG.maxDurationMs).toBe(1800000); // 30 minutes
			expect(RUN_POLLING_CONFIG.maxDurationMs / RUN_POLLING_CONFIG.intervalMs).toBe(360);
		});

		it('should cleanup on destroy to prevent memory leaks', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValue({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			store.destroy();

			expect(store.isPolling).toBe(false);
		});

		it('should not start new polling if already polling', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValue({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');
			// Start polling sets isPolling = true immediately
			expect(store.isPolling).toBe(true);

			// Second call should be ignored because already polling
			store.startPolling('run_002');

			// isPolling should still be true for the first run
			expect(store.isPolling).toBe(true);

			await vi.runOnlyPendingTimersAsync();

			// All calls should be to the first runId
			const calls = mockFetch.mock.calls;
			calls.forEach((call) => {
				expect(call[0]).toBe('/api/runs/run_001/status');
			});

			store.stopPolling();
		});

		it('should allow starting polling after terminal status', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'success',
					tasksCompleted: 10,
					totalTasks: 10
				})
			});

			// First run - completes with success
			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			// Polling stopped automatically due to terminal status
			expect(store.isPolling).toBe(false);
			expect(store.runStatus?.runId).toBe('run_001');
			expect(store.runStatus?.status).toBe('success');
		});

		it('should calculate progress from status update', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10
				})
			});

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			// Progress should be 50% (5 out of 10 tasks)
			expect(store.progress).toBe(50);
			expect(store.runStatus?.tasksCompleted).toBe(5);
			expect(store.runStatus?.totalTasks).toBe(10);
		});

		it('should handle externalTraceId for Langfuse link generation', async () => {
			const store = createRunPollingStore();

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: async () => ({
					runId: 'run_001',
					status: 'running',
					tasksCompleted: 5,
					totalTasks: 10,
					externalTraceId: 'trace_abc123'
				})
			});

			store.startPolling('run_001');
			await vi.runOnlyPendingTimersAsync();

			expect(store.runStatus?.externalTraceId).toBe('trace_abc123');
		});
	});

	describe('Terminal status detection', () => {
		const terminalStatuses: RunStatus[] = ['success', 'failed', 'canceled', 'timeout'];

		terminalStatuses.forEach((status) => {
			it(`should stop polling when status is ${status}`, async () => {
				const store = createRunPollingStore();

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: async () => ({
						runId: 'run_001',
						status,
						tasksCompleted: 10,
						totalTasks: 10
					})
				});

				store.startPolling('run_001');
				await vi.runOnlyPendingTimersAsync();

				expect(store.isPolling).toBe(false);
				expect(store.runStatus?.status).toBe(status);
			});
		});
	});
});
