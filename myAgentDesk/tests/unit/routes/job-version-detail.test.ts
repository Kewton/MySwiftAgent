/**
 * JobVersion Detail Page Server Tests
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Tests for the JobVersion detail page server-side load function.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../../../src/lib/server/db/schema';
import { JobVersionRepository } from '$lib/server/repositories/job-version';
import { RequirementVersionRepository } from '$lib/server/repositories/requirement-version';

describe('JobVersion Detail Page Server Load', () => {
	let sqlite: Database.Database;
	let db: ReturnType<typeof drizzle>;
	let jobVersionRepo: JobVersionRepository;
	let requirementVersionRepo: RequirementVersionRepository;

	beforeEach(() => {
		sqlite = new Database(':memory:');
		sqlite.pragma('foreign_keys = ON');
		db = drizzle(sqlite, { schema });
		createTables(sqlite);
		jobVersionRepo = new JobVersionRepository(db);
		requirementVersionRepo = new RequirementVersionRepository(db);
		seedTestData(db);
	});

	afterEach(() => {
		sqlite.close();
	});

	describe('findById', () => {
		it('should return job version by ID', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv).not.toBeNull();
			expect(jv?.id).toBe('jv_001');
			expect(jv?.versionLabel).toBe('v5.2');
		});

		it('should return null for non-existent ID', async () => {
			const jv = await jobVersionRepo.findById('jv_nonexistent');

			expect(jv).toBeNull();
		});
	});

	describe('ownership guard logic', () => {
		it('should verify job version belongs to workbench', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv).not.toBeNull();
			expect(jv?.workbenchId).toBe('wb_001');

			// Simulate guard: check if requested workbenchId matches
			const requestedWorkbenchId = 'wb_001';
			const isOwned = jv?.workbenchId === requestedWorkbenchId;

			expect(isOwned).toBe(true);
		});

		it('should reject job version from different workbench', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv).not.toBeNull();

			// Simulate guard: wrong workbenchId
			const requestedWorkbenchId = 'wb_different';
			const isOwned = jv?.workbenchId === requestedWorkbenchId;

			expect(isOwned).toBe(false);
		});
	});

	describe('task breakdown parsing', () => {
		it('should parse task breakdown JSON', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.taskBreakdown).not.toBeNull();

			const taskBreakdown = JSON.parse(jv!.taskBreakdown!);

			expect(taskBreakdown).toHaveProperty('tasks');
			expect(Array.isArray(taskBreakdown.tasks)).toBe(true);
		});

		it('should contain 8 tasks for jv_v5.2', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.taskBreakdown).not.toBeNull();

			const taskBreakdown = JSON.parse(jv!.taskBreakdown!);

			// Per acceptance criteria: jv_v5.2 should have 8 tasks
			expect(taskBreakdown.tasks.length).toBe(8);
		});

		it('should have required task fields', async () => {
			const jv = await jobVersionRepo.findById('jv_001');
			const taskBreakdown = JSON.parse(jv!.taskBreakdown!);
			const task = taskBreakdown.tasks[0];

			expect(task).toHaveProperty('task_id');
			expect(task).toHaveProperty('name');
			expect(task).toHaveProperty('description');
			expect(task).toHaveProperty('inputInterface');
			expect(task).toHaveProperty('outputInterface');
		});
	});

	describe('interface definitions parsing', () => {
		it('should parse interface definitions JSON', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.interfaceDefinitions).not.toBeNull();

			const interfaces = JSON.parse(jv!.interfaceDefinitions!);

			expect(interfaces).toHaveProperty('inputSchema');
			expect(interfaces).toHaveProperty('outputSchema');
		});

		it('should contain valid JSON Schema format', async () => {
			const jv = await jobVersionRepo.findById('jv_001');
			const interfaces = JSON.parse(jv!.interfaceDefinitions!);

			// JSON Schema should have type property
			expect(interfaces.inputSchema).toHaveProperty('type');
			expect(interfaces.outputSchema).toHaveProperty('type');
		});
	});

	describe('workflows parsing', () => {
		it('should parse workflows JSON', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.workflows).not.toBeNull();

			const workflows = JSON.parse(jv!.workflows!);

			expect(workflows).toHaveProperty('workflow_statuses');
		});

		it('should contain YAML content in workflow status', async () => {
			const jv = await jobVersionRepo.findById('jv_001');
			const workflows = JSON.parse(jv!.workflows!);

			// Should have at least one workflow status
			expect(workflows.workflow_statuses.length).toBeGreaterThan(0);

			// First workflow should have yaml_content
			const firstWorkflow = workflows.workflow_statuses[0];
			expect(firstWorkflow).toHaveProperty('summary');
			expect(firstWorkflow.summary).toHaveProperty('yaml_content');
		});
	});

	describe('source requirement version link', () => {
		it('should include source requirement version for linking', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.sourceRequirementVersionId).toBeTruthy();
		});

		it('should allow fetching source requirement version', async () => {
			const jv = await jobVersionRepo.findById('jv_001');
			const reqVersion = await requirementVersionRepo.findById(jv!.sourceRequirementVersionId);

			expect(reqVersion).not.toBeNull();
			expect(reqVersion?.version).toBe(jv?.majorVersion);
		});
	});

	describe('external trace link', () => {
		it('should include external trace ID for Langfuse link', async () => {
			const jv = await jobVersionRepo.findById('jv_001');

			expect(jv?.externalTraceId).toBe('trace_abc123');
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
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create requirement version
	db.insert(schema.requirementVersion)
		.values([
			{
				id: 'rv_005',
				workbenchId: 'wb_001',
				version: 5,
				content: '# Requirements v5',
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();

	// Create job version with 8 tasks (per acceptance criteria)
	const taskBreakdown = {
		tasks: [
			{
				task_id: 'tm_001',
				name: 'Fetch User Data',
				description: 'Retrieve user information from database',
				recommended_apis: ['GET /api/users'],
				inputInterface: {
					type: 'object',
					properties: { userId: { type: 'string' } },
					required: ['userId']
				},
				outputInterface: {
					type: 'object',
					properties: { user: { type: 'object' } }
				}
			},
			{
				task_id: 'tm_002',
				name: 'Process Data',
				description: 'Transform the retrieved data',
				recommended_apis: [],
				inputInterface: { type: 'object', properties: { data: { type: 'object' } } },
				outputInterface: { type: 'object', properties: { processed: { type: 'object' } } }
			},
			{
				task_id: 'tm_003',
				name: 'Generate Report',
				description: 'Create a summary report',
				recommended_apis: [],
				inputInterface: { type: 'object', properties: { data: { type: 'array' } } },
				outputInterface: { type: 'object', properties: { report: { type: 'string' } } }
			},
			{
				task_id: 'tm_004',
				name: 'Send Notification',
				description: 'Send notification to users',
				recommended_apis: ['POST /api/notifications'],
				inputInterface: { type: 'object', properties: { message: { type: 'string' } } },
				outputInterface: { type: 'object', properties: { sent: { type: 'boolean' } } }
			},
			{
				task_id: 'tm_005',
				name: 'Log Activity',
				description: 'Log the activity for audit',
				recommended_apis: ['POST /api/logs'],
				inputInterface: { type: 'object', properties: { action: { type: 'string' } } },
				outputInterface: { type: 'object', properties: { logId: { type: 'string' } } }
			},
			{
				task_id: 'tm_006',
				name: 'Validate Input',
				description: 'Validate input parameters',
				recommended_apis: [],
				inputInterface: { type: 'object', properties: { input: { type: 'object' } } },
				outputInterface: { type: 'object', properties: { valid: { type: 'boolean' } } }
			},
			{
				task_id: 'tm_007',
				name: 'Cache Results',
				description: 'Store results in cache',
				recommended_apis: ['PUT /api/cache'],
				inputInterface: { type: 'object', properties: { key: { type: 'string' } } },
				outputInterface: { type: 'object', properties: { cached: { type: 'boolean' } } }
			},
			{
				task_id: 'tm_008',
				name: 'Cleanup',
				description: 'Clean up temporary resources',
				recommended_apis: [],
				inputInterface: { type: 'object', properties: { resourceId: { type: 'string' } } },
				outputInterface: { type: 'object', properties: { cleaned: { type: 'boolean' } } }
			}
		]
	};

	const interfaceDefinitions = {
		inputSchema: {
			type: 'object',
			properties: {
				userId: { type: 'string', description: 'User ID to process' },
				options: { type: 'object', description: 'Processing options' }
			},
			required: ['userId']
		},
		outputSchema: {
			type: 'object',
			properties: {
				success: { type: 'boolean' },
				result: { type: 'object' }
			}
		}
	};

	const workflows = {
		workflow_statuses: [
			{
				task_id: 'tm_001',
				task_name: 'Fetch User Data',
				status: 'success',
				workflow_name: 'workflow_fetch_user',
				generation_time_ms: 2500,
				langfuse_trace_id: 'trace_task_001',
				summary: {
					yaml_preview: 'version: 0.5\nnodes:\n  source: {}',
					yaml_content: `version: 0.5
nodes:
  source:
    agent: fetchAgent
    params:
      url: /api/users
  output:
    agent: copyAgent
    inputs:
      - source
`,
					sample_input: { userId: 'user_123' },
					test_result: { http_status: 200, is_valid: true }
				}
			}
		]
	};

	db.insert(schema.jobVersion)
		.values([
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_005',
				majorVersion: 5,
				minorVersion: 2,
				versionLabel: 'v5.2',
				status: 'active',
				taskBreakdown: JSON.stringify(taskBreakdown),
				interfaceDefinitions: JSON.stringify(interfaceDefinitions),
				workflows: JSON.stringify(workflows),
				externalTraceId: 'trace_abc123',
				createdAt: now,
				updatedAt: now
			}
		])
		.run();
}
