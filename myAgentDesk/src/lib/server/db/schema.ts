/**
 * Database schema definitions for myAgentDesk.
 *
 * This module defines the complete database schema using Drizzle ORM,
 * including all tables, columns, constraints, and type exports.
 *
 * @module schema
 */
import { sqliteTable, text, integer, unique } from 'drizzle-orm/sqlite-core';

// =============================================================================
// Status Enum Types
// =============================================================================

/** Valid status values for workbench entities */
export const WORKBENCH_STATUSES = ['draft', 'active', 'archived'] as const;
export type WorkbenchStatus = (typeof WORKBENCH_STATUSES)[number];

/** Valid status values for requirement versions */
export const REQUIREMENT_VERSION_STATUSES = ['draft', 'submitted', 'active', 'deprecated'] as const;
export type RequirementVersionStatus = (typeof REQUIREMENT_VERSION_STATUSES)[number];

/** Valid status values for job versions */
export const JOB_VERSION_STATUSES = [
	'generating',
	'success',
	'failed',
	'active',
	'deprecated'
] as const;
export type JobVersionStatus = (typeof JOB_VERSION_STATUSES)[number];

/** Valid status values for runs */
export const RUN_STATUSES = [
	'queued',
	'running',
	'success',
	'failed',
	'canceled',
	'timeout'
] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

// =============================================================================
// Table Definitions
// =============================================================================

/**
 * Project table - Top-level entity representing a project.
 *
 * Projects are the highest level of organization and can contain
 * multiple workbenches. Each project has a unique external ID
 * for integration with external systems.
 */
export const project = sqliteTable('project', {
	id: text('id').primaryKey().notNull(),
	externalProjectId: text('external_project_id').notNull().unique(),
	name: text('name').notNull(),
	description: text('description'),
	lastSyncedAt: integer('last_synced_at', { mode: 'timestamp' }),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

/**
 * Workbench table - A workspace within a project.
 *
 * Workbenches represent individual workflow configurations within a project.
 * Each workbench can have multiple requirement versions, job versions,
 * runs, and schedules associated with it.
 */
export const workbench = sqliteTable('workbench', {
	id: text('id').primaryKey().notNull(),
	projectId: text('project_id')
		.notNull()
		.references(() => project.id),
	name: text('name').notNull(),
	description: text('description'),
	status: text('status', { enum: ['draft', 'active', 'archived'] })
		.notNull()
		.default('draft'),
	activeRequirementVersionId: text('active_requirement_version_id'),
	externalJobMasterId: text('external_job_master_id'),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

/**
 * RequirementVersion table - Versioned requirements for a workbench.
 *
 * Stores different versions of requirements for each workbench.
 * Requirements define what a workflow should accomplish.
 * Versions are unique per workbench.
 */
export const requirementVersion = sqliteTable(
	'requirement_version',
	{
		id: text('id').primaryKey().notNull(),
		workbenchId: text('workbench_id')
			.notNull()
			.references(() => workbench.id),
		version: integer('version').notNull(),
		content: text('content').notNull(),
		status: text('status', { enum: ['draft', 'submitted', 'active', 'deprecated'] })
			.notNull()
			.default('draft'),
		changeSummary: text('change_summary'),
		createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
		updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
	},
	(table) => [unique().on(table.workbenchId, table.version)]
);

/**
 * JobVersion table - Generated job versions from requirements.
 *
 * Stores AI-generated job configurations based on requirement versions.
 * Each job version includes task breakdowns, interface definitions,
 * and workflow configurations. Uses semantic versioning (major.minor).
 *
 * Issue #410: Added userInputSchema column for end-to-end schema propagation.
 */
export const jobVersion = sqliteTable(
	'job_version',
	{
		id: text('id').primaryKey().notNull(),
		workbenchId: text('workbench_id')
			.notNull()
			.references(() => workbench.id),
		sourceRequirementVersionId: text('source_requirement_version_id')
			.notNull()
			.references(() => requirementVersion.id),
		majorVersion: integer('major_version').notNull(),
		minorVersion: integer('minor_version').notNull(),
		versionLabel: text('version_label').notNull(),
		status: text('status', { enum: ['generating', 'success', 'failed', 'active', 'deprecated'] })
			.notNull()
			.default('generating'),
		taskBreakdown: text('task_breakdown'),
		interfaceDefinitions: text('interface_definitions'),
		workflows: text('workflows'),
		userInputSchema: text('user_input_schema'), // Issue #410: LLM-generated user input schema
		externalJobMasterId: text('external_job_master_id'),
		externalJobId: text('external_job_id'), // Issue #305: ExpertAgent job_id for polling
		externalTraceId: text('external_trace_id'), // Issue #305: Langfuse trace_id for observability
		errorMessage: text('error_message'),
		generatedAt: integer('generated_at', { mode: 'timestamp' }),
		createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
		updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
	},
	(table) => [unique().on(table.workbenchId, table.majorVersion, table.minorVersion)]
);

/**
 * Run table - Execution records of job versions.
 *
 * Tracks individual executions of job versions, including status,
 * timing, and results. Runs can be triggered manually, by schedules,
 * or by external systems.
 */
export const run = sqliteTable('run', {
	id: text('id').primaryKey().notNull(),
	workbenchId: text('workbench_id')
		.notNull()
		.references(() => workbench.id),
	jobVersionId: text('job_version_id')
		.notNull()
		.references(() => jobVersion.id),
	status: text('status', {
		enum: ['queued', 'running', 'success', 'failed', 'canceled', 'timeout']
	})
		.notNull()
		.default('queued'),
	externalJobId: text('external_job_id'),
	externalTraceId: text('external_trace_id'),
	executionParams: text('execution_params'),
	resultSummary: text('result_summary'),
	startedAt: integer('started_at', { mode: 'timestamp' }),
	completedAt: integer('completed_at', { mode: 'timestamp' }),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

/**
 * Schedule table - Scheduled executions of job versions.
 *
 * Defines cron-based schedules for automatic job execution.
 * Schedules can be enabled/disabled and track their next
 * and last run times.
 */
export const schedule = sqliteTable('schedule', {
	id: text('id').primaryKey().notNull(),
	workbenchId: text('workbench_id')
		.notNull()
		.references(() => workbench.id),
	targetJobVersionId: text('target_job_version_id')
		.notNull()
		.references(() => jobVersion.id),
	name: text('name').notNull(),
	cronExpression: text('cron_expression').notNull(),
	isEnabled: integer('is_enabled', { mode: 'boolean' }).notNull().default(true),
	externalSchedulerId: text('external_scheduler_id'),
	executionParams: text('execution_params'),
	nextRunAt: integer('next_run_at', { mode: 'timestamp' }),
	lastRunAt: integer('last_run_at', { mode: 'timestamp' }),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

// =============================================================================
// Type Exports
// =============================================================================

/**
 * Project entity type (select operations).
 * Represents a project record as returned from the database.
 */
export type Project = typeof project.$inferSelect;
/** Project entity type for insert operations */
export type NewProject = typeof project.$inferInsert;

/** Workbench entity type (select operations) */
export type Workbench = typeof workbench.$inferSelect;
/** Workbench entity type for insert operations */
export type NewWorkbench = typeof workbench.$inferInsert;

/** RequirementVersion entity type (select operations) */
export type RequirementVersion = typeof requirementVersion.$inferSelect;
/** RequirementVersion entity type for insert operations */
export type NewRequirementVersion = typeof requirementVersion.$inferInsert;

/** JobVersion entity type (select operations) */
export type JobVersion = typeof jobVersion.$inferSelect;
/** JobVersion entity type for insert operations */
export type NewJobVersion = typeof jobVersion.$inferInsert;

/** Run entity type (select operations) */
export type Run = typeof run.$inferSelect;
/** Run entity type for insert operations */
export type NewRun = typeof run.$inferInsert;

/** Schedule entity type (select operations) */
export type Schedule = typeof schedule.$inferSelect;
/** Schedule entity type for insert operations */
export type NewSchedule = typeof schedule.$inferInsert;

// =============================================================================
// WorkflowMaster Table
// =============================================================================

/** Valid status values for workflow master entities */
export const WORKFLOW_MASTER_STATUSES = ['pending', 'generating', 'success', 'failed'] as const;
export type WorkflowMasterStatus = (typeof WORKFLOW_MASTER_STATUSES)[number];

/**
 * WorkflowMasters table - Stores generated workflow YAML for each task.
 * Issue #305: Workflow Generation Progress Display
 *
 * Each TaskMaster from the Job Generator results in a WorkflowMaster
 * containing the generated GraphAI workflow YAML.
 */
export const workflowMasters = sqliteTable('workflow_masters', {
	id: text('id').primaryKey().notNull(),
	taskMasterId: text('task_master_id').notNull().unique(),
	jobVersionId: text('job_version_id').references(() => jobVersion.id),
	workflowName: text('workflow_name').notNull(),
	yamlContent: text('yaml_content').notNull(),
	status: text('status', { enum: ['pending', 'generating', 'success', 'failed'] })
		.notNull()
		.default('pending'),
	generationTimeMs: integer('generation_time_ms'),
	errorMessage: text('error_message'),
	langfuseTraceId: text('langfuse_trace_id'),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

/** WorkflowMaster entity type (select operations) */
export type WorkflowMaster = typeof workflowMasters.$inferSelect;
/** WorkflowMaster entity type for insert operations */
export type NewWorkflowMaster = typeof workflowMasters.$inferInsert;
