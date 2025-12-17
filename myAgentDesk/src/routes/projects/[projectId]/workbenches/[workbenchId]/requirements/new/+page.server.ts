/**
 * New Requirement Page Server Load
 * Issue #290: Requirements List and Version Management
 *
 * Handles creation of new requirement versions.
 */
import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId } = params;

	// Get workbench detail from parent layout
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Get next version number
	const nextVersion = await requirementVersionRepository.getNextVersion(workbenchId);

	return {
		workbenchDetail,
		nextVersion
	};
};

export const actions: Actions = {
	/**
	 * Create a new requirement version.
	 */
	default: async ({ params, request }) => {
		const { workbenchId, projectId } = params;
		const formData = await request.formData();
		const content = formData.get('content')?.toString() || '';
		const changeSummary = formData.get('changeSummary')?.toString();

		if (!content.trim()) {
			return fail(400, {
				error: 'Content is required',
				content,
				changeSummary
			});
		}

		const created = await requirementVersionRepository.create(workbenchId, {
			content,
			changeSummary
		});

		throw redirect(
			303,
			`/projects/${projectId}/workbenches/${workbenchId}/requirements/${created.id}`
		);
	}
};
