/**
 * RequirementVersionRepository Tests
 * Issue #290: Requirements List and Version Management
 *
 * Tests for the RequirementVersionRepository class that handles
 * database operations for requirement version entities.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { RequirementVersionRepository } from '$lib/server/repositories/requirement-version';

describe('RequirementVersionRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let repository: RequirementVersionRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repository with test db
		repository = new RequirementVersionRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findByWorkbenchId', () => {
		it('should return requirement versions for specified workbench', async () => {
			const versions = await repository.findByWorkbenchId('wb_001');

			expect(versions).toHaveLength(3);
			expect(versions.every((v) => v.id.startsWith('rv_'))).toBe(true);
		});

		it('should order by version descending', async () => {
			const versions = await repository.findByWorkbenchId('wb_001');

			// Verify order is descending by version
			expect(versions[0].version).toBe(3);
			expect(versions[1].version).toBe(2);
			expect(versions[2].version).toBe(1);
		});

		it('should return empty array when no versions for workbench', async () => {
			const versions = await repository.findByWorkbenchId('nonexistent_wb');

			expect(versions).toHaveLength(0);
		});

		it('should not return versions from other workbenches', async () => {
			const versions = await repository.findByWorkbenchId('wb_001');

			// rv_004 belongs to wb_002, should not appear
			const hasOtherWorkbench = versions.some((v) => v.id === 'rv_004');
			expect(hasOtherWorkbench).toBe(false);
		});
	});

	describe('findById', () => {
		it('should return requirement version when exists', async () => {
			const version = await repository.findById('rv_001');

			expect(version).not.toBeNull();
			expect(version?.id).toBe('rv_001');
			expect(version?.version).toBe(1);
			expect(version?.content).toContain('Initial requirements');
		});

		it('should return null when not found', async () => {
			const version = await repository.findById('nonexistent');

			expect(version).toBeNull();
		});

		it('should include all fields', async () => {
			const version = await repository.findById('rv_001');

			expect(version?.id).toBeDefined();
			expect(version?.workbenchId).toBeDefined();
			expect(version?.version).toBeDefined();
			expect(version?.content).toBeDefined();
			expect(version?.status).toBeDefined();
			expect(version?.changeSummary).toBeDefined();
			expect(version?.createdAt).toBeDefined();
			expect(version?.updatedAt).toBeDefined();
		});
	});

	describe('create', () => {
		it('should create new requirement version with next version number', async () => {
			const created = await repository.create('wb_001', {
				content: '# New Requirements\n\nThis is a new version.',
				changeSummary: 'Added new section'
			});

			expect(created.version).toBe(4); // wb_001 has v1, v2, v3
			expect(created.workbenchId).toBe('wb_001');
			expect(created.content).toContain('New Requirements');
			expect(created.status).toBe('draft');
		});

		it('should create version 1 for new workbench', async () => {
			const created = await repository.create('wb_003', {
				content: '# First Requirements'
			});

			expect(created.version).toBe(1);
		});

		it('should set status to draft by default', async () => {
			const created = await repository.create('wb_001', {
				content: '# Draft Requirements'
			});

			expect(created.status).toBe('draft');
		});
	});

	describe('update', () => {
		it('should update content', async () => {
			const updated = await repository.update('rv_001', {
				content: '# Updated Requirements'
			});

			expect(updated?.content).toBe('# Updated Requirements');
		});

		it('should update changeSummary', async () => {
			const updated = await repository.update('rv_001', {
				changeSummary: 'Updated summary'
			});

			expect(updated?.changeSummary).toBe('Updated summary');
		});

		it('should return null when version not found', async () => {
			const updated = await repository.update('nonexistent', {
				content: 'Updated'
			});

			expect(updated).toBeNull();
		});

		it('should update updatedAt timestamp', async () => {
			const before = await repository.findById('rv_001');
			await new Promise((resolve) => setTimeout(resolve, 10));
			const updated = await repository.update('rv_001', {
				content: 'Updated'
			});

			expect(updated?.updatedAt.getTime()).toBeGreaterThan(before!.updatedAt.getTime());
		});
	});

	describe('setActive', () => {
		it('should set version to active status', async () => {
			const result = await repository.setActive('wb_001', 'rv_002');

			expect(result?.status).toBe('active');
		});

		it('should set previous active version to deprecated', async () => {
			// rv_003 is currently active
			await repository.setActive('wb_001', 'rv_002');

			const previousActive = await repository.findById('rv_003');
			expect(previousActive?.status).toBe('deprecated');
		});

		it('should return null when version not found', async () => {
			const result = await repository.setActive('wb_001', 'nonexistent');

			expect(result).toBeNull();
		});

		it('should return null when version belongs to different workbench', async () => {
			const result = await repository.setActive('wb_001', 'rv_004'); // rv_004 belongs to wb_002

			expect(result).toBeNull();
		});
	});

	describe('updateStatus', () => {
		it('should update status to submitted', async () => {
			const updated = await repository.updateStatus('rv_001', 'submitted');

			expect(updated?.status).toBe('submitted');
		});

		it('should update status to deprecated', async () => {
			const updated = await repository.updateStatus('rv_003', 'deprecated');

			expect(updated?.status).toBe('deprecated');
		});

		it('should return null when version not found', async () => {
			const updated = await repository.updateStatus('nonexistent', 'submitted');

			expect(updated).toBeNull();
		});
	});

	describe('getNextVersion', () => {
		it('should return next version number', async () => {
			const nextVersion = await repository.getNextVersion('wb_001');

			expect(nextVersion).toBe(4);
		});

		it('should return 1 for new workbench', async () => {
			const nextVersion = await repository.getNextVersion('wb_003');

			expect(nextVersion).toBe(1);
		});
	});

	describe('findByWorkbenchAndVersion', () => {
		it('should find version by workbench and version number', async () => {
			const version = await repository.findByWorkbenchAndVersion('wb_001', 2);

			expect(version).not.toBeNull();
			expect(version?.id).toBe('rv_002');
			expect(version?.version).toBe(2);
		});

		it('should return null when version does not exist', async () => {
			const version = await repository.findByWorkbenchAndVersion('wb_001', 99);

			expect(version).toBeNull();
		});
	});

	describe('computeDiff', () => {
		it('should compute diff between two versions', async () => {
			const diff = await repository.computeDiff('rv_001', 'rv_002');

			expect(diff).not.toBeNull();
			expect(diff?.fromVersion).toBe(1);
			expect(diff?.toVersion).toBe(2);
			expect(diff?.diffs.length).toBeGreaterThan(0);
		});

		it('should return null when from version not found', async () => {
			const diff = await repository.computeDiff('nonexistent', 'rv_002');

			expect(diff).toBeNull();
		});

		it('should return null when to version not found', async () => {
			const diff = await repository.computeDiff('rv_001', 'nonexistent');

			expect(diff).toBeNull();
		});

		it('should identify insertions correctly', async () => {
			const diff = await repository.computeDiff('rv_001', 'rv_002');

			// rv_002 has additional content compared to rv_001
			const hasInsertions = diff?.diffs.some((d) => d.operation === 1);
			expect(hasInsertions).toBe(true);
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

	// Create requirement versions for wb_001
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
				content:
					'# Initial requirements\n\nThis is version 1.\n\n## Added section\n\nNew content for version 2.',
				status: 'deprecated',
				changeSummary: 'Added new section',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'rv_003',
				workbenchId: 'wb_001',
				version: 3,
				content:
					'# Requirements v3\n\nCompletely rewritten.\n\n## New Structure\n\nBetter organization.',
				status: 'active',
				changeSummary: 'Major rewrite',
				createdAt: now,
				updatedAt: now
			},
			// Version for wb_002
			{
				id: 'rv_004',
				workbenchId: 'wb_002',
				version: 1,
				content: '# WB2 Requirements',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
