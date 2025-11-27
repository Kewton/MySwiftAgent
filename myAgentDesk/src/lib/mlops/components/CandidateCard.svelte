<script lang="ts">
	/**
	 * CandidateCard - Displays a single candidate interpretation for selection
	 *
	 * Features:
	 * - Shows candidate label, description, and confidence
	 * - Displays requirement preview
	 * - Selection state handling
	 * - Keyboard navigation support
	 */

	import type { Candidate } from '../types';

	export let candidate: Candidate;
	export let selected = false;
	export let disabled = false;

	function formatConfidence(confidence: number): string {
		return `${(confidence * 100).toFixed(0)}%`;
	}

	function formatCompleteness(completeness: number): string {
		return `${(completeness * 100).toFixed(0)}%`;
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			if (!disabled) {
				const element = event.currentTarget as HTMLElement;
				element.click();
			}
		}
	}
</script>

<div
	class="candidate-card p-4 rounded-lg border-2 transition-all cursor-pointer
		{selected
		? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
		: 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600'}
		{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
	role="button"
	tabindex={disabled ? -1 : 0}
	aria-pressed={selected}
	aria-disabled={disabled}
	aria-label="Candidate {candidate.label}: {candidate.description}"
	on:click
	on:keydown={handleKeyDown}
	data-testid="candidate-card-{candidate.id}"
>
	<!-- Header -->
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-2">
			<span
				class="inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold
					{selected
					? 'bg-blue-500 text-white'
					: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
			>
				{candidate.label}
			</span>
			<span class="font-medium text-gray-900 dark:text-gray-100">
				{candidate.description}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<span
				class="text-sm px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
				aria-label="Confidence: {formatConfidence(candidate.confidence)}"
			>
				{formatConfidence(candidate.confidence)} confident
			</span>
		</div>
	</div>

	<!-- Requirements Preview -->
	<div class="grid grid-cols-2 gap-2 text-sm">
		{#if candidate.requirements.data_source}
			<div class="flex flex-col">
				<span class="text-gray-500 dark:text-gray-400">Data Source</span>
				<span class="text-gray-900 dark:text-gray-100 truncate">
					{candidate.requirements.data_source}
				</span>
			</div>
		{/if}

		{#if candidate.requirements.process_description}
			<div class="flex flex-col">
				<span class="text-gray-500 dark:text-gray-400">Process</span>
				<span class="text-gray-900 dark:text-gray-100 truncate">
					{candidate.requirements.process_description}
				</span>
			</div>
		{/if}

		{#if candidate.requirements.output_format}
			<div class="flex flex-col">
				<span class="text-gray-500 dark:text-gray-400">Output</span>
				<span class="text-gray-900 dark:text-gray-100 truncate">
					{candidate.requirements.output_format}
				</span>
			</div>
		{/if}

		{#if candidate.requirements.schedule}
			<div class="flex flex-col">
				<span class="text-gray-500 dark:text-gray-400">Schedule</span>
				<span class="text-gray-900 dark:text-gray-100 truncate">
					{candidate.requirements.schedule}
				</span>
			</div>
		{/if}
	</div>

	<!-- Completeness Bar -->
	<div class="mt-3">
		<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
			<span>Completeness</span>
			<span>{formatCompleteness(candidate.requirements.completeness)}</span>
		</div>
		<div class="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
			<div
				class="h-full bg-blue-500 transition-all duration-300"
				style="width: {candidate.requirements.completeness * 100}%"
				role="progressbar"
				aria-valuenow={candidate.requirements.completeness * 100}
				aria-valuemin={0}
				aria-valuemax={100}
			></div>
		</div>
	</div>

	<!-- Selection Indicator -->
	{#if selected}
		<div class="mt-3 flex items-center gap-2 text-blue-600 dark:text-blue-400">
			<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
				<path
					fill-rule="evenodd"
					d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
					clip-rule="evenodd"
				/>
			</svg>
			<span class="text-sm font-medium">Selected</span>
		</div>
	{/if}
</div>

<style>
	.candidate-card:focus {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
	}
</style>
