import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import { eq, and } from 'drizzle-orm';
import * as schema from '../../../src/lib/server/db/schema';

describe('Database CRUD Operations', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('Project CRUD', () => {
		it('should create a project', async () => {
			const now = new Date();
			const result = await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				description: 'A test project',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should read a project', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				description: 'A test project',
				createdAt: now,
				updatedAt: now
			});

			const projects = await db
				.select()
				.from(schema.project)
				.where(eq(schema.project.id, 'proj_001'));

			expect(projects).toHaveLength(1);
			expect(projects[0].name).toBe('Test Project');
			expect(projects[0].externalProjectId).toBe('ext_proj_001');
		});

		it('should update a project', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			const updatedAt = new Date();
			await db
				.update(schema.project)
				.set({ name: 'Updated Project', updatedAt })
				.where(eq(schema.project.id, 'proj_001'));

			const projects = await db
				.select()
				.from(schema.project)
				.where(eq(schema.project.id, 'proj_001'));

			expect(projects[0].name).toBe('Updated Project');
		});

		it('should delete a project', async () => {
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.delete(schema.project).where(eq(schema.project.id, 'proj_001'));

			const projects = await db
				.select()
				.from(schema.project)
				.where(eq(schema.project.id, 'proj_001'));

			expect(projects).toHaveLength(0);
		});
	});

	describe('Workbench CRUD', () => {
		beforeEach(async () => {
			// Create a project for foreign key relationship
			const now = new Date();
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});
		});

		it('should create a workbench with valid project_id', async () => {
			const now = new Date();
			const result = await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should fail to create workbench with invalid project_id', async () => {
			const now = new Date();
			await expect(
				db.insert(schema.workbench).values({
					id: 'wb_002',
					projectId: 'nonexistent_project',
					name: 'Test Workbench',
					status: 'draft',
					createdAt: now,
					updatedAt: now
				})
			).rejects.toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should read workbench with project relationship', async () => {
			const now = new Date();
			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			const workbenches = await db
				.select()
				.from(schema.workbench)
				.where(eq(schema.workbench.id, 'wb_001'));

			expect(workbenches).toHaveLength(1);
			expect(workbenches[0].projectId).toBe('proj_001');
		});
	});

	describe('RequirementVersion CRUD', () => {
		beforeEach(async () => {
			const now = new Date();
			// Create project and workbench
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});
		});

		it('should create a requirement version', async () => {
			const now = new Date();
			const result = await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirement content',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should fail to create duplicate version for same workbench', async () => {
			const now = new Date();
			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test content v1',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			await expect(
				db.insert(schema.requirementVersion).values({
					id: 'rv_002',
					workbenchId: 'wb_001',
					version: 1, // Same version
					content: 'Test content v1 duplicate',
					status: 'draft',
					createdAt: now,
					updatedAt: now
				})
			).rejects.toThrow(/UNIQUE constraint failed/);
		});

		it('should allow same version for different workbenches', async () => {
			const now = new Date();
			// Create another workbench
			await db.insert(schema.workbench).values({
				id: 'wb_002',
				projectId: 'proj_001',
				name: 'Test Workbench 2',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			// Insert version 1 for both workbenches
			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Content for wb_001',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			const result = await db.insert(schema.requirementVersion).values({
				id: 'rv_002',
				workbenchId: 'wb_002',
				version: 1, // Same version but different workbench
				content: 'Content for wb_002',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});
	});

	describe('JobVersion CRUD', () => {
		beforeEach(async () => {
			const now = new Date();
			// Create full hierarchy
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirement',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});
		});

		it('should create a job version with source_requirement_version_id', async () => {
			const now = new Date();
			const result = await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'generating',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should fail to create job version with invalid requirement version', async () => {
			const now = new Date();
			await expect(
				db.insert(schema.jobVersion).values({
					id: 'jv_001',
					workbenchId: 'wb_001',
					sourceRequirementVersionId: 'nonexistent_rv',
					majorVersion: 1,
					minorVersion: 0,
					versionLabel: 'v1.0',
					status: 'generating',
					createdAt: now,
					updatedAt: now
				})
			).rejects.toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should store JSON data in task_breakdown, interface_definitions, workflows', async () => {
			const now = new Date();
			const taskBreakdown = [
				{ id: 'task_1', name: 'Task 1' },
				{ id: 'task_2', name: 'Task 2' }
			];
			const interfaceDefinitions = { input: 'string', output: 'string' };
			const workflows = [{ id: 'wf_1', steps: ['step1', 'step2'] }];

			await db.insert(schema.jobVersion).values({
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'success',
				taskBreakdown: JSON.stringify(taskBreakdown),
				interfaceDefinitions: JSON.stringify(interfaceDefinitions),
				workflows: JSON.stringify(workflows),
				createdAt: now,
				updatedAt: now
			});

			const jobVersions = await db
				.select()
				.from(schema.jobVersion)
				.where(eq(schema.jobVersion.id, 'jv_001'));

			expect(jobVersions).toHaveLength(1);
			expect(JSON.parse(jobVersions[0].taskBreakdown as string)).toEqual(taskBreakdown);
			expect(JSON.parse(jobVersions[0].interfaceDefinitions as string)).toEqual(
				interfaceDefinitions
			);
			expect(JSON.parse(jobVersions[0].workflows as string)).toEqual(workflows);
		});
	});

	describe('Run CRUD', () => {
		beforeEach(async () => {
			const now = new Date();
			// Create full hierarchy
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirement',
				status: 'draft',
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
				status: 'success',
				createdAt: now,
				updatedAt: now
			});
		});

		it('should create a run', async () => {
			const now = new Date();
			const result = await db.insert(schema.run).values({
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'queued',
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should fail to create run with invalid workbench_id', async () => {
			const now = new Date();
			await expect(
				db.insert(schema.run).values({
					id: 'run_001',
					workbenchId: 'nonexistent_wb',
					jobVersionId: 'jv_001',
					status: 'queued',
					createdAt: now,
					updatedAt: now
				})
			).rejects.toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should fail to create run with invalid job_version_id', async () => {
			const now = new Date();
			await expect(
				db.insert(schema.run).values({
					id: 'run_001',
					workbenchId: 'wb_001',
					jobVersionId: 'nonexistent_jv',
					status: 'queued',
					createdAt: now,
					updatedAt: now
				})
			).rejects.toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should update run status and timestamps', async () => {
			const now = new Date();
			await db.insert(schema.run).values({
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'queued',
				createdAt: now,
				updatedAt: now
			});

			const startedAt = new Date();
			await db
				.update(schema.run)
				.set({ status: 'running', startedAt, updatedAt: startedAt })
				.where(eq(schema.run.id, 'run_001'));

			const runs = await db.select().from(schema.run).where(eq(schema.run.id, 'run_001'));

			expect(runs[0].status).toBe('running');
			expect(runs[0].startedAt).toBeDefined();
		});
	});

	describe('Schedule CRUD', () => {
		beforeEach(async () => {
			const now = new Date();
			// Create full hierarchy
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirement',
				status: 'draft',
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
				status: 'success',
				createdAt: now,
				updatedAt: now
			});
		});

		it('should create a schedule', async () => {
			const now = new Date();
			const result = await db.insert(schema.schedule).values({
				id: 'sched_001',
				workbenchId: 'wb_001',
				targetJobVersionId: 'jv_001',
				name: 'Daily Schedule',
				cronExpression: '0 0 * * *',
				isEnabled: true,
				createdAt: now,
				updatedAt: now
			});

			expect(result.changes).toBe(1);
		});

		it('should toggle schedule is_enabled', async () => {
			const now = new Date();
			await db.insert(schema.schedule).values({
				id: 'sched_001',
				workbenchId: 'wb_001',
				targetJobVersionId: 'jv_001',
				name: 'Daily Schedule',
				cronExpression: '0 0 * * *',
				isEnabled: true,
				createdAt: now,
				updatedAt: now
			});

			await db
				.update(schema.schedule)
				.set({ isEnabled: false, updatedAt: new Date() })
				.where(eq(schema.schedule.id, 'sched_001'));

			const schedules = await db
				.select()
				.from(schema.schedule)
				.where(eq(schema.schedule.id, 'sched_001'));

			expect(schedules[0].isEnabled).toBe(false);
		});
	});

	describe('Hierarchical CRUD - Project -> Workbench -> RequirementVersion', () => {
		it('should create full hierarchy correctly', async () => {
			const now = new Date();

			// Create project
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			// Create workbench under project
			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			// Create requirement version under workbench
			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Initial requirement',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			});

			// Verify full hierarchy
			const projects = await db.select().from(schema.project);
			const workbenches = await db.select().from(schema.workbench);
			const requirementVersions = await db.select().from(schema.requirementVersion);

			expect(projects).toHaveLength(1);
			expect(workbenches).toHaveLength(1);
			expect(requirementVersions).toHaveLength(1);

			expect(workbenches[0].projectId).toBe(projects[0].id);
			expect(requirementVersions[0].workbenchId).toBe(workbenches[0].id);
		});

		it('should cascade relationships correctly through job generation flow', async () => {
			const now = new Date();

			// Create full hierarchy: Project -> Workbench -> RequirementVersion -> JobVersion -> Run
			await db.insert(schema.project).values({
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.workbench).values({
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Test Workbench',
				status: 'active',
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.requirementVersion).values({
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'User requirement content',
				status: 'submitted',
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
				status: 'success',
				taskBreakdown: JSON.stringify([{ id: 't1', name: 'Task 1' }]),
				createdAt: now,
				updatedAt: now
			});

			await db.insert(schema.run).values({
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'success',
				startedAt: now,
				completedAt: now,
				createdAt: now,
				updatedAt: now
			});

			// Verify run links back to job_version and workbench
			const runs = await db.select().from(schema.run).where(eq(schema.run.id, 'run_001'));

			expect(runs[0].jobVersionId).toBe('jv_001');
			expect(runs[0].workbenchId).toBe('wb_001');

			// Verify job_version links to requirement_version
			const jobVersions = await db
				.select()
				.from(schema.jobVersion)
				.where(eq(schema.jobVersion.id, 'jv_001'));

			expect(jobVersions[0].sourceRequirementVersionId).toBe('rv_001');
		});
	});
});

function createTables(sqlite: Database.Database) {
	// Create all tables with proper structure
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
