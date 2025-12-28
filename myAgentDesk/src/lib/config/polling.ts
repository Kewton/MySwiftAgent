/**
 * Polling Configuration
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Centralized polling configuration for real-time status updates.
 */

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
 * Polling configuration for job generation status updates.
 * Note: This is separate from run polling as it uses different intervals.
 */
export const JOB_GENERATION_POLLING_CONFIG = {
	/** Polling interval in milliseconds (1 second) */
	intervalMs: 1000,
	/** Maximum polling duration in milliseconds (15 minutes) */
	maxDurationMs: 900000
} as const;
