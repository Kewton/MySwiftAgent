<script lang="ts">
	/**
	 * Create Job Page - Main page for job creation with MLOps integration
	 *
	 * Issue #192: Create Job MLOps UI integration
	 * Features:
	 * - Chat-based requirement clarification
	 * - Candidate selection from LLM responses
	 * - Feedback submission after job creation
	 * - Job creation with progress tracking
	 */

	import { onMount, afterUpdate } from 'svelte';
	import { page } from '$app/stores';
	import InnerSidebar from '$lib/components/InnerSidebar.svelte';
	import RequirementCard from '$lib/components/create_job/RequirementCard.svelte';
	import ChatContainer from '$lib/components/create_job/ChatContainer.svelte';
	import MessageInput from '$lib/components/create_job/MessageInput.svelte';
	import JobCreationModal from '$lib/components/create_job/JobCreationModal.svelte';
	import MarpViewer from '$lib/components/create_job/MarpViewer.svelte';
	import SlideNavigation from '$lib/components/create_job/SlideNavigation.svelte';
	import CandidateSelector from '$lib/mlops/components/CandidateSelector.svelte';
	import FeedbackModal from '$lib/mlops/components/FeedbackModal.svelte';
	import { conversationStore, activeConversation } from '$lib/stores/conversations';
	import { chatSession } from '$lib/stores/chatSession';
	import { innerSidebarOpen } from '$lib/stores/sidebar';
	import { createSchedule } from '$lib/services/schedule-api';
	import { getMarpPdfUrl, getMarpPngUrls } from '$lib/services/marp-api';
	import { createJobAsync, getJobStatus } from '$lib/services';
	import { selectCandidate, submitFeedback } from '$lib/mlops/api/client';
	import { parseCandidatesFromResponse, type ParsedCandidate } from '$lib/utils/candidate-parser';
	import type { Candidate, FeedbackScores } from '$lib/mlops/types';

	let message = '';
	let isComposing = false; // IME入力中フラグ
	let chatContainer: HTMLDivElement | undefined; // チャットスクロール用ref
	let lastScrollToken = 0;

	// モーダル管理
	let isModalOpen = false;

	// スライド表示用の状態
	let showSlides = false;
	let createdJobId: string | null = null;
	let marpViewerRef: MarpViewer | undefined;
	let currentSlide = 1;
	let totalSlides = 1;

	// MLOps UI状態 (Issue #192)
	let candidates: Candidate[] = [];
	let selectedCandidateId: string | null = null;
	let isCandidateLoading = false;
	let showCandidateSelector = false;
	let isFeedbackModalOpen = false;
	let isFeedbackLoading = false;
	let feedbackSubmitted = false;

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

	// LLMレスポンスから候補を検出・パース (Issue #192)
	$: {
		if (messages.length > 0) {
			const lastMessage = messages[messages.length - 1];
			if (lastMessage.role === 'assistant') {
				const parsedCandidates = parseCandidatesFromResponse(lastMessage.message);
				if (parsedCandidates.length > 0) {
					// ParsedCandidateをCandidateに変換
					candidates = parsedCandidates.map((pc: ParsedCandidate) => ({
						id: pc.id,
						label: pc.label,
						description: pc.description,
						confidence: pc.confidence,
						requirements: pc.requirements
					}));
					showCandidateSelector = true;
					selectedCandidateId = null;
				} else {
					showCandidateSelector = false;
					candidates = [];
				}
			}
		}
	}

	// ジョブ作成状態の管理（localStorage）
	const JOB_CREATION_KEY = 'myAgentDesk_jobCreation';

	interface JobCreationState {
		conversationId: string;
		startTime: number;
		executionMode: 'api_only' | 'schedule' | 'both';
		cronExpression?: string;
		timezone?: string;
		status: 'creating' | 'completed' | 'failed';
		jobId?: string; // ジョブID（ポーリング用）
	}

	function saveJobCreationState(state: JobCreationState) {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(JOB_CREATION_KEY, JSON.stringify(state));
		}
	}

	function clearJobCreationState() {
		if (typeof localStorage !== 'undefined') {
			localStorage.removeItem(JOB_CREATION_KEY);
		}
	}

	function getJobCreationState(): JobCreationState | null {
		if (typeof localStorage !== 'undefined') {
			const stored = localStorage.getItem(JOB_CREATION_KEY);
			if (stored) {
				try {
					return JSON.parse(stored);
				} catch {
					return null;
				}
			}
		}
		return null;
	}

	/**
	 * 候補選択ハンドラー (Issue #192)
	 */
	function handleCandidateSelect(event: CustomEvent<{ candidateId: string }>) {
		selectedCandidateId = event.detail.candidateId;
	}

	/**
	 * 候補確定ハンドラー (Issue #192)
	 */
	async function handleCandidateConfirm(event: CustomEvent<{ candidateId: string }>) {
		if (!conversationId || isCandidateLoading) return;

		isCandidateLoading = true;

		try {
			const response = await selectCandidate(conversationId, event.detail.candidateId);

			// 要件状態を更新
			if (response.requirements) {
				conversationStore.updateRequirements(conversationId, response.requirements);
			}

			// 確認メッセージを追加
			conversationStore.addMessage(conversationId, {
				role: 'assistant',
				message: response.message || '候補を選択しました。',
				timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
			});

			// 候補選択UIを非表示
			showCandidateSelector = false;
			candidates = [];
			selectedCandidateId = null;
		} catch (error) {
			console.error('Failed to select candidate:', error);
			conversationStore.addMessage(conversationId, {
				role: 'assistant',
				message: `候補の選択に失敗しました: ${error instanceof Error ? error.message : '不明なエラー'}`,
				timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
			});
		} finally {
			isCandidateLoading = false;
		}
	}

	/**
	 * フィードバック送信ハンドラー (Issue #192)
	 */
	async function handleFeedbackSubmit(event: CustomEvent<FeedbackScores>) {
		if (!conversationId || isFeedbackLoading) return;

		isFeedbackLoading = true;

		try {
			const response = await submitFeedback({
				conversation_id: conversationId,
				...event.detail
			});

			if (response.success) {
				feedbackSubmitted = true;
				isFeedbackModalOpen = false;

				// フィードバック送信完了メッセージ
				conversationStore.addMessage(conversationId, {
					role: 'assistant',
					message: 'フィードバックを送信しました。ご協力ありがとうございます。',
					timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
				});
			} else {
				throw new Error(response.message || 'フィードバック送信に失敗しました');
			}
		} catch (error) {
			console.error('Failed to submit feedback:', error);
			conversationStore.addMessage(conversationId, {
				role: 'assistant',
				message: `フィードバックの送信に失敗しました: ${error instanceof Error ? error.message : '不明なエラー'}`,
				timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
			});
		} finally {
			isFeedbackLoading = false;
		}
	}

	/**
	 * フィードバックモーダルを閉じる
	 */
	function handleFeedbackClose() {
		isFeedbackModalOpen = false;
	}

	/**
	 * ジョブ作成ポーリングを開始する共通関数
	 */
	async function startJobPolling(
		jobId: string,
		startTime: number,
		executionMode: 'api_only' | 'schedule' | 'both',
		cronExpression?: string,
		timezone?: string
	): Promise<void> {
		let elapsedInterval: ReturnType<typeof setInterval> | null = null;

		// 経過時間を更新するタイマーを開始（5秒ごと）
		elapsedInterval = setInterval(() => {
			const elapsed = Math.floor((Date.now() - startTime) / 1000);
			const minutes = Math.floor(elapsed / 60);
			const seconds = elapsed % 60;
			const timeStr = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;

			// 最新のメッセージを更新
			const conversation = $activeConversation;
			if (conversation && conversation.messages.length > 0) {
				const lastMessage = conversation.messages[conversation.messages.length - 1];
				if (lastMessage.role === 'assistant' && lastMessage.message.includes('経過時間')) {
					// 既存のメッセージを更新
					conversationStore.updateLastMessage(conversationId, {
						...lastMessage,
						message: `ジョブを作成しています...\n\nLLMによるタスク分解と評価を実行中です。数分かかる場合があります。\n\n**経過時間**: ${timeStr}`
					});
				}
			}
		}, 5000);

		// ポーリングループを開始（5秒間隔）
		const pollInterval = setInterval(async () => {
			try {
				const status = await getJobStatus(jobId);

				// 進捗を表示（進捗率が変化した場合のみ更新）
				const elapsed = Math.floor((Date.now() - startTime) / 1000);
				const minutes = Math.floor(elapsed / 60);
				const seconds = elapsed % 60;
				const timeStr = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;

				const conversation = $activeConversation;
				if (conversation && conversation.messages.length > 0) {
					const lastMessage = conversation.messages[conversation.messages.length - 1];
					if (lastMessage.role === 'assistant' && lastMessage.message.includes('経過時間')) {
						conversationStore.updateLastMessage(conversationId, {
							...lastMessage,
							message: `ジョブを作成しています...\n\nLLMによるタスク分解と評価を実行中です。数分かかる場合があります。\n\n**進捗**: ${status.progress}%\n**経過時間**: ${timeStr}`
						});
					}
				}

				// 完了または失敗時にポーリング停止
				if (status.status === 'completed' || status.status === 'failed') {
					clearInterval(pollInterval);
					if (elapsedInterval) {
						clearInterval(elapsedInterval);
					}

					// 完了時の処理
					if (status.status === 'completed' && status.result) {
						createdJobId = status.job_master_id || jobId;

						// スケジュール実行が必要な場合、スケジュールを作成
						if (executionMode === 'schedule' || executionMode === 'both') {
							try {
								// スケジュール設定中メッセージ
								conversationStore.addMessage(conversationId, {
									role: 'assistant',
									message: 'スケジュールを設定しています...',
									timestamp: new Date().toLocaleTimeString('ja-JP', {
										hour: '2-digit',
										minute: '2-digit'
									})
								});

								await createSchedule({
									job_id: createdJobId,
									cron_expression: cronExpression!,
									timezone: timezone!
								});

								// スケジュール設定完了メッセージ
								conversationStore.addMessage(conversationId, {
									role: 'assistant',
									message: `**スケジュール設定が完了しました**\n\n- 実行間隔: ${cronExpression}\n- タイムゾーン: ${timezone}`,
									timestamp: new Date().toLocaleTimeString('ja-JP', {
										hour: '2-digit',
										minute: '2-digit'
									})
								});

								console.log('Schedule created successfully');
							} catch (error) {
								console.error('Failed to create schedule:', error);
								// スケジュール作成失敗はエラーとして表示するが、ジョブ作成は成功しているので継続
								conversationStore.addMessage(conversationId, {
									role: 'assistant',
									message:
										'**警告**: ジョブは作成されましたが、スケジュール設定に失敗しました。',
									timestamp: new Date().toLocaleTimeString('ja-JP', {
										hour: '2-digit',
										minute: '2-digit'
									})
								});
							}
						}

						// ジョブ作成完了メッセージ
						conversationStore.addMessage(conversationId, {
							role: 'assistant',
							message: `**ジョブが正常に作成されました**\n\nジョブID: ${createdJobId}`,
							timestamp: new Date().toLocaleTimeString('ja-JP', {
								hour: '2-digit',
								minute: '2-digit'
							})
						});

						// ジョブ作成成功 - localStorageの状態をクリア
						clearJobCreationState();

						// ジョブ作成成功後、自動的にスライドタブに切り替え
						showSlides = true;

						// フィードバックモーダルを表示 (Issue #192)
						if (!feedbackSubmitted) {
							setTimeout(() => {
								isFeedbackModalOpen = true;
							}, 1000);
						}
					} else if (status.status === 'failed') {
						// エラーメッセージ
						conversationStore.addMessage(conversationId, {
							role: 'assistant',
							message: `**ジョブ作成に失敗しました**\n\nエラー: ${status.error_message || '不明なエラー'}`,
							timestamp: new Date().toLocaleTimeString('ja-JP', {
								hour: '2-digit',
								minute: '2-digit'
							})
						});

						// エラー発生 - localStorageの状態をクリア
						clearJobCreationState();
					}
				}
			} catch (error) {
				console.error('Failed to poll job status:', error);
				// ポーリングエラーは継続（次回のポーリングでリトライ）
			}
		}, 5000);
	}

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

		// ページリロード後のジョブ作成状態チェック
		const savedState = getJobCreationState();
		if (
			savedState &&
			savedState.conversationId === conversationId &&
			savedState.status === 'creating'
		) {
			const elapsed = Math.floor((Date.now() - savedState.startTime) / 1000);
			const minutes = Math.floor(elapsed / 60);
			const seconds = elapsed % 60;
			const timeStr = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;

			if (savedState.jobId) {
				// jobIdがある場合、ポーリングを再開
				// 既存のメッセージを確認
				const conversation = $activeConversation;
				const lastMessage = conversation?.messages[conversation.messages.length - 1];

				// 最後のメッセージが「ジョブを作成しています」系のメッセージかチェック
				if (
					lastMessage &&
					lastMessage.role === 'assistant' &&
					(lastMessage.message.includes('ジョブを作成しています') ||
						lastMessage.message.includes('ジョブ作成を再開しています'))
				) {
					// 既存のメッセージを更新
					conversationStore.updateLastMessage(conversationId, {
						...lastMessage,
						message: `**ジョブ作成を再開しています...**\n\nページがリロードされました（経過時間: ${timeStr}）。\n\nジョブ作成の進捗を追跡しています。\n\n**経過時間**: ${timeStr}`
					});
				} else {
					// 新しいメッセージを追加（初回リロード時）
					conversationStore.addMessage(conversationId, {
						role: 'assistant',
						message: `**ジョブ作成を再開しています...**\n\nページがリロードされました（経過時間: ${timeStr}）。\n\nジョブ作成の進捗を追跡しています。\n\n**経過時間**: ${timeStr}`,
						timestamp: new Date().toLocaleTimeString('ja-JP', {
							hour: '2-digit',
							minute: '2-digit'
						})
					});
				}

				// ポーリングを再開
				startJobPolling(
					savedState.jobId,
					savedState.startTime,
					savedState.executionMode,
					savedState.cronExpression,
					savedState.timezone
				);
			} else {
				// jobIdがない場合（旧バージョンの状態）、追跡不可メッセージを表示
				conversationStore.addMessage(conversationId, {
					role: 'assistant',
					message: `**ジョブ作成状態を追跡できません**\n\nページがリロードされました（経過時間: ${timeStr}）。\n\nバックエンドでジョブ作成処理が継続している可能性がありますが、フロントエンドでは状態を追跡できなくなりました。\n\nジョブ一覧ページで作成状況を確認してください。`,
					timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
				});

				// 状態をクリア
				clearJobCreationState();
			}
		}

		// beforeunloadイベント: ジョブ作成中のページ離脱を警告
		const handleBeforeUnload = (e: BeforeUnloadEvent) => {
			const state = getJobCreationState();
			// 作成中（creating）のみ警告を表示
			// 完了後（completed/failed）やリロード後の復元時は警告しない
			if (state && state.conversationId === conversationId && state.status === 'creating') {
				e.preventDefault();
				e.returnValue = ''; // Chrome requires returnValue to be set
				return 'ジョブを作成中です。ページを離れると作成処理が中断されます。';
			}
		};

		window.addEventListener('beforeunload', handleBeforeUnload);

		return () => {
			window.removeEventListener('beforeunload', handleBeforeUnload);
		};
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

	function handleCreateJob() {
		// モーダルを開く
		isModalOpen = true;
	}

	async function handleModalCreate(
		event: CustomEvent<{
			executionMode: 'api_only' | 'schedule' | 'both';
			cronExpression?: string;
			timezone?: string;
		}>
	) {
		const { executionMode, cronExpression, timezone } = event.detail;

		// モーダルを即座に閉じる
		isModalOpen = false;

		// チャットタブに切り替え
		showSlides = false;

		// 開始時刻を記録
		const startTime = Date.now();

		// 初回の「作成中」メッセージを追加
		conversationStore.addMessage(conversationId, {
			role: 'assistant',
			message:
				'ジョブを作成しています...\n\nLLMによるタスク分解と評価を実行中です。数分かかる場合があります。\n\n**経過時間**: 0秒',
			timestamp: new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })
		});

		try {
			// 非同期ジョブ作成を開始（job_idを即座に取得）
			const { job_id } = await createJobAsync(conversationId, requirements);

			// ジョブ作成状態をlocalStorageに保存（ページリロード検出用）
			saveJobCreationState({
				conversationId,
				startTime,
				executionMode,
				cronExpression,
				timezone,
				status: 'creating',
				jobId: job_id // job_idを保存
			});

			// ポーリングを開始してジョブ作成の進捗を追跡
			await startJobPolling(job_id, startTime, executionMode, cronExpression, timezone);
		} catch (error) {
			console.error('Failed to start job creation:', error);

			// エラーメッセージ
			conversationStore.addMessage(conversationId, {
				role: 'assistant',
				message: `**ジョブ作成の開始に失敗しました**\n\nエラー: ${error instanceof Error ? error.message : '不明なエラー'}`,
				timestamp: new Date().toLocaleTimeString('ja-JP', {
					hour: '2-digit',
					minute: '2-digit'
				})
			});

			// エラー発生 - localStorageの状態をクリア
			clearJobCreationState();
		}
	}

	function handleModalCancel() {
		isModalOpen = false;
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

		<!-- タブ切り替え（ジョブ作成後に表示） -->
		{#if createdJobId}
			<div class="flex border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
				<button
					class="px-6 py-3 text-sm font-medium transition {!showSlides
						? 'border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (showSlides = false)}
					data-testid="chat-tab"
				>
					Chat
				</button>
				<button
					class="px-6 py-3 text-sm font-medium transition {showSlides
						? 'border-b-2 border-indigo-600 text-indigo-600 dark:text-indigo-400'
						: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'}"
					on:click={() => (showSlides = true)}
					data-testid="slides-tab"
				>
					Slides
				</button>
			</div>
		{/if}

		<!-- コンテンツエリア -->
		{#if !showSlides}
			<!-- Scrollable Chat Messages Area -->
			<ChatContainer {messages} bind:containerRef={chatContainer} />

			<!-- Candidate Selector (Issue #192) -->
			{#if showCandidateSelector && candidates.length > 0}
				<div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
					<CandidateSelector
						{candidates}
						selectedId={selectedCandidateId}
						loading={isCandidateLoading}
						on:select={handleCandidateSelect}
						on:confirm={handleCandidateConfirm}
					/>
				</div>
			{/if}

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

<!-- Job Creation Modal -->
<JobCreationModal
	bind:isOpen={isModalOpen}
	isCreatingJob={sessionState.isCreatingJob}
	on:create={handleModalCreate}
	on:cancel={handleModalCancel}
/>

<!-- Feedback Modal (Issue #192) -->
<FeedbackModal
	open={isFeedbackModalOpen}
	{conversationId}
	loading={isFeedbackLoading}
	on:submit={handleFeedbackSubmit}
	on:close={handleFeedbackClose}
/>

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
