<!--
  Run Detail Page (/projects/:projectId/workbenches/:workbenchId/runs/:runId)
  Issue #293: Runs Screen (Execution History / Monitoring)

  Shows run details, progress, task output, and trace information with real-time updates.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import {
		RUN_STATUS_CONFIG,
		getRunDuration,
		calculateProgress,
		isTerminalStatus
	} from '$lib/types/run';
	import { createRunPollingStore } from '$lib/stores/run-polling.svelte';
	import { TaskProgressList } from '$lib/components/runs';
	import type { TaskProgressItem } from '$lib/utils/interface-schema';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// Task progress state
	let tasks = $state<TaskProgressItem[]>([]);
	let tasksLoading = $state(false);
	let tasksError = $state<string | null>(null);

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Polling store for real-time updates
	const pollingStore = createRunPollingStore();

	// Combined status (from server or polling)
	const currentStatus = $derived(pollingStore.runStatus?.status ?? data.run.status);
	const statusConfig = $derived(RUN_STATUS_CONFIG[currentStatus]);
	const progress = $derived(
		calculateProgress(
			pollingStore.runStatus?.tasksCompleted ?? data.run.tasksCompleted,
			pollingStore.runStatus?.totalTasks ?? data.run.totalTasks
		)
	);
	const duration = $derived(getRunDuration(data.run.startedAt, data.run.completedAt));

	// Langfuse trace URL (if available)
	const traceId = $derived(pollingStore.runStatus?.externalTraceId ?? data.run.externalTraceId);
	const langfuseUrl = $derived(traceId ? `http://localhost:3001/trace/${traceId}` : null);

	// State for rerun
	let isRerunning = $state(false);

	// Task polling interval
	let taskPollingInterval: ReturnType<typeof setInterval> | null = null;

	/**
	 * Fetch tasks for this run
	 */
	async function fetchTasks() {
		if (!data.run.externalJobId) {
			tasks = [];
			return;
		}

		try {
			tasksLoading = tasks.length === 0; // Only show loading on initial fetch
			const response = await fetch(`/api/runs/${data.run.id}/tasks`);

			if (response.ok) {
				const result = await response.json();
				tasks = result.tasks;
				tasksError = null;
			} else {
				const errorData = await response.json();
				tasksError = errorData.message || 'Failed to fetch tasks';
			}
		} catch (error) {
			tasksError = 'Failed to fetch tasks';
			console.error('Error fetching tasks:', error);
		} finally {
			tasksLoading = false;
		}
	}

	/**
	 * Start polling for task updates
	 */
	function startTaskPolling() {
		if (taskPollingInterval) return;

		// Fetch immediately
		fetchTasks();

		// Then poll every 3 seconds while run is active
		taskPollingInterval = setInterval(() => {
			if (!isTerminalStatus(currentStatus)) {
				fetchTasks();
			} else {
				// Stop polling when run completes
				stopTaskPolling();
			}
		}, 3000);
	}

	/**
	 * Stop task polling
	 */
	function stopTaskPolling() {
		if (taskPollingInterval) {
			clearInterval(taskPollingInterval);
			taskPollingInterval = null;
		}
	}

	/**
	 * Format date for display
	 */
	function formatDate(date: Date | null): string {
		if (!date) return '-';
		return new Intl.DateTimeFormat('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		}).format(date);
	}

	/**
	 * Handle rerun
	 */
	async function handleRerun() {
		isRerunning = true;
		try {
			const response = await fetch(`/api/runs/${data.run.id}/rerun`, {
				method: 'POST'
			});

			if (response.ok) {
				const newRun = await response.json();
				goto(`/projects/${projectId}/workbenches/${workbenchId}/runs/${newRun.id}`);
			} else {
				console.error('Failed to rerun');
			}
		} catch (error) {
			console.error('Error rerunning:', error);
		} finally {
			isRerunning = false;
		}
	}

	// Start polling if run is in progress
	onMount(() => {
		if (!isTerminalStatus(data.run.status)) {
			pollingStore.startPolling(data.run.id);
		}
		// Always start task polling to fetch initial task data
		startTaskPolling();
	});

	// Cleanup on unmount
	onDestroy(() => {
		pollingStore.destroy();
		stopTaskPolling();
	});
</script>

<div class="run-detail-page">
	<div class="page-header">
		<div class="header-left">
			<a href="/projects/{projectId}/workbenches/{workbenchId}/runs" class="back-link">
				&larr; Back to Runs
			</a>
			<h2>Run: {data.run.id.substring(0, 16)}...</h2>
		</div>
		<div class="actions">
			{#if langfuseUrl}
				<a
					href={langfuseUrl}
					target="_blank"
					rel="noopener noreferrer"
					class="action-button secondary"
				>
					View Trace
				</a>
			{/if}
			{#if data.canRerun}
				<button class="action-button primary" onclick={handleRerun} disabled={isRerunning}>
					{isRerunning ? 'Rerunning...' : 'Rerun'}
				</button>
			{/if}
		</div>
	</div>

	<div class="run-content">
		<!-- Status Section -->
		<div class="content-section">
			<h3>Status</h3>
			<div class="status-bar">
				<span
					class="status-badge"
					style="background: {statusConfig.bgColor}; color: {statusConfig.color}"
				>
					{statusConfig.label}
				</span>
				{#if duration}
					<span class="duration">Duration: {duration}</span>
				{/if}
				{#if pollingStore.isPolling}
					<span class="polling-indicator">Updating...</span>
				{/if}
			</div>
			{#if !isTerminalStatus(currentStatus) && progress > 0}
				<div class="progress-section">
					<div class="progress-bar-large">
						<div class="progress-fill" style="width: {progress}%"></div>
					</div>
					<span class="progress-text">{progress}% complete</span>
				</div>
			{/if}
			{#if pollingStore.error}
				<div class="error-message">{pollingStore.error}</div>
			{/if}
		</div>

		<!-- Details Section -->
		<div class="content-section">
			<h3>Details</h3>
			<div class="details-grid">
				<div class="detail-item">
					<span class="label">Job Version</span>
					<span class="value">{data.run.jobVersionLabel}</span>
				</div>
				<div class="detail-item">
					<span class="label">Created</span>
					<span class="value">{formatDate(data.run.createdAt)}</span>
				</div>
				<div class="detail-item">
					<span class="label">Started</span>
					<span class="value">{formatDate(data.run.startedAt)}</span>
				</div>
				<div class="detail-item">
					<span class="label">Completed</span>
					<span class="value">{formatDate(data.run.completedAt)}</span>
				</div>
				{#if traceId}
					<div class="detail-item">
						<span class="label">Trace ID</span>
						<span class="value mono">{traceId}</span>
					</div>
				{/if}
				{#if data.run.externalJobId}
					<div class="detail-item">
						<span class="label">Job ID</span>
						<span class="value mono">{data.run.externalJobId}</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Execution Params Section -->
		{#if data.run.executionParams}
			<div class="content-section">
				<h3>Execution Parameters</h3>
				<pre class="params-display">{JSON.stringify(
						JSON.parse(data.run.executionParams),
						null,
						2
					)}</pre>
			</div>
		{/if}

		<!-- Result Summary Section -->
		{#if data.run.resultSummary}
			<div class="content-section">
				<h3>Result Summary</h3>
				<div class="result-summary">
					{data.run.resultSummary}
				</div>
			</div>
		{/if}

		<!-- Task Progress Section -->
		{#if data.run.externalJobId || tasks.length > 0}
			<div class="content-section tasks-section">
				<h3>Task Progress</h3>
				<TaskProgressList {tasks} loading={tasksLoading} error={tasksError} />
			</div>
		{/if}
	</div>
</div>

<style>
	.run-detail-page {
		max-width: 900px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1.5rem;
	}

	.header-left {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.back-link {
		font-size: 0.875rem;
		color: #64748b;
		text-decoration: none;
	}

	.back-link:hover {
		color: #3b82f6;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
		padding: 0.5rem 1rem;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		text-decoration: none;
	}

	.action-button.primary {
		background: #3b82f6;
		color: white;
		border: none;
	}

	.action-button.primary:hover:not(:disabled) {
		background: #2563eb;
	}

	.action-button.primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.action-button.secondary {
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
	}

	.action-button.secondary:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	.run-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.content-section {
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
	}

	.content-section h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
	}

	.status-bar {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.status-badge {
		padding: 0.25rem 0.75rem;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.duration {
		font-size: 0.875rem;
		color: #64748b;
	}

	.polling-indicator {
		font-size: 0.75rem;
		color: #3b82f6;
		animation: pulse 1.5s infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	.progress-section {
		margin-top: 1rem;
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.progress-bar-large {
		flex: 1;
		height: 8px;
		background: #e2e8f0;
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		transition: width 0.3s ease;
	}

	.progress-text {
		font-size: 0.875rem;
		color: #64748b;
		min-width: 100px;
	}

	.error-message {
		margin-top: 0.75rem;
		padding: 0.5rem;
		background: #fee2e2;
		color: #991b1b;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}

	.details-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.detail-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.label {
		font-size: 0.75rem;
		color: #64748b;
		text-transform: uppercase;
	}

	.value {
		font-size: 0.875rem;
		color: #1e293b;
	}

	.value.mono {
		font-family: monospace;
		font-size: 0.8rem;
		word-break: break-all;
	}

	.params-display {
		margin: 0;
		padding: 1rem;
		background: #1e293b;
		color: #e2e8f0;
		border-radius: 0.25rem;
		font-family: monospace;
		font-size: 0.75rem;
		overflow-x: auto;
	}

	.result-summary {
		font-size: 0.875rem;
		color: #1e293b;
		line-height: 1.5;
	}

	.tasks-section {
		background: white;
	}

	.tasks-section h3 {
		margin-bottom: 1rem;
	}
</style>
