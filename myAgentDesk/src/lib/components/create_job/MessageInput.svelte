<script lang="ts">
	import Button from '$lib/components/Button.svelte';
	import { t } from '$lib/stores/locale';

	export let message = '';
	export let isStreaming = false;
	export let isComposing = false;
	export let onSend: () => void;
	export let onKeydown: (event: KeyboardEvent) => void;
	export let onCompositionStart: () => void;
	export let onCompositionEnd: () => void;
</script>

<div class="bg-white dark:bg-dark-bg px-6 py-4">
	<div class="max-w-5xl mx-auto">
		<div class="flex gap-3 items-end">
			<textarea
				bind:value={message}
				on:keydown={onKeydown}
				on:compositionstart={onCompositionStart}
				on:compositionend={onCompositionEnd}
				placeholder={t('chat.placeholder')}
				class="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-3 bg-white dark:bg-dark-bg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
				rows="3"
				disabled={isStreaming}
			/>
			<Button variant="primary" on:click={onSend} disabled={isStreaming || !message.trim()}>
				{#if isStreaming}
					⏳
				{:else}
					{t('chat.send')}
				{/if}
			</Button>
		</div>
		<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
			{t('chat.enterToSend')}
			{#if isComposing}
				<span class="text-primary-600 dark:text-primary-400">{t('chat.composing')}</span>
			{/if}
		</p>
	</div>
</div>
