/**
 * WorkbenchRepository
 * Issue #289: Workbench List/Detail Screens
 *
 * Repository class for workbench database operations.
 * Implements N+1 query optimization using subqueries and window functions.
 */

import { eq, desc, and, count, sql } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import {
	workbench,
	run,
	schedule,
	requirementVersion,
	jobVersion,
	type Workbench
} from '$lib/server/db/schema';
import type {
	WorkbenchListItem,
	WorkbenchDetail,
	WorkbenchStats,
	WorkbenchStatusCounts
} from '$lib/types/workbench';

/**
 * Repository for workbench database operations.
 * Handles complex queries with N+1 prevention.
 */
export class WorkbenchRepository {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	constructor(private db: BetterSQLite3Database<any>) {}

	/**
	 * Find a workbench by ID.
	 * Simple lookup without stats.
	 */
	async findById(workbenchId: string): Promise<Workbench | null> {
		const results = await this.db
			.select()
			.from(workbench)
			.where(eq(workbench.id, workbenchId))
			.limit(1);

		return results[0] ?? null;
	}

	/**
	 * Find all workbenches for a project with aggregated statistics.
	 * N+1 optimized: uses subqueries to fetch all data in a single query.
	 *
	 * @param projectId - The project ID to filter by
	 * @returns Array of workbenches with run/schedule statistics
	 */
	async findByProjectWithStats(projectId: string): Promise<WorkbenchListItem[]> {
		// Subquery for run counts per workbench
		const runCountSubquery = this.db
			.select({
				workbenchId: run.workbenchId,
				runCount: count(run.id).as('run_count')
			})
			.from(run)
			.groupBy(run.workbenchId)
			.as('run_stats');

		// Subquery for active schedule counts per workbench
		const scheduleCountSubquery = this.db
			.select({
				workbenchId: schedule.workbenchId,
				scheduleCount: count(schedule.id).as('schedule_count')
			})
			.from(schedule)
			.where(eq(schedule.isEnabled, true))
			.groupBy(schedule.workbenchId)
			.as('schedule_stats');

		// Subquery for latest run info using window function
		// ROW_NUMBER() OVER (PARTITION BY workbench_id ORDER BY created_at DESC)
		const latestRunSubquery = this.db
			.select({
				workbenchId: run.workbenchId,
				status: run.status,
				completedAt: run.completedAt,
				rowNum:
					sql<number>`ROW_NUMBER() OVER (PARTITION BY ${run.workbenchId} ORDER BY ${run.createdAt} DESC)`.as(
						'row_num'
					)
			})
			.from(run)
			.as('latest_run_ranked');

		// Filter to only get the latest run (row_num = 1)
		const latestRunFiltered = this.db
			.select({
				workbenchId: latestRunSubquery.workbenchId,
				lastRunStatus: latestRunSubquery.status,
				lastRunAt: latestRunSubquery.completedAt
			})
			.from(latestRunSubquery)
			.where(eq(latestRunSubquery.rowNum, 1))
			.as('latest_run');

		// Main query with all joins
		const results = await this.db
			.select({
				id: workbench.id,
				name: workbench.name,
				description: workbench.description,
				status: workbench.status,
				activeRequirementVersionId: workbench.activeRequirementVersionId,
				createdAt: workbench.createdAt,
				updatedAt: workbench.updatedAt,
				runCount: sql<number>`COALESCE(${runCountSubquery.runCount}, 0)`,
				scheduleCount: sql<number>`COALESCE(${scheduleCountSubquery.scheduleCount}, 0)`,
				lastRunAt: latestRunFiltered.lastRunAt,
				lastRunStatus: latestRunFiltered.lastRunStatus
			})
			.from(workbench)
			.leftJoin(runCountSubquery, eq(workbench.id, runCountSubquery.workbenchId))
			.leftJoin(scheduleCountSubquery, eq(workbench.id, scheduleCountSubquery.workbenchId))
			.leftJoin(latestRunFiltered, eq(workbench.id, latestRunFiltered.workbenchId))
			.where(eq(workbench.projectId, projectId))
			.orderBy(desc(workbench.updatedAt));

		return results as WorkbenchListItem[];
	}

	/**
	 * Find a workbench by ID with full detail including stats and related entities.
	 *
	 * @param workbenchId - The workbench ID to find
	 * @returns Workbench detail with stats or null if not found
	 */
	async findByIdWithDetail(workbenchId: string): Promise<WorkbenchDetail | null> {
		const results = await this.db
			.select()
			.from(workbench)
			.where(eq(workbench.id, workbenchId))
			.limit(1);

		const wb = results[0];
		if (!wb) return null;

		// Get active requirement version if exists
		let activeReq: { id: string; version: number; status: string } | null = null;
		if (wb.activeRequirementVersionId) {
			const reqResults = await this.db
				.select({
					id: requirementVersion.id,
					version: requirementVersion.version,
					status: requirementVersion.status
				})
				.from(requirementVersion)
				.where(eq(requirementVersion.id, wb.activeRequirementVersionId))
				.limit(1);
			activeReq = reqResults[0] ?? null;
		}

		// Get current active job version
		const jobResults = await this.db
			.select({
				id: jobVersion.id,
				versionLabel: jobVersion.versionLabel,
				status: jobVersion.status
			})
			.from(jobVersion)
			.where(and(eq(jobVersion.workbenchId, workbenchId), eq(jobVersion.status, 'active')))
			.orderBy(desc(jobVersion.createdAt))
			.limit(1);
		const currentJob = jobResults[0] ?? null;

		// Get statistics
		const stats = await this.getWorkbenchStats(workbenchId);

		return {
			id: wb.id,
			name: wb.name,
			description: wb.description,
			status: wb.status,
			projectId: wb.projectId,
			activeRequirementVersion: activeReq
				? {
						id: activeReq.id,
						version: activeReq.version,
						status: activeReq.status as 'draft' | 'submitted' | 'active' | 'deprecated'
					}
				: null,
			currentJobVersion: currentJob
				? {
						id: currentJob.id,
						versionLabel: currentJob.versionLabel,
						status: currentJob.status as
							| 'generating'
							| 'success'
							| 'failed'
							| 'active'
							| 'deprecated'
					}
				: null,
			stats,
			createdAt: wb.createdAt,
			updatedAt: wb.updatedAt
		};
	}

	/**
	 * Get statistical information for a workbench.
	 * Includes run counts, success rates, and schedule counts.
	 */
	private async getWorkbenchStats(workbenchId: string): Promise<WorkbenchStats> {
		// Run statistics
		const runStatsResults = await this.db
			.select({
				total: count(run.id),
				successful: sql<number>`SUM(CASE WHEN ${run.status} = 'success' THEN 1 ELSE 0 END)`,
				failed: sql<number>`SUM(CASE WHEN ${run.status} = 'failed' THEN 1 ELSE 0 END)`,
				pending: sql<number>`SUM(CASE WHEN ${run.status} IN ('queued', 'running') THEN 1 ELSE 0 END)`
			})
			.from(run)
			.where(eq(run.workbenchId, workbenchId));

		const runStats = runStatsResults[0];

		// Active schedule count
		const scheduleStatsResults = await this.db
			.select({
				active: count(schedule.id)
			})
			.from(schedule)
			.where(and(eq(schedule.workbenchId, workbenchId), eq(schedule.isEnabled, true)));

		const scheduleStats = scheduleStatsResults[0];

		// Last run timestamp
		const lastRunResults = await this.db
			.select({ completedAt: run.completedAt })
			.from(run)
			.where(eq(run.workbenchId, workbenchId))
			.orderBy(desc(run.completedAt))
			.limit(1);

		const lastRun = lastRunResults[0];

		const total = runStats?.total ?? 0;
		const successful = runStats?.successful ?? 0;

		return {
			totalRuns: total,
			successfulRuns: successful,
			failedRuns: runStats?.failed ?? 0,
			successRate: total > 0 ? Math.round((successful / total) * 100) : 0,
			lastRunAt: lastRun?.completedAt ?? null,
			activeSchedules: scheduleStats?.active ?? 0,
			pendingRuns: runStats?.pending ?? 0
		};
	}

	/**
	 * Get workbench counts grouped by status for a project.
	 * Used for filter UI badge counts.
	 *
	 * @param projectId - The project ID to count workbenches for
	 * @returns Status counts including 'all' total
	 */
	async getStatusCounts(projectId: string): Promise<WorkbenchStatusCounts> {
		const results = await this.db
			.select({
				status: workbench.status,
				count: count(workbench.id)
			})
			.from(workbench)
			.where(eq(workbench.projectId, projectId))
			.groupBy(workbench.status);

		const counts: WorkbenchStatusCounts = { all: 0, active: 0, draft: 0, archived: 0 };

		for (const r of results) {
			const status = r.status as keyof Omit<WorkbenchStatusCounts, 'all'>;
			counts[status] = r.count;
			counts.all += r.count;
		}

		return counts;
	}
}

// Singleton instance for production use
import { db } from '$lib/server/db';

/** Default repository instance using the production database */
export const workbenchRepository = new WorkbenchRepository(db);
