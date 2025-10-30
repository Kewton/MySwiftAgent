<script lang="ts">
	import { conversationStore, groupedConversations, type Conversation } from '$lib/stores/conversations';
	import { goto } from '$app/navigation';
	import { locale, t } from '$lib/stores/locale';

	export let open = true;
	export let activeConversationId: string | null = null;

	let hoveredId: string | null = null;
	let editingId: string | null = null;
	let editingTitle: string = '';
	let searchQuery: string = '';

	$: conversations = $groupedConversations;
	$: hasConversations = conversations.today.length + conversations.yesterday.length + conversations.lastSevenDays.length + conversations.older.length > 0;

	// Filter conversations based on search query
	$: filteredConversations = {
		today: conversations.today.filter(conv =>
			conv.title.toLowerCase().includes(searchQuery.toLowerCase())
		),
		yesterday: conversations.yesterday.filter(conv =>
			conv.title.toLowerCase().includes(searchQuery.toLowerCase())
		),
		lastSevenDays: conversations.lastSevenDays.filter(conv =>
			conv.title.toLowerCase().includes(searchQuery.toLowerCase())
		),
		older: conversations.older.filter(conv =>
			conv.title.toLowerCase().includes(searchQuery.toLowerCase())
		)
	};

	$: hasFilteredConversations = filteredConversations.today.length + filteredConversations.yesterday.length + filteredConversations.lastSevenDays.length + filteredConversations.older.length > 0;

	function createNewConversation() {
		const newConv = conversationStore.create();
		goto(`/create_job?id=${newConv.id}`);
	}

	function selectConversation(id: string) {
		conversationStore.setActive(id);
		goto(`/create_job?id=${id}`);
	}

	function deleteConversation(event: Event, id: string) {
		event.stopPropagation();
		if (confirm(t('sidebar.deleteConfirm'))) {
			conversationStore.delete(id);
			// アクティブな会話が削除された場合、新しい会話を作成
			if (id === activeConversationId) {
				createNewConversation();
			}
		}
	}

	function startEditing(event: Event, id: string, currentTitle: string) {
		event.stopPropagation();
		editingId = id;
		editingTitle = currentTitle;
	}

	function saveEdit() {
		if (editingId && editingTitle.trim()) {
			conversationStore.updateTitle(editingId, editingTitle.trim());
		}
		editingId = null;
		editingTitle = '';
	}

	function cancelEdit() {
		editingId = null;
		editingTitle = '';
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			saveEdit();
		} else if (event.key === 'Escape') {
			cancelEdit();
		}
	}

	function formatTimestamp(timestamp: number): string {
		const now = Date.now();
		const diff = now - timestamp;
		const minutes = Math.floor(diff / 60000);
		const hours = Math.floor(diff / 3600000);
		const days = Math.floor(diff / 86400000);

		if (minutes < 1) return t('time.now');
		if (minutes < 60) return t('time.minutesAgo', minutes);
		if (hours < 24) return t('time.hoursAgo', hours);
		if (days === 1) return t('time.yesterday');
		if (days < 7) return t('time.daysAgo', days);
		const localeCode = $locale === 'ja' ? 'ja-JP' : 'en-US';
		return new Date(timestamp).toLocaleDateString(localeCode, { month: 'short', day: 'numeric' });
	}

	function renderGroup(title: string, convs: Conversation[]) {
		return { title, conversations: convs };
	}

	$: groups = [
		renderGroup(t('sidebar.today'), filteredConversations.today),
		renderGroup(t('sidebar.yesterday'), filteredConversations.yesterday),
		renderGroup(t('sidebar.lastSevenDays'), filteredConversations.lastSevenDays),
		renderGroup(t('sidebar.older'), filteredConversations.older)
	].filter(g => g.conversations.length > 0);
</script>

{#if open}
	<aside class="sidebar">
		<div class="p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between mb-4">
				<button
					on:click={() => open = false}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors"
					aria-label="Close sidebar"
				>
					<svg class="w-5 h-5 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
					</svg>
				</button>
			</div>
			<button
				on:click={createNewConversation}
				class="w-full btn-primary flex items-center justify-center gap-2"
			>
				<span class="text-xl">+</span>
				{t('sidebar.newChat')}
			</button>

			<!-- Search Box -->
			<div class="mt-3">
				<div class="relative">
					<input
						type="text"
						bind:value={searchQuery}
						placeholder={t('sidebar.searchJobs')}
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
					{#if searchQuery}
						<button
							on:click={() => searchQuery = ''}
							class="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
							aria-label="Clear search"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					{/if}
				</div>
			</div>
		</div>

		<!-- Conversations List (OpenWebUI style) -->
		<div class="flex-1 overflow-y-auto px-2">
			{#if !hasConversations}
				<div class="text-center text-sm text-gray-500 dark:text-gray-400 py-8 px-4">
					{t('sidebar.noConversations')}
				</div>
			{:else if searchQuery && !hasFilteredConversations}
				<div class="text-center text-sm text-gray-500 dark:text-gray-400 py-8 px-4">
					{t('sidebar.noSearchResults')}
				</div>
			{:else}
				{#each groups as group}
					<div class="mb-4">
						<h3 class="text-xs font-semibold text-gray-500 dark:text-gray-400 px-3 mb-2 uppercase">
							{group.title}
						</h3>
						{#each group.conversations as conv}
							<div
								class="relative group"
								on:mouseenter={() => hoveredId = conv.id}
								on:mouseleave={() => hoveredId = null}
							>
								<button
									on:click={() => selectConversation(conv.id)}
									class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors mb-1 {activeConversationId === conv.id ? 'bg-gray-100 dark:bg-dark-hover' : ''}"
								>
									<div class="flex items-start justify-between gap-2">
										<div class="flex-1 min-w-0">
											{#if editingId === conv.id}
												<!-- Edit Mode -->
												<input
													type="text"
													bind:value={editingTitle}
													on:keydown={handleKeydown}
													on:blur={saveEdit}
													on:click={(e) => e.stopPropagation()}
													class="w-full text-sm font-medium text-gray-900 dark:text-white bg-white dark:bg-dark-bg border border-primary-500 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500"
													placeholder="ジョブ名を入力"
													autofocus
												/>
											{:else}
												<!-- Display Mode -->
												<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
													{conv.title}
												</div>
											{/if}
											<div class="text-xs text-gray-500 dark:text-gray-400">
												{formatTimestamp(conv.updatedAt)}
											</div>
										</div>
										{#if hoveredId === conv.id && editingId !== conv.id}
											<div class="flex gap-1">
												<!-- Edit Button -->
												<button
													on:click={(e) => startEditing(e, conv.id, conv.title)}
													class="p-1 hover:bg-blue-100 dark:hover:bg-blue-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
													aria-label="編集"
												>
													<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
													</svg>
												</button>
												<!-- Delete Button -->
												<button
													on:click={(e) => deleteConversation(e, conv.id)}
													class="p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
													aria-label={t('sidebar.delete')}
												>
													<span class="text-red-600 dark:text-red-400">🗑️</span>
												</button>
											</div>
										{/if}
									</div>
								</button>
							</div>
						{/each}
					</div>
				{/each}
			{/if}
		</div>

		<!-- Bottom Actions -->
		<div class="p-4 border-t border-gray-200 dark:border-gray-700">
			<a
				href="/settings"
				class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2"
			>
				⚙️ {t('sidebar.settings')}
			</a>
		</div>
	</aside>
{/if}
