/**
 * Requirements List Page Server Load
 * Issue #290: Requirements List and Version Management
 *
 * Loads requirement versions for the workbench and handles form actions.
 */
import { fail, redirect } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';
import { workbenchRepository } from '$lib/server/repositories/workbench';

export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId } = params;

	// Get workbench detail from parent layout
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Fetch requirement versions
	const requirementVersions = await requirementVersionRepository.findByWorkbenchId(workbenchId);

	return {
		workbenchDetail,
		requirementVersions
	};
};

export const actions: Actions = {
	/**
	 * Set a requirement version as active.
	 */
	setActive: async ({ params, request }) => {
		const { workbenchId } = params;
		const formData = await request.formData();
		const versionId = formData.get('versionId')?.toString();

		if (!versionId) {
			return fail(400, { error: 'Version ID is required' });
		}

		const result = await requirementVersionRepository.setActive(workbenchId, versionId);
		if (!result) {
			return fail(404, { error: 'Version not found or does not belong to this workbench' });
		}

		// Update workbench's activeRequirementVersionId
		await workbenchRepository.update(workbenchId, {});

		return { success: true };
	},

	/**
	 * Create a new requirement version (draft).
	 */
	create: async ({ params, request }) => {
		const { workbenchId, projectId } = params;
		const formData = await request.formData();
		const content = formData.get('content')?.toString() || '';
		const changeSummary = formData.get('changeSummary')?.toString();

		if (!content.trim()) {
			return fail(400, { error: 'Content is required' });
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
