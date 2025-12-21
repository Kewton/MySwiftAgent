/**
 * JobVersionRepository
 * Issue #291: Generate Page (Job Generation)
 *
 * Repository class for job version database operations.
 * Handles CRUD operations and version management for job versions.
 * Version format: vN.M where N = majorVersion (from RequirementVersion.version)
 * and M = minorVersion (sequential within same majorVersion).
 */

import { eq, desc, and, max } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import { jobVersion, type JobVersion, type JobVersionStatus } from '$lib/server/db/schema';

// Re-export types for external use
export type { JobVersion, JobVersionStatus };

/**
 * Input data for creating a new job version.
 */
export interface CreateJobVersionInput {
	workbenchId: string;
	sourceRequirementVersionId: string;
	majorVersion: number;
	minorVersion: number;
}

/**
 * Input data for updating generation result.
 * Issue #305: Added externalJobId for proper separation of job_id and langfuse_trace_id
 */
export interface UpdateGenerationResultInput {
	status: JobVersionStatus;
	taskBreakdown?: string;
	interfaceDefinitions?: string;
	workflows?: string;
	externalJobMasterId?: string;
	externalJobId?: string; // ExpertAgent job_id for polling
	externalTraceId?: string; // Langfuse trace_id for observability link
	errorMessage?: string;
}

/**
 * Repository for job version database operations.
 */
export class JobVersionRepository {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	constructor(private db: BetterSQLite3Database<any>) {}

	/**
	 * Find a job version by ID.
	 *
	 * @param id - The job version ID
	 * @returns Job version or null if not found
	 */
	async findById(id: string): Promise<JobVersion | null> {
		const results = await this.db.select().from(jobVersion).where(eq(jobVersion.id, id)).limit(1);

		return results[0] ?? null;
	}

	/**
	 * Find all job versions for a workbench.
	 * Ordered by version descending (majorVersion, then minorVersion).
	 *
	 * @param workbenchId - The workbench ID to filter by
	 * @returns Array of job versions
	 */
	async findByWorkbenchId(workbenchId: string): Promise<JobVersion[]> {
		const results = await this.db
			.select()
			.from(jobVersion)
			.where(eq(jobVersion.workbenchId, workbenchId))
			.orderBy(desc(jobVersion.majorVersion), desc(jobVersion.minorVersion));

		return results;
	}

	/**
	 * Find job versions with 'generating' status for a workbench.
	 *
	 * @param workbenchId - The workbench ID to filter by
	 * @returns Array of job versions currently generating
	 */
	async findGenerating(workbenchId: string): Promise<JobVersion[]> {
		const results = await this.db
			.select()
			.from(jobVersion)
			.where(and(eq(jobVersion.workbenchId, workbenchId), eq(jobVersion.status, 'generating')))
			.orderBy(desc(jobVersion.createdAt));

		return results;
	}

	/**
	 * Create a new job version with 'generating' status.
	 * Version label is automatically formatted as vN.M.
	 *
	 * @param input - Creation input data
	 * @returns The created job version
	 */
	async create(input: CreateJobVersionInput): Promise<JobVersion> {
		const now = new Date();
		const id = `jv_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
		const versionLabel = `v${input.majorVersion}.${input.minorVersion}`;

		const newJobVersion: JobVersion = {
			id,
			workbenchId: input.workbenchId,
			sourceRequirementVersionId: input.sourceRequirementVersionId,
			majorVersion: input.majorVersion,
			minorVersion: input.minorVersion,
			versionLabel,
			status: 'generating',
			taskBreakdown: null,
			interfaceDefinitions: null,
			workflows: null,
			externalJobMasterId: null,
			externalJobId: null, // Issue #305: For ExpertAgent polling
			externalTraceId: null, // Issue #305: For Langfuse trace link
			errorMessage: null,
			generatedAt: null,
			createdAt: now,
			updatedAt: now
		};

		await this.db.insert(jobVersion).values(newJobVersion);

		return newJobVersion;
	}

	/**
	 * Update the status of a job version.
	 *
	 * @param id - The job version ID
	 * @param status - The new status
	 * @returns Updated job version or null if not found
	 */
	async updateStatus(id: string, status: JobVersionStatus): Promise<JobVersion | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		await this.db
			.update(jobVersion)
			.set({ status, updatedAt: new Date() })
			.where(eq(jobVersion.id, id));

		return this.findById(id);
	}

	/**
	 * Update the generation result of a job version.
	 * Used when job generation completes (success or failure).
	 *
	 * @param id - The job version ID
	 * @param input - Update input data
	 * @returns Updated job version or null if not found
	 */
	async updateGenerationResult(
		id: string,
		input: UpdateGenerationResultInput
	): Promise<JobVersion | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		const updateData: Partial<JobVersion> = {
			status: input.status,
			updatedAt: new Date()
		};

		if (input.taskBreakdown !== undefined) {
			updateData.taskBreakdown = input.taskBreakdown;
		}
		if (input.interfaceDefinitions !== undefined) {
			updateData.interfaceDefinitions = input.interfaceDefinitions;
		}
		if (input.workflows !== undefined) {
			updateData.workflows = input.workflows;
		}
		if (input.externalJobMasterId !== undefined) {
			updateData.externalJobMasterId = input.externalJobMasterId;
		}
		if (input.externalJobId !== undefined) {
			updateData.externalJobId = input.externalJobId;
		}
		if (input.externalTraceId !== undefined) {
			updateData.externalTraceId = input.externalTraceId;
		}
		if (input.errorMessage !== undefined) {
			updateData.errorMessage = input.errorMessage;
		}

		// Set generatedAt timestamp on success
		if (input.status === 'success') {
			updateData.generatedAt = new Date();
		}

		await this.db.update(jobVersion).set(updateData).where(eq(jobVersion.id, id));

		return this.findById(id);
	}

	/**
	 * Get the next minor version number for a given major version.
	 *
	 * @param workbenchId - The workbench ID
	 * @param majorVersion - The major version number
	 * @returns Next minor version number (1 if no versions exist for that major version)
	 */
	async getNextVersion(workbenchId: string, majorVersion: number): Promise<number> {
		const result = await this.db
			.select({ maxMinorVersion: max(jobVersion.minorVersion) })
			.from(jobVersion)
			.where(
				and(eq(jobVersion.workbenchId, workbenchId), eq(jobVersion.majorVersion, majorVersion))
			);

		const maxMinorVersion = result[0]?.maxMinorVersion ?? 0;
		return maxMinorVersion + 1;
	}
}

// Singleton instance for production use
import { db } from '$lib/server/db';

/** Default repository instance using the production database */
export const jobVersionRepository = new JobVersionRepository(db);
