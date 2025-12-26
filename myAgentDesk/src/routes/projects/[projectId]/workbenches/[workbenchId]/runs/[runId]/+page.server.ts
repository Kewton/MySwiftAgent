/**
 * Run Detail Page Server
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Server-side data loading for the run detail page.
 */

import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import type { RunDetail } from '$lib/types/run';

export const load: PageServerLoad = async ({ params }) => {
	const { runId } = params;

	// Get run with job version details
	const runWithJobVersion = await runRepository.getRunWithJobVersion(runId);

	if (!runWithJobVersion) {
		throw error(404, 'Run not found');
	}

	const { run, jobVersion } = runWithJobVersion;

	const runDetail: RunDetail = {
		id: run.id,
		workbenchId: run.workbenchId,
		jobVersionId: run.jobVersionId,
		jobVersionLabel: jobVersion.versionLabel,
		status: run.status,
		externalJobId: run.externalJobId,
		externalTraceId: run.externalTraceId,
		executionParams: run.executionParams,
		resultSummary: run.resultSummary,
		tasksCompleted: null, // TODO: Fetch from JobQueue API
		totalTasks: null, // TODO: Fetch from JobQueue API
		startedAt: run.startedAt,
		completedAt: run.completedAt,
		createdAt: run.createdAt,
		updatedAt: run.updatedAt
	};

	// Check if this run can be rerun (only failed runs)
	const canRerun = ['failed', 'canceled', 'timeout'].includes(run.status);

	return {
		run: runDetail,
		canRerun
	};
};
