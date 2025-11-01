<script lang="ts">
	export let onToggle: () => void;
	export let onCreateConversation: () => void;
	export let title: string;
</script>

<div class="flex items-center justify-between mb-4">
	<button
		on:click={onToggle}
		class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors"
		aria-label="Toggle sidebar"
	>
		<svg
			class="w-5 h-5 text-gray-700 dark:text-gray-300"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M4 6h16M4 12h16M4 18h16"
			/>
		</svg>
	</button>
</div>
<button
	on:click={onCreateConversation}
	class="w-full btn-primary flex items-center justify-center gap-2"
>
	<span class="text-xl">+</span>
	{title}
</button>
