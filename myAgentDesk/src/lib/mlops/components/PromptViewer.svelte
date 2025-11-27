<script lang="ts">
	/**
	 * PromptViewer - Displays prompt content with syntax highlighting potential
	 *
	 * Features:
	 * - Read-only prompt display
	 * - Line numbers
	 * - Copy to clipboard
	 * - Variable highlighting
	 */

	import { createEventDispatcher } from 'svelte';

	export let content: string;
	export let title = 'Prompt Content';
	export let showLineNumbers = true;
	export let maxHeight = '400px';

	const dispatch = createEventDispatcher<{
		copy: void;
	}>();

	let copied = false;

	$: lines = content.split('\n');

	async function handleCopy() {
		try {
			await navigator.clipboard.writeText(content);
			copied = true;
			dispatch('copy');
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy:', error);
		}
	}
</script>

<div class="prompt-viewer" data-testid="prompt-viewer">
	<!-- Header -->
	<div class="flex items-center justify-between mb-2">
		<h4 class="text-sm font-medium text-gray-900 dark:text-gray-100">
			{title}
		</h4>
		<button
			type="button"
			class="flex items-center gap-1.5 px-2 py-1 text-sm rounded
				text-gray-600 dark:text-gray-400
				hover:bg-gray-100 dark:hover:bg-gray-800
				focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
			on:click={handleCopy}
			aria-label={copied ? 'Copied!' : 'Copy to clipboard'}
			data-testid="copy-button"
		>
			{#if copied}
				<svg
					class="w-4 h-4 text-green-500"
					fill="currentColor"
					viewBox="0 0 20 20"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="text-green-600 dark:text-green-400">Copied!</span>
			{:else}
				<svg
					class="w-4 h-4"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					aria-hidden="true"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
					/>
				</svg>
				<span>Copy</span>
			{/if}
		</button>
	</div>

	<!-- Content -->
	<div
		class="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
		style="max-height: {maxHeight}"
	>
		<div class="overflow-auto" style="max-height: {maxHeight}">
			<pre class="p-4 text-sm font-mono">
				<code>
					{#each lines as line, index}
						<div class="flex">
							{#if showLineNumbers}
								<span
									class="select-none w-10 pr-4 text-right text-gray-400 dark:text-gray-500"
									aria-hidden="true">
									{index + 1}
								</span>
							{/if}
							<span class="flex-1 text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-words">
								{line || ' '}
							</span>
						</div>
					{/each}
				</code>
			</pre>
		</div>
	</div>

	<!-- Stats -->
	<div class="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
		<span>{lines.length} lines</span>
		<span>{content.length} characters</span>
	</div>
</div>

<style>
	pre {
		margin: 0;
		tab-size: 4;
	}
</style>
