<script lang="ts">
	/**
	 * RealtimeChart - Simple bar chart for model usage visualization
	 *
	 * Features:
	 * - Horizontal bar chart
	 * - Percentage display
	 * - Responsive design
	 * - Animated transitions
	 */

	import type { ModelUsage } from '../types';

	export let data: ModelUsage[] = [];
	export let title = 'Model Usage';
	export let loading = false;

	const colors = [
		'bg-blue-500',
		'bg-green-500',
		'bg-purple-500',
		'bg-orange-500',
		'bg-pink-500',
		'bg-cyan-500',
		'bg-indigo-500',
		'bg-teal-500'
	];

	function getColor(index: number): string {
		return colors[index % colors.length];
	}

	function formatCount(count: number): string {
		if (count >= 1000000) {
			return `${(count / 1000000).toFixed(1)}M`;
		}
		if (count >= 1000) {
			return `${(count / 1000).toFixed(1)}K`;
		}
		return count.toString();
	}
</script>

<div class="realtime-chart" data-testid="realtime-chart">
	<!-- Title -->
	<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-4">
		{title}
	</h3>

	{#if loading}
		<div class="space-y-3 animate-pulse">
			{#each [0, 1, 2] as i (i)}
				<div class="flex items-center gap-3">
					<div class="w-20 h-4 bg-gray-300 dark:bg-gray-600 rounded"></div>
					<div class="flex-1 h-4 bg-gray-300 dark:bg-gray-600 rounded"></div>
					<div class="w-12 h-4 bg-gray-300 dark:bg-gray-600 rounded"></div>
				</div>
			{/each}
		</div>
	{:else if data.length === 0}
		<div class="text-center py-8 text-gray-500 dark:text-gray-400" data-testid="no-data-message">
			No data available
		</div>
	{:else}
		<div class="space-y-3" role="list" aria-label="Model usage statistics">
			{#each data as item, index (item.model)}
				<div class="flex items-center gap-3" role="listitem">
					<!-- Model Name -->
					<div class="w-28 text-sm text-gray-700 dark:text-gray-300 truncate" title={item.model}>
						{item.model}
					</div>

					<!-- Bar -->
					<div class="flex-1 h-6 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
						<div
							class="{getColor(
								index
							)} h-full rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
							style="width: {Math.max(item.percentage, 5)}%"
							role="progressbar"
							aria-valuenow={item.percentage}
							aria-valuemin={0}
							aria-valuemax={100}
							aria-label="{item.model}: {item.percentage.toFixed(1)}%"
						>
							{#if item.percentage > 15}
								<span class="text-xs font-medium text-white">
									{item.percentage.toFixed(1)}%
								</span>
							{/if}
						</div>
					</div>

					<!-- Stats -->
					<div class="w-20 text-right">
						<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
							{formatCount(item.count)}
						</span>
						{#if item.percentage <= 15}
							<span class="text-xs text-gray-500 dark:text-gray-400 ml-1">
								({item.percentage.toFixed(1)}%)
							</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<!-- Legend / Total -->
		<div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
			<div class="flex justify-between text-sm">
				<span class="text-gray-500 dark:text-gray-400">Total</span>
				<span class="font-medium text-gray-900 dark:text-gray-100">
					{formatCount(data.reduce((sum, item) => sum + item.count, 0))} requests
				</span>
			</div>
		</div>
	{/if}
</div>
