<script lang="ts">
	/**
	 * CandidateSelector - Container for selecting between multiple candidate interpretations
	 *
	 * Features:
	 * - Displays multiple candidates
	 * - Single selection handling
	 * - Loading state
	 * - Confirmation action
	 * - i18n support
	 */

	import { createEventDispatcher } from 'svelte';
	import CandidateCard from './CandidateCard.svelte';
	import type { Candidate } from '../types';
	import { t } from '$lib/stores/locale';

	export let candidates: Candidate[] = [];
	export let selectedId: string | null = null;
	export let loading = false;
	export let disabled = false;

	const dispatch = createEventDispatcher<{
		select: { candidateId: string };
		confirm: { candidateId: string };
	}>();

	function handleSelect(candidateId: string) {
		if (disabled || loading) return;
		selectedId = candidateId;
		dispatch('select', { candidateId });
	}

	function handleConfirm() {
		if (selectedId && !disabled && !loading) {
			dispatch('confirm', { candidateId: selectedId });
		}
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (!candidates.length) return;

		const currentIndex = candidates.findIndex((c) => c.id === selectedId);

		switch (event.key) {
			case 'ArrowDown':
			case 'ArrowRight': {
				event.preventDefault();
				const nextIndex = currentIndex < candidates.length - 1 ? currentIndex + 1 : 0;
				handleSelect(candidates[nextIndex].id);
				break;
			}

			case 'ArrowUp':
			case 'ArrowLeft': {
				event.preventDefault();
				const prevIndex = currentIndex > 0 ? currentIndex - 1 : candidates.length - 1;
				handleSelect(candidates[prevIndex].id);
				break;
			}

			case 'Enter':
				if (selectedId) {
					event.preventDefault();
					handleConfirm();
				}
				break;
		}
	}
</script>

<div
	class="candidate-selector"
	role="listbox"
	tabindex="-1"
	aria-label="Candidate interpretations"
	aria-activedescendant={selectedId ? `candidate-${selectedId}` : undefined}
	on:keydown={handleKeyDown}
	data-testid="candidate-selector"
>
	<!-- Header -->
	<div class="mb-4">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
			{t('mlops.selectInterpretation')}
		</h3>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			{t('mlops.selectInterpretationDesc')}
		</p>
	</div>

	<!-- Candidates List -->
	{#if candidates.length === 0}
		<div
			class="text-center py-8 text-gray-500 dark:text-gray-400"
			data-testid="no-candidates-message"
		>
			{t('mlops.noCandidates')}
		</div>
	{:else}
		<div class="space-y-3" role="group">
			{#each candidates as candidate (candidate.id)}
				<div
					id="candidate-{candidate.id}"
					role="option"
					aria-selected={selectedId === candidate.id}
				>
					<CandidateCard
						{candidate}
						selected={selectedId === candidate.id}
						disabled={disabled || loading}
						on:select={() => handleSelect(candidate.id)}
					/>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Confirm Button -->
	{#if candidates.length > 0}
		<div class="mt-6 flex justify-end">
			<button
				type="button"
				class="px-4 py-2 rounded-lg font-medium transition-colors
					{selectedId && !disabled && !loading
					? 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
					: 'bg-gray-200 text-gray-400 cursor-not-allowed dark:bg-gray-700'}"
				disabled={!selectedId || disabled || loading}
				on:click={handleConfirm}
				data-testid="confirm-selection-button"
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
						{t('mlops.confirming')}
					</span>
				{:else}
					{t('mlops.confirmSelection')}
				{/if}
			</button>
		</div>
	{/if}
</div>

<style>
	.candidate-selector:focus-within {
		outline: none;
	}
</style>
