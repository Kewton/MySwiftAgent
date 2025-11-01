import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	// Redirect root path to /create_job
	throw redirect(302, '/create_job');
};
