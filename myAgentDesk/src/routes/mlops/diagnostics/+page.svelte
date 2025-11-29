<script lang="ts">
	/**
	 * MLOps Diagnostics Page - View conversation diagnostic information
	 *
	 * Features:
	 * - Diagnostics list with filtering
	 * - Detailed conversation view
	 * - Timeline visualization
	 * - Langfuse trace link
	 * - i18n support
	 */

	import { onMount } from 'svelte';
	import ConversationTimeline from '$lib/mlops/components/ConversationTimeline.svelte';
	import { listDiagnostics, getDiagnosticInfo } from '$lib/mlops/api/client';
	import type { DiagnosticSummary, DiagnosticInfo, DiagnosticsQuery } from '$lib/mlops/types';
	import { locale, t } from '$lib/stores/locale';

	let diagnosticsList: DiagnosticSummary[] = [];
	let selectedDiagnostic: DiagnosticInfo | null = null;
	let loading = true;
	let detailLoading = false;
	let error: string | null = null;
	let total = 0;

	// Filters
	let filterJobId = '';
	let filterUserId = '';

	// Demo data for testing/development
	const demoData: DiagnosticSummary[] = [
		{
			conversation_id: 'conv-demo-001',
			user_id: 'user-123',
			start_time: new Date().toISOString(),
			turn_count: 5
		},
		{
			conversation_id: 'conv-demo-002',
			user_id: 'user-456',
			start_time: new Date(Date.now() - 3600000).toISOString(),
			turn_count: 8
		}
	];

	async function loadDiagnostics() {
		loading = true;
		error = null;

		try {
			const query: DiagnosticsQuery = {
				limit: 50
			};
			if (filterJobId) query.job_id = filterJobId;
			if (filterUserId) query.user_id = filterUserId;

			const response = await listDiagnostics(query);
			diagnosticsList = response.items;
			total = response.total;

			// If no data from API, use demo data for development
			if (diagnosticsList.length === 0) {
				diagnosticsList = demoData;
				total = diagnosticsList.length;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load diagnostics';
			// Use demo data on error
			diagnosticsList = demoData;
			total = diagnosticsList.length;
		} finally {
			loading = false;
		}
	}

	async function selectDiagnostic(conversationId: string) {
		detailLoading = true;
		error = null;

		try {
			selectedDiagnostic = await getDiagnosticInfo(conversationId);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load diagnostic details';
			// Use demo data on error
			selectedDiagnostic = {
				conversation_id: conversationId,
				user_id: 'user-demo',
				project_id: 'project-demo',
				job_id: null,
				workflow_id: null,
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				turn_count: 3,
				messages: [
					{
						role: 'user',
						content: 'I want to analyze sales data',
						timestamp: new Date().toISOString()
					},
					{
						role: 'assistant',
						content: 'Could you tell me more about your data source?',
						timestamp: new Date().toISOString()
					},
					{
						role: 'user',
						content: 'It is a CSV file from our CRM',
						timestamp: new Date().toISOString()
					}
				],
				langfuse_trace_url: 'http://localhost:3001/trace/demo',
				metadata: {}
			};
		} finally {
			detailLoading = false;
		}
	}

	function clearSelection() {
		selectedDiagnostic = null;
	}

	function handleFilter() {
		loadDiagnostics();
	}

	function formatDate(dateString: string): string {
		try {
			return new Date(dateString).toLocaleString('ja-JP');
		} catch {
			return dateString;
		}
	}

	onMount(() => {
		loadDiagnostics();
	});
</script>

<svelte:head>
	<title>Diagnostics | MLOps | myAgentDesk</title>
</svelte:head>

<div class="diagnostics-page" data-testid="mlops-diagnostics-page">
	<!-- Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
			{t('mlops.conversationDiagnostics')}
		</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">
			{$locale === 'ja'
				? '会話診断情報の表示と分析'
				: 'View and analyze conversation diagnostic information'}
		</p>
	</div>

	<!-- Error Message -->
	{#if error}
		<div
			class="mb-6 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400"
			role="alert"
		>
			<p class="font-medium">Note</p>
			<p class="text-sm mt-1">{error} - Showing demo data</p>
		</div>
	{/if}

	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Diagnostics List -->
		<div class="lg:col-span-1 bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
			<!-- Filters -->
			<div class="mb-4 space-y-2">
				<input
					type="text"
					placeholder={t('mlops.filterJobId')}
					bind:value={filterJobId}
					class="w-full px-3 py-2 text-sm rounded-lg border
						border-gray-300 dark:border-gray-600
						bg-white dark:bg-gray-700
						text-gray-900 dark:text-gray-100"
					data-testid="filter-job-id"
				/>
				<input
					type="text"
					placeholder={t('mlops.filterUserId')}
					bind:value={filterUserId}
					class="w-full px-3 py-2 text-sm rounded-lg border
						border-gray-300 dark:border-gray-600
						bg-white dark:bg-gray-700
						text-gray-900 dark:text-gray-100"
					data-testid="filter-user-id"
				/>
				<button
					type="button"
					class="w-full px-3 py-2 text-sm font-medium rounded-lg
						bg-blue-600 text-white hover:bg-blue-700"
					on:click={handleFilter}
					data-testid="apply-filter-button"
				>
					{t('mlops.applyFilter')}
				</button>
			</div>

			<!-- List -->
			<div class="space-y-2">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
					{total} conversations
				</div>

				{#if loading}
					<div class="space-y-2 animate-pulse">
						{#each [0, 1, 2] as i (i)}
							<div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-700">
								<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-2/3 mb-2"></div>
								<div class="h-3 bg-gray-300 dark:bg-gray-600 rounded w-1/2"></div>
							</div>
						{/each}
					</div>
				{:else if diagnosticsList.length === 0}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">No diagnostics found</div>
				{:else}
					{#each diagnosticsList as item (item.conversation_id)}
						<button
							type="button"
							class="w-full text-left p-3 rounded-lg transition-colors
								{selectedDiagnostic?.conversation_id === item.conversation_id
								? 'bg-blue-100 dark:bg-blue-900/30 border-2 border-blue-500'
								: 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 border-2 border-transparent'}"
							on:click={() => selectDiagnostic(item.conversation_id)}
							data-testid="diagnostic-item-{item.conversation_id}"
						>
							<div class="font-medium text-gray-900 dark:text-gray-100 text-sm truncate">
								{item.conversation_id}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{item.turn_count} turns - {formatDate(item.start_time)}
							</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>

		<!-- Detail View -->
		<div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
			{#if detailLoading}
				<div class="animate-pulse space-y-4">
					<div class="h-6 bg-gray-300 dark:bg-gray-600 rounded w-1/3"></div>
					<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-2/3"></div>
					<div class="h-48 bg-gray-300 dark:bg-gray-600 rounded"></div>
				</div>
			{:else if selectedDiagnostic}
				<!-- Header -->
				<div class="flex items-start justify-between mb-6">
					<div>
						<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
							{selectedDiagnostic.conversation_id}
						</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
							User: {selectedDiagnostic.user_id} | {selectedDiagnostic.turn_count} turns
						</p>
					</div>
					<button
						type="button"
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
						on:click={clearSelection}
						aria-label="Close detail view"
					>
						<svg
							class="w-5 h-5"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>

				<!-- Metadata -->
				<div class="grid grid-cols-2 gap-4 mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
					<div>
						<span class="text-xs text-gray-500 dark:text-gray-400">Start Time</span>
						<p class="text-sm text-gray-900 dark:text-gray-100">
							{formatDate(selectedDiagnostic.start_time)}
						</p>
					</div>
					<div>
						<span class="text-xs text-gray-500 dark:text-gray-400">End Time</span>
						<p class="text-sm text-gray-900 dark:text-gray-100">
							{selectedDiagnostic.end_time ? formatDate(selectedDiagnostic.end_time) : '-'}
						</p>
					</div>
					{#if selectedDiagnostic.job_id}
						<div>
							<span class="text-xs text-gray-500 dark:text-gray-400">Job ID</span>
							<p class="text-sm text-gray-900 dark:text-gray-100">{selectedDiagnostic.job_id}</p>
						</div>
					{/if}
					{#if selectedDiagnostic.langfuse_trace_url}
						<div>
							<span class="text-xs text-gray-500 dark:text-gray-400">Trace</span>
							<a
								href={selectedDiagnostic.langfuse_trace_url}
								target="_blank"
								rel="noopener noreferrer"
								class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
								data-testid="langfuse-link"
							>
								View in Langfuse
							</a>
						</div>
					{/if}
				</div>

				<!-- Timeline -->
				<div>
					<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-4">
						Conversation Timeline
					</h3>
					<ConversationTimeline messages={selectedDiagnostic.messages} />
				</div>
			{:else}
				<div class="text-center py-12 text-gray-500 dark:text-gray-400">
					<svg
						class="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
						/>
					</svg>
					<p class="text-lg font-medium">{t('mlops.selectConversation')}</p>
				</div>
			{/if}
		</div>
	</div>
</div>
