import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = () => {
	// Redirect root path to /chat
	throw redirect(302, '/chat');
};
