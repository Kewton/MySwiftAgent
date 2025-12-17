/**
 * Requirement Detail Page Server Load
 * Issue #290: Requirements List and Version Management
 *
 * Loads requirement version detail and handles actions.
 */
import { error, fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

export const load: PageServerLoad = async ({ params, parent, url }) => {
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

	// Check for compare query param
	const compareToId = url.searchParams.get('compare');
	let diff = null;
	let compareVersion = null;

	if (compareToId) {
		compareVersion = await requirementVersionRepository.findById(compareToId);
		if (compareVersion && compareVersion.workbenchId === workbenchId) {
			diff = await requirementVersionRepository.computeDiff(compareToId, reqVersionId);
		}
	}

	// Get all versions for comparison dropdown
	const allVersions = await requirementVersionRepository.findByWorkbenchId(workbenchId);

	return {
		workbenchDetail,
		requirementVersion,
		diff,
		compareVersion,
		allVersions
	};
};

export const actions: Actions = {
	/**
	 * Set this version as active.
	 */
	setActive: async ({ params }) => {
		const { workbenchId, reqVersionId } = params;

		const result = await requirementVersionRepository.setActive(workbenchId, reqVersionId);
		if (!result) {
			return fail(404, { error: 'Version not found' });
		}

		// Update workbench to reference this version
		// This updates the activeRequirementVersionId
		// For now, we just return success
		return { success: true, message: 'Version set as active' };
	},

	/**
	 * Update the status of this version.
	 */
	updateStatus: async ({ params, request }) => {
		const { reqVersionId } = params;
		const formData = await request.formData();
		const status = formData.get('status')?.toString() as
			| 'draft'
			| 'submitted'
			| 'active'
			| 'deprecated';

		if (!status || !['draft', 'submitted', 'active', 'deprecated'].includes(status)) {
			return fail(400, { error: 'Invalid status' });
		}

		const result = await requirementVersionRepository.updateStatus(reqVersionId, status);
		if (!result) {
			return fail(404, { error: 'Version not found' });
		}

		return { success: true, message: `Status updated to ${status}` };
	}
};
