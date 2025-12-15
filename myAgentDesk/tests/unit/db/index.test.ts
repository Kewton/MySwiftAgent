import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';

describe('Database Index Module', () => {
	describe('Schema Exports', () => {
		it('should export project table schema', () => {
			expect(schema.project).toBeDefined();
		});

		it('should export workbench table schema', () => {
			expect(schema.workbench).toBeDefined();
		});

		it('should export requirementVersion table schema', () => {
			expect(schema.requirementVersion).toBeDefined();
		});

		it('should export jobVersion table schema', () => {
			expect(schema.jobVersion).toBeDefined();
		});

		it('should export run table schema', () => {
			expect(schema.run).toBeDefined();
		});

		it('should export schedule table schema', () => {
			expect(schema.schedule).toBeDefined();
		});
	});

	describe('Type Exports', () => {
		it('should allow creating NewProject type', () => {
			const project: schema.NewProject = {
				id: 'test_proj',
				externalProjectId: 'ext_proj',
				name: 'Test Project',
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(project.id).toBe('test_proj');
		});

		it('should allow creating NewWorkbench type', () => {
			const workbench: schema.NewWorkbench = {
				id: 'test_wb',
				projectId: 'test_proj',
				name: 'Test Workbench',
				status: 'draft',
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(workbench.id).toBe('test_wb');
		});

		it('should allow creating NewRequirementVersion type', () => {
			const rv: schema.NewRequirementVersion = {
				id: 'test_rv',
				workbenchId: 'test_wb',
				version: 1,
				content: 'Test content',
				status: 'draft',
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(rv.id).toBe('test_rv');
		});

		it('should allow creating NewJobVersion type', () => {
			const jv: schema.NewJobVersion = {
				id: 'test_jv',
				workbenchId: 'test_wb',
				sourceRequirementVersionId: 'test_rv',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'generating',
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(jv.id).toBe('test_jv');
		});

		it('should allow creating NewRun type', () => {
			const run: schema.NewRun = {
				id: 'test_run',
				workbenchId: 'test_wb',
				jobVersionId: 'test_jv',
				status: 'queued',
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(run.id).toBe('test_run');
		});

		it('should allow creating NewSchedule type', () => {
			const schedule: schema.NewSchedule = {
				id: 'test_sched',
				workbenchId: 'test_wb',
				targetJobVersionId: 'test_jv',
				name: 'Test Schedule',
				cronExpression: '0 * * * *',
				isEnabled: true,
				createdAt: new Date(),
				updatedAt: new Date()
			};
			expect(schedule.id).toBe('test_sched');
		});
	});

	describe('Drizzle Integration', () => {
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

		it('should create drizzle instance with schema', () => {
			expect(db).toBeDefined();
		});

		it('should be able to query tables', async () => {
			const projects = await db.select().from(schema.project);
			expect(projects).toEqual([]);
		});

		it('should support insert operations', async () => {
			const now = new Date();
			const result = await db.insert(schema.project).values({
				id: 'proj_test',
				externalProjectId: 'ext_test',
				name: 'Test Project',
				createdAt: now,
				updatedAt: now
			});
			expect(result.changes).toBe(1);
		});

		it('should enable foreign keys by default', () => {
			const fkEnabled = sqlite.pragma('foreign_keys') as Array<{ foreign_keys: number }>;
			expect(fkEnabled[0].foreign_keys).toBe(1);
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
