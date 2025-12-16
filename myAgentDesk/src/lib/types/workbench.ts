/**
 * Workbench Type Definitions
 * Issue #289: Workbench List/Detail Screens
 *
 * Type definitions for workbench-related entities used in
 * list views, detail views, and filtering.
 */

import type {
	WorkbenchStatus,
	RunStatus,
	RequirementVersionStatus,
	JobVersionStatus
} from '$lib/server/db/schema';

// =============================================================================
// Summary Types for Related Entities
// =============================================================================

/** Summary of a requirement version (for display in workbench detail) */
export interface RequirementVersionSummary {
	id: string;
	version: number;
	status: RequirementVersionStatus;
}

/** Summary of a job version (for display in workbench detail) */
export interface JobVersionSummary {
	id: string;
	versionLabel: string;
	status: JobVersionStatus;
}

// =============================================================================
// List View Types
// =============================================================================

/**
 * Workbench data for list views.
 * Includes aggregated statistics for run counts and schedule info.
 * Optimized for N+1 query prevention.
 */
export interface WorkbenchListItem {
	id: string;
	name: string;
	description: string | null;
	status: WorkbenchStatus;
	activeRequirementVersionId: string | null;
	runCount: number;
	lastRunAt: Date | null;
	lastRunStatus: RunStatus | null;
	scheduleCount: number;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Detail View Types
// =============================================================================

/**
 * Statistical information for a workbench.
 * Used in the overview panel of workbench detail view.
 */
export interface WorkbenchStats {
	totalRuns: number;
	successfulRuns: number;
	failedRuns: number;
	successRate: number; // Percentage (0-100)
	lastRunAt: Date | null;
	activeSchedules: number;
	pendingRuns: number;
}

/**
 * Complete workbench data for detail views.
 * Includes related entity summaries and statistics.
 */
export interface WorkbenchDetail {
	id: string;
	name: string;
	description: string | null;
	status: WorkbenchStatus;
	projectId: string;
	activeRequirementVersion: RequirementVersionSummary | null;
	currentJobVersion: JobVersionSummary | null;
	stats: WorkbenchStats;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Filter Types
// =============================================================================

/**
 * Status counts for filter UI.
 * Displays the count of workbenches in each status category.
 */
export interface WorkbenchStatusCounts {
	all: number;
	active: number;
	draft: number;
	archived: number;
}

/**
 * Valid values for workbench status filter.
 * 'all' shows all workbenches regardless of status.
 */
export type WorkbenchStatusFilter = 'all' | WorkbenchStatus;

// =============================================================================
// Form/Input Types
// =============================================================================

/**
 * Input data for creating a new workbench.
 * Used by the CreateWorkbenchModal component.
 */
export interface CreateWorkbenchInput {
	name: string;
	description?: string;
}
