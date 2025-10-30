/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// OpenWebUI inspired color palette
				primary: {
					50: '#f0f9ff',
					100: '#e0f2fe',
					200: '#bae6fd',
					300: '#7dd3fc',
					400: '#38bdf8',
					500: '#0ea5e9',
					600: '#0284c7',
					700: '#0369a1',
					800: '#075985',
					900: '#0c4a6e'
				},
				// Dify inspired accent colors
				accent: {
					purple: '#8b5cf6',
					pink: '#ec4899',
					orange: '#f97316'
				},
				// Dark mode colors (OpenWebUI style)
				dark: {
					bg: '#0f172a',
					card: '#1e293b',
					hover: '#334155'
				}
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', 'sans-serif']
			}
		}
	},
	plugins: [],
	darkMode: 'class'
};
