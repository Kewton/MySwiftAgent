/**
 * Review Page Server Tests
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Tests for the Review page server-side load function.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { JobVersionRepository } from '$lib/server/repositories/job-version';
import { RequirementVersionRepository } from '$lib/server/repositories/requirement-version';

describe('Review Page Server Load', () => {
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

	describe('load function logic', () => {
		it('should return job versions sorted by version descending', async () => {
			const workbenchId = 'wb_001';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);

			// Should return in descending order (newest first)
			expect(jobVersions.length).toBeGreaterThan(0);

			// Check sorting: each version should be >= next version
			for (let i = 0; i < jobVersions.length - 1; i++) {
				const current = jobVersions[i];
				const next = jobVersions[i + 1];

				const currentVersion = current.majorVersion * 100 + current.minorVersion;
				const nextVersion = next.majorVersion * 100 + next.minorVersion;

				expect(currentVersion).toBeGreaterThanOrEqual(nextVersion);
			}
		});

		it('should include all required fields for list display', async () => {
			const workbenchId = 'wb_001';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);
			const jv = jobVersions[0];

			expect(jv).toHaveProperty('id');
			expect(jv).toHaveProperty('versionLabel');
			expect(jv).toHaveProperty('status');
			expect(jv).toHaveProperty('sourceRequirementVersionId');
			expect(jv).toHaveProperty('majorVersion');
			expect(jv).toHaveProperty('minorVersion');
			expect(jv).toHaveProperty('createdAt');
		});

		it('should format version label as vN.M', async () => {
			const workbenchId = 'wb_001';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);

			for (const jv of jobVersions) {
				expect(jv.versionLabel).toMatch(/^v\d+\.\d+$/);
				// Verify version label matches actual version numbers
				expect(jv.versionLabel).toBe(`v${jv.majorVersion}.${jv.minorVersion}`);
			}
		});

		it('should return empty array when no job versions exist', async () => {
			const workbenchId = 'wb_nonexistent';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);

			expect(jobVersions).toHaveLength(0);
		});
	});

	describe('status display', () => {
		it('should correctly identify active job versions', async () => {
			const workbenchId = 'wb_001';

			// Create an active job version
			const jv = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 5,
				minorVersion: 1
			});

			await jobVersionRepo.updateStatus(jv.id, 'active');

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);
			const activeJv = jobVersions.find((v) => v.id === jv.id);

			expect(activeJv?.status).toBe('active');
		});

		it('should correctly identify deprecated job versions', async () => {
			const workbenchId = 'wb_001';

			// Create a deprecated job version
			const jv = await jobVersionRepo.create({
				workbenchId,
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 5,
				minorVersion: 2
			});

			await jobVersionRepo.updateStatus(jv.id, 'deprecated');

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);
			const deprecatedJv = jobVersions.find((v) => v.id === jv.id);

			expect(deprecatedJv?.status).toBe('deprecated');
		});

		it('should handle all valid status values', async () => {
			const validStatuses = ['generating', 'success', 'failed', 'active', 'deprecated'] as const;

			for (const status of validStatuses) {
				expect(schema.JOB_VERSION_STATUSES).toContain(status);
			}
		});
	});

	describe('source requirement version link', () => {
		it('should include source requirement version id for linking', async () => {
			const workbenchId = 'wb_001';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);

			for (const jv of jobVersions) {
				expect(jv.sourceRequirementVersionId).toBeTruthy();
				expect(jv.sourceRequirementVersionId).toMatch(/^rv_/);
			}
		});

		it('should allow lookup of source requirement version', async () => {
			const workbenchId = 'wb_001';

			const jobVersions = await jobVersionRepo.findByWorkbenchId(workbenchId);
			const jv = jobVersions[0];

			if (jv) {
				const reqVersion = await requirementVersionRepo.findById(jv.sourceRequirementVersionId);
				expect(reqVersion).not.toBeNull();
				expect(reqVersion?.version).toBe(jv.majorVersion);
			}
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

	// Create job versions
	db.insert(schema.jobVersion)
		.values([
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 1,
				versionLabel: 'v1.1',
				status: 'deprecated',
				taskBreakdown: JSON.stringify({
					tasks: [
						{
							task_id: 'tm_001',
							name: 'Fetch Data',
							description: 'Fetch data from API'
						}
					]
				}),
				createdAt: earliest,
				updatedAt: earliest
			},
			{
				id: 'jv_002',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_002',
				majorVersion: 2,
				minorVersion: 1,
				versionLabel: 'v2.1',
				status: 'active',
				taskBreakdown: JSON.stringify({
					tasks: [
						{
							task_id: 'tm_002',
							name: 'Process Data',
							description: 'Process the fetched data'
						}
					]
				}),
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'jv_003',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 3,
				minorVersion: 1,
				versionLabel: 'v3.1',
				status: 'success',
				taskBreakdown: JSON.stringify({
					tasks: [
						{
							task_id: 'tm_003',
							name: 'Generate Report',
							description: 'Generate a report'
						}
					]
				}),
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
