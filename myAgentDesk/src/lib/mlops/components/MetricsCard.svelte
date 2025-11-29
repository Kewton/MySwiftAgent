<script lang="ts">
	/**
	 * MetricsCard - Displays a single metric value with label and trend
	 *
	 * Features:
	 * - Large value display
	 * - Optional trend indicator
	 * - Color variants
	 * - Loading state
	 */

	export let label: string;
	export let value: string | number;
	export let sublabel = '';
	export let trend: 'up' | 'down' | 'neutral' | null = null;
	export let trendValue = '';
	export let variant: 'default' | 'success' | 'warning' | 'danger' = 'default';
	export let loading = false;

	const variantColors: Record<
		string,
		{ bg: string; text: string; trendUp: string; trendDown: string }
	> = {
		default: {
			bg: 'bg-gray-50 dark:bg-gray-800',
			text: 'text-gray-900 dark:text-gray-100',
			trendUp: 'text-green-600',
			trendDown: 'text-red-600'
		},
		success: {
			bg: 'bg-green-50 dark:bg-green-900/20',
			text: 'text-green-900 dark:text-green-100',
			trendUp: 'text-green-700',
			trendDown: 'text-red-600'
		},
		warning: {
			bg: 'bg-yellow-50 dark:bg-yellow-900/20',
			text: 'text-yellow-900 dark:text-yellow-100',
			trendUp: 'text-green-600',
			trendDown: 'text-red-600'
		},
		danger: {
			bg: 'bg-red-50 dark:bg-red-900/20',
			text: 'text-red-900 dark:text-red-100',
			trendUp: 'text-green-600',
			trendDown: 'text-red-700'
		}
	};

	$: colors = variantColors[variant] || variantColors.default;
</script>

<div
	class="metrics-card p-4 rounded-xl {colors.bg} transition-all"
	data-testid="metrics-card-{label.toLowerCase().replace(/\s+/g, '-')}"
>
	{#if loading}
		<div class="animate-pulse">
			<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-1/2 mb-2"></div>
			<div class="h-8 bg-gray-300 dark:bg-gray-600 rounded w-3/4 mb-1"></div>
			<div class="h-3 bg-gray-300 dark:bg-gray-600 rounded w-1/3"></div>
		</div>
	{:else}
		<!-- Label -->
		<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
			{label}
		</div>

		<!-- Value -->
		<div class="flex items-baseline gap-2">
			<span class="text-2xl font-bold {colors.text}">
				{value}
			</span>

			<!-- Trend Indicator -->
			{#if trend && trendValue}
				<span
					class="flex items-center text-sm font-medium
						{trend === 'up' ? colors.trendUp : trend === 'down' ? colors.trendDown : 'text-gray-500'}"
				>
					{#if trend === 'up'}
						<svg class="w-4 h-4 mr-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
							<path
								fill-rule="evenodd"
								d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
					{:else if trend === 'down'}
						<svg class="w-4 h-4 mr-0.5" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
							<path
								fill-rule="evenodd"
								d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
					{trendValue}
				</span>
			{/if}
		</div>

		<!-- Sublabel -->
		{#if sublabel}
			<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
				{sublabel}
			</div>
		{/if}
	{/if}
</div>
