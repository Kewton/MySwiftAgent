/**
 * Project Types
 * Issue #288: Project screens implementation
 *
 * Type definitions for project-related data.
 */
import type { Run, Schedule, Workbench, Project } from '$lib/server/db/schema';

/**
 * Project statistics for dashboard display
 */
export interface ProjectStats {
	workbenchCount: number;
	recentRunCount: number;
	activeScheduleCount: number;
}

/**
 * Project with statistics for detail view
 */
export interface ProjectWithStats {
	project: Project;
	stats: ProjectStats;
}

/**
 * Project list item with workbench count
 */
export interface ProjectListItem extends Project {
	workbenchCount: number;
}

/**
 * Run with workbench info for display in project detail
 */
export interface RunWithWorkbench extends Run {
	workbench: Pick<Workbench, 'id' | 'name'>;
}

/**
 * Schedule with workbench info for display in project detail
 */
export interface ScheduleWithWorkbench extends Schedule {
	workbench: Pick<Workbench, 'id' | 'name'>;
}

/**
 * Input for creating a new project
 */
export interface CreateProjectInput {
	name: string;
	description?: string;
}

/**
 * Input for updating a project
 */
export interface UpdateProjectInput {
	name?: string;
	description?: string;
}

/**
 * Vault secret display item
 */
export interface VaultSecretItem {
	key: string;
	project: string;
	description?: string;
	isConnected: boolean;
	lastTestedAt?: Date;
}

/**
 * Vault connection status
 */
export type VaultConnectionStatus = 'connected' | 'disconnected' | 'testing' | 'error';

/**
 * Project page data from server load
 */
export interface ProjectPageData {
	project: Project;
	stats: ProjectStats;
	recentRuns: RunWithWorkbench[];
	recentSchedules: ScheduleWithWorkbench[];
}

/**
 * Projects list page data from server load
 */
export interface ProjectsListPageData {
	projects: ProjectListItem[];
}

/**
 * Vault page data from server load
 */
export interface VaultPageData {
	project: Project;
	secrets: VaultSecretItem[];
	connectionStatus: VaultConnectionStatus;
}
