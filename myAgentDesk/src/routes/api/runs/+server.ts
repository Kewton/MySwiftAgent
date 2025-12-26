/**
 * Run API Endpoints
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * POST /api/runs - Create a new run with JobQueue integration
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { JobQueueClient } from '$lib/api/clients/job-queue';
import { loadConfigFromEnv } from '$lib/api/config';
import { isOk } from '$lib/api/result';

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
 * Create a new run with JobQueue integration.
 *
 * Request body:
 * - workbenchId: string (required)
 * - jobVersionId: string (required)
 * - executionParams: string (optional JSON) - Parameters for job execution
 *
 * Flow:
 * 1. Create run record with 'queued' status
 * 2. If JobVersion has externalJobMasterId, create job on JobQueue
 * 3. Update run with externalJobId from JobQueue response
 *
 * Response: Created run object with status and optional externalJobId
 */
export const POST: RequestHandler = async ({ request }) => {
	try {
		const body = await request.json();

		// Validate required fields
		if (!body.workbenchId) {
			return json({ error: 'Bad Request', message: 'workbenchId is required' }, { status: 400 });
		}
		if (!body.jobVersionId) {
			return json({ error: 'Bad Request', message: 'jobVersionId is required' }, { status: 400 });
		}

		// Verify job version exists
		const jobVersion = await jobVersionRepository.findById(body.jobVersionId);
		if (!jobVersion) {
			return json({ error: 'Not Found', message: 'Job version not found' }, { status: 404 });
		}

		// Create the run record
		const run = await runRepository.create({
			workbenchId: body.workbenchId,
			jobVersionId: body.jobVersionId,
			executionParams: body.executionParams
		});

		let externalJobId: string | null = null;
		let status = run.status;

		// If JobVersion has externalJobMasterId, create job on JobQueue
		if (jobVersion.externalJobMasterId) {
			try {
				const jobQueueClient = getJobQueueClient();

				// Parse execution params if provided
				let bodyParams: Record<string, unknown> = {};
				if (body.executionParams) {
					try {
						bodyParams = JSON.parse(body.executionParams);
					} catch {
						// If parsing fails, use as-is or empty
						console.warn('Failed to parse executionParams, using empty body');
					}
				}

				// Create job from master template
				const jobResult = await jobQueueClient.createJobFromMaster(
					jobVersion.externalJobMasterId,
					{
						name: `Run ${run.id}`,
						body: bodyParams,
						tags: [`run:${run.id}`, `workbench:${body.workbenchId}`]
					}
				);

				if (isOk(jobResult)) {
					externalJobId = jobResult.value.job_id;

					// Update run with external job ID
					await runRepository.updateResult(run.id, {
						status: 'queued',
						externalJobId
					});

					console.log(`Created job ${externalJobId} for run ${run.id}`);
				} else {
					// Job creation failed, but run is still created
					console.error('Failed to create job on JobQueue:', jobResult.error);
					// Keep run in queued status - can be retried later
				}
			} catch (jobQueueError) {
				// JobQueue communication error - log but don't fail the run creation
				console.error('JobQueue communication error:', jobQueueError);
			}
		}

		return json(
			{
				id: run.id,
				status,
				workbenchId: run.workbenchId,
				jobVersionId: run.jobVersionId,
				externalJobId,
				createdAt: run.createdAt.toISOString()
			},
			{ status: 201 }
		);
	} catch (error) {
		console.error('Error creating run:', error);
		return json(
			{ error: 'Internal Server Error', message: 'Failed to create run' },
			{ status: 500 }
		);
	}
};
