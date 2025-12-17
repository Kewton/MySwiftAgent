/**
 * RequirementVersionRepository
 * Issue #290: Requirements List and Version Management
 *
 * Repository class for requirement version database operations.
 * Handles CRUD operations, version management, and diff computation.
 */

import { eq, desc, and, max } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import { requirementVersion, type RequirementVersion } from '$lib/server/db/schema';
import type {
	RequirementVersionListItem,
	RequirementVersionDetail,
	CreateRequirementVersionInput,
	UpdateRequirementVersionInput,
	RequirementDiff,
	DiffEntry
} from '$lib/types/requirement';
import { diff_match_patch, type Diff } from 'diff-match-patch';

/**
 * Repository for requirement version database operations.
 */
export class RequirementVersionRepository {
	private dmp: InstanceType<typeof diff_match_patch>;

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	constructor(private db: BetterSQLite3Database<any>) {
		this.dmp = new diff_match_patch();
	}

	/**
	 * Map a database result to RequirementVersionDetail.
	 * Extracts common mapping logic used by findById and findByWorkbenchAndVersion.
	 *
	 * @param row - Raw database row
	 * @returns Mapped RequirementVersionDetail
	 */
	private mapToDetail(row: RequirementVersion): RequirementVersionDetail {
		return {
			id: row.id,
			workbenchId: row.workbenchId,
			version: row.version,
			content: row.content,
			status: row.status as RequirementVersionDetail['status'],
			changeSummary: row.changeSummary,
			createdAt: row.createdAt,
			updatedAt: row.updatedAt
		};
	}

	/**
	 * Find all requirement versions for a workbench.
	 * Ordered by version descending (newest first).
	 *
	 * @param workbenchId - The workbench ID to filter by
	 * @returns Array of requirement versions
	 */
	async findByWorkbenchId(workbenchId: string): Promise<RequirementVersionListItem[]> {
		const results = await this.db
			.select({
				id: requirementVersion.id,
				version: requirementVersion.version,
				status: requirementVersion.status,
				changeSummary: requirementVersion.changeSummary,
				createdAt: requirementVersion.createdAt,
				updatedAt: requirementVersion.updatedAt
			})
			.from(requirementVersion)
			.where(eq(requirementVersion.workbenchId, workbenchId))
			.orderBy(desc(requirementVersion.version));

		return results as RequirementVersionListItem[];
	}

	/**
	 * Find a requirement version by ID.
	 *
	 * @param id - The requirement version ID
	 * @returns Requirement version detail or null if not found
	 */
	async findById(id: string): Promise<RequirementVersionDetail | null> {
		const results = await this.db
			.select()
			.from(requirementVersion)
			.where(eq(requirementVersion.id, id))
			.limit(1);

		const row = results[0];
		return row ? this.mapToDetail(row) : null;
	}

	/**
	 * Find a requirement version by workbench ID and version number.
	 *
	 * @param workbenchId - The workbench ID
	 * @param version - The version number
	 * @returns Requirement version detail or null if not found
	 */
	async findByWorkbenchAndVersion(
		workbenchId: string,
		version: number
	): Promise<RequirementVersionDetail | null> {
		const results = await this.db
			.select()
			.from(requirementVersion)
			.where(
				and(
					eq(requirementVersion.workbenchId, workbenchId),
					eq(requirementVersion.version, version)
				)
			)
			.limit(1);

		const row = results[0];
		return row ? this.mapToDetail(row) : null;
	}

	/**
	 * Create a new requirement version.
	 * Automatically assigns the next version number.
	 *
	 * @param workbenchId - The workbench ID
	 * @param input - Creation input data
	 * @returns The created requirement version
	 */
	async create(
		workbenchId: string,
		input: CreateRequirementVersionInput
	): Promise<RequirementVersion> {
		const now = new Date();
		const id = `rv_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
		const nextVersion = await this.getNextVersion(workbenchId);

		const newVersion = {
			id,
			workbenchId,
			version: nextVersion,
			content: input.content,
			status: 'draft' as const,
			changeSummary: input.changeSummary ?? null,
			createdAt: now,
			updatedAt: now
		};

		await this.db.insert(requirementVersion).values(newVersion);

		return newVersion;
	}

	/**
	 * Update a requirement version.
	 *
	 * @param id - The requirement version ID
	 * @param input - Update input data
	 * @returns Updated requirement version or null if not found
	 */
	async update(
		id: string,
		input: UpdateRequirementVersionInput
	): Promise<RequirementVersionDetail | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		const updateData: Partial<RequirementVersion> = {
			updatedAt: new Date()
		};

		if (input.content !== undefined) {
			updateData.content = input.content;
		}
		if (input.changeSummary !== undefined) {
			updateData.changeSummary = input.changeSummary;
		}

		await this.db.update(requirementVersion).set(updateData).where(eq(requirementVersion.id, id));

		return this.findById(id);
	}

	/**
	 * Set a requirement version as active and deprecate the previous active version.
	 *
	 * @param workbenchId - The workbench ID
	 * @param versionId - The version ID to set as active
	 * @returns Updated requirement version or null if not found/invalid
	 */
	async setActive(
		workbenchId: string,
		versionId: string
	): Promise<RequirementVersionDetail | null> {
		// Verify the version exists and belongs to the workbench
		const version = await this.findById(versionId);
		if (!version || version.workbenchId !== workbenchId) {
			return null;
		}

		// Find and deprecate the current active version
		const activeVersions = await this.db
			.select()
			.from(requirementVersion)
			.where(
				and(
					eq(requirementVersion.workbenchId, workbenchId),
					eq(requirementVersion.status, 'active')
				)
			);

		for (const active of activeVersions) {
			if (active.id !== versionId) {
				await this.db
					.update(requirementVersion)
					.set({ status: 'deprecated', updatedAt: new Date() })
					.where(eq(requirementVersion.id, active.id));
			}
		}

		// Set the new version as active
		await this.db
			.update(requirementVersion)
			.set({ status: 'active', updatedAt: new Date() })
			.where(eq(requirementVersion.id, versionId));

		return this.findById(versionId);
	}

	/**
	 * Update the status of a requirement version.
	 *
	 * @param id - The requirement version ID
	 * @param status - The new status
	 * @returns Updated requirement version or null if not found
	 */
	async updateStatus(
		id: string,
		status: 'draft' | 'submitted' | 'active' | 'deprecated'
	): Promise<RequirementVersionDetail | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		await this.db
			.update(requirementVersion)
			.set({ status, updatedAt: new Date() })
			.where(eq(requirementVersion.id, id));

		return this.findById(id);
	}

	/**
	 * Get the next version number for a workbench.
	 *
	 * @param workbenchId - The workbench ID
	 * @returns Next version number (1 if no versions exist)
	 */
	async getNextVersion(workbenchId: string): Promise<number> {
		const result = await this.db
			.select({ maxVersion: max(requirementVersion.version) })
			.from(requirementVersion)
			.where(eq(requirementVersion.workbenchId, workbenchId));

		const maxVersion = result[0]?.maxVersion ?? 0;
		return maxVersion + 1;
	}

	/**
	 * Compute diff between two requirement versions.
	 *
	 * @param fromId - The source version ID
	 * @param toId - The target version ID
	 * @returns Diff result or null if versions not found
	 */
	async computeDiff(fromId: string, toId: string): Promise<RequirementDiff | null> {
		const fromVersion = await this.findById(fromId);
		const toVersion = await this.findById(toId);

		if (!fromVersion || !toVersion) {
			return null;
		}

		const diffs = this.dmp.diff_main(fromVersion.content, toVersion.content);
		this.dmp.diff_cleanupSemantic(diffs);

		const diffEntries: DiffEntry[] = diffs.map((diff: Diff) => ({
			operation: diff[0] as -1 | 0 | 1,
			text: diff[1]
		}));

		return {
			fromVersion: fromVersion.version,
			toVersion: toVersion.version,
			diffs: diffEntries
		};
	}
}

// Singleton instance for production use
import { db } from '$lib/server/db';

/** Default repository instance using the production database */
export const requirementVersionRepository = new RequirementVersionRepository(db);
