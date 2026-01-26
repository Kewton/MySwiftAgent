/**
 * Job Status API Endpoint
 * Issue #291: Generate Page (Job Generation)
 * Issue #305: Enhanced with real-time progress tracking (phase, progress, task_breakdown, workflow_statuses)
 * Issue #410: Added userInputSchema propagation for dynamic form generation
 *
 * GET /api/jobs/[jobId]/status
 * Returns the current status of a job version for polling.
 * When status is 'generating', queries ExpertAgent API for real-time status.
 */

import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import {
	ExpertAgentClient,
	type TaskBreakdownItem,
	type WorkflowStatusItem
} from '$lib/api/clients/expert-agent';
import { loadConfigFromEnv } from '$lib/api/config';

/**
 * Get job version status for polling.
 * Issue #305: Use externalJobId for polling, externalTraceId is for Langfuse link only.
 * Issue #305: Pass through progress tracking fields (phase, progress, task_breakdown, workflow_statuses).
 */
export const GET: RequestHandler = async ({ params }) => {
	const { jobId } = params;

	let jobVersion = await jobVersionRepository.findById(jobId);
	if (!jobVersion) {
		throw error(404, 'Job version not found');
	}

	// Issue #305: Track real-time progress from ExpertAgent API
	let progress: number | null = null;
	let phase: string | null = null;
	let taskBreakdownFromApi: TaskBreakdownItem[] | null = null;
	let workflowStatuses: WorkflowStatusItem[] | null = null;
	let langfuseTraceId: string | null = null;

	// If job is generating, query ExpertAgent API for real-time status
	// Issue #305: Use externalJobId for polling (not externalTraceId which is for Langfuse)
	if (jobVersion.status === 'generating' && jobVersion.externalJobId) {
		const config = loadConfigFromEnv();
		const expertAgentClient = new ExpertAgentClient({
			baseUrl: config.expertAgent.baseUrl,
			adminToken: config.expertAgent.adminToken
		});

		const apiResult = await expertAgentClient.getJobStatus(jobVersion.externalJobId);

		if (apiResult.ok) {
			const externalStatus = apiResult.value.status;
			const result = apiResult.value.result;

			// Issue #305: Capture progress tracking fields from API response
			progress = apiResult.value.progress ?? null;
			phase = apiResult.value.phase ?? null;
			taskBreakdownFromApi = apiResult.value.task_breakdown ?? null;
			workflowStatuses = apiResult.value.workflow_statuses ?? null;

			// Map ExpertAgent status to our status
			if (externalStatus === 'completed' || externalStatus === 'success') {
				// Check internal result status - API completed but job may have failed internally
				const resultStatus = result?.status;
				langfuseTraceId = result?.langfuse_trace_id ?? null;

				if (resultStatus === 'failed' || resultStatus === 'error') {
					// Internal job generation failed
					// Issue #305: Save workflow_statuses for trace links
					// Issue #310: Save taskBreakdown even on failure (for debugging)
					// Issue #396: Also try to get workflow_statuses from result object as fallback
					// Issue #410: Save userInputSchema even on failure (for debugging)
					const updated = await jobVersionRepository.updateGenerationResult(jobId, {
						status: 'failed',
						errorMessage: result?.error_message || 'Job generation failed',
						externalTraceId: langfuseTraceId ?? undefined,
						externalJobMasterId: result?.job_master_id ?? undefined,
						workflows: workflowStatuses
							? JSON.stringify(workflowStatuses)
							: result?.workflow_statuses
								? JSON.stringify(result.workflow_statuses)
								: undefined,
						taskBreakdown: taskBreakdownFromApi
							? JSON.stringify(taskBreakdownFromApi)
							: result?.task_breakdown
								? JSON.stringify(result.task_breakdown)
								: undefined,
						interfaceDefinitions: result?.interface_definitions
							? JSON.stringify(result.interface_definitions)
							: undefined,
						userInputSchema: result?.user_input_schema
							? JSON.stringify(result.user_input_schema)
							: undefined
					});
					if (updated) {
						jobVersion = updated;
					}
				} else {
					// Job completed successfully
					// Issue #305: Save workflow_statuses for trace links
					// Issue #310: Save taskBreakdown and interfaceDefinitions to DB
					// Issue #396: Also try to get workflow_statuses from result object as fallback
					// Issue #410: Save userInputSchema for dynamic form generation
					const updated = await jobVersionRepository.updateGenerationResult(jobId, {
						status: 'success',
						externalJobMasterId:
							result?.job_master_id ?? apiResult.value.job_master_id ?? undefined,
						externalTraceId: langfuseTraceId ?? undefined,
						workflows: workflowStatuses
							? JSON.stringify(workflowStatuses)
							: result?.workflow_statuses
								? JSON.stringify(result.workflow_statuses)
								: undefined,
						taskBreakdown: taskBreakdownFromApi
							? JSON.stringify(taskBreakdownFromApi)
							: result?.task_breakdown
								? JSON.stringify(result.task_breakdown)
								: undefined,
						interfaceDefinitions: result?.interface_definitions
							? JSON.stringify(result.interface_definitions)
							: undefined,
						userInputSchema: result?.user_input_schema
							? JSON.stringify(result.user_input_schema)
							: undefined
					});
					if (updated) {
						jobVersion = updated;
					}
				}
			} else if (externalStatus === 'failed' || externalStatus === 'error') {
				// API level failure
				const updated = await jobVersionRepository.updateGenerationResult(jobId, {
					status: 'failed',
					errorMessage: apiResult.value.error_message || 'Job generation failed in ExpertAgent'
				});
				if (updated) {
					jobVersion = updated;
				}
			}
			// If status is still 'running' or 'pending' or 'creating', keep as 'generating'
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
		userInputSchema: jobVersion.userInputSchema, // Issue #410
		errorMessage: jobVersion.errorMessage,
		generatedAt: jobVersion.generatedAt?.toISOString() ?? null,
		updatedAt: jobVersion.updatedAt.toISOString(),
		// Issue #305: Real-time progress tracking fields from ExpertAgent API
		progress,
		phase,
		task_breakdown: taskBreakdownFromApi,
		workflow_statuses: workflowStatuses,
		langfuseTraceId
	});
};
