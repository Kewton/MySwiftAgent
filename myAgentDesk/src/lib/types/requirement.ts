/**
 * Requirement Type Definitions
 * Issue #290: Requirements List and Version Management
 *
 * Type definitions for requirement version entities used in
 * list views, detail views, editing, and diff display.
 */

import type { RequirementVersionStatus } from '$lib/server/db/schema';

// =============================================================================
// List View Types
// =============================================================================

/**
 * Requirement version data for list views.
 * Includes basic info and status for display in version list.
 */
export interface RequirementVersionListItem {
	id: string;
	version: number;
	status: RequirementVersionStatus;
	changeSummary: string | null;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Detail View Types
// =============================================================================

/**
 * Complete requirement version data for detail views.
 * Includes full content and metadata.
 */
export interface RequirementVersionDetail {
	id: string;
	workbenchId: string;
	version: number;
	content: string;
	status: RequirementVersionStatus;
	changeSummary: string | null;
	createdAt: Date;
	updatedAt: Date;
}

// =============================================================================
// Diff Types
// =============================================================================

/**
 * Diff operation type.
 * -1: deletion, 0: equal, 1: insertion
 */
export type DiffOperation = -1 | 0 | 1;

/**
 * Single diff entry representing a text change.
 */
export interface DiffEntry {
	operation: DiffOperation;
	text: string;
}

/**
 * Result of comparing two requirement versions.
 */
export interface RequirementDiff {
	fromVersion: number;
	toVersion: number;
	diffs: DiffEntry[];
}

// =============================================================================
// Form/Input Types
// =============================================================================

/**
 * Input data for creating a new requirement version.
 */
export interface CreateRequirementVersionInput {
	content: string;
	changeSummary?: string;
}

/**
 * Input data for updating a requirement version.
 */
export interface UpdateRequirementVersionInput {
	content?: string;
	changeSummary?: string;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Status display configuration.
 */
export const REQUIREMENT_STATUS_CONFIG: Record<
	RequirementVersionStatus,
	{ label: string; color: string; bgColor: string }
> = {
	draft: { label: 'Draft', color: '#92400e', bgColor: '#fef3c7' },
	submitted: { label: 'Submitted', color: '#1e40af', bgColor: '#dbeafe' },
	active: { label: 'Active', color: '#166534', bgColor: '#dcfce7' },
	deprecated: { label: 'Deprecated', color: '#64748b', bgColor: '#f1f5f9' }
};
