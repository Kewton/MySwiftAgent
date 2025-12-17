/**
 * Improve Page Server Load
 * Issue #290: Requirements List and Version Management
 *
 * Loads the active requirement version content for display and improvement.
 */
import { redirect, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId, projectId } = params;

	// Get workbench detail from parent layout
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Find the active requirement version
	let activeRequirement = null;
	if (workbenchDetail?.activeRequirementVersion?.id) {
		activeRequirement = await requirementVersionRepository.findById(
			workbenchDetail.activeRequirementVersion.id
		);
	}

	// If no active version, try to get the latest version
	if (!activeRequirement) {
		const allVersions = await requirementVersionRepository.findByWorkbenchId(workbenchId);
		if (allVersions.length > 0) {
			// Get the full detail of the latest version
			activeRequirement = await requirementVersionRepository.findById(allVersions[0].id);
		}
	}

	return {
		workbenchDetail,
		activeRequirement,
		projectId,
		workbenchId
	};
};

export const actions: Actions = {
	/**
	 * Create a new version from the current requirements.
	 */
	createVersion: async ({ params, request }) => {
		const { workbenchId, projectId } = params;
		const formData = await request.formData();
		const content = formData.get('content')?.toString() ?? '';
		const changeSummary = formData.get('changeSummary')?.toString() ?? 'Improvement update';

		if (!content.trim()) {
			return fail(400, { error: 'Content is required' });
		}

		// Create new version
		const newVersion = await requirementVersionRepository.create(workbenchId, {
			content,
			changeSummary
		});

		// Redirect to the new version's edit page
		redirect(
			303,
			`/projects/${projectId}/workbenches/${workbenchId}/requirements/${newVersion.id}/edit`
		);
	}
};
