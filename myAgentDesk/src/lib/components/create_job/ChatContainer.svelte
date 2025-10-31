<script lang="ts">
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import Card from '$lib/components/Card.svelte';
	import { t } from '$lib/stores/locale';
	import type { Message } from '$lib/stores/conversations';

	export let messages: Message[];
	export let containerRef: HTMLDivElement | undefined = undefined;
</script>

<div bind:this={containerRef} class="flex-1 overflow-y-auto px-6 py-6">
	<div class="max-w-5xl mx-auto">
		{#if messages.length === 0}
			<Card>
				<div class="text-center py-8">
					<div class="text-6xl mb-4">💬</div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
						{t('chat.startTitle')}
					</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						{t('chat.startDescription')}
					</p>
				</div>
			</Card>
		{:else}
			<div>
				{#each messages as msg}
					<ChatBubble role={msg.role} message={msg.message} timestamp={msg.timestamp} />
				{/each}
			</div>
		{/if}
	</div>
</div>
