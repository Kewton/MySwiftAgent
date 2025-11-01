<script lang="ts">
	import type { Conversation } from '$lib/stores/conversations';
	import ConversationItem from './ConversationItem.svelte';

	export let title: string;
	export let conversations: Conversation[];
	export let activeId: string | null;
	export let onSelect: (id: string) => void;
	export let onDelete: (id: string) => void;
	export let onRename: (id: string, title: string) => void;
	export let editLabel: string;
	export let deleteLabel: string;
	export let timestampFormatter: (timestamp: number) => string;
	export let placeholder: string;
</script>

{#if conversations.length > 0}
	<div class="mb-4">
		<h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 px-3 mb-2 uppercase">
			{title}
		</h3>
		{#each conversations as conversation}
			<ConversationItem
				{conversation}
				active={conversation.id === activeId}
				timestampLabel={timestampFormatter(conversation.updatedAt)}
				{onSelect}
				{onDelete}
				{onRename}
				{editLabel}
				{deleteLabel}
				{placeholder}
			/>
		{/each}
	</div>
{/if}
