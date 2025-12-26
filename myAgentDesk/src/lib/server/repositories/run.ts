/**
 * RunRepository
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Repository class for run database operations.
 * Handles CRUD operations and status management for run executions.
 */

import { eq, desc, and, or, count } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import { run, jobVersion, workbench, type Run, type RunStatus } from '$lib/server/db/schema';
import { isTerminalStatus } from '$lib/types/run';

// Re-export types for external use
export type { Run, RunStatus };

/**
 * Input data for creating a new run.
 */
export interface CreateRunInput {
	workbenchId: string;
	jobVersionId: string;
	executionParams?: string;
}

/**
 * Input data for updating run result.
 */
export interface UpdateRunResultInput {
	status: RunStatus;
	externalJobId?: string;
	externalTraceId?: string;
	resultSummary?: string;
}

/**
 * Options for querying runs.
 */
export interface FindRunsOptions {
	limit?: number;
	offset?: number;
}

/**
 * Run with job version details.
 */
export interface RunWithJobVersion {
	run: Run;
	jobVersion: {
		id: string;
		versionLabel: string;
		majorVersion: number;
		minorVersion: number;
	};
}

/**
 * Repository for run database operations.
 */
export class RunRepository {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	constructor(private db: BetterSQLite3Database<any>) {}

	/**
	 * Find a run by ID.
	 *
	 * @param id - The run ID
	 * @returns Run or null if not found
	 */
	async findById(id: string): Promise<Run | null> {
		const results = await this.db.select().from(run).where(eq(run.id, id)).limit(1);

		return results[0] ?? null;
	}

	/**
	 * Find all runs for a workbench.
	 * Ordered by createdAt descending (newest first).
	 *
	 * @param workbenchId - The workbench ID to filter by
	 * @param options - Query options (limit, offset)
	 * @returns Array of runs
	 */
	async findByWorkbenchId(workbenchId: string, options: FindRunsOptions = {}): Promise<Run[]> {
		let query = this.db
			.select()
			.from(run)
			.where(eq(run.workbenchId, workbenchId))
			.orderBy(desc(run.createdAt));

		// SQLite requires LIMIT when using OFFSET
		if (options.limit !== undefined || options.offset !== undefined) {
			const limit = options.limit ?? 1000; // Default large limit if only offset is specified
			query = query.limit(limit) as typeof query;
		}
		if (options.offset !== undefined) {
			query = query.offset(options.offset) as typeof query;
		}

		const results = await query;
		return results;
	}

	/**
	 * Find runs with active (non-terminal) status for a workbench.
	 *
	 * @param workbenchId - The workbench ID to filter by
	 * @returns Array of active runs
	 */
	async findActiveRuns(workbenchId: string): Promise<Run[]> {
		const results = await this.db
			.select()
			.from(run)
			.where(
				and(
					eq(run.workbenchId, workbenchId),
					or(eq(run.status, 'queued'), eq(run.status, 'running'))
				)
			)
			.orderBy(desc(run.createdAt));

		return results;
	}

	/**
	 * Create a new run with 'queued' status.
	 *
	 * @param input - Creation input data
	 * @returns The created run
	 */
	async create(input: CreateRunInput): Promise<Run> {
		const now = new Date();
		const id = `run_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

		const newRun: Run = {
			id,
			workbenchId: input.workbenchId,
			jobVersionId: input.jobVersionId,
			status: 'queued',
			externalJobId: null,
			externalTraceId: null,
			executionParams: input.executionParams ?? null,
			resultSummary: null,
			startedAt: null,
			completedAt: null,
			createdAt: now,
			updatedAt: now
		};

		await this.db.insert(run).values(newRun);

		return newRun;
	}

	/**
	 * Update the status of a run.
	 * Automatically sets startedAt when transitioning to 'running'
	 * and completedAt when transitioning to a terminal status.
	 *
	 * @param id - The run ID
	 * @param status - The new status
	 * @returns Updated run or null if not found
	 */
	async updateStatus(id: string, status: RunStatus): Promise<Run | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		const now = new Date();
		const updateData: Partial<Run> = {
			status,
			updatedAt: now
		};

		// Set startedAt when transitioning to running
		if (status === 'running' && !existing.startedAt) {
			updateData.startedAt = now;
		}

		// Set completedAt when transitioning to terminal status
		if (isTerminalStatus(status) && !existing.completedAt) {
			updateData.completedAt = now;
		}

		await this.db.update(run).set(updateData).where(eq(run.id, id));

		return this.findById(id);
	}

	/**
	 * Update the result of a run.
	 * Used when run completes (success or failure).
	 *
	 * @param id - The run ID
	 * @param input - Update input data
	 * @returns Updated run or null if not found
	 */
	async updateResult(id: string, input: UpdateRunResultInput): Promise<Run | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		const now = new Date();
		const updateData: Partial<Run> = {
			status: input.status,
			updatedAt: now
		};

		if (input.externalJobId !== undefined) {
			updateData.externalJobId = input.externalJobId;
		}
		if (input.externalTraceId !== undefined) {
			updateData.externalTraceId = input.externalTraceId;
		}
		if (input.resultSummary !== undefined) {
			updateData.resultSummary = input.resultSummary;
		}

		// Set completedAt when transitioning to terminal status
		if (isTerminalStatus(input.status) && !existing.completedAt) {
			updateData.completedAt = now;
		}

		await this.db.update(run).set(updateData).where(eq(run.id, id));

		return this.findById(id);
	}

	/**
	 * Get a run with its job version details.
	 *
	 * @param id - The run ID
	 * @returns Run with job version or null if not found
	 */
	async getRunWithJobVersion(id: string): Promise<RunWithJobVersion | null> {
		const results = await this.db
			.select({
				run: run,
				jobVersion: {
					id: jobVersion.id,
					versionLabel: jobVersion.versionLabel,
					majorVersion: jobVersion.majorVersion,
					minorVersion: jobVersion.minorVersion
				}
			})
			.from(run)
			.innerJoin(jobVersion, eq(run.jobVersionId, jobVersion.id))
			.where(eq(run.id, id))
			.limit(1);

		return results[0] ?? null;
	}

	/**
	 * Count total runs for a workbench.
	 *
	 * @param workbenchId - The workbench ID
	 * @returns Number of runs
	 */
	async countByWorkbenchId(workbenchId: string): Promise<number> {
		const result = await this.db
			.select({ count: count() })
			.from(run)
			.where(eq(run.workbenchId, workbenchId));

		return result[0]?.count ?? 0;
	}

	/**
	 * Get recent runs across all workbenches in a project.
	 *
	 * @param projectId - The project ID
	 * @param limit - Maximum number of runs to return
	 * @returns Array of runs with job version info
	 */
	async getRecentRuns(projectId: string, limit: number): Promise<RunWithJobVersion[]> {
		const results = await this.db
			.select({
				run: run,
				jobVersion: {
					id: jobVersion.id,
					versionLabel: jobVersion.versionLabel,
					majorVersion: jobVersion.majorVersion,
					minorVersion: jobVersion.minorVersion
				}
			})
			.from(run)
			.innerJoin(jobVersion, eq(run.jobVersionId, jobVersion.id))
			.innerJoin(workbench, eq(run.workbenchId, workbench.id))
			.where(eq(workbench.projectId, projectId))
			.orderBy(desc(run.createdAt))
			.limit(limit);

		return results;
	}
}

// Singleton instance for production use
import { db } from '$lib/server/db';

/** Default repository instance using the production database */
export const runRepository = new RunRepository(db);
