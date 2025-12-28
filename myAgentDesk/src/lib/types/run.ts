/**
 * Run Type Definitions
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Type definitions for run entities used in list views, detail views,
 * and real-time status polling.
 */

import type { RunStatus } from '$lib/server/db/schema';

// =============================================================================
// List View Types
// =============================================================================

/**
 * Run data for list views.
 * Includes basic info and status for display in run list.
 */
export interface RunListItem {
	id: string;
	workbenchId: string;
	jobVersionId: string;
	jobVersionLabel: string;
	status: RunStatus;
	tasksCompleted: number | null;
	totalTasks: number | null;
	startedAt: Date | null;
	completedAt: Date | null;
	createdAt: Date;
}

// =============================================================================
// Detail View Types
// =============================================================================

/**
 * Complete run data for detail views.
 * Includes full content and metadata.
 */
export interface RunDetail {
	id: string;
	workbenchId: string;
	jobVersionId: string;
	jobVersionLabel: string;
	status: RunStatus;
	externalJobId: string | null;
	externalTraceId: string | null;
	executionParams: string | null;
	resultSummary: string | null;
	tasksCompleted: number | null;
	totalTasks: number | null;
	startedAt: Date | null;
	completedAt: Date | null;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Polling Types
// =============================================================================

/**
 * Run status update for polling responses.
 */
export interface RunStatusUpdate {
	runId: string;
	status: RunStatus;
	tasksCompleted: number | null;
	totalTasks: number | null;
	externalTraceId: string | null;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Status display configuration for runs.
 */
export const RUN_STATUS_CONFIG: Record<
	RunStatus,
	{ label: string; color: string; bgColor: string }
> = {
	queued: { label: 'Queued', color: '#64748b', bgColor: '#f1f5f9' },
	running: { label: 'Running', color: '#92400e', bgColor: '#fef3c7' },
	success: { label: 'Success', color: '#166534', bgColor: '#dcfce7' },
	failed: { label: 'Failed', color: '#dc2626', bgColor: '#fee2e2' },
	canceled: { label: 'Canceled', color: '#64748b', bgColor: '#f1f5f9' },
	timeout: { label: 'Timeout', color: '#9a3412', bgColor: '#ffedd5' }
};

/**
 * Terminal statuses that indicate the run has completed.
 */
export const TERMINAL_STATUSES: readonly RunStatus[] = [
	'success',
	'failed',
	'canceled',
	'timeout'
] as const;

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if a run status is a terminal status (run has completed).
 *
 * @param status - The run status to check
 * @returns true if the status is terminal, false otherwise
 */
export function isTerminalStatus(status: RunStatus): boolean {
	return (TERMINAL_STATUSES as readonly string[]).includes(status);
}

/**
 * Calculate the progress percentage of a run.
 *
 * @param tasksCompleted - Number of tasks completed
 * @param totalTasks - Total number of tasks
 * @returns Progress percentage (0-100)
 */
export function calculateProgress(
	tasksCompleted: number | null | undefined,
	totalTasks: number | null | undefined
): number {
	if (
		tasksCompleted === null ||
		tasksCompleted === undefined ||
		totalTasks === null ||
		totalTasks === undefined ||
		totalTasks === 0
	) {
		return 0;
	}
	return Math.round((tasksCompleted / totalTasks) * 100);
}

/**
 * Calculate the duration of a run.
 *
 * @param startedAt - When the run started
 * @param completedAt - When the run completed (null for ongoing runs)
 * @returns Formatted duration string (e.g., "2m 34s") or null if not started
 */
export function getRunDuration(
	startedAt: Date | null | undefined,
	completedAt: Date | null | undefined
): string | null {
	if (!startedAt) {
		return null;
	}

	const endTime = completedAt ? completedAt.getTime() : Date.now();
	const durationMs = endTime - startedAt.getTime();

	const seconds = Math.floor(durationMs / 1000) % 60;
	const minutes = Math.floor(durationMs / 60000) % 60;
	const hours = Math.floor(durationMs / 3600000);

	if (hours > 0) {
		return `${hours}h ${minutes}m ${seconds}s`;
	} else if (minutes > 0) {
		return `${minutes}m ${seconds}s`;
	} else {
		return `${seconds}s`;
	}
}
