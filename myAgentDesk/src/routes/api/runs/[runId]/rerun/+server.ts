/**
 * Rerun API Endpoint
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * POST /api/runs/:runId/rerun - Create a new run from a failed run
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { runRepository } from '$lib/server/repositories/run';

/**
 * Create a new run from an existing run (rerun).
 *
 * The original run must be in a terminal failed state (failed, canceled, timeout).
 *
 * Response: New run object with status 'queued' and reference to original run
 */
export const POST: RequestHandler = async ({ params }) => {
	try {
		const { runId } = params;

		// Find the original run
		const originalRun = await runRepository.findById(runId);

		if (!originalRun) {
			return json({ error: 'Not Found', message: 'Run not found' }, { status: 404 });
		}

		// Verify the run is in a failed terminal state
		const rerunableStatuses = ['failed', 'canceled', 'timeout'];
		if (!rerunableStatuses.includes(originalRun.status)) {
			return json(
				{
					error: 'Bad Request',
					message: `Cannot rerun a run with status '${originalRun.status}'. Only failed, canceled, or timeout runs can be rerun.`
				},
				{ status: 400 }
			);
		}

		// Create a new run with the same configuration
		const newRun = await runRepository.create({
			workbenchId: originalRun.workbenchId,
			jobVersionId: originalRun.jobVersionId,
			executionParams: originalRun.executionParams ?? undefined
		});

		return json(
			{
				id: newRun.id,
				status: newRun.status,
				originalRunId: originalRun.id,
				workbenchId: newRun.workbenchId,
				jobVersionId: newRun.jobVersionId,
				createdAt: newRun.createdAt.toISOString()
			},
			{ status: 201 }
		);
	} catch (error) {
		console.error('Error creating rerun:', error);
		return json(
			{ error: 'Internal Server Error', message: 'Failed to create rerun' },
			{ status: 500 }
		);
	}
};
