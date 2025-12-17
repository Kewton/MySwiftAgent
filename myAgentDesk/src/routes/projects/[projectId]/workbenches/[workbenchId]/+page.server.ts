/**
 * Workbench Detail Page Server
 * Issue #289: Workbench List/Detail Screens
 *
 * Handles form actions for workbench updates.
 */
import type { Actions } from './$types';
import { workbenchRepository } from '$lib/server/repositories/workbench';
import { fail } from '@sveltejs/kit';

export const actions: Actions = {
	updateDescription: async ({ params, request }) => {
		const { workbenchId } = params;
		const data = await request.formData();
		const description = data.get('description')?.toString() ?? '';

		try {
			await workbenchRepository.update(workbenchId, {
				description: description || undefined
			});
			return { success: true };
		} catch {
			return fail(500, { error: 'Failed to update description' });
		}
	}
};
