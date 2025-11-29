<script lang="ts">
	/**
	 * PromptEditor - Textarea for editing prompt content with preview
	 *
	 * Features:
	 * - Syntax-aware textarea
	 * - Live preview
	 * - Character/line count
	 * - Save action
	 */

	import { createEventDispatcher } from 'svelte';
	import PromptViewer from './PromptViewer.svelte';

	export let content = '';
	export let description = '';
	export let loading = false;
	export let disabled = false;

	const dispatch = createEventDispatcher<{
		save: { content: string; description: string };
		cancel: void;
	}>();

	let showPreview = false;
	let originalContent = content;
	let originalDescription = description;

	$: isDirty = content !== originalContent || description !== originalDescription;
	$: lineCount = content.split('\n').length;
	$: charCount = content.length;

	function handleSave() {
		if (!isDirty || disabled || loading) return;
		dispatch('save', { content, description });
	}

	function handleCancel() {
		content = originalContent;
		description = originalDescription;
		dispatch('cancel');
	}

	function handleReset() {
		content = originalContent;
		description = originalDescription;
	}
</script>

<div class="prompt-editor" data-testid="prompt-editor">
	<!-- Description Input -->
	<div class="mb-4">
		<label
			for="version-description"
			class="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-1"
		>
			Version Description
		</label>
		<input
			id="version-description"
			type="text"
			bind:value={description}
			placeholder="Describe the changes in this version..."
			class="w-full px-3 py-2 rounded-lg border
				border-gray-300 dark:border-gray-600
				bg-white dark:bg-gray-800
				text-gray-900 dark:text-gray-100
				focus:ring-2 focus:ring-blue-500 focus:border-blue-500
				disabled:opacity-50 disabled:cursor-not-allowed"
			disabled={disabled || loading}
			data-testid="description-input"
		/>
	</div>

	<!-- Mode Toggle -->
	<div class="flex items-center justify-between mb-2">
		<label for="prompt-content" class="block text-sm font-medium text-gray-900 dark:text-gray-100">
			Prompt Content
		</label>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="px-2 py-1 text-xs rounded transition-colors
					{!showPreview
					? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
					: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => (showPreview = false)}
				data-testid="edit-tab"
			>
				Edit
			</button>
			<button
				type="button"
				class="px-2 py-1 text-xs rounded transition-colors
					{showPreview
					? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
					: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'}"
				on:click={() => (showPreview = true)}
				data-testid="preview-tab"
			>
				Preview
			</button>
		</div>
	</div>

	<!-- Editor / Preview -->
	{#if showPreview}
		<PromptViewer {content} title="" maxHeight="300px" />
	{:else}
		<div class="relative">
			<textarea
				id="prompt-content"
				bind:value={content}
				rows="12"
				class="w-full px-3 py-2 rounded-lg border font-mono text-sm
					border-gray-300 dark:border-gray-600
					bg-white dark:bg-gray-800
					text-gray-900 dark:text-gray-100
					focus:ring-2 focus:ring-blue-500 focus:border-blue-500
					disabled:opacity-50 disabled:cursor-not-allowed"
				placeholder="Enter your prompt content here..."
				disabled={disabled || loading}
				data-testid="content-textarea"
			></textarea>

			<!-- Stats -->
			<div class="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500">
				{lineCount} lines, {charCount} chars
			</div>
		</div>
	{/if}

	<!-- Actions -->
	<div class="mt-4 flex items-center justify-between">
		<div>
			{#if isDirty}
				<button
					type="button"
					class="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
					on:click={handleReset}
					disabled={loading}
					data-testid="reset-button"
				>
					Reset changes
				</button>
			{/if}
		</div>

		<div class="flex gap-2">
			<button
				type="button"
				class="px-4 py-2 rounded-lg font-medium
					text-gray-700 dark:text-gray-300
					bg-gray-100 dark:bg-gray-800
					hover:bg-gray-200 dark:hover:bg-gray-700
					focus:ring-2 focus:ring-gray-500 focus:ring-offset-2
					disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={loading}
				on:click={handleCancel}
				data-testid="cancel-button"
			>
				Cancel
			</button>
			<button
				type="button"
				class="px-4 py-2 rounded-lg font-medium text-white
					{isDirty && !disabled && !loading
					? 'bg-blue-600 hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
					: 'bg-gray-400 cursor-not-allowed'}"
				disabled={!isDirty || disabled || loading}
				on:click={handleSave}
				data-testid="save-button"
			>
				{#if loading}
					<span class="flex items-center gap-2">
						<svg
							class="animate-spin h-4 w-4"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						Saving...
					</span>
				{:else}
					Save New Version
				{/if}
			</button>
		</div>
	</div>
</div>
