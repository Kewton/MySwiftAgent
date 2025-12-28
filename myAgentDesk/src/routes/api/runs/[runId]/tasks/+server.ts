/**
 * Run Tasks API Endpoint
 * Issue #293: JobQueue Integration for Runs
 *
 * GET /api/runs/{runId}/tasks - Get task progress for a run
 *
 * Returns enriched task list with interface definitions from JobVersion.
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { JobQueueClient } from '$lib/api/clients/job-queue';
import { loadConfigFromEnv } from '$lib/api/config';
import { mergeTasksWithInterfaces } from '$lib/utils/interface-schema';
import { isErr } from '$lib/api/result';

/**
 * Create JobQueueClient with environment configuration
 */
function getJobQueueClient(): JobQueueClient {
	const config = loadConfigFromEnv();
	return new JobQueueClient({
		baseUrl: config.jobQueue.baseUrl,
		apiToken: config.jobQueue.apiToken
	});
}

/**
 * GET /api/runs/{runId}/tasks
 *
 * Returns task progress for a run, merging JobQueue task data
 * with interface definitions from the associated JobVersion.
 */
export const GET: RequestHandler = async ({ params }) => {
	try {
		const { runId } = params;

		// Get run from database
		const run = await runRepository.findById(runId);
		if (!run) {
			return json({ error: 'Not Found', message: 'Run not found' }, { status: 404 });
		}

		// If no externalJobId, return empty task list
		if (!run.externalJobId) {
			return json({
				runId: run.id,
				tasks: [],
				total: 0
			});
		}

		// Get tasks from JobQueue
		const jobQueueClient = getJobQueueClient();
		const tasksResult = await jobQueueClient.getJobTasks(run.externalJobId);

		if (isErr(tasksResult)) {
			console.error('Failed to fetch tasks from JobQueue:', tasksResult.error);
			return json(
				{
					error: 'Bad Gateway',
					message: 'Failed to fetch tasks from JobQueue'
				},
				{ status: 502 }
			);
		}

		// Get JobVersion for interface definitions
		const jobVersion = await jobVersionRepository.findById(run.jobVersionId);
		const interfaceDefinitions = jobVersion?.interfaceDefinitions || null;

		// Merge tasks with interface definitions
		const enrichedTasks = mergeTasksWithInterfaces(tasksResult.value.tasks, interfaceDefinitions);

		return json({
			runId: run.id,
			tasks: enrichedTasks,
			total: tasksResult.value.total
		});
	} catch (error) {
		console.error('Error getting run tasks:', error);
		return json(
			{ error: 'Internal Server Error', message: 'Failed to get run tasks' },
			{ status: 500 }
		);
	}
};
