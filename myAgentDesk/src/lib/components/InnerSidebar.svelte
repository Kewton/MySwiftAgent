<script lang="ts">
	import { goto } from '$app/navigation';
	import { locale, t } from '$lib/stores/locale';
	import { conversationStore, groupedConversations } from '$lib/stores/conversations';
	import SearchBox from './sidebar/SearchBox.svelte';
	import ConversationGroup from './sidebar/ConversationGroup.svelte';

	export let open = true;
	export let activeConversationId: string | null = null;

	let searchQuery = '';

	$: conversations = $groupedConversations;
	$: hasConversations =
		conversations.today.length +
			conversations.yesterday.length +
			conversations.lastSevenDays.length +
			conversations.older.length >
		0;

	function normalize(value: string): string {
		return value.toLowerCase();
	}

	function filterList(list: typeof conversations.today) {
		const query = normalize(searchQuery);
		if (!query) return list;
		return list.filter((conversation) => normalize(conversation.title).includes(query));
	}

	$: filteredConversations = {
		today: filterList(conversations.today),
		yesterday: filterList(conversations.yesterday),
		lastSevenDays: filterList(conversations.lastSevenDays),
		older: filterList(conversations.older)
	};

	$: hasFilteredConversations =
		filteredConversations.today.length +
			filteredConversations.yesterday.length +
			filteredConversations.lastSevenDays.length +
			filteredConversations.older.length >
		0;

	function createNewConversation() {
		const newConversation = conversationStore.create();
		goto(`/create_job?id=${newConversation.id}`);
	}

	function selectConversation(id: string) {
		conversationStore.setActive(id);
		goto(`/create_job?id=${id}`);
	}

	function deleteConversation(id: string) {
		if (!confirm(t('sidebar.deleteConfirm'))) return;
		conversationStore.delete(id);
		if (id === activeConversationId) {
			createNewConversation();
		}
	}

	function renameConversation(id: string, title: string) {
		conversationStore.updateTitle(id, title);
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

	function buildGroup(title: string, list: typeof conversations.today) {
		return { title, conversations: list };
	}

	$: groups = [
		buildGroup(t('sidebar.today'), filteredConversations.today),
		buildGroup(t('sidebar.yesterday'), filteredConversations.yesterday),
		buildGroup(t('sidebar.lastSevenDays'), filteredConversations.lastSevenDays),
		buildGroup(t('sidebar.older'), filteredConversations.older)
	].filter((group) => group.conversations.length > 0);

	$: editPlaceholder = $locale === 'ja' ? 'ジョブ名を入力' : 'Enter job name';
	$: editLabel = $locale === 'ja' ? '編集' : 'Edit';
	$: deleteLabel = t('sidebar.delete');
</script>

{#if open}
	<aside
		class="h-screen bg-white dark:bg-dark-card border-r border-gray-200 dark:border-gray-700 flex flex-col"
		style="width: var(--inner-sidebar-width, 256px);"
	>
		<div class="p-4 border-b border-gray-200 dark:border-gray-700">
			<button
				on:click={createNewConversation}
				class="w-full mb-3 px-4 py-2 bg-primary-600 dark:bg-primary-700 text-white rounded-lg hover:bg-primary-700 dark:hover:bg-primary-600 transition-colors flex items-center justify-center gap-2"
			>
				<span>➕</span>
				<span class="text-sm font-medium">{t('sidebar.newChat')}</span>
			</button>
			<SearchBox
				value={searchQuery}
				onInput={(value) => (searchQuery = value)}
				placeholder={t('sidebar.searchJobs')}
			/>
		</div>

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
					<ConversationGroup
						title={group.title}
						conversations={group.conversations}
						activeId={activeConversationId}
						onSelect={selectConversation}
						onDelete={deleteConversation}
						onRename={renameConversation}
						{editLabel}
						{deleteLabel}
						timestampFormatter={formatTimestamp}
						placeholder={editPlaceholder}
					/>
				{/each}
			{/if}
		</div>
	</aside>
{/if}
