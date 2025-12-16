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
			'svelte/no-navigation-without-resolve': 'off',
			'svelte/require-each-key': 'warn'
		}
	},
	{
		files: ['**/*.ts'],
		languageOptions: {
			parser: tseslint.parser
		},
		rules: {
			'@typescript-eslint/no-unused-vars': [
				'warn',
				{
					argsIgnorePattern: '^_',
					varsIgnorePattern: '^_'
				}
			]
		}
	},
	{
		ignores: ['build/', '.svelte-kit/', 'dist/', 'coverage/', 'src/routes/(preview)/']
	}
);
