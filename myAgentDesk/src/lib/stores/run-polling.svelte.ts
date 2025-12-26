/**
 * Run Polling Store
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Svelte 5 runes-based store for real-time run status polling.
 * Handles automatic polling, cleanup, and memory leak prevention.
 */

import type { RunStatus } from '$lib/server/db/schema';
import { isTerminalStatus, calculateProgress } from '$lib/types/run';

/**
 * Polling configuration for run status updates.
 */
export const RUN_POLLING_CONFIG = {
	/** Polling interval in milliseconds (5 seconds) */
	intervalMs: 5000,
	/** Maximum polling duration in milliseconds (30 minutes) */
	maxDurationMs: 1800000
} as const;

/**
 * Run status update from polling API.
 */
export interface RunPollingStatus {
	runId: string;
	status: RunStatus;
	tasksCompleted: number | null;
	totalTasks: number | null;
	externalTraceId: string | null;
}

/**
 * Run polling store interface.
 */
export interface RunPollingStore {
	/** Whether polling is currently active */
	readonly isPolling: boolean;
	/** Current run status from last poll */
	readonly runStatus: RunPollingStatus | null;
	/** Error message if polling failed */
	readonly error: string | null;
	/** Progress percentage (0-100) */
	readonly progress: number;
	/** Start polling for a run */
	startPolling: (runId: string) => void;
	/** Stop polling */
	stopPolling: () => void;
	/** Cleanup resources (call on component destroy) */
	destroy: () => void;
}

/**
 * Create a run polling store using Svelte 5 runes.
 *
 * @returns Run polling store
 */
export function createRunPollingStore(): RunPollingStore {
	let isPolling = $state(false);
	let runStatus = $state<RunPollingStatus | null>(null);
	let error = $state<string | null>(null);

	let intervalId: ReturnType<typeof setInterval> | null = null;
	let pollingStartTime: number | null = null;
	let currentRunId: string | null = null;

	const progress = $derived(
		runStatus ? calculateProgress(runStatus.tasksCompleted, runStatus.totalTasks) : 0
	);

	/**
	 * Fetch run status from API.
	 */
	async function fetchStatus(runId: string): Promise<RunPollingStatus> {
		const response = await fetch(`/api/runs/${runId}/status`);

		if (!response.ok) {
			const errorData = await response.json();
			throw new Error(errorData.error || `HTTP ${response.status}`);
		}

		return response.json();
	}

	/**
	 * Perform a single poll cycle.
	 */
	async function poll(): Promise<void> {
		if (!currentRunId || !isPolling) return;

		// Check for timeout
		if (pollingStartTime && Date.now() - pollingStartTime > RUN_POLLING_CONFIG.maxDurationMs) {
			error = 'Polling timeout: Run status monitoring exceeded 30 minutes';
			stopPolling();
			return;
		}

		try {
			const status = await fetchStatus(currentRunId);
			runStatus = status;

			// Stop polling if terminal status reached
			if (isTerminalStatus(status.status)) {
				stopPolling();
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch run status';
			stopPolling();
		}
	}

	/**
	 * Start polling for a run.
	 */
	function startPolling(runId: string): void {
		// Don't start if already polling
		if (isPolling) return;

		currentRunId = runId;
		isPolling = true;
		error = null;
		pollingStartTime = Date.now();

		// Perform initial poll
		poll();

		// Set up interval for subsequent polls
		intervalId = setInterval(poll, RUN_POLLING_CONFIG.intervalMs);
	}

	/**
	 * Stop polling.
	 */
	function stopPolling(): void {
		if (intervalId) {
			clearInterval(intervalId);
			intervalId = null;
		}
		isPolling = false;
		pollingStartTime = null;
	}

	/**
	 * Cleanup resources (call on component destroy).
	 */
	function destroy(): void {
		stopPolling();
		currentRunId = null;
		runStatus = null;
		error = null;
	}

	return {
		get isPolling() {
			return isPolling;
		},
		get runStatus() {
			return runStatus;
		},
		get error() {
			return error;
		},
		get progress() {
			return progress;
		},
		startPolling,
		stopPolling,
		destroy
	};
}
