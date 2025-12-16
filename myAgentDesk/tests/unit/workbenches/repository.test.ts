/**
 * WorkbenchRepository Tests
 * Issue #289: Workbench List/Detail Screens
 *
 * Tests for the WorkbenchRepository class that handles
 * database operations for workbench entities.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { WorkbenchRepository } from '$lib/server/repositories/workbench';

describe('WorkbenchRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let repository: WorkbenchRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repository with test db
		repository = new WorkbenchRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findByProjectWithStats', () => {
		it('should return workbenches for specified project', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			expect(workbenches).toHaveLength(2);
			expect(workbenches.every((wb) => wb.id.startsWith('wb_'))).toBe(true);
		});

		it('should include run count', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			const wb001 = workbenches.find((wb) => wb.id === 'wb_001');
			expect(wb001?.runCount).toBe(3); // We seeded 3 runs for wb_001
		});

		it('should include schedule count (active only)', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			const wb001 = workbenches.find((wb) => wb.id === 'wb_001');
			expect(wb001?.scheduleCount).toBe(1); // 1 enabled schedule
		});

		it('should include last run info', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			const wb001 = workbenches.find((wb) => wb.id === 'wb_001');
			expect(wb001?.lastRunAt).toBeDefined();
			expect(wb001?.lastRunStatus).toBe('success');
		});

		it('should order by updatedAt descending', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			// Verify order is descending by updatedAt
			for (let i = 0; i < workbenches.length - 1; i++) {
				const current = new Date(workbenches[i].updatedAt).getTime();
				const next = new Date(workbenches[i + 1].updatedAt).getTime();
				expect(current).toBeGreaterThanOrEqual(next);
			}
		});

		it('should return empty array when no workbenches for project', async () => {
			const workbenches = await repository.findByProjectWithStats('nonexistent_project');

			expect(workbenches).toHaveLength(0);
		});

		it('should not return workbenches from other projects', async () => {
			const workbenches = await repository.findByProjectWithStats('proj_001');

			// wb_003 belongs to proj_002, should not appear
			const hasOtherProject = workbenches.some((wb) => wb.id === 'wb_003');
			expect(hasOtherProject).toBe(false);
		});
	});

	describe('findByIdWithDetail', () => {
		it('should return workbench with stats', async () => {
			const workbench = await repository.findByIdWithDetail('wb_001');

			expect(workbench).not.toBeNull();
			expect(workbench?.id).toBe('wb_001');
			expect(workbench?.stats).toBeDefined();
			expect(workbench?.stats.totalRuns).toBe(3);
		});

		it('should include active requirement version when exists', async () => {
			const workbench = await repository.findByIdWithDetail('wb_001');

			expect(workbench?.activeRequirementVersion).toBeDefined();
			expect(workbench?.activeRequirementVersion?.version).toBe(1);
		});

		it('should include current job version when exists', async () => {
			const workbench = await repository.findByIdWithDetail('wb_001');

			expect(workbench?.currentJobVersion).toBeDefined();
			expect(workbench?.currentJobVersion?.status).toBe('active');
		});

		it('should return null when workbench not found', async () => {
			const workbench = await repository.findByIdWithDetail('nonexistent_wb');

			expect(workbench).toBeNull();
		});

		it('should calculate success rate correctly', async () => {
			const workbench = await repository.findByIdWithDetail('wb_001');

			// 2 successful out of 3 total = 67%
			expect(workbench?.stats.successRate).toBe(67);
		});

		it('should return 0 success rate when no runs', async () => {
			const workbench = await repository.findByIdWithDetail('wb_002');

			expect(workbench?.stats.successRate).toBe(0);
			expect(workbench?.stats.totalRuns).toBe(0);
		});
	});

	describe('getStatusCounts', () => {
		it('should return counts per status', async () => {
			const counts = await repository.getStatusCounts('proj_001');

			expect(counts.active).toBe(1);
			expect(counts.draft).toBe(1);
		});

		it('should include total (all) count', async () => {
			const counts = await repository.getStatusCounts('proj_001');

			expect(counts.all).toBe(2); // total of active + draft + archived
		});

		it('should return zero counts for project with no workbenches', async () => {
			const counts = await repository.getStatusCounts('nonexistent_project');

			expect(counts.all).toBe(0);
			expect(counts.active).toBe(0);
			expect(counts.draft).toBe(0);
			expect(counts.archived).toBe(0);
		});
	});

	describe('findById', () => {
		it('should return workbench when exists', async () => {
			const workbench = await repository.findById('wb_001');

			expect(workbench).not.toBeNull();
			expect(workbench?.id).toBe('wb_001');
			expect(workbench?.projectId).toBe('proj_001');
		});

		it('should return null when not found', async () => {
			const workbench = await repository.findById('nonexistent');

			expect(workbench).toBeNull();
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

function seedTestData(db: ReturnType<typeof drizzle>) {
	const now = new Date();
	const earlier = new Date(now.getTime() - 3600000); // 1 hour ago

	// Create projects
	db.insert(schema.project)
		.values([
			{
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project 1',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'proj_002',
				externalProjectId: 'ext_proj_002',
				name: 'Test Project 2',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create workbenches
	db.insert(schema.workbench)
		.values([
			{
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Workbench 1',
				description: 'First workbench',
				status: 'active',
				activeRequirementVersionId: 'rv_001',
				createdAt: earlier,
				updatedAt: now
			},
			{
				id: 'wb_002',
				projectId: 'proj_001',
				name: 'Workbench 2',
				description: 'Second workbench',
				status: 'draft',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'wb_003',
				projectId: 'proj_002',
				name: 'Workbench 3 (Other Project)',
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create requirement versions
	db.insert(schema.requirementVersion)
		.values([
			{
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content: 'Test requirements',
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create job versions
	db.insert(schema.jobVersion)
		.values([
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'jv_002',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 1,
				versionLabel: 'v1.1',
				status: 'deprecated',
				createdAt: earlier,
				updatedAt: earlier
			}
		])
		.run();

	// Create runs (3 total: 2 success, 1 failed)
	const runTime1 = new Date(now.getTime() - 7200000); // 2 hours ago
	const runTime2 = new Date(now.getTime() - 3600000); // 1 hour ago
	const runTime3 = now;

	db.insert(schema.run)
		.values([
			{
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'success',
				startedAt: runTime1,
				completedAt: runTime1,
				createdAt: runTime1,
				updatedAt: runTime1
			},
			{
				id: 'run_002',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'failed',
				startedAt: runTime2,
				completedAt: runTime2,
				createdAt: runTime2,
				updatedAt: runTime2
			},
			{
				id: 'run_003',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'success',
				startedAt: runTime3,
				completedAt: runTime3,
				createdAt: runTime3,
				updatedAt: runTime3
			}
		])
		.run();

	// Create schedules (1 enabled, 1 disabled)
	db.insert(schema.schedule)
		.values([
			{
				id: 'sched_001',
				workbenchId: 'wb_001',
				targetJobVersionId: 'jv_001',
				name: 'Daily Schedule',
				cronExpression: '0 0 * * *',
				isEnabled: true,
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'sched_002',
				workbenchId: 'wb_001',
				targetJobVersionId: 'jv_001',
				name: 'Disabled Schedule',
				cronExpression: '0 12 * * *',
				isEnabled: false,
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
