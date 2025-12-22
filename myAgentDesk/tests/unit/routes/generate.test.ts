/**
 * Generate Page Form Action Tests
 * Issue #291: Generate Page (Job Generation)
 *
 * Tests for the Generate page server-side form actions.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { JobVersionRepository } from '$lib/server/repositories/job-version';
import { RequirementVersionRepository } from '$lib/server/repositories/requirement-version';

describe('Generate Page Form Actions', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let jobVersionRepo: JobVersionRepository;
	let requirementVersionRepo: RequirementVersionRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repositories with test db
		jobVersionRepo = new JobVersionRepository(db);
		requirementVersionRepo = new RequirementVersionRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('generateJob action logic', () => {
		it('should create job version with correct majorVersion from requirement version', async () => {
			// Simulate the action logic
			const workbenchId = 'wb_001';
			const reqVersionId = 'rv_003';

			// Get the active requirement version
			const reqVersion = await requirementVersionRepo.findById(reqVersionId);
			expect(reqVersion).not.toBeNull();
			expect(reqVersion?.version).toBe(3);

			// Calculate version numbers
			const majorVersion = reqVersion!.version;
			const minorVersion = await jobVersionRepo.getNextVersion(workbenchId, majorVersion);

			// Create new job version
			const newJobVersion = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: reqVersionId,
				majorVersion,
				minorVersion
			});

			expect(newJobVersion.majorVersion).toBe(3);
			expect(newJobVersion.minorVersion).toBe(1);
			expect(newJobVersion.versionLabel).toBe('v3.1');
			expect(newJobVersion.status).toBe('generating');
		});

		it('should increment minorVersion for subsequent generations from same requirement', async () => {
			const workbenchId = 'wb_001';
			const reqVersionId = 'rv_003';

			// Create first job version
			const first = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: reqVersionId,
				majorVersion: 3,
				minorVersion: 1
			});

			// Get next minor version
			const nextMinor = await jobVersionRepo.getNextVersion(workbenchId, 3);
			expect(nextMinor).toBe(2);

			// Create second job version
			const second = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: reqVersionId,
				majorVersion: 3,
				minorVersion: nextMinor
			});

			expect(first.versionLabel).toBe('v3.1');
			expect(second.versionLabel).toBe('v3.2');
		});

		it('should check for existing generating jobs', async () => {
			const workbenchId = 'wb_001';
			const reqVersionId = 'rv_003';

			// Create a generating job
			await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: reqVersionId,
				majorVersion: 3,
				minorVersion: 1
			});

			// Check for generating jobs
			const generatingJobs = await jobVersionRepo.findGenerating(workbenchId);
			expect(generatingJobs).toHaveLength(1);
		});
	});

	describe('version numbering rules', () => {
		it('should format version as vN.M where N is requirement version', async () => {
			// Test for v1.1, v1.2, v2.1 scenarios
			const workbenchId = 'wb_001';

			// v1.1 from requirement v1
			const v1_1 = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 1
			});
			expect(v1_1.versionLabel).toBe('v1.1');

			// v1.2 from requirement v1
			const v1_2 = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 2
			});
			expect(v1_2.versionLabel).toBe('v1.2');

			// v2.1 from requirement v2
			const v2_1 = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_002',
				majorVersion: 2,
				minorVersion: 1
			});
			expect(v2_1.versionLabel).toBe('v2.1');
		});

		it('should correctly calculate next minor version for each major version', async () => {
			const workbenchId = 'wb_001';

			// Create some job versions
			await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 1
			});

			await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 2
			});

			await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_002',
				majorVersion: 2,
				minorVersion: 1
			});

			// Check next versions
			expect(await jobVersionRepo.getNextVersion(workbenchId, 1)).toBe(3);
			expect(await jobVersionRepo.getNextVersion(workbenchId, 2)).toBe(2);
			expect(await jobVersionRepo.getNextVersion(workbenchId, 3)).toBe(1);
		});
	});

	describe('job status lifecycle', () => {
		it('should start with generating status', async () => {
			const job = await jobVersionRepo.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 1
			});

			expect(job.status).toBe('generating');
		});

		it('should transition to success on completion', async () => {
			const job = await jobVersionRepo.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 1
			});

			const updated = await jobVersionRepo.updateGenerationResult(job.id, {
				status: 'success',
				taskBreakdown: '{"tasks": []}',
				externalJobMasterId: 'ext_123',
				externalTraceId: 'trace_123'
			});

			expect(updated?.status).toBe('success');
			expect(updated?.generatedAt).not.toBeNull();
		});

		it('should transition to failed on error', async () => {
			const job = await jobVersionRepo.create({
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 1
			});

			const updated = await jobVersionRepo.updateGenerationResult(job.id, {
				status: 'failed',
				errorMessage: 'Timeout: Job generation exceeded 5 minutes'
			});

			expect(updated?.status).toBe('failed');
			expect(updated?.errorMessage).toBe('Timeout: Job generation exceeded 5 minutes');
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
				content: '# Requirements v1',
				status: 'deprecated',
				createdAt: earliest,
				updatedAt: earliest
			},
			{
				id: 'rv_002',
				workbenchId: 'wb_001',
				version: 2,
				content: '# Requirements v2',
				status: 'deprecated',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'rv_003',
				workbenchId: 'wb_001',
				version: 3,
				content: '# Requirements v3',
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
