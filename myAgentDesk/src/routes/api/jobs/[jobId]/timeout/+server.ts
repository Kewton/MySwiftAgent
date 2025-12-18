/**
 * Job Timeout API Endpoint
 * Issue #291: Generate Page (Job Generation)
 *
 * POST /api/jobs/[jobId]/timeout
 * Handles timeout for job generation (5 minute limit).
 */

import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { TIMEOUT_ERROR_MESSAGE } from '$lib/types/job-version';

/**
 * Handle job generation timeout.
 * Sets job status to 'failed' with timeout error message.
 */
export const POST: RequestHandler = async ({ params }) => {
	const { jobId } = params;

	const jobVersion = await jobVersionRepository.findById(jobId);
	if (!jobVersion) {
		throw error(404, 'Job version not found');
	}

	// Only timeout jobs that are still generating
	if (jobVersion.status !== 'generating') {
		return json({
			success: false,
			message: `Job is not generating (current status: ${jobVersion.status})`,
			status: jobVersion.status
		});
	}

	// Update status to failed with timeout message
	const updated = await jobVersionRepository.updateGenerationResult(jobId, {
		status: 'failed',
		errorMessage: TIMEOUT_ERROR_MESSAGE
	});

	return json({
		success: true,
		jobVersionId: updated?.id,
		status: updated?.status,
		errorMessage: updated?.errorMessage,
		message: 'Job marked as failed due to timeout'
	});
};
