/**
 * Workbench Layout Server Load
 * Issue #285: SvelteKit Routing Foundation
 *
 * Guards access to workbench pages by validating workbench existence and project ownership.
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { validateWorkbenchAccess } from '$lib/guards/workbench-guard';

export const load: LayoutServerLoad = async ({ params, parent }) => {
	const { workbenchId, projectId } = params;

	// Get project from parent layout (ensures project guard ran first)
	await parent();

	// TODO: Replace with actual database query
	// For MVP, we use mock data
	const mockWorkbench = {
		id: workbenchId,
		name: `Workbench ${workbenchId}`,
		projectId: projectId
	};

	// In production, this would be: const workbenchData = await db.query.workbench.findFirst(...)
	const workbenchData = workbenchId.startsWith('wb_') ? mockWorkbench : null;

	const result = validateWorkbenchAccess(workbenchData, workbenchId, projectId);

	if (!result.valid) {
		throw error(result.error!.status, {
			message: result.error!.message
		});
	}

	return {
		workbench: result.workbench!
	};
};
