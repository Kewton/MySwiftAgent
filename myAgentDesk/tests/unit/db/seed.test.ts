import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { getDefaultSeedData, seedDatabase, clearAllData } from '../../../src/lib/server/db/seed';

describe('Seed Data Module', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;

	beforeEach(() => {
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });
		createTables(sqlite);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('getDefaultSeedData', () => {
		it('should return valid seed data structure', () => {
			const seedData = getDefaultSeedData();

			expect(seedData).toBeDefined();
			expect(seedData.projects).toBeDefined();
			expect(seedData.workbenches).toBeDefined();
			expect(seedData.requirementVersions).toBeDefined();
			expect(seedData.jobVersions).toBeDefined();
			expect(seedData.runs).toBeDefined();
			expect(seedData.schedules).toBeDefined();
		});

		it('should contain correct number of projects', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.projects.length).toBe(3);
		});

		it('should contain correct number of workbenches', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.workbenches.length).toBe(5);
		});

		it('should contain correct number of requirement versions', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.requirementVersions.length).toBe(4);
		});

		it('should contain correct number of job versions', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.jobVersions.length).toBe(3);
		});

		it('should contain correct number of runs', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.runs.length).toBe(3);
		});

		it('should contain correct number of schedules', () => {
			const seedData = getDefaultSeedData();
			expect(seedData.schedules.length).toBe(3);
		});

		it('should have valid project IDs', () => {
			const seedData = getDefaultSeedData();
			const projectIds = seedData.projects.map((p) => p.id);

			expect(projectIds).toContain('proj_001');
			expect(projectIds).toContain('proj_002');
			expect(projectIds).toContain('proj_003');
		});

		it('should have valid workbench-project relationships', () => {
			const seedData = getDefaultSeedData();
			const projectIds = seedData.projects.map((p) => p.id);

			seedData.workbenches.forEach((wb) => {
				expect(projectIds).toContain(wb.projectId);
			});
		});

		it('should have valid requirement version-workbench relationships', () => {
			const seedData = getDefaultSeedData();
			const workbenchIds = seedData.workbenches.map((wb) => wb.id);

			seedData.requirementVersions.forEach((rv) => {
				expect(workbenchIds).toContain(rv.workbenchId);
			});
		});

		it('should have valid job version relationships', () => {
			const seedData = getDefaultSeedData();
			const workbenchIds = seedData.workbenches.map((wb) => wb.id);
			const requirementVersionIds = seedData.requirementVersions.map((rv) => rv.id);

			seedData.jobVersions.forEach((jv) => {
				expect(workbenchIds).toContain(jv.workbenchId);
				expect(requirementVersionIds).toContain(jv.sourceRequirementVersionId);
			});
		});

		it('should have valid run relationships', () => {
			const seedData = getDefaultSeedData();
			const workbenchIds = seedData.workbenches.map((wb) => wb.id);
			const jobVersionIds = seedData.jobVersions.map((jv) => jv.id);

			seedData.runs.forEach((run) => {
				expect(workbenchIds).toContain(run.workbenchId);
				expect(jobVersionIds).toContain(run.jobVersionId);
			});
		});

		it('should have valid schedule relationships', () => {
			const seedData = getDefaultSeedData();
			const workbenchIds = seedData.workbenches.map((wb) => wb.id);
			const jobVersionIds = seedData.jobVersions.map((jv) => jv.id);

			seedData.schedules.forEach((schedule) => {
				expect(workbenchIds).toContain(schedule.workbenchId);
				expect(jobVersionIds).toContain(schedule.targetJobVersionId);
			});
		});

		it('should have valid timestamps on all entities', () => {
			const seedData = getDefaultSeedData();

			seedData.projects.forEach((p) => {
				expect(p.createdAt).toBeInstanceOf(Date);
				expect(p.updatedAt).toBeInstanceOf(Date);
			});

			seedData.workbenches.forEach((wb) => {
				expect(wb.createdAt).toBeInstanceOf(Date);
				expect(wb.updatedAt).toBeInstanceOf(Date);
			});
		});
	});

	describe('seedDatabase function', () => {
		it('should seed database with provided data', async () => {
			const seedData = getDefaultSeedData();

			// Use the seedDatabase function
			await seedDatabase(db, seedData);

			// Verify counts
			const projects = await db.select().from(schema.project);
			const workbenches = await db.select().from(schema.workbench);
			const requirementVersions = await db.select().from(schema.requirementVersion);
			const jobVersions = await db.select().from(schema.jobVersion);
			const runs = await db.select().from(schema.run);
			const schedules = await db.select().from(schema.schedule);

			expect(projects.length).toBe(3);
			expect(workbenches.length).toBe(5);
			expect(requirementVersions.length).toBe(4);
			expect(jobVersions.length).toBe(3);
			expect(runs.length).toBe(3);
			expect(schedules.length).toBe(3);
		});

		it('should maintain FK integrity after seeding', async () => {
			const seedData = getDefaultSeedData();
			await seedDatabase(db, seedData);

			// Verify FK integrity by querying with joins
			const workbenchWithProject = sqlite
				.prepare(
					`
				SELECT w.id, w.name, p.name as project_name
				FROM workbench w
				JOIN project p ON w.project_id = p.id
			`
				)
				.all();

			expect(workbenchWithProject.length).toBe(5);
		});
	});

	describe('clearAllData function', () => {
		it('should clear all data from database', async () => {
			const seedData = getDefaultSeedData();

			// First seed the database
			await seedDatabase(db, seedData);

			// Verify data exists
			let projects = await db.select().from(schema.project);
			expect(projects.length).toBe(3);

			// Clear all data
			await clearAllData(db);

			// Verify all tables are empty
			projects = await db.select().from(schema.project);
			const workbenches = await db.select().from(schema.workbench);
			const requirementVersions = await db.select().from(schema.requirementVersion);
			const jobVersions = await db.select().from(schema.jobVersion);
			const runs = await db.select().from(schema.run);
			const schedules = await db.select().from(schema.schedule);

			expect(projects.length).toBe(0);
			expect(workbenches.length).toBe(0);
			expect(requirementVersions.length).toBe(0);
			expect(jobVersions.length).toBe(0);
			expect(runs.length).toBe(0);
			expect(schedules.length).toBe(0);
		});

		it('should not throw when clearing empty database', async () => {
			// Clear on empty database should not throw
			await expect(clearAllData(db)).resolves.not.toThrow();
		});
	});

	describe('Seed Data Integration', () => {
		it('should be insertable into database', async () => {
			const seedData = getDefaultSeedData();

			// Insert all data in order
			for (const project of seedData.projects) {
				await db.insert(schema.project).values(project);
			}

			for (const workbench of seedData.workbenches) {
				await db.insert(schema.workbench).values(workbench);
			}

			for (const rv of seedData.requirementVersions) {
				await db.insert(schema.requirementVersion).values(rv);
			}

			for (const jv of seedData.jobVersions) {
				await db.insert(schema.jobVersion).values(jv);
			}

			for (const run of seedData.runs) {
				await db.insert(schema.run).values(run);
			}

			for (const schedule of seedData.schedules) {
				await db.insert(schema.schedule).values(schedule);
			}

			// Verify counts
			const projects = await db.select().from(schema.project);
			const workbenches = await db.select().from(schema.workbench);
			const requirementVersions = await db.select().from(schema.requirementVersion);
			const jobVersions = await db.select().from(schema.jobVersion);
			const runs = await db.select().from(schema.run);
			const schedules = await db.select().from(schema.schedule);

			expect(projects.length).toBe(3);
			expect(workbenches.length).toBe(5);
			expect(requirementVersions.length).toBe(4);
			expect(jobVersions.length).toBe(3);
			expect(runs.length).toBe(3);
			expect(schedules.length).toBe(3);
		});

		it('should maintain FK integrity after insertion', async () => {
			const seedData = getDefaultSeedData();

			// Insert all data
			for (const project of seedData.projects) {
				await db.insert(schema.project).values(project);
			}

			for (const workbench of seedData.workbenches) {
				await db.insert(schema.workbench).values(workbench);
			}

			for (const rv of seedData.requirementVersions) {
				await db.insert(schema.requirementVersion).values(rv);
			}

			for (const jv of seedData.jobVersions) {
				await db.insert(schema.jobVersion).values(jv);
			}

			for (const run of seedData.runs) {
				await db.insert(schema.run).values(run);
			}

			for (const schedule of seedData.schedules) {
				await db.insert(schema.schedule).values(schedule);
			}

			// Verify FK integrity by querying with joins
			const workbenchWithProject = sqlite
				.prepare(
					`
				SELECT w.id, w.name, p.name as project_name
				FROM workbench w
				JOIN project p ON w.project_id = p.id
			`
				)
				.all();

			expect(workbenchWithProject.length).toBe(5);
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
			external_job_id TEXT,
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
			external_job_id TEXT,
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
