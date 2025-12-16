/**
 * Vault Settings Page Server Load
 * Issue #288: Project screens implementation
 *
 * Loads vault secrets for the project.
 */
import type { PageServerLoad } from './$types';
import type { VaultSecretItem, VaultConnectionStatus } from '$lib/types/project';

export const load: PageServerLoad = async ({ params: _params, parent }) => {
	// projectId would be used to filter secrets by project in production

	// Get parent data (project from layout)
	const parentData = await parent();

	// TODO: In production, this would call myVault API
	// For now, return mock data structure
	const secrets: VaultSecretItem[] = [];

	// Connection status - would be determined by actual API call
	const connectionStatus: VaultConnectionStatus = 'disconnected';

	return {
		project: parentData.project,
		secrets,
		connectionStatus
	};
};
