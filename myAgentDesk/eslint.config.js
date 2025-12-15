import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import svelte from 'eslint-plugin-svelte';
import prettier from 'eslint-config-prettier';
import globals from 'globals';
import svelteParser from 'svelte-eslint-parser';

export default tseslint.config(
	js.configs.recommended,
	...tseslint.configs.recommended,
	...svelte.configs['flat/recommended'],
	prettier,
	...svelte.configs['flat/prettier'],
	{
		languageOptions: {
			globals: {
				...globals.browser,
				...globals.node
			}
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parser: svelteParser,
			parserOptions: {
				parser: tseslint.parser
			}
		},
		rules: {
			// Disable navigation rules that don't apply to SvelteKit app router
			'svelte/no-navigation-without-resolve': 'off',
			'svelte/require-each-key': 'warn'
		}
	},
	{
		files: ['**/*.ts'],
		languageOptions: {
			parser: tseslint.parser
		}
	},
	{
		ignores: [
			'build/',
			'.svelte-kit/',
			'dist/',
			'coverage/',
			'node_modules/',
			'src/routes/(preview)/**' // Ignore preview mockup files
		]
	}
);
