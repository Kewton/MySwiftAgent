<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { page } from '$app/stores';
	import InnerSidebar from '$lib/components/InnerSidebar.svelte';
	import RequirementCard from '$lib/components/create_job/RequirementCard.svelte';
	import ChatContainer from '$lib/components/create_job/ChatContainer.svelte';
	import MessageInput from '$lib/components/create_job/MessageInput.svelte';
	import { conversationStore, activeConversation } from '$lib/stores/conversations';
	import { chatSession } from '$lib/stores/chatSession';
	import { innerSidebarOpen } from '$lib/stores/sidebar';

	let message = '';
	let isComposing = false; // IME入力中フラグ
	let chatContainer: HTMLDivElement | undefined; // チャットスクロール用ref
	let lastScrollToken = 0;

	// アクティブな会話のリアクティブデータ
	$: activeConv = $activeConversation;
	$: conversationId = activeConv?.id || '';
	$: messages = activeConv?.messages || [];
	$: requirements = activeConv?.requirements || {
		data_source: null,
		process_description: null,
		output_format: null,
		schedule: null,
		completeness: 0
	};
	$: sessionState = $chatSession;

	onMount(() => {
		// URLパラメータから会話IDを取得
		const id = $page.url.searchParams.get('id');

		if (id) {
			// 既存の会話を選択
			conversationStore.setActive(id);
		} else if (!activeConv) {
			// 会話が存在しない場合、新規作成
			const newConv = conversationStore.create();
			window.history.replaceState({}, '', `/create_job?id=${newConv.id}`);
		}

		// Auto-open inner sidebar on this page
		innerSidebarOpen.set(true);
	});

	// メッセージ追加後に自動スクロール
	afterUpdate(() => {
		if (!chatContainer) return;
		const { scrollToken } = sessionState;
		if (scrollToken !== lastScrollToken) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
			lastScrollToken = scrollToken;
		}
	});

	// IME入力開始
	function handleCompositionStart() {
		isComposing = true;
	}

	// IME入力終了
	function handleCompositionEnd() {
		// compositionend後もフラグを少し維持（Enterキーイベントとの競合を防ぐ）
		setTimeout(() => {
			isComposing = false;
		}, 100);
	}

	// キーボードイベント（IME対応）
	function handleKeydown(event: KeyboardEvent) {
		// IME入力中はEnterを無視（event.isComposingもチェック）
		if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !isComposing) {
			event.preventDefault();
			handleSend();
		}
	}

	async function handleSend() {
		if (!message.trim() || sessionState.isStreaming) return;
		const userMessage = message;
		message = '';
		await chatSession.sendMessage(userMessage);
	}

	async function handleCreateJob() {
		await chatSession.submitJob();
	}
</script>

<svelte:head>
	<title>Create Job - myAgentDesk</title>
</svelte:head>

<!-- Layout -->
<div class="flex h-full">
	<!-- Inner Sidebar (conversation history) -->
	<InnerSidebar open={$innerSidebarOpen} activeConversationId={conversationId} />

	<!-- Main Content -->
	<main class="flex-1 flex flex-col bg-white dark:bg-dark-bg overflow-hidden">
		<!-- Fixed Requirement State Card -->
		<RequirementCard
			{requirements}
			isCreatingJob={sessionState.isCreatingJob}
			onCreateJob={handleCreateJob}
		/>

		<!-- Scrollable Chat Messages Area -->
		<ChatContainer {messages} bind:containerRef={chatContainer} />

		<!-- Input Area -->
		<MessageInput
			bind:message
			isStreaming={sessionState.isStreaming}
			{isComposing}
			onSend={handleSend}
			onKeydown={handleKeydown}
			onCompositionStart={handleCompositionStart}
			onCompositionEnd={handleCompositionEnd}
		/>
	</main>
</div>

<style>
	/* Custom scrollbar styling */
	:global(.overflow-y-auto)::-webkit-scrollbar {
		width: 8px;
	}

	:global(.overflow-y-auto)::-webkit-scrollbar-track {
		background: transparent;
	}

	:global(.overflow-y-auto)::-webkit-scrollbar-thumb {
		background: rgba(0, 0, 0, 0.2);
		border-radius: 4px;
	}

	:global(.dark .overflow-y-auto)::-webkit-scrollbar-thumb {
		background: rgba(255, 255, 255, 0.2);
	}
</style>
