/**
 * Runs List Page Server
 * Issue #293: Runs Screen (Execution History / Monitoring)
 *
 * Server-side data loading for the runs list page.
 */

import type { PageServerLoad } from './$types';
import { runRepository } from '$lib/server/repositories/run';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import type { RunListItem } from '$lib/types/run';

export const load: PageServerLoad = async ({ params }) => {
	const { workbenchId } = params;

	// Get all runs for this workbench
	const runs = await runRepository.findByWorkbenchId(workbenchId);

	// Get job version details for each run
	const runListItems: RunListItem[] = await Promise.all(
		runs.map(async (run) => {
			const jobVersion = await jobVersionRepository.findById(run.jobVersionId);
			return {
				id: run.id,
				workbenchId: run.workbenchId,
				jobVersionId: run.jobVersionId,
				jobVersionLabel: jobVersion?.versionLabel ?? 'Unknown',
				status: run.status,
				tasksCompleted: null, // TODO: Fetch from JobQueue API
				totalTasks: null, // TODO: Fetch from JobQueue API
				startedAt: run.startedAt,
				completedAt: run.completedAt,
				createdAt: run.createdAt
			};
		})
	);

	// Get active job versions for the "New Run" button
	const jobVersions = await jobVersionRepository.findByWorkbenchId(workbenchId);
	const activeJobVersions = jobVersions.filter(
		(jv) => jv.status === 'active' || jv.status === 'success'
	);

	return {
		runs: runListItems,
		activeJobVersions: activeJobVersions.map((jv) => ({
			id: jv.id,
			versionLabel: jv.versionLabel,
			status: jv.status
		}))
	};
};
