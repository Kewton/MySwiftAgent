import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	optimizeDeps: {
		// Pre-bundle client-side dependencies
		include: ['marked', 'dompurify']
	}
});
