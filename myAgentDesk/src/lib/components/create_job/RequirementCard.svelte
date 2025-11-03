<script lang="ts">
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';
	import { t } from '$lib/stores/locale';
	import type { RequirementState } from '$lib/stores/conversations';

	export let requirements: RequirementState;
	export let isCreatingJob = false;
	export let onCreateJob: () => void;

	let collapsed = false;

	$: isReady = requirements.completeness >= 0.8;
</script>

<div class="px-4 pt-3 pb-2 bg-white dark:bg-dark-bg border-b border-gray-200 dark:border-gray-800">
	<Card>
		<div class="space-y-4 py-2">
			<!-- Header with Collapse Button -->
			<div class="flex items-center justify-between">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
					{t('requirement.title')}
				</h3>
				<button
					on:click={() => (collapsed = !collapsed)}
					class="p-2 text-2xl text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
					aria-label={collapsed ? t('requirement.expand') : t('requirement.collapse')}
				>
					{collapsed ? '▼' : '▲'}
				</button>
			</div>

			{#if !collapsed}
				<!-- Detailed Information (collapsible) -->
				<div class="grid grid-cols-2 gap-2">
					<div>
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{t('requirement.dataSource')}
						</div>
						<div class="text-base font-medium text-gray-900 dark:text-white">
							{requirements.data_source || t('requirement.undefined')}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{t('requirement.outputFormat')}
						</div>
						<div class="text-base font-medium text-gray-900 dark:text-white">
							{requirements.output_format || t('requirement.undefined')}
						</div>
					</div>
					<div class="col-span-2">
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{t('requirement.processDescription')}
						</div>
						<div class="text-base font-medium text-gray-900 dark:text-white">
							{requirements.process_description || t('requirement.undefined')}
						</div>
					</div>
					<div>
						<div class="text-sm text-gray-500 dark:text-gray-400">
							{t('requirement.schedule')}
						</div>
						<div class="text-base font-medium text-gray-900 dark:text-white">
							{requirements.schedule || t('requirement.undefined')}
						</div>
					</div>
				</div>
			{/if}

			<!-- Completeness Bar (always visible) -->
			<div>
				<div class="flex justify-between items-center mb-2">
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
							{t('requirement.completeness')}
						</span>
						<!-- Help Icon with Tooltip -->
						<div class="relative inline-block group">
							<span
								class="flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-400 dark:border-gray-500 text-gray-500 dark:text-gray-400 text-xs font-bold cursor-help hover:border-gray-600 dark:hover:border-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
							>
								?
							</span>
							<!-- Custom Tooltip -->
							<div class="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 w-80">
								<div
									class="bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg p-3 shadow-lg"
								>
									<div class="font-semibold mb-2">{t('legend.title')}</div>
									<div class="space-y-1">
										<div class="flex items-start gap-2">
											<span class="text-purple-400">•</span>
											<span>{t('legend.stage1')}</span>
										</div>
										<div class="flex items-start gap-2">
											<span class="text-purple-400">•</span>
											<span>{t('legend.stage2')}</span>
										</div>
										<div class="flex items-start gap-2">
											<span class="text-purple-400">•</span>
											<span>{t('legend.stage3')}</span>
										</div>
										<div class="flex items-start gap-2">
											<span class="text-purple-400">•</span>
											<span>{t('legend.stage4')}</span>
										</div>
										<div class="flex items-start gap-2">
											<span class="text-green-400">•</span>
											<span class="font-medium">{t('legend.stage5')}</span>
										</div>
									</div>
									<!-- Tooltip Arrow -->
									<div
										class="absolute left-4 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-gray-900 dark:border-t-gray-800"
									></div>
								</div>
							</div>
						</div>
					</div>
					<span
						class="text-sm font-bold {isReady
							? 'text-green-600 dark:text-green-400'
							: 'text-purple-600 dark:text-purple-400'}"
					>
						{(requirements.completeness * 100).toFixed(0)}%
					</span>
				</div>
				<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
					<div
						class="h-full transition-all duration-500 {isReady
							? 'bg-gradient-to-r from-green-500 to-green-600'
							: 'bg-gradient-to-r from-purple-500 to-purple-600'}"
						style="width: {requirements.completeness * 100}%"
					/>
				</div>

				{#if isReady}
					<p class="text-xs text-green-600 dark:text-green-400 mt-2">
						{t('requirement.readyToCreate')}
					</p>
				{:else}
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						{t('requirement.needsMore')}
					</p>
				{/if}
			</div>

			<!-- Create Job Button -->
			<Button
				variant="primary"
				on:click={onCreateJob}
				disabled={!isReady || isCreatingJob}
				class="w-full"
			>
				{#if isCreatingJob}
					{t('requirement.creatingJob')}
				{:else}
					{t('requirement.createJob')}
				{/if}
			</Button>
		</div>
	</Card>
</div>
