import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';

describe('Database Schema Tests', () => {
	let sqlite: Database.Database;
	let _db: ReturnType<typeof drizzle>;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		_db = drizzle(sqlite, { schema });

		// Create tables using raw SQL from schema definitions
		createTables(sqlite);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('Table Creation', () => {
		it('should create project table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='project'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should create workbench table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='workbench'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should create requirement_version table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='requirement_version'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should create job_version table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='job_version'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should create run table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='run'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should create schedule table', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='schedule'")
				.all();
			expect(tables).toHaveLength(1);
		});

		it('should have exactly 6 tables', () => {
			const tables = sqlite
				.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
				.all();
			expect(tables).toHaveLength(6);
		});
	});

	describe('Column Definitions', () => {
		it('should have correct columns in project table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('project')").all() as Array<{
				name: string;
				notnull: number;
			}>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('external_project_id');
			expect(columnNames).toContain('name');
			expect(columnNames).toContain('description');
			expect(columnNames).toContain('last_synced_at');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});

		it('should have correct columns in workbench table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('workbench')").all() as Array<{
				name: string;
			}>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('project_id');
			expect(columnNames).toContain('name');
			expect(columnNames).toContain('description');
			expect(columnNames).toContain('status');
			expect(columnNames).toContain('active_requirement_version_id');
			expect(columnNames).toContain('external_job_master_id');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});

		it('should have correct columns in requirement_version table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('requirement_version')").all() as Array<{
				name: string;
			}>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('workbench_id');
			expect(columnNames).toContain('version');
			expect(columnNames).toContain('content');
			expect(columnNames).toContain('status');
			expect(columnNames).toContain('change_summary');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});

		it('should have correct columns in job_version table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('job_version')").all() as Array<{
				name: string;
			}>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('workbench_id');
			expect(columnNames).toContain('source_requirement_version_id');
			expect(columnNames).toContain('major_version');
			expect(columnNames).toContain('minor_version');
			expect(columnNames).toContain('version_label');
			expect(columnNames).toContain('status');
			expect(columnNames).toContain('task_breakdown');
			expect(columnNames).toContain('interface_definitions');
			expect(columnNames).toContain('workflows');
			expect(columnNames).toContain('external_job_master_id');
			expect(columnNames).toContain('external_trace_id');
			expect(columnNames).toContain('error_message');
			expect(columnNames).toContain('generated_at');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});

		it('should have correct columns in run table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('run')").all() as Array<{ name: string }>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('workbench_id');
			expect(columnNames).toContain('job_version_id');
			expect(columnNames).toContain('status');
			expect(columnNames).toContain('external_job_id');
			expect(columnNames).toContain('external_trace_id');
			expect(columnNames).toContain('execution_params');
			expect(columnNames).toContain('result_summary');
			expect(columnNames).toContain('started_at');
			expect(columnNames).toContain('completed_at');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});

		it('should have correct columns in schedule table', () => {
			const columns = sqlite.prepare("PRAGMA table_info('schedule')").all() as Array<{
				name: string;
			}>;
			const columnNames = columns.map((c) => c.name);

			expect(columnNames).toContain('id');
			expect(columnNames).toContain('workbench_id');
			expect(columnNames).toContain('target_job_version_id');
			expect(columnNames).toContain('name');
			expect(columnNames).toContain('cron_expression');
			expect(columnNames).toContain('is_enabled');
			expect(columnNames).toContain('external_scheduler_id');
			expect(columnNames).toContain('execution_params');
			expect(columnNames).toContain('next_run_at');
			expect(columnNames).toContain('last_run_at');
			expect(columnNames).toContain('created_at');
			expect(columnNames).toContain('updated_at');
		});
	});

	describe('NOT NULL Constraints', () => {
		it('should enforce NOT NULL on project.name', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
						 VALUES (?, ?, NULL, ?, ?)`
					)
					.run('proj_test', 'ext_test', now, now);
			}).toThrow();
		});

		it('should enforce NOT NULL on workbench.project_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO workbench (id, project_id, name, status, created_at, updated_at)
						 VALUES (?, NULL, ?, ?, ?, ?)`
					)
					.run('wb_test', 'Test Workbench', 'draft', now, now);
			}).toThrow();
		});

		it('should enforce NOT NULL on requirement_version.content', () => {
			const now = Date.now();
			// First create project and workbench
			sqlite
				.prepare(
					`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?)`
				)
				.run('proj_test', 'ext_test', 'Test Project', now, now);

			sqlite
				.prepare(
					`INSERT INTO workbench (id, project_id, name, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?)`
				)
				.run('wb_test', 'proj_test', 'Test Workbench', 'draft', now, now);

			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO requirement_version (id, workbench_id, version, content, status, created_at, updated_at)
						 VALUES (?, ?, ?, NULL, ?, ?, ?)`
					)
					.run('rv_test', 'wb_test', 1, 'draft', now, now);
			}).toThrow();
		});
	});

	describe('Foreign Key Constraints', () => {
		it('should enforce FK constraint on workbench.project_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO workbench (id, project_id, name, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?)`
					)
					.run('wb_test', 'nonexistent_project', 'Test Workbench', 'draft', now, now);
			}).toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should enforce FK constraint on requirement_version.workbench_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO requirement_version (id, workbench_id, version, content, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?, ?)`
					)
					.run('rv_test', 'nonexistent_workbench', 1, 'Test content', 'draft', now, now);
			}).toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should enforce FK constraint on job_version.workbench_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO job_version (id, workbench_id, source_requirement_version_id, major_version, minor_version, version_label, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
					)
					.run('jv_test', 'nonexistent_workbench', 'rv_test', 1, 0, 'v1.0', 'generating', now, now);
			}).toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should enforce FK constraint on run.workbench_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO run (id, workbench_id, job_version_id, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?)`
					)
					.run('run_test', 'nonexistent_workbench', 'jv_test', 'queued', now, now);
			}).toThrow(/FOREIGN KEY constraint failed/);
		});

		it('should enforce FK constraint on schedule.workbench_id', () => {
			const now = Date.now();
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO schedule (id, workbench_id, target_job_version_id, name, cron_expression, is_enabled, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
					)
					.run(
						'sched_test',
						'nonexistent_workbench',
						'jv_test',
						'Test Schedule',
						'0 0 * * *',
						1,
						now,
						now
					);
			}).toThrow(/FOREIGN KEY constraint failed/);
		});
	});

	describe('Unique Constraints', () => {
		it('should enforce unique constraint on project.external_project_id', () => {
			const now = Date.now();
			sqlite
				.prepare(
					`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?)`
				)
				.run('proj_1', 'ext_unique', 'Project 1', now, now);

			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?)`
					)
					.run('proj_2', 'ext_unique', 'Project 2', now, now);
			}).toThrow(/UNIQUE constraint failed/);
		});

		it('should enforce unique constraint on requirement_version (workbench_id, version)', () => {
			const now = Date.now();
			// Setup: create project and workbench
			sqlite
				.prepare(
					`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?)`
				)
				.run('proj_test', 'ext_test', 'Test Project', now, now);

			sqlite
				.prepare(
					`INSERT INTO workbench (id, project_id, name, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?)`
				)
				.run('wb_test', 'proj_test', 'Test Workbench', 'draft', now, now);

			// Insert first requirement version
			sqlite
				.prepare(
					`INSERT INTO requirement_version (id, workbench_id, version, content, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?, ?)`
				)
				.run('rv_1', 'wb_test', 1, 'Content v1', 'draft', now, now);

			// Try to insert duplicate version for same workbench
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO requirement_version (id, workbench_id, version, content, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?, ?)`
					)
					.run('rv_2', 'wb_test', 1, 'Content v1 duplicate', 'draft', now, now);
			}).toThrow(/UNIQUE constraint failed/);
		});

		it('should enforce unique constraint on job_version (workbench_id, major_version, minor_version)', () => {
			const now = Date.now();
			// Setup: create full hierarchy
			sqlite
				.prepare(
					`INSERT INTO project (id, external_project_id, name, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?)`
				)
				.run('proj_test', 'ext_test', 'Test Project', now, now);

			sqlite
				.prepare(
					`INSERT INTO workbench (id, project_id, name, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?)`
				)
				.run('wb_test', 'proj_test', 'Test Workbench', 'draft', now, now);

			sqlite
				.prepare(
					`INSERT INTO requirement_version (id, workbench_id, version, content, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?, ?)`
				)
				.run('rv_test', 'wb_test', 1, 'Content', 'draft', now, now);

			// Insert first job version
			sqlite
				.prepare(
					`INSERT INTO job_version (id, workbench_id, source_requirement_version_id, major_version, minor_version, version_label, status, created_at, updated_at)
					 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
				)
				.run('jv_1', 'wb_test', 'rv_test', 1, 0, 'v1.0', 'generating', now, now);

			// Try to insert duplicate version for same workbench
			expect(() => {
				sqlite
					.prepare(
						`INSERT INTO job_version (id, workbench_id, source_requirement_version_id, major_version, minor_version, version_label, status, created_at, updated_at)
						 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`
					)
					.run('jv_2', 'wb_test', 'rv_test', 1, 0, 'v1.0 duplicate', 'generating', now, now);
			}).toThrow(/UNIQUE constraint failed/);
		});
	});

	describe('Type Exports', () => {
		it('should export Project type', () => {
			expect(schema.project).toBeDefined();
		});

		it('should export Workbench type', () => {
			expect(schema.workbench).toBeDefined();
		});

		it('should export RequirementVersion type', () => {
			expect(schema.requirementVersion).toBeDefined();
		});

		it('should export JobVersion type', () => {
			expect(schema.jobVersion).toBeDefined();
		});

		it('should export Run type', () => {
			expect(schema.run).toBeDefined();
		});

		it('should export Schedule type', () => {
			expect(schema.schedule).toBeDefined();
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
