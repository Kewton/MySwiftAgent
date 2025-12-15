import { sqliteTable, text, integer, unique } from 'drizzle-orm/sqlite-core';

// Project table - Top-level entity representing a project
export const project = sqliteTable('project', {
	id: text('id').primaryKey().notNull(),
	externalProjectId: text('external_project_id').notNull().unique(),
	name: text('name').notNull(),
	description: text('description'),
	lastSyncedAt: integer('last_synced_at', { mode: 'timestamp' }),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
	updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
});

// Workbench table - A workspace within a project
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

// RequirementVersion table - Versioned requirements for a workbench
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

// JobVersion table - Generated job versions from requirements
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
		externalJobMasterId: text('external_job_master_id'),
		externalTraceId: text('external_trace_id'),
		errorMessage: text('error_message'),
		generatedAt: integer('generated_at', { mode: 'timestamp' }),
		createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
		updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull()
	},
	(table) => [unique().on(table.workbenchId, table.majorVersion, table.minorVersion)]
);

// Run table - Execution records of job versions
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

// Schedule table - Scheduled executions of job versions
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

// Type exports for use in application code
export type Project = typeof project.$inferSelect;
export type NewProject = typeof project.$inferInsert;

export type Workbench = typeof workbench.$inferSelect;
export type NewWorkbench = typeof workbench.$inferInsert;

export type RequirementVersion = typeof requirementVersion.$inferSelect;
export type NewRequirementVersion = typeof requirementVersion.$inferInsert;

export type JobVersion = typeof jobVersion.$inferSelect;
export type NewJobVersion = typeof jobVersion.$inferInsert;

export type Run = typeof run.$inferSelect;
export type NewRun = typeof run.$inferInsert;

export type Schedule = typeof schedule.$inferSelect;
export type NewSchedule = typeof schedule.$inferInsert;
