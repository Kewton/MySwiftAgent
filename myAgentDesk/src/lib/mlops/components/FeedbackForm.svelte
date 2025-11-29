<script lang="ts">
	/**
	 * FeedbackForm - Form for submitting conversation feedback scores
	 *
	 * Features:
	 * - Four score categories (1-5 scale)
	 * - Optional comment field
	 * - Validation
	 * - Loading state
	 * - i18n support
	 */

	import { createEventDispatcher } from 'svelte';
	import ScoreSlider from './ScoreSlider.svelte';
	import type { FeedbackScores } from '../types';
	import { t } from '$lib/stores/locale';

	export let conversationId: string;
	export let loading = false;
	export let disabled = false;

	const dispatch = createEventDispatcher<{
		submit: FeedbackScores;
		cancel: void;
	}>();

	let scores: FeedbackScores = {
		requirement_clarity: undefined,
		interpretation_accuracy: undefined,
		response_helpfulness: undefined,
		overall_satisfaction: undefined,
		comment: ''
	};

	$: hasAnyScore =
		scores.requirement_clarity !== undefined ||
		scores.interpretation_accuracy !== undefined ||
		scores.response_helpfulness !== undefined ||
		scores.overall_satisfaction !== undefined;

	function handleSubmit() {
		if (!hasAnyScore || disabled || loading) return;
		dispatch('submit', scores);
	}

	function handleCancel() {
		dispatch('cancel');
	}

	function handleScoreChange(field: keyof FeedbackScores, value: number) {
		scores = { ...scores, [field]: value };
	}
</script>

<form class="feedback-form" on:submit|preventDefault={handleSubmit} data-testid="feedback-form">
	<div class="space-y-6">
		<!-- Requirement Clarity -->
		<ScoreSlider
			id="requirement-clarity"
			label={t('mlops.requirementClarity')}
			description={t('mlops.requirementClarityDesc')}
			value={scores.requirement_clarity}
			{disabled}
			on:change={(e) => handleScoreChange('requirement_clarity', e.detail.value)}
		/>

		<!-- Interpretation Accuracy -->
		<ScoreSlider
			id="interpretation-accuracy"
			label={t('mlops.interpretationAccuracy')}
			description={t('mlops.interpretationAccuracyDesc')}
			value={scores.interpretation_accuracy}
			{disabled}
			on:change={(e) => handleScoreChange('interpretation_accuracy', e.detail.value)}
		/>

		<!-- Response Helpfulness -->
		<ScoreSlider
			id="response-helpfulness"
			label={t('mlops.responseHelpfulness')}
			description={t('mlops.responseHelpfulnessDesc')}
			value={scores.response_helpfulness}
			{disabled}
			on:change={(e) => handleScoreChange('response_helpfulness', e.detail.value)}
		/>

		<!-- Overall Satisfaction -->
		<ScoreSlider
			id="overall-satisfaction"
			label={t('mlops.overallSatisfaction')}
			description={t('mlops.overallSatisfactionDesc')}
			value={scores.overall_satisfaction}
			{disabled}
			on:change={(e) => handleScoreChange('overall_satisfaction', e.detail.value)}
		/>

		<!-- Comment -->
		<div>
			<label
				for="feedback-comment"
				class="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2"
			>
				{t('mlops.additionalComments')}
			</label>
			<textarea
				id="feedback-comment"
				bind:value={scores.comment}
				rows="3"
				class="w-full px-3 py-2 border rounded-lg resize-none
					border-gray-300 dark:border-gray-600
					bg-white dark:bg-gray-800
					text-gray-900 dark:text-gray-100
					focus:ring-2 focus:ring-blue-500 focus:border-blue-500
					disabled:opacity-50 disabled:cursor-not-allowed"
				placeholder={t('mlops.commentPlaceholder')}
				disabled={disabled || loading}
				data-testid="feedback-comment"
			></textarea>
		</div>
	</div>

	<!-- Actions -->
	<div class="mt-6 flex justify-end gap-3">
		<button
			type="button"
			class="px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300
				bg-gray-100 dark:bg-gray-800
				hover:bg-gray-200 dark:hover:bg-gray-700
				focus:ring-2 focus:ring-gray-500 focus:ring-offset-2
				disabled:opacity-50 disabled:cursor-not-allowed"
			disabled={loading}
			on:click={handleCancel}
			data-testid="feedback-cancel"
		>
			{t('mlops.cancel')}
		</button>
		<button
			type="submit"
			class="px-4 py-2 rounded-lg font-medium text-white
				{hasAnyScore && !disabled && !loading
				? 'bg-blue-600 hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
				: 'bg-gray-400 cursor-not-allowed'}"
			disabled={!hasAnyScore || disabled || loading}
			data-testid="feedback-submit"
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
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						></path>
					</svg>
					{t('mlops.submitting')}
				</span>
			{:else}
				{t('mlops.submitFeedback')}
			{/if}
		</button>
	</div>

	<!-- Conversation ID (hidden, for reference) -->
	<input type="hidden" name="conversation_id" value={conversationId} />
</form>
