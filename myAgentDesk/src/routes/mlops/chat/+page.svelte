<script lang="ts">
	/**
	 * MLOps Chat Page - Requirement clarification with candidate selection and feedback
	 *
	 * Features:
	 * - Candidate selection UI
	 * - Feedback form
	 * - Chat history display
	 * - Requirements progress
	 * - i18n support
	 */

	import { onMount } from 'svelte';
	import CandidateSelector from '$lib/mlops/components/CandidateSelector.svelte';
	import FeedbackModal from '$lib/mlops/components/FeedbackModal.svelte';
	import { selectCandidate, submitFeedback } from '$lib/mlops/api/client';
	import type { Candidate, FeedbackScores, RequirementState } from '$lib/mlops/types';
	import { t } from '$lib/stores/locale';

	// Demo data for development
	const demoConversationId = 'conv_demo_001';

	let candidates: Candidate[] = [
		{
			id: 'A',
			label: 'A',
			description: 'Sales data analysis with monthly aggregation',
			confidence: 0.85,
			requirements: {
				data_source: 'CSV files from sales department',
				process_description: 'Monthly sales aggregation',
				output_format: 'Excel report',
				schedule: 'Daily at 9:00 AM',
				completeness: 0.75
			}
		},
		{
			id: 'B',
			label: 'B',
			description: 'Real-time sales dashboard',
			confidence: 0.72,
			requirements: {
				data_source: 'Sales database API',
				process_description: 'Real-time dashboard update',
				output_format: 'Web dashboard',
				schedule: 'Every 5 minutes',
				completeness: 0.65
			}
		}
	];

	let selectedCandidateId: string | null = null;
	let selectionLoading = false;
	let showFeedbackModal = false;
	let feedbackLoading = false;
	let currentRequirements: RequirementState | null = null;
	let successMessage: string | null = null;
	let errorMessage: string | null = null;

	async function handleCandidateSelect(event: CustomEvent<{ candidateId: string }>) {
		selectedCandidateId = event.detail.candidateId;
	}

	async function handleCandidateConfirm(event: CustomEvent<{ candidateId: string }>) {
		selectionLoading = true;
		errorMessage = null;

		try {
			const response = await selectCandidate(demoConversationId, event.detail.candidateId);
			currentRequirements = response.requirements;
			successMessage = response.message;
			candidates = []; // Clear candidates after selection
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Failed to select candidate';
		} finally {
			selectionLoading = false;
		}
	}

	async function handleFeedbackSubmit(event: CustomEvent<FeedbackScores>) {
		feedbackLoading = true;
		errorMessage = null;

		try {
			const response = await submitFeedback({
				conversation_id: demoConversationId,
				...event.detail
			});
			successMessage = response.message;
			showFeedbackModal = false;
		} catch (err) {
			errorMessage = err instanceof Error ? err.message : 'Failed to submit feedback';
		} finally {
			feedbackLoading = false;
		}
	}

	function openFeedbackModal() {
		showFeedbackModal = true;
	}

	function closeFeedbackModal() {
		showFeedbackModal = false;
	}

	onMount(() => {
		// Initial setup - could connect to SSE here for real-time candidates
	});
</script>

<svelte:head>
	<title>Chat | MLOps | myAgentDesk</title>
</svelte:head>

<div class="chat-page" data-testid="mlops-chat-page">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
			{t('mlops.requirementClarification')}
		</h1>

		<button
			type="button"
			class="flex items-center gap-2 px-4 py-2 rounded-lg font-medium
				text-gray-700 dark:text-gray-300
				bg-gray-100 dark:bg-gray-800
				hover:bg-gray-200 dark:hover:bg-gray-700
				focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
			on:click={openFeedbackModal}
			data-testid="open-feedback-button"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
				/>
			</svg>
			{t('mlops.rateExperience')}
		</button>
	</div>

	<!-- Success Message -->
	{#if successMessage}
		<div
			class="mb-6 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
			role="status"
			data-testid="success-message"
		>
			<p>{successMessage}</p>
		</div>
	{/if}

	<!-- Error Message -->
	{#if errorMessage}
		<div
			class="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
			role="alert"
			data-testid="error-message"
		>
			<p>{errorMessage}</p>
		</div>
	{/if}

	<!-- Current Requirements Display -->
	{#if currentRequirements}
		<div class="mb-6 p-6 rounded-xl bg-white dark:bg-gray-800 shadow-sm">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
				{t('mlops.confirmedRequirements')}
			</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				{#if currentRequirements.data_source}
					<div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{t('mlops.dataSource')}</span>
						<p class="text-gray-900 dark:text-gray-100">{currentRequirements.data_source}</p>
					</div>
				{/if}
				{#if currentRequirements.process_description}
					<div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{t('mlops.process')}</span>
						<p class="text-gray-900 dark:text-gray-100">
							{currentRequirements.process_description}
						</p>
					</div>
				{/if}
				{#if currentRequirements.output_format}
					<div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{t('mlops.output')}</span>
						<p class="text-gray-900 dark:text-gray-100">{currentRequirements.output_format}</p>
					</div>
				{/if}
				{#if currentRequirements.schedule}
					<div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{t('mlops.schedule')}</span>
						<p class="text-gray-900 dark:text-gray-100">{currentRequirements.schedule}</p>
					</div>
				{/if}
			</div>
			<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<span class="text-sm text-gray-500 dark:text-gray-400">{t('mlops.completeness')}</span>
					<span class="font-medium text-gray-900 dark:text-gray-100">
						{(currentRequirements.completeness * 100).toFixed(0)}%
					</span>
				</div>
				<div class="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
					<div
						class="h-full bg-green-500 transition-all duration-300"
						style="width: {currentRequirements.completeness * 100}%"
					></div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Candidate Selection -->
	{#if candidates.length > 0}
		<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
			<CandidateSelector
				{candidates}
				bind:selectedId={selectedCandidateId}
				loading={selectionLoading}
				on:select={handleCandidateSelect}
				on:confirm={handleCandidateConfirm}
			/>
		</div>
	{:else if !currentRequirements}
		<div class="text-center py-12 text-gray-500 dark:text-gray-400">
			<svg
				class="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
				/>
			</svg>
			<p class="text-lg font-medium">{t('mlops.noActiveConversation')}</p>
			<p class="mt-2">{t('mlops.startNewConversation')}</p>
		</div>
	{/if}

	<!-- Feedback Modal -->
	<FeedbackModal
		open={showFeedbackModal}
		conversationId={demoConversationId}
		loading={feedbackLoading}
		on:submit={handleFeedbackSubmit}
		on:close={closeFeedbackModal}
	/>
</div>
