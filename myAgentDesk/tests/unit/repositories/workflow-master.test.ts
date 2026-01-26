/**
 * WorkflowMasterRepository Tests
 * Issue #305: Workflow Generation Progress Display
 *
 * Tests for the WorkflowMasterRepository class that handles
 * database operations for workflow master entities.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { WorkflowMasterRepository } from '$lib/server/repositories/workflow-master';

describe('WorkflowMasterRepository', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let repository: WorkflowMasterRepository;

	beforeEach(() => {
		// Create in-memory database for testing
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });

		// Create tables
		createTables(sqlite);

		// Create repository with test db
		repository = new WorkflowMasterRepository(db);

		// Seed test data
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findById', () => {
		it('should return workflow master when exists', async () => {
			const workflowMaster = await repository.findById('wm_001');

			expect(workflowMaster).not.toBeNull();
			expect(workflowMaster?.id).toBe('wm_001');
			expect(workflowMaster?.taskMasterId).toBe('tm_001');
			expect(workflowMaster?.workflowName).toBe('workflow_gmail_fetch');
			expect(workflowMaster?.status).toBe('success');
		});

		it('should return null when not found', async () => {
			const workflowMaster = await repository.findById('nonexistent');

			expect(workflowMaster).toBeNull();
		});

		it('should include all fields', async () => {
			const workflowMaster = await repository.findById('wm_001');

			expect(workflowMaster?.id).toBeDefined();
			expect(workflowMaster?.taskMasterId).toBeDefined();
			expect(workflowMaster?.workflowName).toBeDefined();
			expect(workflowMaster?.yamlContent).toBeDefined();
			expect(workflowMaster?.status).toBeDefined();
			expect(workflowMaster?.generationTimeMs).toBeDefined();
			expect(workflowMaster?.langfuseTraceId).toBeDefined();
			expect(workflowMaster?.createdAt).toBeDefined();
			expect(workflowMaster?.updatedAt).toBeDefined();
		});
	});

	describe('findByTaskMasterId', () => {
		it('should return workflow master by task master id', async () => {
			const workflowMaster = await repository.findByTaskMasterId('tm_001');

			expect(workflowMaster).not.toBeNull();
			expect(workflowMaster?.taskMasterId).toBe('tm_001');
		});

		it('should return null when not found', async () => {
			const workflowMaster = await repository.findByTaskMasterId('nonexistent');

			expect(workflowMaster).toBeNull();
		});
	});

	describe('findByJobVersionId', () => {
		it('should return all workflow masters for a job version', async () => {
			const workflowMasters = await repository.findByJobVersionId('jv_001');

			expect(workflowMasters.length).toBe(3);
			expect(workflowMasters.every((wm) => wm.id.startsWith('wm_'))).toBe(true);
		});

		it('should return empty array when no workflow masters', async () => {
			const workflowMasters = await repository.findByJobVersionId('nonexistent');

			expect(workflowMasters).toHaveLength(0);
		});

		it('should order by created at descending', async () => {
			const workflowMasters = await repository.findByJobVersionId('jv_001');

			// wm_003 should be first (most recent)
			expect(workflowMasters[0].id).toBe('wm_003');
		});
	});

	describe('create', () => {
		it('should create new workflow master with pending status', async () => {
			const created = await repository.create({
				taskMasterId: 'tm_new',
				workflowName: 'workflow_new',
				yamlContent: 'version: 0.6\nnodes: {}'
			});

			expect(created.id).toMatch(/^wm_/);
			expect(created.taskMasterId).toBe('tm_new');
			expect(created.workflowName).toBe('workflow_new');
			expect(created.yamlContent).toBe('version: 0.6\nnodes: {}');
			expect(created.status).toBe('pending');
		});

		it('should set timestamps on creation', async () => {
			const now = Date.now();
			const created = await repository.create({
				taskMasterId: 'tm_new2',
				workflowName: 'workflow_new2',
				yamlContent: 'version: 0.6'
			});

			expect(created.createdAt.getTime()).toBeGreaterThanOrEqual(now);
			expect(created.updatedAt.getTime()).toBeGreaterThanOrEqual(now);
		});
	});

	describe('updateStatus', () => {
		it('should update status to generating', async () => {
			const updated = await repository.updateStatus('wm_003', 'generating');

			expect(updated?.status).toBe('generating');
		});

		it('should update status to success with generation time', async () => {
			const updated = await repository.updateGenerationResult('wm_003', {
				status: 'success',
				generationTimeMs: 28500
			});

			expect(updated?.status).toBe('success');
			expect(updated?.generationTimeMs).toBe(28500);
		});

		it('should update status to failed with error message', async () => {
			const updated = await repository.updateGenerationResult('wm_003', {
				status: 'failed',
				errorMessage: 'API rate limit exceeded'
			});

			expect(updated?.status).toBe('failed');
			expect(updated?.errorMessage).toBe('API rate limit exceeded');
		});

		it('should return null when not found', async () => {
			const updated = await repository.updateStatus('nonexistent', 'success');

			expect(updated).toBeNull();
		});
	});

	describe('updateGenerationResult', () => {
		it('should update with complete result', async () => {
			const updated = await repository.updateGenerationResult('wm_003', {
				status: 'success',
				yamlContent: 'version: 0.6\nnodes:\n  fetchNode: {}',
				generationTimeMs: 32100,
				langfuseTraceId: 'trace_new_123'
			});

			expect(updated?.status).toBe('success');
			expect(updated?.yamlContent).toBe('version: 0.6\nnodes:\n  fetchNode: {}');
			expect(updated?.generationTimeMs).toBe(32100);
			expect(updated?.langfuseTraceId).toBe('trace_new_123');
		});

		it('should update updatedAt timestamp', async () => {
			const before = await repository.findById('wm_003');
			await new Promise((resolve) => setTimeout(resolve, 50));
			const updated = await repository.updateGenerationResult('wm_003', {
				status: 'success',
				generationTimeMs: 30000
			});

			expect(updated?.updatedAt.getTime()).toBeGreaterThanOrEqual(before!.updatedAt.getTime());
		});
	});

	describe('bulkCreate', () => {
		it('should create multiple workflow masters at once', async () => {
			const created = await repository.bulkCreate([
				{
					taskMasterId: 'tm_bulk_1',
					workflowName: 'workflow_bulk_1',
					yamlContent: 'version: 0.6'
				},
				{
					taskMasterId: 'tm_bulk_2',
					workflowName: 'workflow_bulk_2',
					yamlContent: 'version: 0.6'
				}
			]);

			expect(created.length).toBe(2);
			expect(created[0].taskMasterId).toBe('tm_bulk_1');
			expect(created[1].taskMasterId).toBe('tm_bulk_2');
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

		CREATE TABLE IF NOT EXISTS workflow_masters (
			id TEXT PRIMARY KEY NOT NULL,
			task_master_id TEXT NOT NULL UNIQUE,
			job_version_id TEXT REFERENCES job_version(id),
			workflow_name TEXT NOT NULL,
			yaml_content TEXT NOT NULL,
			status TEXT NOT NULL DEFAULT 'pending',
			generation_time_ms INTEGER,
			error_message TEXT,
			langfuse_trace_id TEXT,
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

	// Create workbench
	db.insert(schema.workbench)
		.values([
			{
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Workbench 1',
				description: 'First workbench',
				status: 'active',
				createdAt: earliest,
				updatedAt: now
			}
		])
		.run();

	// Create requirement version
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

	// Create job version
	db.insert(schema.jobVersion)
		.values([
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 1,
				versionLabel: 'v1.1',
				status: 'success',
				createdAt: earlier,
				updatedAt: earlier
			}
		])
		.run();

	// Create workflow masters
	db.insert(schema.workflowMasters)
		.values([
			{
				id: 'wm_001',
				taskMasterId: 'tm_001',
				jobVersionId: 'jv_001',
				workflowName: 'workflow_gmail_fetch',
				yamlContent: 'version: 0.6\nnodes:\n  gmailNode: {}',
				status: 'success',
				generationTimeMs: 28500,
				langfuseTraceId: 'trace_001',
				createdAt: earliest,
				updatedAt: earliest
			},
			{
				id: 'wm_002',
				taskMasterId: 'tm_002',
				jobVersionId: 'jv_001',
				workflowName: 'workflow_claude_summarize',
				yamlContent: 'version: 0.6\nnodes:\n  claudeNode: {}',
				status: 'success',
				generationTimeMs: 32100,
				langfuseTraceId: 'trace_002',
				createdAt: earlier,
				updatedAt: earlier
			},
			{
				id: 'wm_003',
				taskMasterId: 'tm_003',
				jobVersionId: 'jv_001',
				workflowName: 'workflow_slack_post',
				yamlContent: 'version: 0.6',
				status: 'pending',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
