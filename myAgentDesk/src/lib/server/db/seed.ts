/**
 * Database seeding utilities for myAgentDesk.
 *
 * This module provides functions for seeding the database with initial/test data
 * and clearing all data from the database. Used for development, testing,
 * and demonstration purposes.
 *
 * @module seed
 */
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';

/**
 * Type for Drizzle database instance.
 * Uses generic type for flexibility in tests with different schema configurations.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type DrizzleDB = BetterSQLite3Database<any>;

/**
 * Structure for seed data containing all entity arrays.
 * Data must be provided in dependency order (projects first, then workbenches, etc.)
 */
export interface SeedData {
	projects: schema.NewProject[];
	workbenches: schema.NewWorkbench[];
	requirementVersions: schema.NewRequirementVersion[];
	jobVersions: schema.NewJobVersion[];
	runs: schema.NewRun[];
	schedules: schema.NewSchedule[];
}

/**
 * Clear all data from the database.
 *
 * Deletes all records from all tables in reverse dependency order
 * to avoid foreign key constraint violations.
 *
 * @param database - Drizzle database instance to clear
 * @returns Promise that resolves when all data is cleared
 *
 * @example
 * ```typescript
 * import { db } from '$lib/server/db';
 * import { clearAllData } from '$lib/server/db/seed';
 *
 * // Clear all data before running tests
 * await clearAllData(db);
 * ```
 */
export async function clearAllData(database: DrizzleDB): Promise<void> {
	await database.delete(schema.schedule);
	await database.delete(schema.run);
	await database.delete(schema.jobVersion);
	await database.delete(schema.requirementVersion);
	await database.delete(schema.workbench);
	await database.delete(schema.project);
}

/**
 * Seed the database with provided data.
 *
 * Inserts all provided data in dependency order (projects first, then
 * workbenches, requirement versions, job versions, runs, and schedules).
 *
 * @param database - Drizzle database instance to seed
 * @param data - Seed data containing all entities to insert
 * @returns Promise that resolves when all data is inserted
 * @throws Error if foreign key constraints are violated
 *
 * @example
 * ```typescript
 * import { db } from '$lib/server/db';
 * import { seedDatabase, getDefaultSeedData } from '$lib/server/db/seed';
 *
 * // Seed with default data
 * await seedDatabase(db, getDefaultSeedData());
 * ```
 */
export async function seedDatabase(database: DrizzleDB, data: SeedData): Promise<void> {
	// Insert in order of dependencies
	for (const project of data.projects) {
		await database.insert(schema.project).values(project);
	}

	for (const workbench of data.workbenches) {
		await database.insert(schema.workbench).values(workbench);
	}

	for (const rv of data.requirementVersions) {
		await database.insert(schema.requirementVersion).values(rv);
	}

	for (const jv of data.jobVersions) {
		await database.insert(schema.jobVersion).values(jv);
	}

	for (const run of data.runs) {
		await database.insert(schema.run).values(run);
	}

	for (const schedule of data.schedules) {
		await database.insert(schema.schedule).values(schedule);
	}
}

/**
 * Get default seed data for development and testing.
 *
 * Returns a complete set of sample data including projects, workbenches,
 * requirement versions, job versions, runs, and schedules. This data
 * demonstrates the full data model relationships.
 *
 * @returns SeedData object with all default entities
 *
 * @example
 * ```typescript
 * import { getDefaultSeedData, seedDatabase } from '$lib/server/db/seed';
 * import { db } from '$lib/server/db';
 *
 * const seedData = getDefaultSeedData();
 * console.log(`Seeding ${seedData.projects.length} projects`);
 * await seedDatabase(db, seedData);
 * ```
 */
export function getDefaultSeedData(): SeedData {
	const now = new Date();

	return {
		projects: [
			{
				id: 'proj_001',
				externalProjectId: 'default_project',
				name: 'Default Project',
				description: 'Default project for testing and demos',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'proj_002',
				externalProjectId: 'podcast_project',
				name: 'Podcast Auto Generation',
				description: 'Automated podcast content generation workflow',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'proj_003',
				externalProjectId: 'analysis_project',
				name: 'Data Analysis Project',
				description: 'Data analysis and reporting workflows',
				createdAt: now,
				updatedAt: now
			}
		],
		workbenches: [
			{
				id: 'wb_001',
				projectId: 'proj_001',
				name: 'Email Auto Reply',
				description: 'Automatic email response generation',
				status: 'active',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'wb_002',
				projectId: 'proj_001',
				name: 'Report Generation',
				description: 'Weekly and monthly report generation',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'wb_003',
				projectId: 'proj_002',
				name: 'Podcast Script Generator',
				description: 'AI-powered podcast script creation',
				status: 'active',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'wb_004',
				projectId: 'proj_002',
				name: 'Audio Transcription',
				description: 'Audio to text transcription workflow',
				status: 'draft',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'wb_005',
				projectId: 'proj_003',
				name: 'Sales Data Analysis',
				description: 'Monthly sales data analysis and insights',
				status: 'active',
				createdAt: now,
				updatedAt: now
			}
		],
		requirementVersions: [
			{
				id: 'rv_001',
				workbenchId: 'wb_001',
				version: 1,
				content:
					'Generate professional email responses based on incoming email content and context.',
				status: 'active',
				changeSummary: 'Initial requirement',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'rv_002',
				workbenchId: 'wb_001',
				version: 2,
				content:
					'Generate professional email responses with sentiment analysis and priority classification.',
				status: 'draft',
				changeSummary: 'Added sentiment analysis and priority',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'rv_003',
				workbenchId: 'wb_003',
				version: 1,
				content: 'Generate podcast scripts on technology topics with engaging narrative structure.',
				status: 'active',
				changeSummary: 'Initial requirement',
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'rv_004',
				workbenchId: 'wb_005',
				version: 1,
				content:
					'Analyze sales data and generate insights with visualizations and recommendations.',
				status: 'active',
				changeSummary: 'Initial requirement',
				createdAt: now,
				updatedAt: now
			}
		],
		jobVersions: [
			{
				id: 'jv_001',
				workbenchId: 'wb_001',
				sourceRequirementVersionId: 'rv_001',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				taskBreakdown: JSON.stringify([
					{ id: 'task_1', name: 'Parse incoming email', order: 1 },
					{ id: 'task_2', name: 'Extract key information', order: 2 },
					{ id: 'task_3', name: 'Generate response', order: 3 }
				]),
				interfaceDefinitions: JSON.stringify({
					input: { email_content: 'string', sender: 'string' },
					output: { response: 'string', subject: 'string' }
				}),
				workflows: JSON.stringify([{ id: 'wf_1', name: 'Email Response Flow', steps: 3 }]),
				generatedAt: now,
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'jv_002',
				workbenchId: 'wb_003',
				sourceRequirementVersionId: 'rv_003',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'success',
				taskBreakdown: JSON.stringify([
					{ id: 'task_1', name: 'Research topic', order: 1 },
					{ id: 'task_2', name: 'Create outline', order: 2 },
					{ id: 'task_3', name: 'Write script', order: 3 },
					{ id: 'task_4', name: 'Add transitions', order: 4 }
				]),
				generatedAt: now,
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'jv_003',
				workbenchId: 'wb_005',
				sourceRequirementVersionId: 'rv_004',
				majorVersion: 1,
				minorVersion: 0,
				versionLabel: 'v1.0',
				status: 'active',
				taskBreakdown: JSON.stringify([
					{ id: 'task_1', name: 'Load data', order: 1 },
					{ id: 'task_2', name: 'Clean and transform', order: 2 },
					{ id: 'task_3', name: 'Analyze trends', order: 3 },
					{ id: 'task_4', name: 'Generate visualizations', order: 4 },
					{ id: 'task_5', name: 'Create report', order: 5 }
				]),
				generatedAt: now,
				createdAt: now,
				updatedAt: now
			}
		],
		runs: [
			{
				id: 'run_001',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'success',
				externalJobId: 'ext_job_001',
				startedAt: new Date(now.getTime() - 3600000),
				completedAt: new Date(now.getTime() - 3500000),
				resultSummary: JSON.stringify({ processed: 5, successful: 5, failed: 0 }),
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'run_002',
				workbenchId: 'wb_001',
				jobVersionId: 'jv_001',
				status: 'running',
				externalJobId: 'ext_job_002',
				startedAt: now,
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'run_003',
				workbenchId: 'wb_003',
				jobVersionId: 'jv_002',
				status: 'success',
				externalJobId: 'ext_job_003',
				startedAt: new Date(now.getTime() - 7200000),
				completedAt: new Date(now.getTime() - 7000000),
				resultSummary: JSON.stringify({ script_length: 2500, sections: 5 }),
				createdAt: now,
				updatedAt: now
			}
		],
		schedules: [
			{
				id: 'sched_001',
				workbenchId: 'wb_001',
				targetJobVersionId: 'jv_001',
				name: 'Hourly Email Check',
				cronExpression: '0 * * * *',
				isEnabled: true,
				nextRunAt: new Date(now.getTime() + 3600000),
				lastRunAt: now,
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'sched_002',
				workbenchId: 'wb_005',
				targetJobVersionId: 'jv_003',
				name: 'Daily Sales Analysis',
				cronExpression: '0 9 * * *',
				isEnabled: true,
				nextRunAt: new Date(now.getTime() + 86400000),
				createdAt: now,
				updatedAt: now
			},
			{
				id: 'sched_003',
				workbenchId: 'wb_003',
				targetJobVersionId: 'jv_002',
				name: 'Weekly Podcast Script',
				cronExpression: '0 10 * * 1',
				isEnabled: false,
				createdAt: now,
				updatedAt: now
			}
		]
	};
}
