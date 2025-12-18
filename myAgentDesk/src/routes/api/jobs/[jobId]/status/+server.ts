/**
 * Job Status API Endpoint
 * Issue #291: Generate Page (Job Generation)
 *
 * GET /api/jobs/[jobId]/status
 * Returns the current status of a job version for polling.
 * When status is 'generating', queries ExpertAgent API for real-time status.
 */

import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { ExpertAgentClient } from '$lib/api/clients/expert-agent';
import { loadConfigFromEnv } from '$lib/api/config';

/**
 * Get job version status for polling.
 * If status is 'generating' and externalTraceId exists, query ExpertAgent API.
 */
export const GET: RequestHandler = async ({ params }) => {
	const { jobId } = params;

	let jobVersion = await jobVersionRepository.findById(jobId);
	if (!jobVersion) {
		throw error(404, 'Job version not found');
	}

	// If job is generating, query ExpertAgent API for real-time status
	if (jobVersion.status === 'generating' && jobVersion.externalTraceId) {
		const config = loadConfigFromEnv();
		const expertAgentClient = new ExpertAgentClient({
			baseUrl: config.expertAgent.baseUrl,
			adminToken: config.expertAgent.adminToken
		});

		const apiResult = await expertAgentClient.getJobStatus(jobVersion.externalTraceId);

		if (apiResult.ok) {
			const externalStatus = apiResult.value.status;

			// Map ExpertAgent status to our status
			if (externalStatus === 'completed' || externalStatus === 'success') {
				// Job completed successfully
				const updated = await jobVersionRepository.updateGenerationResult(jobId, {
					status: 'success',
					externalJobMasterId: apiResult.value.job_master_id ?? undefined
				});
				if (updated) {
					jobVersion = updated;
				}
			} else if (externalStatus === 'failed' || externalStatus === 'error') {
				// Job failed
				const updated = await jobVersionRepository.updateGenerationResult(jobId, {
					status: 'failed',
					errorMessage: 'Job generation failed in ExpertAgent'
				});
				if (updated) {
					jobVersion = updated;
				}
			}
			// If status is still 'running' or 'pending', keep as 'generating'
		}
		// If API call fails, continue with current DB status
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
