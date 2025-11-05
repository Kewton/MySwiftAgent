<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ScheduleSelector from './ScheduleSelector.svelte';
	import CronEditor from './CronEditor.svelte';

	export let isOpen = false;
	export let isCreatingJob = false;

	const dispatch = createEventDispatcher<{
		create: {
			executionMode: 'api_only' | 'schedule' | 'both';
			cronExpression?: string;
			timezone?: string;
		};
		cancel: void;
	}>();

	let currentStep: 'mode' | 'schedule' = 'mode';
	let executionMode: 'api_only' | 'schedule' | 'both' = 'api_only';
	let cronExpression = '0 9 * * *';
	let timezone = 'Asia/Tokyo';

	function handleExecutionModeChange(mode: 'api_only' | 'schedule' | 'both') {
		executionMode = mode;
	}

	function handleCronChange(cron: string) {
		cronExpression = cron;
	}

	function handleNext() {
		if (executionMode === 'api_only') {
			// API Onlyの場合は直接作成
			handleCreate();
		} else {
			// スケジュール設定が必要な場合は次のステップへ
			currentStep = 'schedule';
		}
	}

	function handleBack() {
		currentStep = 'mode';
	}

	function handleCreate() {
		dispatch('create', {
			executionMode,
			cronExpression: executionMode !== 'api_only' ? cronExpression : undefined,
			timezone: executionMode !== 'api_only' ? timezone : undefined
		});
	}

	function handleCancel() {
		// モーダルをリセット
		currentStep = 'mode';
		executionMode = 'api_only';
		dispatch('cancel');
	}

	// モーダルが開かれたときにリセット
	$: if (isOpen) {
		currentStep = 'mode';
		executionMode = 'api_only';
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
		on:click={handleCancel}
		role="button"
		tabindex="-1"
		on:keydown={(e) => e.key === 'Escape' && handleCancel()}
	/>

	<!-- Modal -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4"
		role="dialog"
		aria-modal="true"
	>
		<div
			class="bg-white dark:bg-dark-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
			on:click|stopPropagation
			role="presentation"
		>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
					{currentStep === 'mode' ? 'ジョブ作成 - 実行方法の選択' : 'ジョブ作成 - スケジュール設定'}
				</h2>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto px-6 py-4">
				{#if currentStep === 'mode'}
					<!-- Step 1: 実行方法選択 -->
					<div class="space-y-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							ジョブの実行方法を選択してください。
						</p>
						<ScheduleSelector {executionMode} onChange={handleExecutionModeChange} />
					</div>
				{:else}
					<!-- Step 2: スケジュール設定 -->
					<div class="space-y-4">
						<p class="text-sm text-gray-600 dark:text-gray-400">
							実行スケジュールを設定してください。
						</p>
						<CronEditor bind:cronExpression bind:timezone onCronChange={handleCronChange} />
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div
				class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center"
			>
				<button
					type="button"
					on:click={handleCancel}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					disabled={isCreatingJob}
				>
					キャンセル
				</button>

				<div class="flex gap-2">
					{#if currentStep === 'schedule'}
						<button
							type="button"
							on:click={handleBack}
							class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
							disabled={isCreatingJob}
						>
							戻る
						</button>
					{/if}

					{#if currentStep === 'mode'}
						<button
							type="button"
							on:click={handleNext}
							class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={isCreatingJob}
						>
							{executionMode === 'api_only' ? 'Create' : 'Next'}
						</button>
					{:else}
						<button
							type="button"
							on:click={handleCreate}
							class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							disabled={isCreatingJob}
						>
							{isCreatingJob ? '作成中...' : 'Create'}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* モーダルのスムーズなアニメーション */
	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes slideUp {
		from {
			transform: translateY(20px);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}

	div[role='dialog'] > div {
		animation: slideUp 0.2s ease-out;
	}
</style>
