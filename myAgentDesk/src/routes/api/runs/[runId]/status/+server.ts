/**
 * Run Status API Endpoint
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * GET /api/runs/:runId/status - Get run status for polling
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { runRepository } from '$lib/server/repositories/run';

/**
 * Get run status for polling.
 *
 * Response:
 * - runId: string
 * - status: RunStatus
 * - tasksCompleted: number | null
 * - totalTasks: number | null
 * - externalTraceId: string | null
 */
export const GET: RequestHandler = async ({ params }) => {
	try {
		const { runId } = params;

		const run = await runRepository.findById(runId);

		if (!run) {
			return json({ error: 'Not Found', message: 'Run not found' }, { status: 404 });
		}

		// TODO: In the future, this would fetch task progress from JobQueue API
		// For now, we return placeholder values
		const tasksCompleted = null;
		const totalTasks = null;

		return json({
			runId: run.id,
			status: run.status,
			tasksCompleted,
			totalTasks,
			externalTraceId: run.externalTraceId
		});
	} catch (error) {
		console.error('Error fetching run status:', error);
		return json(
			{ error: 'Internal Server Error', message: 'Failed to fetch run status' },
			{ status: 500 }
		);
	}
};
