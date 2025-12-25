/**
 * JobVersion Activate API Endpoint
 * Issue #292: Review Page (JobVersion Detail)
 *
 * POST /api/job-versions/:id/activate
 *
 * Activates a job version, deprecating the current active version.
 */

import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';

export const POST: RequestHandler = async ({ params }) => {
	const { id: jobVersionId } = params;

	// Find the job version
	const jv = await jobVersionRepository.findById(jobVersionId);

	if (!jv) {
		throw error(404, {
			message: 'Job version not found'
		});
	}

	// Only allow activation of successful or deprecated versions
	if (jv.status !== 'success' && jv.status !== 'deprecated') {
		throw error(400, {
			message: `Cannot activate job version with status '${jv.status}'. Only 'success' or 'deprecated' versions can be activated.`
		});
	}

	// Find and deprecate any currently active job version in the same workbench
	const allVersions = await jobVersionRepository.findByWorkbenchId(jv.workbenchId);
	const currentActive = allVersions.find((v) => v.status === 'active');

	if (currentActive && currentActive.id !== jobVersionId) {
		await jobVersionRepository.updateStatus(currentActive.id, 'deprecated');
	}

	// Activate the requested job version
	const updated = await jobVersionRepository.updateStatus(jobVersionId, 'active');

	if (!updated) {
		throw error(500, {
			message: 'Failed to activate job version'
		});
	}

	return json({
		success: true,
		jobVersionId: updated.id,
		versionLabel: updated.versionLabel,
		status: updated.status,
		previousActiveId: currentActive?.id ?? null
	});
};
