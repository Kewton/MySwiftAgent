/**
 * Generate Page Server
 * Issue #291: Generate Page (Job Generation)
 *
 * Server-side logic for the Generate page.
 * Handles loading workbench data and form actions for job generation.
 */

import { fail } from '@sveltejs/kit';
import type { PageServerLoad, Actions } from './$types';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { workbenchRepository } from '$lib/server/repositories/workbench';

/**
 * Load function for the Generate page.
 * Extends parent layout data with active requirement version and generating job info.
 */
export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId } = params;

	// Get parent data (includes workbench and workbenchDetail)
	const parentData = await parent();
	const workbenchDetail = parentData.workbenchDetail;

	// Get active requirement version content if exists
	let activeRequirementVersion = null;
	if (workbenchDetail?.activeRequirementVersion?.id) {
		const reqVersion = await requirementVersionRepository.findById(
			workbenchDetail.activeRequirementVersion.id
		);
		if (reqVersion) {
			activeRequirementVersion = {
				id: reqVersion.id,
				version: reqVersion.version,
				content: reqVersion.content,
				status: reqVersion.status,
				changeSummary: reqVersion.changeSummary
			};
		}
	}

	// Check for any currently generating jobs
	const generatingJobs = await jobVersionRepository.findGenerating(workbenchId);
	const currentGeneratingJob =
		generatingJobs.length > 0
			? {
					id: generatingJobs[0].id,
					versionLabel: generatingJobs[0].versionLabel,
					status: generatingJobs[0].status,
					createdAt: generatingJobs[0].createdAt.toISOString()
				}
			: null;

	// Get recent job versions for history
	const allJobVersions = await jobVersionRepository.findByWorkbenchId(workbenchId);
	const recentJobVersions = allJobVersions.slice(0, 5).map((jv) => ({
		id: jv.id,
		versionLabel: jv.versionLabel,
		status: jv.status,
		externalTraceId: jv.externalTraceId,
		generatedAt: jv.generatedAt?.toISOString() ?? null,
		createdAt: jv.createdAt.toISOString()
	}));

	return {
		activeRequirementVersion,
		currentGeneratingJob,
		recentJobVersions
	};
};

/**
 * Form actions for job generation.
 */
export const actions: Actions = {
	/**
	 * Generate a new job from the active requirement version.
	 */
	generateJob: async ({ params }) => {
		const { workbenchId } = params;

		// Get workbench to find active requirement version
		const workbenchDetail = await workbenchRepository.findByIdWithDetail(workbenchId);
		if (!workbenchDetail) {
			return fail(404, { error: 'Workbench not found' });
		}

		// Validate active requirement version exists
		if (!workbenchDetail.activeRequirementVersion?.id) {
			return fail(400, {
				error: 'No active requirement version. Please set an active version first.'
			});
		}

		// Get the active requirement version
		const reqVersion = await requirementVersionRepository.findById(
			workbenchDetail.activeRequirementVersion.id
		);
		if (!reqVersion) {
			return fail(404, { error: 'Active requirement version not found' });
		}

		// Check if there's already a generating job
		const generatingJobs = await jobVersionRepository.findGenerating(workbenchId);
		if (generatingJobs.length > 0) {
			return fail(400, {
				error: 'A job is already being generated. Please wait for it to complete.'
			});
		}

		// Calculate version numbers
		// majorVersion = requirement version number
		// minorVersion = next sequential number for that major version
		const majorVersion = reqVersion.version;
		const minorVersion = await jobVersionRepository.getNextVersion(workbenchId, majorVersion);

		// Create new job version with 'generating' status
		const newJobVersion = await jobVersionRepository.create({
			workbenchId,
			sourceRequirementVersionId: reqVersion.id,
			majorVersion,
			minorVersion
		});

		return {
			success: true,
			jobVersionId: newJobVersion.id,
			versionLabel: newJobVersion.versionLabel,
			message: `Job generation started: ${newJobVersion.versionLabel}`
		};
	}
};
