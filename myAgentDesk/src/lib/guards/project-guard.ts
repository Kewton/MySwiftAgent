/**
 * Project Guard
 * Issue #285: SvelteKit Routing Foundation
 *
 * Validates project access and existence.
 */

export interface Project {
	id: string;
	name: string;
}

export interface GuardError {
	code: string;
	message: string;
	status: number;
}

export interface ProjectGuardResult {
	valid: boolean;
	project?: Project;
	error?: GuardError;
}

/**
 * Validates that a project exists and matches the requested ID.
 * Returns 404 for non-existent or mismatched projects to prevent information leakage.
 *
 * @param project - The project data from the database (or null/undefined if not found)
 * @param requestedId - The project ID from the URL params
 * @returns ProjectGuardResult with validation result
 */
export function validateProjectAccess(
	project: Project | null | undefined,
	requestedId: string
): ProjectGuardResult {
	// Check if project exists
	if (!project) {
		return {
			valid: false,
			error: {
				code: 'PROJECT_NOT_FOUND',
				message: 'Project not found',
				status: 404
			}
		};
	}

	// Check if project ID matches (security check)
	if (project.id !== requestedId) {
		return {
			valid: false,
			error: {
				code: 'PROJECT_NOT_FOUND',
				message: 'Project not found',
				status: 404
			}
		};
	}

	return {
		valid: true,
		project
	};
}
