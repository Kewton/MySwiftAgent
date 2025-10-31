<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { page } from '$app/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';
	import { conversationStore, activeConversation, type Message } from '$lib/stores/conversations';
	import { t } from '$lib/stores/locale';

	let sidebarOpen = true;
	let message = '';
	let isStreaming = false;
	let isCreatingJob = false;
	let isComposing = false; // IME入力中フラグ
	let requirementCardCollapsed = false; // 要求状態カードの折りたたみ状態
	let chatContainer: HTMLDivElement; // チャットスクロール用ref
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

	const API_BASE = 'http://localhost:8104/aiagent-api/v1';

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
				window.history.replaceState({}, '', `/create_job?id=${newConv.id}`);
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

		try {
			const response = await fetch(`${API_BASE}/chat/requirement-definition`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					conversation_id: conversationId,
					user_message: userMessage,
					context: {
						previous_messages: messages.map((m) => ({ role: m.role, content: m.message })),
						current_requirements: requirements
					}
				})
			});

			if (!response.ok) {
				throw new Error(`HTTP ${response.status}: ${response.statusText}`);
			}

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			let assistantMessage = '';
			let hasAddedAssistantMsg = false;

			if (reader) {
				// eslint-disable-next-line no-constant-condition
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					const chunk = decoder.decode(value, { stream: true });
					const lines = chunk.split('\n');

					for (const line of lines) {
						if (line.startsWith('data: ')) {
							const data = JSON.parse(line.substring(6));

							if (data.type === 'message') {
								assistantMessage += data.data.content;

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
							} else if (data.type === 'requirement_update') {
								// 要求状態を更新
								conversationStore.updateRequirements(conversationId, data.data.requirements);
							}
						}
					}
				}
			}
		} catch (error) {
			console.error('Error streaming chat:', error);
			const errorMsg: Message = {
				role: 'assistant',
				message: t('error.general'),
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
			const response = await fetch(`${API_BASE}/chat/create-job`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					conversation_id: conversationId,
					requirements: requirements
				})
			});

			const result = await response.json();

			if (response.ok) {
				// ジョブ結果を保存
				conversationStore.saveJobResult(conversationId, result);

				// 成功メッセージを追加
				const successMsg: Message = {
					role: 'assistant',
					message: t('job.createSuccess', result.job_id, result.job_master_id),
					timestamp: formatTime()
				};
				conversationStore.addMessage(conversationId, successMsg);
			} else {
				throw new Error(result.detail || t('error.jobCreation'));
			}
		} catch (error) {
			console.error('Error creating job:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
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
		<div
			class="px-4 pt-3 pb-2 bg-white dark:bg-dark-bg border-b border-gray-200 dark:border-gray-800"
		>
			<Card>
				<div class="space-y-4 py-2">
					<!-- Header with Collapse Button -->
					<div class="flex items-center justify-between">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
							{t('requirement.title')}
						</h3>
						<button
							on:click={() => (requirementCardCollapsed = !requirementCardCollapsed)}
							class="p-2 text-2xl text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
							aria-label={requirementCardCollapsed
								? t('requirement.expand')
								: t('requirement.collapse')}
						>
							{requirementCardCollapsed ? '▼' : '▲'}
						</button>
					</div>

					{#if !requirementCardCollapsed}
						<!-- Detailed Information (collapsible) -->
						<div class="grid grid-cols-2 gap-2">
							<div>
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{t('requirement.dataSource')}
								</div>
								<div class="text-base font-medium text-gray-900 dark:text-white">
									{requirements.data_source || t('requirement.undefined')}
								</div>
							</div>
							<div>
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{t('requirement.outputFormat')}
								</div>
								<div class="text-base font-medium text-gray-900 dark:text-white">
									{requirements.output_format || t('requirement.undefined')}
								</div>
							</div>
							<div class="col-span-2">
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{t('requirement.processDescription')}
								</div>
								<div class="text-base font-medium text-gray-900 dark:text-white">
									{requirements.process_description || t('requirement.undefined')}
								</div>
							</div>
							<div>
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{t('requirement.schedule')}
								</div>
								<div class="text-base font-medium text-gray-900 dark:text-white">
									{requirements.schedule || t('requirement.undefined')}
								</div>
							</div>
						</div>
					{/if}

					<!-- Completeness Bar (always visible) -->
					<div>
						<div class="flex justify-between items-center mb-2">
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
									{t('requirement.completeness')}
								</span>
								<!-- Help Icon with Tooltip -->
								<div class="relative inline-block group">
									<span
										class="flex items-center justify-center w-5 h-5 rounded-full border-2 border-gray-400 dark:border-gray-500 text-gray-500 dark:text-gray-400 text-xs font-bold cursor-help hover:border-gray-600 dark:hover:border-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
									>
										?
									</span>
									<!-- Custom Tooltip -->
									<div class="absolute left-0 bottom-full mb-2 hidden group-hover:block z-50 w-80">
										<div
											class="bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg p-3 shadow-lg"
										>
											<div class="font-semibold mb-2">{t('legend.title')}</div>
											<div class="space-y-1">
												<div class="flex items-start gap-2">
													<span class="text-purple-400">•</span>
													<span>{t('legend.stage1')}</span>
												</div>
												<div class="flex items-start gap-2">
													<span class="text-purple-400">•</span>
													<span>{t('legend.stage2')}</span>
												</div>
												<div class="flex items-start gap-2">
													<span class="text-purple-400">•</span>
													<span>{t('legend.stage3')}</span>
												</div>
												<div class="flex items-start gap-2">
													<span class="text-purple-400">•</span>
													<span>{t('legend.stage4')}</span>
												</div>
												<div class="flex items-start gap-2">
													<span class="text-green-400">•</span>
													<span class="font-medium">{t('legend.stage5')}</span>
												</div>
											</div>
											<!-- Tooltip Arrow -->
											<div
												class="absolute left-4 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-gray-900 dark:border-t-gray-800"
											></div>
										</div>
									</div>
								</div>
							</div>
							<span
								class="text-sm font-bold {requirements.completeness >= 0.8
									? 'text-green-600 dark:text-green-400'
									: 'text-purple-600 dark:text-purple-400'}"
							>
								{(requirements.completeness * 100).toFixed(0)}%
							</span>
						</div>
						<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
							<div
								class="h-full transition-all duration-500 {requirements.completeness >= 0.8
									? 'bg-gradient-to-r from-green-500 to-green-600'
									: 'bg-gradient-to-r from-purple-500 to-purple-600'}"
								style="width: {requirements.completeness * 100}%"
							/>
						</div>

						{#if requirements.completeness >= 0.8}
							<p class="text-xs text-green-600 dark:text-green-400 mt-2">
								{t('requirement.readyToCreate')}
							</p>
						{:else}
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
								{t('requirement.needsMore')}
							</p>
						{/if}
					</div>

					<!-- Create Job Button -->
					<Button
						variant="primary"
						on:click={handleCreateJob}
						disabled={requirements.completeness < 0.8 || isCreatingJob}
						class="w-full"
					>
						{#if isCreatingJob}
							{t('requirement.creatingJob')}
						{:else}
							{t('requirement.createJob')}
						{/if}
					</Button>
				</div>
			</Card>
		</div>

		<!-- Scrollable Chat Messages Area -->
		<div bind:this={chatContainer} class="flex-1 overflow-y-auto px-6 py-6">
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

		<!-- Input Area -->
		<div class="bg-white dark:bg-dark-bg px-6 py-4">
			<div class="max-w-5xl mx-auto">
				<div class="flex gap-3 items-end">
					<textarea
						bind:value={message}
						on:keydown={handleKeydown}
						on:compositionstart={handleCompositionStart}
						on:compositionend={handleCompositionEnd}
						placeholder={t('chat.placeholder')}
						class="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-3 bg-white dark:bg-dark-bg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
						rows="3"
						disabled={isStreaming}
					/>
					<Button variant="primary" on:click={handleSend} disabled={isStreaming || !message.trim()}>
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
