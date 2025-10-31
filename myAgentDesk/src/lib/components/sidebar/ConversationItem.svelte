<script lang="ts">
	import type { Conversation } from '$lib/stores/conversations';
	export let conversation: Conversation;
	export let active = false;
	export let timestampLabel: string;
	export let onSelect: (id: string) => void;
	export let onDelete: (id: string) => void;
	export let onRename: (id: string, title: string) => void;
	export let editLabel: string;
	export let deleteLabel: string;
	export let placeholder: string;

	let isHovered = false;
	let isEditing = false;
	let draftTitle = conversation.title;

	function startEditing(event: Event) {
		event.stopPropagation();
		isEditing = true;
		draftTitle = conversation.title;
	}

	function handleDelete(event: Event) {
		event.stopPropagation();
		onDelete(conversation.id);
	}

	function saveEdit() {
		if (!draftTitle.trim()) {
			isEditing = false;
			return;
		}
		onRename(conversation.id, draftTitle.trim());
		isEditing = false;
	}

	function cancelEdit() {
		isEditing = false;
		draftTitle = conversation.title;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			saveEdit();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEdit();
		}
	}
</script>

<div
	class="relative group"
	role="listitem"
	on:mouseenter={() => (isHovered = true)}
	on:mouseleave={() => (isHovered = false)}
>
	<button
		on:click={() => onSelect(conversation.id)}
		class={`w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors mb-1 ${
			active ? 'bg-gray-100 dark:bg-dark-hover' : ''
		}`}
	>
		<div class="flex items-start justify-between gap-2">
			<div class="flex-1 min-w-0">
				{#if isEditing}
					<input
						type="text"
						bind:value={draftTitle}
						on:keydown={handleKeydown}
						on:blur={saveEdit}
						on:click={(event) => event.stopPropagation()}
						class="w-full text-sm font-medium text-gray-900 dark:text-white bg-white dark:bg-dark-bg border border-primary-500 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500"
						{placeholder}
					/>
				{:else}
					<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
						{conversation.title}
					</div>
				{/if}
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{timestampLabel}
				</div>
			</div>
			{#if isHovered && !isEditing}
				<div class="flex gap-1">
					<button
						on:click={startEditing}
						class="p-1 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
						aria-label={editLabel}
					>
						<svg
							class="w-4 h-4 text-blue-600 dark:text-blue-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
							/>
						</svg>
					</button>
					<button
						on:click={handleDelete}
						class="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
						aria-label={deleteLabel}
					>
						<span class="text-red-600 dark:text-red-400">🗑️</span>
					</button>
				</div>
			{/if}
		</div>
	</button>
</div>
