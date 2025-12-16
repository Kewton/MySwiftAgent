/**
 * Project Repository
 * Issue #288: Project screens implementation
 *
 * Repository layer for Project entity CRUD operations
 * and statistics queries.
 */
import { eq, desc, and, gte } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from '../db/schema';
import type { Project, NewProject, Run, Schedule, Workbench } from '../db/schema';

/**
 * Project with statistics
 */
export interface ProjectWithStats {
	project: Project;
	stats: ProjectStats;
}

/**
 * Project statistics
 */
export interface ProjectStats {
	workbenchCount: number;
	recentRunCount: number;
	activeScheduleCount: number;
}

/**
 * Project list item with workbench count
 */
export interface ProjectListItem extends Project {
	workbenchCount: number;
}

/**
 * Run with workbench info for display
 */
export interface RunWithWorkbench extends Run {
	workbench: Pick<Workbench, 'id' | 'name'>;
}

/**
 * Schedule with workbench info for display
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
 * Generates a unique ID with a prefix
 */
function generateId(prefix: string): string {
	const timestamp = Date.now().toString(36);
	const random = Math.random().toString(36).substring(2, 8);
	return `${prefix}_${timestamp}${random}`;
}

/**
 * Project repository for database operations
 */
export class ProjectRepository {
	constructor(private db: BetterSQLite3Database<typeof schema>) {}

	/**
	 * Find all projects ordered by updatedAt desc
	 */
	async findAll(): Promise<Project[]> {
		const projects = await this.db
			.select()
			.from(schema.project)
			.orderBy(desc(schema.project.updatedAt));

		return projects;
	}

	/**
	 * Find all projects with workbench count
	 */
	async findAllWithStats(): Promise<ProjectListItem[]> {
		const projects = await this.db
			.select()
			.from(schema.project)
			.orderBy(desc(schema.project.updatedAt));

		const result: ProjectListItem[] = [];

		for (const project of projects) {
			const workbenches = await this.db
				.select()
				.from(schema.workbench)
				.where(eq(schema.workbench.projectId, project.id));

			result.push({
				...project,
				workbenchCount: workbenches.length
			});
		}

		return result;
	}

	/**
	 * Find a project by ID
	 */
	async findById(id: string): Promise<Project | null> {
		const projects = await this.db
			.select()
			.from(schema.project)
			.where(eq(schema.project.id, id))
			.limit(1);

		return projects.length > 0 ? projects[0] : null;
	}

	/**
	 * Find a project by ID with statistics
	 */
	async findByIdWithStats(id: string): Promise<ProjectWithStats | null> {
		const project = await this.findById(id);

		if (!project) {
			return null;
		}

		const stats = await this.getProjectStats(id);

		return {
			project,
			stats
		};
	}

	/**
	 * Get statistics for a project
	 */
	async getProjectStats(projectId: string): Promise<ProjectStats> {
		// Get workbench count
		const workbenches = await this.db
			.select()
			.from(schema.workbench)
			.where(eq(schema.workbench.projectId, projectId));

		const workbenchIds = workbenches.map((w) => w.id);

		if (workbenchIds.length === 0) {
			return {
				workbenchCount: 0,
				recentRunCount: 0,
				activeScheduleCount: 0
			};
		}

		// Get recent run count (last 7 days)
		const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
		let recentRunCount = 0;

		for (const wbId of workbenchIds) {
			const runs = await this.db
				.select()
				.from(schema.run)
				.where(and(eq(schema.run.workbenchId, wbId), gte(schema.run.createdAt, sevenDaysAgo)));
			recentRunCount += runs.length;
		}

		// Get active schedule count
		let activeScheduleCount = 0;

		for (const wbId of workbenchIds) {
			const schedules = await this.db
				.select()
				.from(schema.schedule)
				.where(and(eq(schema.schedule.workbenchId, wbId), eq(schema.schedule.isEnabled, true)));
			activeScheduleCount += schedules.length;
		}

		return {
			workbenchCount: workbenches.length,
			recentRunCount,
			activeScheduleCount
		};
	}

	/**
	 * Get recent runs for a project
	 */
	async getRecentRuns(projectId: string, limit: number): Promise<RunWithWorkbench[]> {
		const workbenches = await this.db
			.select()
			.from(schema.workbench)
			.where(eq(schema.workbench.projectId, projectId));

		if (workbenches.length === 0) {
			return [];
		}

		const workbenchMap = new Map(workbenches.map((w) => [w.id, { id: w.id, name: w.name }]));
		const allRuns: RunWithWorkbench[] = [];

		for (const wb of workbenches) {
			const runs = await this.db
				.select()
				.from(schema.run)
				.where(eq(schema.run.workbenchId, wb.id))
				.orderBy(desc(schema.run.createdAt));

			for (const run of runs) {
				allRuns.push({
					...run,
					workbench: workbenchMap.get(run.workbenchId)!
				});
			}
		}

		// Sort by createdAt desc and limit
		return allRuns
			.sort((a, b) => (b.createdAt?.getTime() ?? 0) - (a.createdAt?.getTime() ?? 0))
			.slice(0, limit);
	}

	/**
	 * Get recent schedules for a project
	 */
	async getRecentSchedules(projectId: string, limit: number): Promise<ScheduleWithWorkbench[]> {
		const workbenches = await this.db
			.select()
			.from(schema.workbench)
			.where(eq(schema.workbench.projectId, projectId));

		if (workbenches.length === 0) {
			return [];
		}

		const workbenchMap = new Map(workbenches.map((w) => [w.id, { id: w.id, name: w.name }]));
		const allSchedules: ScheduleWithWorkbench[] = [];

		for (const wb of workbenches) {
			const schedules = await this.db
				.select()
				.from(schema.schedule)
				.where(eq(schema.schedule.workbenchId, wb.id))
				.orderBy(desc(schema.schedule.createdAt));

			for (const schedule of schedules) {
				allSchedules.push({
					...schedule,
					workbench: workbenchMap.get(schedule.workbenchId)!
				});
			}
		}

		// Sort by createdAt desc and limit
		return allSchedules
			.sort((a, b) => (b.createdAt?.getTime() ?? 0) - (a.createdAt?.getTime() ?? 0))
			.slice(0, limit);
	}

	/**
	 * Create a new project
	 */
	async create(input: CreateProjectInput): Promise<Project> {
		const now = new Date();
		const id = generateId('proj');
		const externalProjectId = generateId('ext');

		const newProject: NewProject = {
			id,
			externalProjectId,
			name: input.name,
			description: input.description,
			createdAt: now,
			updatedAt: now
		};

		await this.db.insert(schema.project).values(newProject);

		const project = await this.findById(id);
		return project!;
	}

	/**
	 * Update a project
	 */
	async update(id: string, input: UpdateProjectInput): Promise<Project | null> {
		const existing = await this.findById(id);

		if (!existing) {
			return null;
		}

		const updates: Partial<NewProject> = {
			updatedAt: new Date()
		};

		if (input.name !== undefined) {
			updates.name = input.name;
		}

		if (input.description !== undefined) {
			updates.description = input.description;
		}

		await this.db.update(schema.project).set(updates).where(eq(schema.project.id, id));

		return this.findById(id);
	}

	/**
	 * Delete a project
	 */
	async delete(id: string): Promise<boolean> {
		const existing = await this.findById(id);

		if (!existing) {
			return false;
		}

		await this.db.delete(schema.project).where(eq(schema.project.id, id));
		return true;
	}
}
