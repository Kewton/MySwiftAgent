/**
 * Edit Requirement Page Server Load
 * Issue #290: Requirements List and Version Management
 *
 * Handles editing existing requirement versions.
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId, reqVersionId } = params;

	// Get workbench detail from parent layout
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Fetch requirement version detail
	const requirementVersion = await requirementVersionRepository.findById(reqVersionId);
	if (!requirementVersion) {
		throw error(404, { message: 'Requirement version not found' });
	}

	// Verify it belongs to the correct workbench
	if (requirementVersion.workbenchId !== workbenchId) {
		throw error(404, { message: 'Requirement version not found in this workbench' });
	}

	return {
		workbenchDetail,
		requirementVersion
	};
};

export const actions: Actions = {
	/**
	 * Update the requirement version.
	 */
	default: async ({ params, request }) => {
		const { workbenchId, projectId, reqVersionId } = params;
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

		const updated = await requirementVersionRepository.update(reqVersionId, {
			content,
			changeSummary
		});

		if (!updated) {
			return fail(404, { error: 'Requirement version not found' });
		}

		throw redirect(
			303,
			`/projects/${projectId}/workbenches/${workbenchId}/requirements/${reqVersionId}`
		);
	}
};
