import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit()],
	test: {
		include: ['src/**/*.{test,spec}.{js,ts}']
	},
	server: {
		port: 5173,
		proxy: {
			// Cloudflare API proxy (for future Phase 2)
			'/api': {
				target: process.env.CLOUDFLARE_API_URL || 'http://localhost:8787',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	},
	preview: {
		port: 8000
	}
});
