/**
 * Project Detail Page Server Load
 * Issue #288: Project screens implementation
 *
 * Loads project statistics, recent runs, and recent schedules.
 */
import type { PageServerLoad } from './$types';
import { db } from '$lib/server/db';
import { ProjectRepository } from '$lib/server/repositories/project';

const projectRepository = new ProjectRepository(db);

export const load: PageServerLoad = async ({ params, parent }) => {
	const { projectId } = params;

	// Get parent data (project from layout)
	const parentData = await parent();

	// Load project stats and related data
	const [stats, recentRuns, recentSchedules] = await Promise.all([
		projectRepository.getProjectStats(projectId),
		projectRepository.getRecentRuns(projectId, 5),
		projectRepository.getRecentSchedules(projectId, 5)
	]);

	return {
		project: parentData.project,
		stats,
		recentRuns,
		recentSchedules
	};
};
