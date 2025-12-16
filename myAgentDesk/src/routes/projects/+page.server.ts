/**
 * Projects List Page Server Load
 * Issue #288: Project screens implementation
 *
 * Loads all projects with workbench counts for the projects list page.
 */
import type { PageServerLoad, Actions } from './$types';
import { db } from '$lib/server/db';
import { ProjectRepository } from '$lib/server/repositories/project';
import { fail, redirect } from '@sveltejs/kit';

const projectRepository = new ProjectRepository(db);

export const load: PageServerLoad = async () => {
	const projects = await projectRepository.findAllWithStats();

	return {
		projects
	};
};

export const actions: Actions = {
	create: async ({ request }) => {
		const data = await request.formData();
		const name = data.get('name')?.toString();
		const description = data.get('description')?.toString();

		if (!name || name.trim().length === 0) {
			return fail(400, {
				error: 'Project name is required'
			});
		}

		try {
			const project = await projectRepository.create({
				name: name.trim(),
				description: description?.trim()
			});

			throw redirect(303, `/projects/${project.id}`);
		} catch (error) {
			if (error instanceof Response) {
				throw error;
			}
			return fail(500, {
				error: 'Failed to create project'
			});
		}
	}
};
