/**
 * Job Version Type Definitions
 * Issue #291: Generate Page (Job Generation)
 *
 * Type definitions for job version entities used in
 * list views, detail views, and generation status display.
 */

import type { JobVersionStatus } from '$lib/server/db/schema';

// =============================================================================
// List View Types
// =============================================================================

/**
 * Job version data for list views.
 * Includes basic info and status for display in version list.
 */
export interface JobVersionListItem {
	id: string;
	versionLabel: string;
	status: JobVersionStatus;
	sourceRequirementVersionId: string;
	majorVersion: number;
	minorVersion: number;
	externalJobMasterId: string | null;
	externalTraceId: string | null;
	generatedAt: Date | null;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Detail View Types
// =============================================================================

/**
 * Complete job version data for detail views.
 * Includes full content and metadata.
 */
export interface JobVersionDetail {
	id: string;
	workbenchId: string;
	sourceRequirementVersionId: string;
	majorVersion: number;
	minorVersion: number;
	versionLabel: string;
	status: JobVersionStatus;
	taskBreakdown: string | null;
	interfaceDefinitions: string | null;
	workflows: string | null;
	externalJobMasterId: string | null;
	externalTraceId: string | null;
	errorMessage: string | null;
	generatedAt: Date | null;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Generation Status Types
// =============================================================================

/**
 * Generation status for polling.
 */
export interface GenerationStatus {
	jobVersionId: string;
	status: JobVersionStatus;
	progress: number; // 0-100
	externalJobMasterId: string | null;
	externalTraceId: string | null;
	errorMessage: string | null;
}

/**
 * Generation result after completion.
 */
export interface GenerationResult {
	success: boolean;
	jobVersionId: string;
	versionLabel: string;
	status: JobVersionStatus;
	taskBreakdown: string | null;
	interfaceDefinitions: string | null;
	workflows: string | null;
	externalJobMasterId: string | null;
	externalTraceId: string | null;
	errorMessage: string | null;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Status display configuration for job versions.
 */
export const JOB_VERSION_STATUS_CONFIG: Record<
	JobVersionStatus,
	{ label: string; color: string; bgColor: string }
> = {
	generating: { label: 'Generating', color: '#92400e', bgColor: '#fef3c7' },
	success: { label: 'Success', color: '#166534', bgColor: '#dcfce7' },
	failed: { label: 'Failed', color: '#dc2626', bgColor: '#fee2e2' },
	active: { label: 'Active', color: '#1e40af', bgColor: '#dbeafe' },
	deprecated: { label: 'Deprecated', color: '#64748b', bgColor: '#f1f5f9' }
};

/**
 * Polling configuration for job generation.
 * Issue #305: Reduced interval from 2s to 1s for better progress tracking.
 * Issue #305: Extended timeout from 5 to 15 minutes for complex workflow generation
 * with LLM Evaluation (fast_mode=False).
 */
export const POLLING_CONFIG = {
	intervalMs: 1000,
	maxDurationMs: 900000 // 15 minutes
} as const;

/**
 * Timeout error message.
 */
export const TIMEOUT_ERROR_MESSAGE = 'Timeout: Job generation exceeded 15 minutes';
