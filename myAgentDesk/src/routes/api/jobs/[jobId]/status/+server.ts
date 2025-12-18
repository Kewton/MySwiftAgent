/**
 * Job Status API Endpoint
 * Issue #291: Generate Page (Job Generation)
 *
 * GET /api/jobs/[jobId]/status
 * Returns the current status of a job version for polling.
 */

import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';

/**
 * Get job version status for polling.
 */
export const GET: RequestHandler = async ({ params }) => {
	const { jobId } = params;

	const jobVersion = await jobVersionRepository.findById(jobId);
	if (!jobVersion) {
		throw error(404, 'Job version not found');
	}

	return json({
		jobVersionId: jobVersion.id,
		status: jobVersion.status,
		versionLabel: jobVersion.versionLabel,
		externalJobMasterId: jobVersion.externalJobMasterId,
		externalTraceId: jobVersion.externalTraceId,
		taskBreakdown: jobVersion.taskBreakdown,
		interfaceDefinitions: jobVersion.interfaceDefinitions,
		workflows: jobVersion.workflows,
		errorMessage: jobVersion.errorMessage,
		generatedAt: jobVersion.generatedAt?.toISOString() ?? null,
		updatedAt: jobVersion.updatedAt.toISOString()
	});
};
