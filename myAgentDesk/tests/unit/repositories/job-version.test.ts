/**
 * JobVersionRepository Tests
 * Issue #291: Generate Page (Job Generation)
 *
 * Tests for the JobVersionRepository class that handles
 * database operations for job version entities.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { JobVersionRepository } from '$lib/server/repositories/job-version';

describe('JobVersionRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let repository: JobVersionRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repository with test db
		repository = new JobVersionRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findById', () => {
		it('should return job version when exists', async () => {
			const jobVersion = await repository.findById('jv_001');

			expect(jobVersion).not.toBeNull();
			expect(jobVersion?.id).toBe('jv_001');
			expect(jobVersion?.versionLabel).toBe('v3.1');
			expect(jobVersion?.status).toBe('success');
		});

		it('should return null when not found', async () => {
			const jobVersion = await repository.findById('nonexistent');

			expect(jobVersion).toBeNull();
		});

		it('should include all fields', async () => {
			const jobVersion = await repository.findById('jv_001');

			expect(jobVersion?.id).toBeDefined();
			expect(jobVersion?.workbenchId).toBeDefined();
			expect(jobVersion?.sourceRequirementVersionId).toBeDefined();
			expect(jobVersion?.majorVersion).toBeDefined();
			expect(jobVersion?.minorVersion).toBeDefined();
			expect(jobVersion?.versionLabel).toBeDefined();
			expect(jobVersion?.status).toBeDefined();
			expect(jobVersion?.createdAt).toBeDefined();
			expect(jobVersion?.updatedAt).toBeDefined();
		});
	});

	describe('findByWorkbenchId', () => {
		it('should return job versions for specified workbench', async () => {
			const versions = await repository.findByWorkbenchId('wb_001');

			expect(versions).toHaveLength(2);
			expect(versions.every((v) => v.workbenchId === 'wb_001')).toBe(true);
		});

		it('should order by version descending (majorVersion, then minorVersion)', async () => {
			const versions = await repository.findByWorkbenchId('wb_001');

			// jv_002 (v3.2) should come before jv_001 (v3.1)
			expect(versions[0].versionLabel).toBe('v3.2');
			expect(versions[1].versionLabel).toBe('v3.1');
		});

		it('should return empty array when no versions for workbench', async () => {
			const versions = await repository.findByWorkbenchId('nonexistent_wb');

			expect(versions).toHaveLength(0);
		});
	});

	describe('findGenerating', () => {
		it('should return job versions with generating status', async () => {
			const generatingVersions = await repository.findGenerating('wb_001');

			expect(generatingVersions).toHaveLength(1);
			expect(generatingVersions[0].status).toBe('generating');
			expect(generatingVersions[0].id).toBe('jv_002');
		});

		it('should return empty array when no generating versions', async () => {
			// First update jv_002 to not be generating
			await repository.updateStatus('jv_002', 'success');
			const generatingVersions = await repository.findGenerating('wb_001');

			expect(generatingVersions).toHaveLength(0);
		});
	});

	describe('create', () => {
		it('should create new job version with generating status', async () => {
			const created = await repository.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 3
			});

			expect(created.id).toMatch(/^jv_/);
			expect(created.workbenchId).toBe('wb_001');
			expect(created.sourceRequirementVersionId).toBe('rv_003');
			expect(created.majorVersion).toBe(3);
			expect(created.minorVersion).toBe(3);
			expect(created.versionLabel).toBe('v3.3');
			expect(created.status).toBe('generating');
		});

		it('should set timestamps on creation', async () => {
			const now = Date.now();
			const created = await repository.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 4
			});

			expect(created.createdAt.getTime()).toBeGreaterThanOrEqual(now);
			expect(created.updatedAt.getTime()).toBeGreaterThanOrEqual(now);
		});
	});

	describe('updateStatus', () => {
		it('should update status to success', async () => {
			const updated = await repository.updateStatus('jv_002', 'success');

			expect(updated?.status).toBe('success');
		});

		it('should update status to failed', async () => {
			const updated = await repository.updateStatus('jv_002', 'failed');

			expect(updated?.status).toBe('failed');
		});

		it('should update status to active', async () => {
			const updated = await repository.updateStatus('jv_001', 'active');

			expect(updated?.status).toBe('active');
		});

		it('should return null when version not found', async () => {
			const updated = await repository.updateStatus('nonexistent', 'success');

			expect(updated).toBeNull();
		});

		it('should update updatedAt timestamp', async () => {
			const before = await repository.findById('jv_002');
			await new Promise((resolve) => setTimeout(resolve, 50));
			const updated = await repository.updateStatus('jv_002', 'success');

			expect(updated?.updatedAt.getTime()).toBeGreaterThanOrEqual(before!.updatedAt.getTime());
		});
	});

	describe('updateGenerationResult', () => {
		it('should update with success result', async () => {
			const updated = await repository.updateGenerationResult('jv_002', {
				status: 'success',
				taskBreakdown: JSON.stringify({ tasks: ['task1', 'task2'] }),
				interfaceDefinitions: JSON.stringify({ interfaces: {} }),
				workflows: JSON.stringify({ workflow: 'test' }),
				externalJobMasterId: 'ext_job_123',
				externalTraceId: 'trace_123'
			});

			expect(updated?.status).toBe('success');
			expect(updated?.taskBreakdown).toBe(JSON.stringify({ tasks: ['task1', 'task2'] }));
			expect(updated?.interfaceDefinitions).toBe(JSON.stringify({ interfaces: {} }));
			expect(updated?.workflows).toBe(JSON.stringify({ workflow: 'test' }));
			expect(updated?.externalJobMasterId).toBe('ext_job_123');
			expect(updated?.externalTraceId).toBe('trace_123');
			expect(updated?.generatedAt).not.toBeNull();
		});

		it('should update with failure result', async () => {
			const updated = await repository.updateGenerationResult('jv_002', {
				status: 'failed',
				errorMessage: 'Generation failed due to timeout'
			});

			expect(updated?.status).toBe('failed');
			expect(updated?.errorMessage).toBe('Generation failed due to timeout');
		});

		it('should return null when version not found', async () => {
			const updated = await repository.updateGenerationResult('nonexistent', {
				status: 'success'
			});

			expect(updated).toBeNull();
		});
	});

	describe('getNextVersion', () => {
		it('should return next minor version for existing major version', async () => {
			const nextVersion = await repository.getNextVersion('wb_001', 3);

			// wb_001 has v3.1 and v3.2, so next should be 3
			expect(nextVersion).toBe(3);
		});

		it('should return 1 for new major version', async () => {
			const nextVersion = await repository.getNextVersion('wb_001', 4);

			expect(nextVersion).toBe(1);
		});

		it('should return 1 for workbench with no versions', async () => {
			const nextVersion = await repository.getNextVersion('wb_003', 1);

			expect(nextVersion).toBe(1);
		});
	});

	describe('version label format', () => {
		it('should format version label as vN.M', async () => {
			const created = await repository.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 5,
				minorVersion: 2
			});

			expect(created.versionLabel).toBe('v5.2');
		});

		it('should handle single digit versions', async () => {
			const created = await repository.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 1,
				minorVersion: 1
			});

			expect(created.versionLabel).toBe('v1.1');
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
				activeRequirementVersionId: 'rv_003',
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
			},
			{
				id: 'wb_003',
				projectId: 'proj_001',
				name: 'Workbench 3 (No versions)',
				status: 'draft',
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
				content: '# Initial requirements\n\nThis is version 1.',
				status: 'deprecated',
				changeSummary: 'Initial version',
				createdAt: earliest,
				updatedAt: earliest
			},
			{
				id: 'rv_002',
				workbenchId: 'wb_001',
				version: 2,
				content: '# Requirements v2\n\nUpdated version.',
				status: 'deprecated',
				changeSummary: 'Second version',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'rv_003',
				workbenchId: 'wb_001',
				version: 3,
				content: '# Requirements v3\n\nCurrent active version.',
				status: 'active',
				changeSummary: 'Third version',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create job versions for wb_001
	db.insert(schema.jobVersion)
		.values([
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 1,
				versionLabel: 'v3.1',
				status: 'success',
				taskBreakdown: JSON.stringify({ tasks: ['task1'] }),
				interfaceDefinitions: JSON.stringify({}),
				workflows: JSON.stringify({ flow: 'test' }),
				externalJobMasterId: 'ext_jm_001',
				externalTraceId: 'trace_001',
				generatedAt: earlier,
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'jv_002',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 2,
				versionLabel: 'v3.2',
				status: 'generating',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
