/**
 * Project Layout Server Load
 * Issue #288: Project screens implementation
 *
 * Guards access to project pages by validating project existence.
 */
import { error } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { validateProjectAccess } from '$lib/guards/project-guard';
import { db } from '$lib/server/db';
import { ProjectRepository } from '$lib/server/repositories/project';

const projectRepository = new ProjectRepository(db);

export const load: LayoutServerLoad = async ({ params }) => {
	const { projectId } = params;

	// Query the database for the project
	const projectData = await projectRepository.findById(projectId);

	const result = validateProjectAccess(
		projectData ? { id: projectData.id, name: projectData.name } : null,
		projectId
	);

	if (!result.valid) {
		throw error(result.error!.status, {
			message: result.error!.message
		});
	}

	return {
		project: projectData!
	};
};
