<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { page } from '$app/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import RequirementCard from '$lib/components/create_job/RequirementCard.svelte';
	import ChatContainer from '$lib/components/create_job/ChatContainer.svelte';
	import MessageInput from '$lib/components/create_job/MessageInput.svelte';
	import { conversationStore, activeConversation, type Message } from '$lib/stores/conversations';
	import { t } from '$lib/stores/locale';
	import { streamChatRequirementDefinition, createJob, ServiceError } from '$lib/services';

	let sidebarOpen = true;
	let message = '';
	let isStreaming = false;
	let isCreatingJob = false;
	let isComposing = false; // IME入力中フラグ
	let chatContainer: HTMLDivElement | undefined; // チャットスクロール用ref
	let shouldScrollToBottom = false; // スクロールフラグ

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

	onMount(() => {
		// URLパラメータから会話IDを取得
		const id = $page.url.searchParams.get('id');

		if (id) {
			// 既存の会話を選択
			conversationStore.setActive(id);
		} else {
			// 会話が存在しない場合、新規作成
			if (!activeConv) {
				const newConv = conversationStore.create();
				window.history.replaceState({}, '', `/?id=${newConv.id}`);
			}
		}
	});

	// メッセージ追加後に自動スクロール
	afterUpdate(() => {
		if (shouldScrollToBottom && chatContainer) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
			shouldScrollToBottom = false;
		}
	});

	function formatTime(): string {
		const now = new Date();
		return now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
	}

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
		if (!message.trim() || isStreaming || !conversationId) return;

		const userMessage = message.trim();
		message = '';

		// ユーザーメッセージを追加
		const userMsg: Message = {
			role: 'user',
			message: userMessage,
			timestamp: formatTime()
		};
		conversationStore.addMessage(conversationId, userMsg);
		shouldScrollToBottom = true; // メッセージ追加後にスクロール

		isStreaming = true;

		let assistantMessage = '';
		let hasAddedAssistantMsg = false;

		try {
			await streamChatRequirementDefinition(
				conversationId,
				userMessage,
				messages.map((m) => ({ role: m.role, content: m.message })),
				requirements,
				// メッセージチャンク受信時
				(content: string) => {
					assistantMessage += content;

					// アシスタントメッセージを追加または更新
					if (!hasAddedAssistantMsg) {
						const assistantMsg: Message = {
							role: 'assistant',
							message: assistantMessage,
							timestamp: formatTime()
						};
						conversationStore.addMessage(conversationId, assistantMsg);
						hasAddedAssistantMsg = true;
					} else {
						conversationStore.updateLastAssistantMessage(conversationId, assistantMessage);
					}
				},
				// 要求状態更新時
				(updatedRequirements) => {
					conversationStore.updateRequirements(conversationId, updatedRequirements);
				}
			);
		} catch (error) {
			console.error('Error streaming chat:', error);
			const errorMessage =
				error instanceof ServiceError
					? error.message
					: error instanceof Error
						? error.message
						: t('error.general');
			const errorMsg: Message = {
				role: 'assistant',
				message: errorMessage,
				timestamp: formatTime()
			};
			conversationStore.addMessage(conversationId, errorMsg);
		} finally {
			isStreaming = false;
		}
	}

	async function handleCreateJob() {
		if (requirements.completeness < 0.8) {
			alert(t('alert.insufficientRequirements', (requirements.completeness * 100).toFixed(0)));
			return;
		}

		if (!conversationId) {
			alert(t('alert.noConversation'));
			return;
		}

		isCreatingJob = true;

		try {
			const result = await createJob(conversationId, requirements);

			// ジョブ結果を保存
			conversationStore.saveJobResult(conversationId, result);

			// 成功メッセージを追加
			const successMsg: Message = {
				role: 'assistant',
				message: t('job.createSuccess', result.job_id, result.job_master_id),
				timestamp: formatTime()
			};
			conversationStore.addMessage(conversationId, successMsg);
		} catch (error) {
			console.error('Error creating job:', error);
			const errorMessage =
				error instanceof ServiceError
					? error.message
					: error instanceof Error
						? error.message
						: String(error);
			const errorMsg: Message = {
				role: 'assistant',
				message: `❌ **${t('error.jobCreation')}** ${errorMessage}`,
				timestamp: formatTime()
			};
			conversationStore.addMessage(conversationId, errorMsg);
		} finally {
			isCreatingJob = false;
		}
	}
</script>

<svelte:head>
	<title>Create Job - myAgentDesk</title>
</svelte:head>

<!-- Layout -->
<div class="flex h-[calc(100vh-4rem)]">
	<!-- Sidebar (fixed position, overlays content) -->
	<div class="fixed top-16 left-0 bottom-0 z-40">
		<Sidebar bind:open={sidebarOpen} activeConversationId={conversationId} />
	</div>

	<!-- Main Content with left margin when sidebar is open -->
	<main
		class="flex-1 flex flex-col bg-white dark:bg-dark-bg overflow-hidden transition-all duration-300"
		class:ml-64={sidebarOpen}
	>
		<!-- Header -->
		<div class="bg-white dark:bg-dark-card border-b border-gray-200 dark:border-gray-800 px-6 py-2">
			<div class="flex items-center gap-3">
				{#if !sidebarOpen}
					<button
						on:click={() => (sidebarOpen = true)}
						class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors"
						aria-label="Open sidebar"
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
				{/if}
				<div>
					<h1 class="text-xl font-bold text-gray-900 dark:text-white">{t('header.title')}</h1>
					{#if t('header.subtitle')}
						<p class="text-xs text-gray-500 dark:text-gray-400">{t('header.subtitle')}</p>
					{/if}
				</div>
			</div>
		</div>

		<!-- Fixed Requirement State Card -->
		<RequirementCard {requirements} {isCreatingJob} onCreateJob={handleCreateJob} />

		<!-- Scrollable Chat Messages Area -->
		<ChatContainer {messages} bind:containerRef={chatContainer} />

		<!-- Input Area -->
		<MessageInput
			bind:message
			{isStreaming}
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
