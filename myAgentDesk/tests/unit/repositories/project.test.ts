/**
 * Project Repository Tests
 * Issue #288: Project screens implementation
 *
 * Tests for the project repository layer including CRUD operations
 * and statistics queries.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { ProjectRepository } from '../../../src/lib/server/repositories/project';

describe('ProjectRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle<typeof schema>>;
	let repository: ProjectRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Initialize repository
		repository = new ProjectRepository(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findAll', () => {
		it('should return empty array when no projects exist', async () => {
			const projects = await repository.findAll();
			expect(projects).toEqual([]);
		});

		it('should return all projects ordered by updatedAt desc', async () => {
			const now = new Date();
			const earlier = new Date(now.getTime() - 1000);

			await db.insert(schema.project).values([
				{
					id: 'proj_001',
					externalProjectId: 'ext_001',
					name: 'Project A',
					createdAt: earlier,
					updatedAt: earlier
				},
				{
					id: 'proj_002',
					externalProjectId: 'ext_002',
					name: 'Project B',
					createdAt: now,
					updatedAt: now
				}
			]);

			const projects = await repository.findAll();

			expect(projects).toHaveLength(2);
			expect(projects[0].id).toBe('proj_002'); // More recent first
			expect(projects[1].id).toBe('proj_001');
		});

		it('should include workbench count in returned projects', async () => {
			const now = new Date();

			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Project A',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values([
				{
					id: 'wb_001',
					projectId: 'proj_001',
					name: 'Workbench 1',
					status: 'active',
					createdAt: now,
					updatedAt: now
				},
				{
					id: 'wb_002',
					projectId: 'proj_001',
					name: 'Workbench 2',
					status: 'draft',
					createdAt: now,
					updatedAt: now
				}
			]);

			const projects = await repository.findAllWithStats();

			expect(projects).toHaveLength(1);
			expect(projects[0].workbenchCount).toBe(2);
		});
	});

	describe('findById', () => {
		it('should return null when project does not exist', async () => {
			const project = await repository.findById('nonexistent');
			expect(project).toBeNull();
		});

		it('should return project when it exists', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				description: 'A test project',
				createdAt: now,
				updatedAt: now
			});

			const project = await repository.findById('proj_001');

			expect(project).not.toBeNull();
			expect(project?.id).toBe('proj_001');
			expect(project?.name).toBe('Test Project');
			expect(project?.description).toBe('A test project');
		});
	});

	describe('findByIdWithStats', () => {
		it('should return null when project does not exist', async () => {
			const result = await repository.findByIdWithStats('nonexistent');
			expect(result).toBeNull();
		});

		it('should return project with statistics', async () => {
			const now = new Date();
			const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

			// Create project
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			// Create workbenches
			await db.insert(schema.workbench).values([
				{
					id: 'wb_001',
					projectId: 'proj_001',
					name: 'Workbench 1',
					status: 'active',
					createdAt: now,
					updatedAt: now
				},
				{
					id: 'wb_002',
					projectId: 'proj_001',
					name: 'Workbench 2',
					status: 'draft',
					createdAt: now,
					updatedAt: now
				}
			]);

			// Create requirement version for job version FK
			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirement',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			// Create job version for run and schedule FK
			await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			// Create runs (2 recent, 1 old)
			await db.insert(schema.run).values([
				{
					id: 'run_001',
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'success',
					createdAt: now,
					updatedAt: now
				},
				{
					id: 'run_002',
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'running',
					createdAt: now,
					updatedAt: now
				},
				{
					id: 'run_003',
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'success',
					createdAt: sevenDaysAgo,
					updatedAt: sevenDaysAgo
				}
			]);

			// Create schedules (1 enabled, 1 disabled)
			await db.insert(schema.schedule).values([
				{
					id: 'sched_001',
					workbenchId: 'wb_001',
					targetJobVersionId: 'jv_001',
					name: 'Daily',
					cronExpression: '0 0 * * *',
					isEnabled: true,
					createdAt: now,
					updatedAt: now
				},
				{
					id: 'sched_002',
					workbenchId: 'wb_001',
					targetJobVersionId: 'jv_001',
					name: 'Weekly',
					cronExpression: '0 0 * * 0',
					isEnabled: false,
					createdAt: now,
					updatedAt: now
				}
			]);

			const result = await repository.findByIdWithStats('proj_001');

			expect(result).not.toBeNull();
			expect(result?.project.id).toBe('proj_001');
			expect(result?.stats.workbenchCount).toBe(2);
			expect(result?.stats.activeScheduleCount).toBe(1);
		});
	});

	describe('getProjectStats', () => {
		it('should return zero counts for project with no data', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Empty Project',
				createdAt: now,
				updatedAt: now
			});

			const stats = await repository.getProjectStats('proj_001');

			expect(stats.workbenchCount).toBe(0);
			expect(stats.recentRunCount).toBe(0);
			expect(stats.activeScheduleCount).toBe(0);
		});
	});

	describe('getRecentRuns', () => {
		it('should return empty array when project has no runs', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			const runs = await repository.getRecentRuns('proj_001', 10);
			expect(runs).toEqual([]);
		});

		it('should return runs for project ordered by createdAt desc', async () => {
			const now = new Date();
			const earlier = new Date(now.getTime() - 1000);

			// Setup project hierarchy
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Workbench 1',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.run).values([
				{
					id: 'run_001',
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'success',
					createdAt: earlier,
					updatedAt: earlier
				},
				{
					id: 'run_002',
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'running',
					createdAt: now,
					updatedAt: now
				}
			]);

			const runs = await repository.getRecentRuns('proj_001', 10);

			expect(runs).toHaveLength(2);
			expect(runs[0].id).toBe('run_002'); // More recent first
			expect(runs[1].id).toBe('run_001');
		});

		it('should respect limit parameter', async () => {
			const now = new Date();

			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Workbench 1',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			// Create 5 runs
			for (let i = 1; i <= 5; i++) {
				await db.insert(schema.run).values({
					id: `run_00${i}`,
					workbenchId: 'wb_001',
					jobVersionId: 'jv_001',
					status: 'success',
					createdAt: new Date(now.getTime() + i * 1000),
					updatedAt: new Date(now.getTime() + i * 1000)
				});
			}

			const runs = await repository.getRecentRuns('proj_001', 3);

			expect(runs).toHaveLength(3);
		});
	});

	describe('getRecentSchedules', () => {
		it('should return empty array when project has no schedules', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			const schedules = await repository.getRecentSchedules('proj_001', 10);
			expect(schedules).toEqual([]);
		});

		it('should return schedules for project ordered by createdAt desc', async () => {
			const now = new Date();
			const earlier = new Date(now.getTime() - 1000);

			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Workbench 1',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.schedule).values([
				{
					id: 'sched_001',
					workbenchId: 'wb_001',
					targetJobVersionId: 'jv_001',
					name: 'Older',
					cronExpression: '0 0 * * *',
					isEnabled: true,
					createdAt: earlier,
					updatedAt: earlier
				},
				{
					id: 'sched_002',
					workbenchId: 'wb_001',
					targetJobVersionId: 'jv_001',
					name: 'Newer',
					cronExpression: '0 12 * * *',
					isEnabled: true,
					createdAt: now,
					updatedAt: now
				}
			]);

			const schedules = await repository.getRecentSchedules('proj_001', 10);

			expect(schedules).toHaveLength(2);
			expect(schedules[0].id).toBe('sched_002'); // More recent first
		});
	});

	describe('create', () => {
		it('should create a new project', async () => {
			const result = await repository.create({
				name: 'New Project',
				description: 'A new test project'
			});

			expect(result.id).toBeDefined();
			expect(result.name).toBe('New Project');
			expect(result.description).toBe('A new test project');
			expect(result.externalProjectId).toBeDefined();

			// Verify persisted
			const project = await repository.findById(result.id);
			expect(project).not.toBeNull();
			expect(project?.name).toBe('New Project');
		});

		it('should generate unique IDs for projects', async () => {
			const project1 = await repository.create({ name: 'Project 1' });
			const project2 = await repository.create({ name: 'Project 2' });

			expect(project1.id).not.toBe(project2.id);
			expect(project1.externalProjectId).not.toBe(project2.externalProjectId);
		});
	});

	describe('update', () => {
		it('should update project name and description', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'Original Name',
				description: 'Original description',
				createdAt: now,
				updatedAt: now
			});

			const updated = await repository.update('proj_001', {
				name: 'Updated Name',
				description: 'Updated description'
			});

			expect(updated?.name).toBe('Updated Name');
			expect(updated?.description).toBe('Updated description');
		});

		it('should return null when updating non-existent project', async () => {
			const result = await repository.update('nonexistent', { name: 'New Name' });
			expect(result).toBeNull();
		});
	});

	describe('delete', () => {
		it('should delete a project', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_001',
				name: 'To Delete',
				createdAt: now,
				updatedAt: now
			});

			const deleted = await repository.delete('proj_001');

			expect(deleted).toBe(true);

			const project = await repository.findById('proj_001');
			expect(project).toBeNull();
		});

		it('should return false when deleting non-existent project', async () => {
			const deleted = await repository.delete('nonexistent');
			expect(deleted).toBe(false);
		});
	});
});

function createTables(sqlite: Database.Database) {
	sqlite.exec(`
		CREATE TABLE IF NOT EXISTS project (
			id TEXT PRIMARY KEY NOT NULL,
			external_project_id TEXT NOT NULL UNIQUE,
			name TEXT NOT NULL,
			description TEXT,
			last_synced_at INTEGER,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL
		);

		CREATE TABLE IF NOT EXISTS workbench (
			id TEXT PRIMARY KEY NOT NULL,
			project_id TEXT NOT NULL REFERENCES project(id),
			name TEXT NOT NULL,
			description TEXT,
			status TEXT NOT NULL DEFAULT 'draft',
			active_requirement_version_id TEXT,
			external_job_master_id TEXT,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL
		);

		CREATE TABLE IF NOT EXISTS requirement_version (
			id TEXT PRIMARY KEY NOT NULL,
			workbench_id TEXT NOT NULL REFERENCES workbench(id),
			version INTEGER NOT NULL,
			content TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'draft',
			change_summary TEXT,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL,
			UNIQUE(workbench_id, version)
		);

		CREATE TABLE IF NOT EXISTS job_version (
			id TEXT PRIMARY KEY NOT NULL,
			workbench_id TEXT NOT NULL REFERENCES workbench(id),
			source_requirement_version_id TEXT NOT NULL REFERENCES requirement_version(id),
			major_version INTEGER NOT NULL,
			minor_version INTEGER NOT NULL,
			version_label TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'generating',
			task_breakdown TEXT,
			interface_definitions TEXT,
			workflows TEXT,
			external_job_master_id TEXT,
			external_trace_id TEXT,
			error_message TEXT,
			generated_at INTEGER,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL,
			UNIQUE(workbench_id, major_version, minor_version)
		);

		CREATE TABLE IF NOT EXISTS run (
			id TEXT PRIMARY KEY NOT NULL,
			workbench_id TEXT NOT NULL REFERENCES workbench(id),
			job_version_id TEXT NOT NULL REFERENCES job_version(id),
			status TEXT NOT NULL DEFAULT 'queued',
			external_job_id TEXT,
			external_trace_id TEXT,
			execution_params TEXT,
			result_summary TEXT,
			started_at INTEGER,
			completed_at INTEGER,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL
		);

		CREATE TABLE IF NOT EXISTS schedule (
			id TEXT PRIMARY KEY NOT NULL,
			workbench_id TEXT NOT NULL REFERENCES workbench(id),
			target_job_version_id TEXT NOT NULL REFERENCES job_version(id),
			name TEXT NOT NULL,
			cron_expression TEXT NOT NULL,
			is_enabled INTEGER NOT NULL DEFAULT 1,
			external_scheduler_id TEXT,
			execution_params TEXT,
			next_run_at INTEGER,
			last_run_at INTEGER,
			created_at INTEGER NOT NULL,
			updated_at INTEGER NOT NULL
		);
	`);
}
