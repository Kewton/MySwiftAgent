<script lang="ts">
	/**
	 * PromptVersionList - Displays list of prompt versions with selection
	 *
	 * Features:
	 * - Version list with timestamps
	 * - Active version indicator
	 * - Selection handling
	 * - Activate version action
	 */

	import { createEventDispatcher } from 'svelte';
	import type { PromptVersion } from '../types';

	export let versions: PromptVersion[] = [];
	export let selectedVersionId: string | null = null;
	export let loading = false;

	const dispatch = createEventDispatcher<{
		select: { versionId: string };
		activate: { versionId: string };
	}>();

	function handleSelect(versionId: string) {
		selectedVersionId = versionId;
		dispatch('select', { versionId });
	}

	function handleActivate(versionId: string) {
		dispatch('activate', { versionId });
	}

	function formatDate(dateString: string): string {
		try {
			const date = new Date(dateString);
			return date.toLocaleDateString('ja-JP', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return dateString;
		}
	}

	// Sort versions by version number descending
	$: sortedVersions = [...versions].sort((a, b) => b.version - a.version);
</script>

<div class="prompt-version-list" data-testid="prompt-version-list">
	<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Version History</h3>

	{#if loading}
		<div class="space-y-2 animate-pulse">
			{#each [0, 1, 2] as i (i)}
				<div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-800">
					<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/3 mb-2"></div>
					<div class="h-3 bg-gray-300 dark:bg-gray-600 rounded w-2/3"></div>
				</div>
			{/each}
		</div>
	{:else if sortedVersions.length === 0}
		<div class="text-center py-6 text-gray-500 dark:text-gray-400" data-testid="no-versions">
			No versions available
		</div>
	{:else}
		<ul class="space-y-2" role="listbox" aria-label="Prompt versions">
			{#each sortedVersions as version (version.id)}
				<li
					class="relative rounded-lg border-2 transition-all cursor-pointer
						{selectedVersionId === version.id
						? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
						: 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}"
					role="option"
					aria-selected={selectedVersionId === version.id}
					tabindex="0"
					on:click={() => handleSelect(version.id)}
					on:keydown={(e) => e.key === 'Enter' && handleSelect(version.id)}
					data-testid="version-{version.id}"
				>
					<div class="p-3">
						<div class="flex items-center justify-between mb-1">
							<div class="flex items-center gap-2">
								<span class="font-medium text-gray-900 dark:text-gray-100">
									v{version.version}
								</span>
								{#if version.is_active}
									<span
										class="px-2 py-0.5 text-xs font-medium rounded-full
											bg-green-100 dark:bg-green-900/30
											text-green-700 dark:text-green-400"
									>
										Active
									</span>
								{/if}
							</div>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								{formatDate(version.created_at)}
							</span>
						</div>

						<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
							{version.description || 'No description'}
						</p>

						<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							by {version.created_by}
						</div>
					</div>

					<!-- Activate Button (for non-active versions) -->
					{#if selectedVersionId === version.id && !version.is_active}
						<div class="absolute top-2 right-2">
							<button
								type="button"
								class="px-2 py-1 text-xs font-medium rounded
									bg-blue-600 text-white
									hover:bg-blue-700
									focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
								on:click|stopPropagation={() => handleActivate(version.id)}
								data-testid="activate-button"
							>
								Activate
							</button>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
