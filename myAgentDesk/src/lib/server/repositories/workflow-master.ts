/**
 * WorkflowMasterRepository
 * Issue #305: Workflow Generation Progress Display
 *
 * Repository class for workflow master database operations.
 * Handles CRUD operations for workflow masters that store
 * generated GraphAI workflow YAML for each task.
 */

import { eq, desc } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import {
	workflowMasters,
	type WorkflowMaster,
	type WorkflowMasterStatus
} from '$lib/server/db/schema';

// Re-export types for external use
export type { WorkflowMaster, WorkflowMasterStatus };

/**
 * Input data for creating a new workflow master.
 */
export interface CreateWorkflowMasterInput {
	taskMasterId: string;
	jobVersionId?: string;
	workflowName: string;
	yamlContent: string;
}

/**
 * Input data for updating generation result.
 */
export interface UpdateWorkflowMasterResultInput {
	status: WorkflowMasterStatus;
	yamlContent?: string;
	generationTimeMs?: number;
	errorMessage?: string;
	langfuseTraceId?: string;
}

/**
 * Repository for workflow master database operations.
 */
export class WorkflowMasterRepository {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	constructor(private db: BetterSQLite3Database<any>) {}

	/**
	 * Find a workflow master by ID.
	 *
	 * @param id - The workflow master ID
	 * @returns Workflow master or null if not found
	 */
	async findById(id: string): Promise<WorkflowMaster | null> {
		const results = await this.db
			.select()
			.from(workflowMasters)
			.where(eq(workflowMasters.id, id))
			.limit(1);

		return results[0] ?? null;
	}

	/**
	 * Find a workflow master by task master ID.
	 *
	 * @param taskMasterId - The task master ID
	 * @returns Workflow master or null if not found
	 */
	async findByTaskMasterId(taskMasterId: string): Promise<WorkflowMaster | null> {
		const results = await this.db
			.select()
			.from(workflowMasters)
			.where(eq(workflowMasters.taskMasterId, taskMasterId))
			.limit(1);

		return results[0] ?? null;
	}

	/**
	 * Find all workflow masters for a job version.
	 * Ordered by created at descending.
	 *
	 * @param jobVersionId - The job version ID to filter by
	 * @returns Array of workflow masters
	 */
	async findByJobVersionId(jobVersionId: string): Promise<WorkflowMaster[]> {
		const results = await this.db
			.select()
			.from(workflowMasters)
			.where(eq(workflowMasters.jobVersionId, jobVersionId))
			.orderBy(desc(workflowMasters.createdAt));

		return results;
	}

	/**
	 * Create a new workflow master with 'pending' status.
	 *
	 * @param input - Creation input data
	 * @returns The created workflow master
	 */
	async create(input: CreateWorkflowMasterInput): Promise<WorkflowMaster> {
		const now = new Date();
		const id = `wm_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

		const newWorkflowMaster: WorkflowMaster = {
			id,
			taskMasterId: input.taskMasterId,
			jobVersionId: input.jobVersionId ?? null,
			workflowName: input.workflowName,
			yamlContent: input.yamlContent,
			status: 'pending',
			generationTimeMs: null,
			errorMessage: null,
			langfuseTraceId: null,
			createdAt: now,
			updatedAt: now
		};

		await this.db.insert(workflowMasters).values(newWorkflowMaster);

		return newWorkflowMaster;
	}

	/**
	 * Create multiple workflow masters at once.
	 *
	 * @param inputs - Array of creation inputs
	 * @returns Array of created workflow masters
	 */
	async bulkCreate(inputs: CreateWorkflowMasterInput[]): Promise<WorkflowMaster[]> {
		const now = new Date();
		const newWorkflowMasters: WorkflowMaster[] = inputs.map((input, index) => ({
			id: `wm_${Date.now()}_${index}_${Math.random().toString(36).substring(2, 9)}`,
			taskMasterId: input.taskMasterId,
			jobVersionId: input.jobVersionId ?? null,
			workflowName: input.workflowName,
			yamlContent: input.yamlContent,
			status: 'pending' as const,
			generationTimeMs: null,
			errorMessage: null,
			langfuseTraceId: null,
			createdAt: now,
			updatedAt: now
		}));

		await this.db.insert(workflowMasters).values(newWorkflowMasters);

		return newWorkflowMasters;
	}

	/**
	 * Update the status of a workflow master.
	 *
	 * @param id - The workflow master ID
	 * @param status - The new status
	 * @returns Updated workflow master or null if not found
	 */
	async updateStatus(id: string, status: WorkflowMasterStatus): Promise<WorkflowMaster | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		await this.db
			.update(workflowMasters)
			.set({ status, updatedAt: new Date() })
			.where(eq(workflowMasters.id, id));

		return this.findById(id);
	}

	/**
	 * Update the generation result of a workflow master.
	 * Used when workflow generation completes (success or failure).
	 *
	 * @param id - The workflow master ID
	 * @param input - Update input data
	 * @returns Updated workflow master or null if not found
	 */
	async updateGenerationResult(
		id: string,
		input: UpdateWorkflowMasterResultInput
	): Promise<WorkflowMaster | null> {
		const existing = await this.findById(id);
		if (!existing) return null;

		const updateData: Partial<WorkflowMaster> = {
			status: input.status,
			updatedAt: new Date()
		};

		if (input.yamlContent !== undefined) {
			updateData.yamlContent = input.yamlContent;
		}
		if (input.generationTimeMs !== undefined) {
			updateData.generationTimeMs = input.generationTimeMs;
		}
		if (input.errorMessage !== undefined) {
			updateData.errorMessage = input.errorMessage;
		}
		if (input.langfuseTraceId !== undefined) {
			updateData.langfuseTraceId = input.langfuseTraceId;
		}

		await this.db.update(workflowMasters).set(updateData).where(eq(workflowMasters.id, id));

		return this.findById(id);
	}
}

// Singleton instance for production use
import { db } from '$lib/server/db';

/** Default repository instance using the production database */
export const workflowMasterRepository = new WorkflowMasterRepository(db);
