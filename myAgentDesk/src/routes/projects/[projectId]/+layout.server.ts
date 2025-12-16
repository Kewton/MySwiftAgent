/**
 * Project Layout Server Load
 * Issue #285: SvelteKit Routing Foundation
 *
 * Guards access to project pages by validating project existence.
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { validateProjectAccess } from '$lib/guards/project-guard';

export const load: LayoutServerLoad = async ({ params }) => {
	const { projectId } = params;

	// TODO: Replace with actual database query
	// For MVP, we use mock data
	const mockProject = {
		id: projectId,
		name: `Project ${projectId}`
	};

	// In production, this would be: const projectData = await db.query.project.findFirst(...)
	const projectData = projectId.startsWith('proj_') ? mockProject : null;

	const result = validateProjectAccess(projectData, projectId);

	if (!result.valid) {
		throw error(result.error!.status, {
			message: result.error!.message
		});
	}

	return {
		project: result.project!
	};
};
