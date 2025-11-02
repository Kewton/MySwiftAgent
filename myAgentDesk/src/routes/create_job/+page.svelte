<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { page } from '$app/stores';
	import InnerSidebar from '$lib/components/InnerSidebar.svelte';
	import RequirementCard from '$lib/components/create_job/RequirementCard.svelte';
	import ChatContainer from '$lib/components/create_job/ChatContainer.svelte';
	import MessageInput from '$lib/components/create_job/MessageInput.svelte';
	import ScheduleSelector from '$lib/components/create_job/ScheduleSelector.svelte';
	import CronEditor from '$lib/components/create_job/CronEditor.svelte';
	import MarpViewer from '$lib/components/create_job/MarpViewer.svelte';
	import SlideNavigation from '$lib/components/create_job/SlideNavigation.svelte';
	import { conversationStore, activeConversation } from '$lib/stores/conversations';
	import { chatSession } from '$lib/stores/chatSession';
	import { innerSidebarOpen } from '$lib/stores/sidebar';
	import { createSchedule } from '$lib/services/schedule-api';
	import { getMarpPdfUrl, getMarpPngUrls } from '$lib/services/marp-api';

	let message = '';
	let isComposing = false; // IME入力中フラグ
	let chatContainer: HTMLDivElement | undefined; // チャットスクロール用ref
	let lastScrollToken = 0;

	// スケジュール設定用の状態
	let executionMode: 'api_only' | 'schedule' | 'both' = 'api_only';
	let cronExpression = '0 9 * * *';
	let timezone = 'Asia/Tokyo';

	// スライド表示用の状態
	let showSlides = false;
	let createdJobId: string | null = null;
	let marpViewerRef: MarpViewer | undefined;
	let currentSlide = 1;
	let totalSlides = 1;

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
		try {
			// まずジョブを作成
			const jobResult = await chatSession.submitJob();

			if (jobResult && jobResult.job_id) {
				// ジョブ作成成功時の処理
				createdJobId = jobResult.job_id;

				// スケジュール実行が必要な場合、スケジュールを作成
				if (executionMode === 'schedule' || executionMode === 'both') {
					try {
						await createSchedule({
							job_id: jobResult.job_id,
							cron_expression: cronExpression,
							timezone: timezone
						});
						console.log('Schedule created successfully');
					} catch (error) {
						console.error('Failed to create schedule:', error);
						// スケジュール作成失敗はエラーとして表示するが、ジョブ作成は成功しているので継続
						alert('ジョブは作成されましたが、スケジュール設定に失敗しました。');
					}
				}

				// ジョブ作成成功後、自動的にスライドタブに切り替え
				showSlides = true;
			}
		} catch (error) {
			console.error('Failed to create job:', error);
			throw error;
		}
	}

	function handleExecutionModeChange(mode: 'api_only' | 'schedule' | 'both') {
		executionMode = mode;
	}

	function handleCronChange(cron: string) {
		cronExpression = cron;
	}

	// スライドナビゲーション
	function handlePrevSlide() {
		if (marpViewerRef) {
			marpViewerRef.prevSlide();
		}
	}

	function handleNextSlide() {
		if (marpViewerRef) {
			marpViewerRef.nextSlide();
		}
	}

	function handleFullscreen() {
		const viewer = document.querySelector('.marp-viewer-container');
		if (viewer) {
			viewer.requestFullscreen();
		}
	}

	async function handleExportPdf() {
		if (!createdJobId) return;
		try {
			const pdfUrl = await getMarpPdfUrl(createdJobId);
			window.open(pdfUrl, '_blank');
		} catch (error) {
			console.error('Failed to export PDF:', error);
			alert('PDFのエクスポートに失敗しました。');
		}
	}

	async function handleExportPng() {
		if (!createdJobId) return;
		try {
			const pngUrls = await getMarpPngUrls(createdJobId);
			// 各スライドのPNGを順次ダウンロード
			pngUrls.forEach((url, index) => {
				const link = document.createElement('a');
				link.href = url;
				link.download = `slide-${index + 1}.png`;
				link.click();
			});
		} catch (error) {
			console.error('Failed to export PNG:', error);
			alert('PNGのエクスポートに失敗しました。');
		}
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

		<!-- Schedule Settings (表示条件: completeness >= 0.8) -->
		{#if requirements.completeness >= 0.8 && !showSlides}
			<div class="px-6 py-4 space-y-4 border-b border-gray-200 dark:border-gray-700">
				<!-- 実行方法選択 -->
				<ScheduleSelector {executionMode} onChange={handleExecutionModeChange} />

				<!-- Cron式編集（スケジュール実行の場合のみ表示） -->
				{#if executionMode === 'schedule' || executionMode === 'both'}
					<CronEditor bind:cronExpression bind:timezone onCronChange={handleCronChange} />
				{/if}
			</div>
		{/if}

		<!-- タブ切り替え（ジョブ作成後に表示） -->
		{#if createdJobId}
			<div class="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
				<button
					class="px-6 py-3 text-sm font-medium transition {!showSlides
						? 'border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (showSlides = false)}
				>
					💬 チャット
				</button>
				<button
					class="px-6 py-3 text-sm font-medium transition {showSlides
						? 'border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (showSlides = true)}
				>
					📊 スライド
				</button>
			</div>
		{/if}

		<!-- コンテンツエリア -->
		{#if !showSlides}
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
		{:else if createdJobId}
			<!-- スライド表示エリア -->
			<div class="flex-1 flex flex-col overflow-hidden">
				<div class="flex-1 overflow-auto">
					<MarpViewer
						jobId={createdJobId}
						bind:this={marpViewerRef}
						bind:currentSlide
						bind:totalSlides
					/>
				</div>
				<SlideNavigation
					{currentSlide}
					{totalSlides}
					onPrev={handlePrevSlide}
					onNext={handleNextSlide}
					onFullscreen={handleFullscreen}
					onExportPdf={handleExportPdf}
					onExportPng={handleExportPng}
				/>
			</div>
		{/if}
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
