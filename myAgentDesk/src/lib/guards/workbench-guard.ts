/**
 * Workbench Guard
 * Issue #285: SvelteKit Routing Foundation
 *
 * Validates workbench access, existence, and project ownership.
 */

export interface Workbench {
	id: string;
	name: string;
	projectId: string;
}

export interface GuardError {
	code: string;
	message: string;
	status: number;
}

export interface WorkbenchGuardResult {
	valid: boolean;
	workbench?: Workbench;
	error?: GuardError;
}

/**
 * Validates that a workbench exists, matches the requested ID, and belongs to the specified project.
 * Returns 404 for any mismatch to prevent information leakage (security best practice).
 *
 * @param workbench - The workbench data from the database (or null/undefined if not found)
 * @param requestedId - The workbench ID from the URL params
 * @param projectId - The project ID from the URL params (for ownership validation)
 * @returns WorkbenchGuardResult with validation result
 */
export function validateWorkbenchAccess(
	workbench: Workbench | null | undefined,
	requestedId: string,
	projectId: string
): WorkbenchGuardResult {
	// Check if workbench exists
	if (!workbench) {
		return {
			valid: false,
			error: {
				code: 'WORKBENCH_NOT_FOUND',
				message: 'Workbench not found',
				status: 404
			}
		};
	}

	// Check if workbench ID matches
	if (workbench.id !== requestedId) {
		return {
			valid: false,
			error: {
				code: 'WORKBENCH_NOT_FOUND',
				message: 'Workbench not found',
				status: 404
			}
		};
	}

	// Security check: Verify workbench belongs to the specified project
	// This prevents URL manipulation attacks where someone tries to access
	// a workbench from another project by changing the URL
	if (workbench.projectId !== projectId) {
		return {
			valid: false,
			error: {
				code: 'WORKBENCH_NOT_FOUND',
				message: 'Workbench not found',
				status: 404
			}
		};
	}

	return {
		valid: true,
		workbench
	};
}
