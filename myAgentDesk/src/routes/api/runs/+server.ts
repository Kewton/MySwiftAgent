/**
 * Run API Endpoints
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * POST /api/runs - Create a new run
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';

/**
 * Create a new run.
 *
 * Request body:
 * - workbenchId: string (required)
 * - jobVersionId: string (required)
 * - executionParams: string (optional)
 *
 * Response: Created run object with status 'queued'
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

		// Create the run
		const run = await runRepository.create({
			workbenchId: body.workbenchId,
			jobVersionId: body.jobVersionId,
			executionParams: body.executionParams
		});

		return json(
			{
				id: run.id,
				status: run.status,
				workbenchId: run.workbenchId,
				jobVersionId: run.jobVersionId,
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
