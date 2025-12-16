/**
 * Workbench Layout Server Load
 * Issue #289: Workbench List/Detail Screens
 *
 * Guards access to workbench pages by validating workbench existence and project ownership.
 * Uses real database queries for validation.
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { validateWorkbenchAccess } from '$lib/guards/workbench-guard';
import { workbenchRepository } from '$lib/server/repositories/workbench';

export const load: LayoutServerLoad = async ({ params, parent }) => {
	const { workbenchId, projectId } = params;

	// Get project from parent layout (ensures project guard ran first)
	await parent();

	// Fetch workbench from database with full detail
	const workbenchDetail = await workbenchRepository.findByIdWithDetail(workbenchId);

	// Validate workbench access (exists, ID matches, belongs to project)
	const result = validateWorkbenchAccess(
		workbenchDetail
			? {
					id: workbenchDetail.id,
					name: workbenchDetail.name,
					projectId: workbenchDetail.projectId
				}
			: null,
		workbenchId,
		projectId
	);

	if (!result.valid) {
		throw error(result.error!.status, {
			message: result.error!.message
		});
	}

	return {
		workbench: result.workbench!,
		workbenchDetail
	};
};
