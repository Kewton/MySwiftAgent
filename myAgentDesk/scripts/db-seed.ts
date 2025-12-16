import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../src/lib/server/db/schema';

const DATABASE_PATH = process.env.DATABASE_URL || './data/local.db';

console.log('Connecting to database:', DATABASE_PATH);

const sqlite = new Database(DATABASE_PATH);
sqlite.pragma('foreign_keys = ON');
const db = drizzle(sqlite, { schema });

async function seed() {
	console.log('Starting seed...');

	const now = new Date();

	// Clear existing data (in reverse order of dependencies)
	console.log('Clearing existing data...');
	db.delete(schema.schedule).run();
	db.delete(schema.run).run();
	db.delete(schema.jobVersion).run();
	db.delete(schema.requirementVersion).run();
	db.delete(schema.workbench).run();
	db.delete(schema.project).run();

	// Insert Projects
	console.log('Inserting projects...');
	const projects = [
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
	];

	for (const project of projects) {
		await db.insert(schema.project).values(project);
	}
	console.log(`Inserted ${projects.length} projects`);

	// Insert Workbenches
	console.log('Inserting workbenches...');
	const workbenches = [
		{
			id: 'wb_001',
			projectId: 'proj_001',
			name: 'Email Auto Reply',
			description: 'Automatic email response generation',
			status: 'active' as const,
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'wb_002',
			projectId: 'proj_001',
			name: 'Report Generation',
			description: 'Weekly and monthly report generation',
			status: 'draft' as const,
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'wb_003',
			projectId: 'proj_002',
			name: 'Podcast Script Generator',
			description: 'AI-powered podcast script creation',
			status: 'active' as const,
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'wb_004',
			projectId: 'proj_002',
			name: 'Audio Transcription',
			description: 'Audio to text transcription workflow',
			status: 'draft' as const,
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'wb_005',
			projectId: 'proj_003',
			name: 'Sales Data Analysis',
			description: 'Monthly sales data analysis and insights',
			status: 'active' as const,
			createdAt: now,
			updatedAt: now
		}
	];

	for (const workbench of workbenches) {
		await db.insert(schema.workbench).values(workbench);
	}
	console.log(`Inserted ${workbenches.length} workbenches`);

	// Insert Requirement Versions
	console.log('Inserting requirement versions...');
	const requirementVersions = [
		{
			id: 'rv_001',
			workbenchId: 'wb_001',
			version: 1,
			content: 'Generate professional email responses based on incoming email content and context.',
			status: 'active' as const,
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
			status: 'draft' as const,
			changeSummary: 'Added sentiment analysis and priority',
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'rv_003',
			workbenchId: 'wb_003',
			version: 1,
			content: 'Generate podcast scripts on technology topics with engaging narrative structure.',
			status: 'active' as const,
			changeSummary: 'Initial requirement',
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'rv_004',
			workbenchId: 'wb_005',
			version: 1,
			content: 'Analyze sales data and generate insights with visualizations and recommendations.',
			status: 'active' as const,
			changeSummary: 'Initial requirement',
			createdAt: now,
			updatedAt: now
		}
	];

	for (const rv of requirementVersions) {
		await db.insert(schema.requirementVersion).values(rv);
	}
	console.log(`Inserted ${requirementVersions.length} requirement versions`);

	// Insert Job Versions
	console.log('Inserting job versions...');
	const jobVersions = [
		{
			id: 'jv_001',
			workbenchId: 'wb_001',
			sourceRequirementVersionId: 'rv_001',
			majorVersion: 1,
			minorVersion: 0,
			versionLabel: 'v1.0',
			status: 'active' as const,
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
			status: 'success' as const,
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
			status: 'active' as const,
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
	];

	for (const jv of jobVersions) {
		await db.insert(schema.jobVersion).values(jv);
	}
	console.log(`Inserted ${jobVersions.length} job versions`);

	// Insert Runs
	console.log('Inserting runs...');
	const runs = [
		{
			id: 'run_001',
			workbenchId: 'wb_001',
			jobVersionId: 'jv_001',
			status: 'success' as const,
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
			status: 'running' as const,
			externalJobId: 'ext_job_002',
			startedAt: now,
			createdAt: now,
			updatedAt: now
		},
		{
			id: 'run_003',
			workbenchId: 'wb_003',
			jobVersionId: 'jv_002',
			status: 'success' as const,
			externalJobId: 'ext_job_003',
			startedAt: new Date(now.getTime() - 7200000),
			completedAt: new Date(now.getTime() - 7000000),
			resultSummary: JSON.stringify({ script_length: 2500, sections: 5 }),
			createdAt: now,
			updatedAt: now
		}
	];

	for (const run of runs) {
		await db.insert(schema.run).values(run);
	}
	console.log(`Inserted ${runs.length} runs`);

	// Insert Schedules
	console.log('Inserting schedules...');
	const schedules = [
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
	];

	for (const schedule of schedules) {
		await db.insert(schema.schedule).values(schedule);
	}
	console.log(`Inserted ${schedules.length} schedules`);

	console.log('Seed completed successfully!');
}

seed()
	.then(() => {
		sqlite.close();
		process.exit(0);
	})
	.catch((error) => {
		console.error('Seed failed:', error);
		sqlite.close();
		process.exit(1);
	});
