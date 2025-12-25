/**
 * Generate Page Server
 * Issue #291: Generate Page (Job Generation)
 *
 * Server-side logic for the Generate page.
 * Handles loading workbench data and form actions for job generation.
 */

import { fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';
import { jobVersionRepository, type JobVersion } from '$lib/server/repositories/job-version';
import { workbenchRepository } from '$lib/server/repositories/workbench';
import { ExpertAgentClient } from '$lib/api/clients/expert-agent';
import { loadConfigFromEnv } from '$lib/api/config';

/**
 * Sync langfuse_trace_id for completed jobs that may have missing external_trace_id.
 * Issue #305: Use externalJobId for API lookup, store result in externalTraceId.
 */
async function syncLangfuseTraceIds(jobVersions: JobVersion[]): Promise<void> {
	const config = loadConfigFromEnv();
	const expertAgentClient = new ExpertAgentClient({
		baseUrl: config.expertAgent.baseUrl,
		adminToken: config.expertAgent.adminToken
	});

	// Filter completed jobs that have externalJobId but missing externalTraceId
	const jobsNeedingSync = jobVersions.filter(
		(jv) =>
			(jv.status === 'failed' || jv.status === 'success') && jv.externalJobId && !jv.externalTraceId
	);

	// Process each job needing sync
	for (const job of jobsNeedingSync) {
		try {
			// Query ExpertAgent API using externalJobId to get langfuse_trace_id
			const apiResult = await expertAgentClient.getJobStatus(job.externalJobId!);

			if (apiResult.ok) {
				const result = apiResult.value.result;
				const langfuseTraceId = result?.langfuse_trace_id;

				// Update externalTraceId with langfuse_trace_id
				if (langfuseTraceId) {
					await jobVersionRepository.updateGenerationResult(job.id, {
						status: job.status, // Keep existing status
						externalTraceId: langfuseTraceId
					});
					// Update the in-memory object for immediate use
					job.externalTraceId = langfuseTraceId;
				}
			}
		} catch {
			// Silently ignore errors - this is a best-effort sync
		}
	}
}

/**
 * Load function for the Generate page.
 * Extends parent layout data with active requirement version and generating job info.
 */
export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId } = params;

	// Get parent data (includes workbench and workbenchDetail)
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Get active requirement version content if exists
	let activeRequirementVersion = null;
	if (workbenchDetail?.activeRequirementVersion?.id) {
		const reqVersion = await requirementVersionRepository.findById(
			workbenchDetail.activeRequirementVersion.id
		);
		if (reqVersion) {
			activeRequirementVersion = {
				id: reqVersion.id,
				version: reqVersion.version,
				content: reqVersion.content,
				status: reqVersion.status,
				changeSummary: reqVersion.changeSummary
			};
		}
	}

	// Check for any currently generating jobs
	const generatingJobs = await jobVersionRepository.findGenerating(workbenchId);
	const currentGeneratingJob =
		generatingJobs.length > 0
			? {
					id: generatingJobs[0].id,
					versionLabel: generatingJobs[0].versionLabel,
					status: generatingJobs[0].status,
					createdAt: generatingJobs[0].createdAt.toISOString()
				}
			: null;

	// Get recent job versions for history
	const allJobVersions = await jobVersionRepository.findByWorkbenchId(workbenchId);
	const recentJobs = allJobVersions.slice(0, 5);

	// Sync langfuse_trace_id for completed jobs (handles stale external_trace_id)
	await syncLangfuseTraceIds(recentJobs);

	// Issue #305: Include workflows (JSON) for per-task trace links
	const recentJobVersions = recentJobs.map((jv) => ({
		id: jv.id,
		versionLabel: jv.versionLabel,
		status: jv.status,
		externalTraceId: jv.externalTraceId,
		workflows: jv.workflows, // JSON string containing workflow_statuses with trace IDs
		generatedAt: jv.generatedAt?.toISOString() ?? null,
		createdAt: jv.createdAt.toISOString()
	}));

	return {
		activeRequirementVersion,
		currentGeneratingJob,
		recentJobVersions
	};
};

/**
 * Form actions for job generation.
 */
export const actions: Actions = {
	/**
	 * Generate a new job from the active requirement version.
	 */
	generateJob: async ({ params }) => {
		const { workbenchId } = params;

		// Get workbench to find active requirement version
		const workbenchDetail = await workbenchRepository.findByIdWithDetail(workbenchId);
		if (!workbenchDetail) {
			return fail(404, { error: 'Workbench not found' });
		}

		// Validate active requirement version exists
		if (!workbenchDetail.activeRequirementVersion?.id) {
			return fail(400, {
				error: 'No active requirement version. Please set an active version first.'
			});
		}

		// Get the active requirement version
		const reqVersion = await requirementVersionRepository.findById(
			workbenchDetail.activeRequirementVersion.id
		);
		if (!reqVersion) {
			return fail(404, { error: 'Active requirement version not found' });
		}

		// Check if there's already a generating job
		const generatingJobs = await jobVersionRepository.findGenerating(workbenchId);
		if (generatingJobs.length > 0) {
			return fail(400, {
				error: 'A job is already being generated. Please wait for it to complete.'
			});
		}

		// Calculate version numbers
		// majorVersion = requirement version number
		// minorVersion = next sequential number for that major version
		const majorVersion = reqVersion.version;
		const minorVersion = await jobVersionRepository.getNextVersion(workbenchId, majorVersion);

		// Create new job version with 'generating' status
		const newJobVersion = await jobVersionRepository.create({
			workbenchId,
			sourceRequirementVersionId: reqVersion.id,
			majorVersion,
			minorVersion
		});

		// Call ExpertAgent API to start job generation
		const config = loadConfigFromEnv();
		const expertAgentClient = new ExpertAgentClient({
			baseUrl: config.expertAgent.baseUrl,
			adminToken: config.expertAgent.adminToken
		});

		const apiResult = await expertAgentClient.generateJob({
			user_requirement: reqVersion.content
		});

		if (!apiResult.ok) {
			// API call failed - update job version status to failed
			await jobVersionRepository.updateGenerationResult(newJobVersion.id, {
				status: 'failed',
				errorMessage: apiResult.error.message || 'Failed to call ExpertAgent API'
			});
			return fail(500, {
				error: `Failed to start job generation: ${apiResult.error.message}`
			});
		}

		// Issue #305: Save both job_id (for polling) and langfuse_trace_id (for trace link)
		await jobVersionRepository.updateGenerationResult(newJobVersion.id, {
			status: 'generating',
			externalJobId: apiResult.value.job_id, // For polling
			externalTraceId: apiResult.value.langfuse_trace_id ?? undefined, // For Langfuse link
			externalJobMasterId: apiResult.value.job_master_id ?? undefined
		});

		return {
			success: true,
			jobVersionId: newJobVersion.id,
			versionLabel: newJobVersion.versionLabel,
			externalJobId: apiResult.value.job_id,
			message: `Job generation started: ${newJobVersion.versionLabel}`
		};
	}
};
