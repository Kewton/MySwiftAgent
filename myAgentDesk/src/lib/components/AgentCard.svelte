<script lang="ts">
	export let name: string;
	export let description: string;
	export let icon: string = '🤖';
	export let color: 'purple' | 'pink' | 'orange' | 'blue' = 'purple';
	export let status: 'active' | 'inactive' | 'error' = 'inactive';

	const colorClasses = {
		purple: 'border-accent-purple shadow-purple-200 dark:shadow-purple-900/20',
		pink: 'border-accent-pink shadow-pink-200 dark:shadow-pink-900/20',
		orange: 'border-accent-orange shadow-orange-200 dark:shadow-orange-900/20',
		blue: 'border-primary-500 shadow-primary-200 dark:shadow-primary-900/20'
	};

	const statusStyles = {
		active: 'bg-green-500',
		inactive: 'bg-gray-400',
		error: 'bg-red-500'
	};

	const statusLabels = {
		active: 'Active',
		inactive: 'Inactive',
		error: 'Error'
	};
</script>

<div class="node-card {colorClasses[color]}">
	<div class="flex items-start justify-between mb-3">
		<div class="text-4xl">{icon}</div>
		<div class="flex items-center gap-2">
			<div class="w-2 h-2 rounded-full {statusStyles[status]}"></div>
			<span class="text-xs text-gray-600 dark:text-gray-400">{statusLabels[status]}</span>
		</div>
	</div>
	<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
		{name}
	</h3>
	<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
		{description}
	</p>
	<div class="mt-4 flex gap-2">
		<button class="btn-primary text-sm px-3 py-1.5">Configure</button>
		<button class="btn-secondary text-sm px-3 py-1.5">View Details</button>
	</div>
</div>
