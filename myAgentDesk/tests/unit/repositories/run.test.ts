/**
 * RunRepository Tests
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Tests for the RunRepository class that handles
 * database operations for run entities.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { RunRepository } from '$lib/server/repositories/run';

describe('RunRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let repository: RunRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repository with test db
		repository = new RunRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findById', () => {
		it('should return run when exists', async () => {
			const run = await repository.findById('run_001');

			expect(run).not.toBeNull();
			expect(run?.id).toBe('run_001');
			expect(run?.status).toBe('success');
		});

		it('should return null when not found', async () => {
			const run = await repository.findById('nonexistent');

			expect(run).toBeNull();
		});

		it('should include all fields', async () => {
			const run = await repository.findById('run_001');

			expect(run?.id).toBeDefined();
			expect(run?.workbenchId).toBeDefined();
			expect(run?.jobVersionId).toBeDefined();
			expect(run?.status).toBeDefined();
			expect(run?.createdAt).toBeDefined();
			expect(run?.updatedAt).toBeDefined();
		});
	});

	describe('findByWorkbenchId', () => {
		it('should return runs for specified workbench', async () => {
			const runs = await repository.findByWorkbenchId('wb_001');

			expect(runs).toHaveLength(3);
			expect(runs.every((r) => r.workbenchId === 'wb_001')).toBe(true);
		});

		it('should order by createdAt descending (newest first)', async () => {
			const runs = await repository.findByWorkbenchId('wb_001');

			// run_003 (running) should come first as it's newest
			expect(runs[0].id).toBe('run_003');
			expect(runs[1].id).toBe('run_002');
			expect(runs[2].id).toBe('run_001');
		});

		it('should return empty array when no runs for workbench', async () => {
			const runs = await repository.findByWorkbenchId('nonexistent_wb');

			expect(runs).toHaveLength(0);
		});

		it('should support limit parameter', async () => {
			const runs = await repository.findByWorkbenchId('wb_001', { limit: 2 });

			expect(runs).toHaveLength(2);
		});

		it('should support offset parameter', async () => {
			const runs = await repository.findByWorkbenchId('wb_001', { offset: 1 });

			expect(runs).toHaveLength(2);
			expect(runs[0].id).toBe('run_002');
		});
	});

	describe('findActiveRuns', () => {
		it('should return runs with queued or running status', async () => {
			const activeRuns = await repository.findActiveRuns('wb_001');

			expect(activeRuns.length).toBeGreaterThan(0);
			activeRuns.forEach((run) => {
				expect(['queued', 'running']).toContain(run.status);
			});
		});

		it('should return empty array when no active runs', async () => {
			// Update all runs to terminal status
			await repository.updateStatus('run_002', 'success');
			await repository.updateStatus('run_003', 'failed');

			const activeRuns = await repository.findActiveRuns('wb_001');

			expect(activeRuns).toHaveLength(0);
		});
	});

	describe('create', () => {
		it('should create new run with queued status', async () => {
			const created = await repository.create({
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001'
			});

			expect(created.id).toMatch(/^run_/);
			expect(created.workbenchId).toBe('wb_001');
			expect(created.jobVersionId).toBe('jv_001');
			expect(created.status).toBe('queued');
		});

		it('should set timestamps on creation', async () => {
			const now = Date.now();
			const created = await repository.create({
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001'
			});

			expect(created.createdAt.getTime()).toBeGreaterThanOrEqual(now);
			expect(created.updatedAt.getTime()).toBeGreaterThanOrEqual(now);
		});

		it('should accept optional execution params', async () => {
			const created = await repository.create({
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				executionParams: JSON.stringify({ key: 'value' })
			});

			expect(created.executionParams).toBe(JSON.stringify({ key: 'value' }));
		});
	});

	describe('updateStatus', () => {
		it('should update status to running', async () => {
			const updated = await repository.updateStatus('run_002', 'running');

			expect(updated?.status).toBe('running');
		});

		it('should update status to success', async () => {
			const updated = await repository.updateStatus('run_003', 'success');

			expect(updated?.status).toBe('success');
		});

		it('should update status to failed', async () => {
			const updated = await repository.updateStatus('run_003', 'failed');

			expect(updated?.status).toBe('failed');
		});

		it('should set startedAt when transitioning to running', async () => {
			const updated = await repository.updateStatus('run_002', 'running');

			expect(updated?.startedAt).not.toBeNull();
		});

		it('should set completedAt when transitioning to terminal status', async () => {
			await repository.updateStatus('run_002', 'running');
			const updated = await repository.updateStatus('run_002', 'success');

			expect(updated?.completedAt).not.toBeNull();
		});

		it('should return null when run not found', async () => {
			const updated = await repository.updateStatus('nonexistent', 'success');

			expect(updated).toBeNull();
		});

		it('should update updatedAt timestamp', async () => {
			const before = await repository.findById('run_002');
			await new Promise((resolve) => setTimeout(resolve, 50));
			const updated = await repository.updateStatus('run_002', 'running');

			expect(updated?.updatedAt.getTime()).toBeGreaterThan(before!.updatedAt.getTime());
		});
	});

	describe('updateResult', () => {
		it('should update with success result', async () => {
			const updated = await repository.updateResult('run_003', {
				status: 'success',
				externalJobId: 'ext_job_123',
				externalTraceId: 'trace_123',
				resultSummary: 'All tasks completed successfully'
			});

			expect(updated?.status).toBe('success');
			expect(updated?.externalJobId).toBe('ext_job_123');
			expect(updated?.externalTraceId).toBe('trace_123');
			expect(updated?.resultSummary).toBe('All tasks completed successfully');
			expect(updated?.completedAt).not.toBeNull();
		});

		it('should update with failure result', async () => {
			const updated = await repository.updateResult('run_003', {
				status: 'failed',
				resultSummary: 'Task 3 failed: Connection timeout'
			});

			expect(updated?.status).toBe('failed');
			expect(updated?.resultSummary).toBe('Task 3 failed: Connection timeout');
		});

		it('should return null when run not found', async () => {
			const updated = await repository.updateResult('nonexistent', {
				status: 'success'
			});

			expect(updated).toBeNull();
		});
	});

	describe('getRunWithJobVersion', () => {
		it('should return run with job version details', async () => {
			const runWithVersion = await repository.getRunWithJobVersion('run_001');

			expect(runWithVersion).not.toBeNull();
			expect(runWithVersion?.run.id).toBe('run_001');
			expect(runWithVersion?.jobVersion.id).toBe('jv_001');
			expect(runWithVersion?.jobVersion.versionLabel).toBe('v3.1');
		});

		it('should return null when run not found', async () => {
			const runWithVersion = await repository.getRunWithJobVersion('nonexistent');

			expect(runWithVersion).toBeNull();
		});
	});

	describe('countByWorkbenchId', () => {
		it('should return correct count for workbench', async () => {
			const count = await repository.countByWorkbenchId('wb_001');

			expect(count).toBe(3);
		});

		it('should return 0 for workbench with no runs', async () => {
			const count = await repository.countByWorkbenchId('wb_002');

			expect(count).toBe(0);
		});
	});

	describe('getRecentRuns', () => {
		it('should return recent runs across all workbenches in project', async () => {
			const recentRuns = await repository.getRecentRuns('proj_001', 10);

			expect(recentRuns.length).toBeGreaterThan(0);
		});

		it('should respect limit parameter', async () => {
			const recentRuns = await repository.getRecentRuns('proj_001', 2);

			expect(recentRuns.length).toBeLessThanOrEqual(2);
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
			user_input_schema TEXT,
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
	`);
}

function seedTestData(db: ReturnType<typeof drizzle>) {
	const now = new Date();
	const earlier = new Date(now.getTime() - 3600000); // 1 hour ago
	const earliest = new Date(now.getTime() - 7200000); // 2 hours ago

	// Create project
	db.insert(schema.project)
		.values([
			{
				id: 'proj_001',
				externalProjectId: 'ext_proj_001',
				name: 'Test Project 1',
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
				createdAt: earliest,
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
				content: '# Requirements',
				status: 'active',
				createdAt: earliest,
				updatedAt: earliest
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
				majorVersion: 3,
				minorVersion: 1,
				versionLabel: 'v3.1',
				status: 'success',
				generatedAt: earlier,
				createdAt: earlier,
				updatedAt: earlier
			}
		])
		.run();

	// Create runs for wb_001
	db.insert(schema.run)
		.values([
			{
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'success',
				externalJobId: 'ext_job_001',
				externalTraceId: 'trace_001',
				startedAt: earliest,
				completedAt: earlier,
				createdAt: earliest,
				updatedAt: earlier
			},
			{
				id: 'run_002',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'queued',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'run_003',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'running',
				startedAt: now,
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
