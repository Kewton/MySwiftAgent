/**
 * Review Page Server
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Server-side logic for the Review page.
 * Loads all job versions for a workbench with sorting and status information.
 */

import type { PageServerLoad } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

/**
 * Job version list item for display.
 */
export interface JobVersionListItem {
	id: string;
	versionLabel: string;
	status: string;
	sourceRequirementVersionId: string;
	sourceRequirementVersion: number;
	majorVersion: number;
	minorVersion: number;
	externalTraceId: string | null;
	generatedAt: string | null;
	createdAt: string;
}

/**
 * Load function for the Review page.
 * Returns all job versions for the workbench, sorted by version descending.
 */
export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId } = params;

	// Get parent data (includes workbench validation)
	await parent();

	// Get all job versions for this workbench
	const jobVersions = await jobVersionRepository.findByWorkbenchId(workbenchId);

	// Build a map of requirement version IDs to version numbers
	const reqVersionMap = new Map<string, number>();
	for (const jv of jobVersions) {
		if (!reqVersionMap.has(jv.sourceRequirementVersionId)) {
			const reqVersion = await requirementVersionRepository.findById(jv.sourceRequirementVersionId);
			if (reqVersion) {
				reqVersionMap.set(jv.sourceRequirementVersionId, reqVersion.version);
			}
		}
	}

	// Transform to list items
	const jobVersionList: JobVersionListItem[] = jobVersions.map((jv) => ({
		id: jv.id,
		versionLabel: jv.versionLabel,
		status: jv.status,
		sourceRequirementVersionId: jv.sourceRequirementVersionId,
		sourceRequirementVersion: reqVersionMap.get(jv.sourceRequirementVersionId) ?? jv.majorVersion,
		majorVersion: jv.majorVersion,
		minorVersion: jv.minorVersion,
		externalTraceId: jv.externalTraceId,
		generatedAt: jv.generatedAt?.toISOString() ?? null,
		createdAt: jv.createdAt.toISOString()
	}));

	// Find active job version (if any)
	const activeJobVersion = jobVersionList.find((jv) => jv.status === 'active') ?? null;

	return {
		jobVersions: jobVersionList,
		activeJobVersion
	};
};
