<script lang="ts">
	export let value: string;
	export let onInput: (value: string) => void;
	export let placeholder: string;

	function handleInput(event: Event) {
		const target = event.target as HTMLInputElement;
		onInput(target.value);
	}
</script>

<div class="relative mt-3">
	<input
		type="text"
		{value}
		on:input={handleInput}
		{placeholder}
		class="w-full px-3 py-2 pl-9 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-bg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
	/>
	<svg
		class="absolute left-3 top-2.5 w-4 h-4 text-gray-400 dark:text-gray-500"
		fill="none"
		stroke="currentColor"
		viewBox="0 0 24 24"
	>
		<path
			stroke-linecap="round"
			stroke-linejoin="round"
			stroke-width="2"
			d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
		/>
	</svg>
	{#if value}
		<button
			on:click={() => onInput('')}
			class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
			aria-label="Clear search"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M6 18L18 6M6 6l12 12"
				/>
			</svg>
		</button>
	{/if}
</div>
