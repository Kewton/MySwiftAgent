<script lang="ts">
	/**
	 * ScoreSlider - Score input component with 1-5 scale
	 *
	 * Features:
	 * - 1-5 scale with visual representation
	 * - Accessible labels for each score
	 * - Touch-friendly design
	 * - Keyboard navigation
	 */

	import { createEventDispatcher } from 'svelte';

	export let value: number | undefined = undefined;
	export let label: string;
	export let description = '';
	export let id: string;
	export let disabled = false;

	const dispatch = createEventDispatcher<{
		change: { value: number };
	}>();

	const scores = [
		{ value: 1, label: 'Poor' },
		{ value: 2, label: 'Fair' },
		{ value: 3, label: 'Good' },
		{ value: 4, label: 'Very Good' },
		{ value: 5, label: 'Excellent' }
	];

	function handleSelect(score: number) {
		if (disabled) return;
		value = score;
		dispatch('change', { value: score });
	}

	function handleKeyDown(event: KeyboardEvent, score: number) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			handleSelect(score);
		}
	}

	function getScoreColor(score: number): string {
		const colors: Record<number, string> = {
			1: 'bg-red-500',
			2: 'bg-orange-500',
			3: 'bg-yellow-500',
			4: 'bg-lime-500',
			5: 'bg-green-500'
		};
		return colors[score] || 'bg-gray-500';
	}
</script>

<div class="score-slider" data-testid="score-slider-{id}">
	<div class="mb-2">
		<label for={id} class="block text-sm font-medium text-gray-900 dark:text-gray-100">
			{label}
		</label>
		{#if description}
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
				{description}
			</p>
		{/if}
	</div>

	<div class="flex gap-2" role="radiogroup" aria-labelledby="{id}-label" {id}>
		{#each scores as score (score.value)}
			<button
				type="button"
				class="flex-1 flex flex-col items-center p-2 rounded-lg border-2 transition-all
					{value === score.value
					? `border-blue-500 ${getScoreColor(score.value)} text-white`
					: 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}
					{disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
				role="radio"
				aria-checked={value === score.value}
				aria-label="{label}: {score.label}"
				tabindex={value === score.value || (value === undefined && score.value === 1) ? 0 : -1}
				{disabled}
				on:click={() => handleSelect(score.value)}
				on:keydown={(e) => handleKeyDown(e, score.value)}
				data-testid="score-{score.value}"
			>
				<span
					class="text-lg font-bold
						{value === score.value ? 'text-white' : 'text-gray-700 dark:text-gray-300'}"
				>
					{score.value}
				</span>
				<span
					class="text-xs mt-0.5
						{value === score.value ? 'text-white/90' : 'text-gray-500 dark:text-gray-400'}"
				>
					{score.label}
				</span>
			</button>
		{/each}
	</div>

	<!-- Selected Value Display -->
	{#if value !== undefined}
		<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
			Selected: <span class="font-medium">{scores[value - 1]?.label}</span>
		</div>
	{/if}
</div>

<style>
	.score-slider button:focus {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
	}
</style>
