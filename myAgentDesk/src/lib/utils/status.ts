/**
 * Status Configuration Utilities
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Unified status configuration for job versions.
 * Single source of truth for status styling (DRY principle).
 */

import type { JobVersionStatus } from '$lib/server/db/schema';

/**
 * Status display configuration.
 */
export interface StatusConfig {
	label: string;
	class: string;
	color: string;
	bgColor: string;
}

/**
 * Job version status configurations.
 * Provides both CSS class names and inline style values for flexibility.
 */
export const JOB_VERSION_STATUS: Record<JobVersionStatus | 'default', StatusConfig> = {
	generating: {
		label: 'Generating',
		class: 'status-generating',
		color: '#92400e',
		bgColor: '#fef3c7'
	},
	success: {
		label: 'Success',
		class: 'status-success',
		color: '#166534',
		bgColor: '#dcfce7'
	},
	failed: {
		label: 'Failed',
		class: 'status-failed',
		color: '#dc2626',
		bgColor: '#fee2e2'
	},
	active: {
		label: 'Active',
		class: 'status-active',
		color: '#1e40af',
		bgColor: '#dbeafe'
	},
	deprecated: {
		label: 'Deprecated',
		class: 'status-deprecated',
		color: '#64748b',
		bgColor: '#f1f5f9'
	},
	default: {
		label: 'Unknown',
		class: 'status-default',
		color: '#6b7280',
		bgColor: '#f3f4f6'
	}
};

/**
 * Get status configuration for a job version status.
 *
 * @param status - Job version status string
 * @returns Status configuration object
 *
 * @example
 * getStatusConfig('active') // { label: 'Active', class: 'status-active', ... }
 * getStatusConfig('unknown') // { label: 'unknown', class: 'status-default', ... }
 */
export function getStatusConfig(status: string): StatusConfig {
	const config = JOB_VERSION_STATUS[status as JobVersionStatus];
	if (config) {
		return config;
	}
	// Return default config with the original status as label
	return {
		...JOB_VERSION_STATUS.default,
		label: status
	};
}

/**
 * Check if a status can be activated.
 * Only 'success' and 'deprecated' statuses can be activated.
 *
 * @param status - Job version status string
 * @returns true if the status can be activated
 */
export function canActivate(status: string): boolean {
	return status === 'success' || status === 'deprecated';
}

/**
 * Check if a status allows starting a run.
 * Only 'active' status allows starting runs.
 *
 * @param status - Job version status string
 * @returns true if runs can be started
 */
export function canStartRun(status: string): boolean {
	return status === 'active';
}
