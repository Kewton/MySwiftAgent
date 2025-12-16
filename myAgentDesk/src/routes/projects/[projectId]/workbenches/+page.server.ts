/**
 * Workbench List Page Server Load
 * Issue #289: Workbench List/Detail Screens
 *
 * Fetches workbench list data with statistics and status counts
 * for the workbench list view.
 */
import type { PageServerLoad } from './$types';
import { workbenchRepository } from '$lib/server/repositories/workbench';
import type { WorkbenchStatusFilter } from '$lib/types/workbench';

export const load: PageServerLoad = async ({ params, url }) => {
	const { projectId } = params;

	// Get filter from URL query params
	const statusFilter = (url.searchParams.get('status') as WorkbenchStatusFilter) || 'all';

	// Fetch workbenches with stats
	const allWorkbenches = await workbenchRepository.findByProjectWithStats(projectId);

	// Filter by status if not 'all'
	const workbenches =
		statusFilter === 'all'
			? allWorkbenches
			: allWorkbenches.filter((wb) => wb.status === statusFilter);

	// Fetch status counts for filter UI
	const statusCounts = await workbenchRepository.getStatusCounts(projectId);

	return {
		workbenches,
		statusCounts,
		currentFilter: statusFilter
	};
};
