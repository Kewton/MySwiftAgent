<!--
  TaskProgressCard Component
  Issue #293: Runs Screen - Task Progress Display

  Displays a single task's progress with status, timing, and expandable input/output.

  Props:
  - task: TaskProgressItem object
  - expanded: Optional initial expanded state (default: false)
-->
<script lang="ts">
	import type { TaskProgressItem } from '$lib/utils/interface-schema';
	import OutputViewer from './OutputViewer.svelte';

	interface Props {
		task: TaskProgressItem;
		expanded?: boolean;
	}

	let { task, expanded = false }: Props = $props();

	// Local toggle state, managed separately for user interaction
	let localExpanded = $state<boolean | null>(null);

	// Effective expanded state: use local state if set, otherwise use prop
	const isExpanded = $derived(localExpanded !== null ? localExpanded : expanded);

	function toggleExpand() {
		localExpanded = !isExpanded;
	}

	// Format duration for display
	function formatDuration(ms: number | null | undefined): string {
		if (ms == null) return '-';
		if (ms < 1000) return `${ms}ms`;
		const seconds = ms / 1000;
		if (seconds < 60) return `${seconds.toFixed(1)}s`;
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = (seconds % 60).toFixed(0);
		return `${minutes}m ${remainingSeconds}s`;
	}

	// Get status icon
	function getStatusIcon(status: string): string {
		switch (status) {
			case 'succeeded':
				return '✓';
			case 'failed':
				return '✗';
			case 'running':
				return '⟳';
			case 'pending':
				return '○';
			case 'skipped':
				return '−';
			default:
				return '?';
		}
	}

	// Format timestamp for display
	function formatTime(date: Date | string | undefined): string {
		if (!date) return '-';
		const dateObj = date instanceof Date ? date : new Date(date);
		if (isNaN(dateObj.getTime())) return '-';
		return dateObj.toLocaleTimeString('ja-JP', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
	}

	const hasData = $derived(task.inputData || task.outputData || task.error);
</script>

<article
	class="task-card"
	class:succeeded={task.status === 'succeeded'}
	class:failed={task.status === 'failed'}
	class:running={task.status === 'running'}
	class:pending={task.status === 'pending'}
	class:skipped={task.status === 'skipped'}
	role="region"
	aria-labelledby="task-header-{task.taskId}"
>
	<div class="task-header" id="task-header-{task.taskId}">
		<div class="task-number" aria-hidden="true">{task.order}</div>
		<div class="task-content">
			<div class="task-main">
				<span class="task-name">{task.taskName}</span>
				<span class="task-status" aria-label="Status: {task.status}">
					<span class="status-icon">{getStatusIcon(task.status)}</span>
					{task.status}
				</span>
			</div>
			<div class="task-meta">
				{#if task.startedAt}
					<span class="meta-item">
						<span class="meta-label">Started:</span>
						{formatTime(task.startedAt)}
					</span>
				{/if}
				{#if task.durationMs != null}
					<span class="meta-item">
						<span class="meta-label">Duration:</span>
						{formatDuration(task.durationMs)}
					</span>
				{/if}
			</div>
		</div>
		{#if hasData}
			<button
				type="button"
				class="expand-button"
				onclick={toggleExpand}
				aria-expanded={isExpanded}
				aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
			>
				{isExpanded ? 'Hide' : 'Details'}
				<span class="icon" aria-hidden="true">{isExpanded ? '−' : '+'}</span>
			</button>
		{/if}
	</div>

	{#if isExpanded && hasData}
		<div class="task-details" role="region" aria-label="Task details">
			{#if task.error}
				<div class="error-section">
					<h5>Error</h5>
					<div class="error-message">{task.error}</div>
				</div>
			{/if}

			<div class="data-section">
				{#if task.inputData}
					<OutputViewer
						data={task.inputData}
						title="Input Data"
						taskId={task.taskId}
						type="input"
					/>
				{/if}

				{#if task.outputData}
					<OutputViewer
						data={task.outputData}
						title="Output Data"
						taskId={task.taskId}
						type="output"
					/>
				{/if}
			</div>
		</div>
	{/if}
</article>

<style>
	.task-card {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: white;
		overflow: hidden;
		transition: border-color 0.2s;
	}

	.task-card.succeeded {
		border-left: 3px solid #22c55e;
	}

	.task-card.failed {
		border-left: 3px solid #ef4444;
	}

	.task-card.running {
		border-left: 3px solid #3b82f6;
		animation: pulse 2s infinite;
	}

	.task-card.pending {
		border-left: 3px solid #9ca3af;
	}

	.task-card.skipped {
		border-left: 3px solid #eab308;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.8;
		}
	}

	.task-header {
		display: grid;
		grid-template-columns: 2rem 1fr auto;
		gap: 0.75rem;
		padding: 0.875rem;
		background: #f8fafc;
		align-items: center;
	}

	.task-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		background: #64748b;
		color: white;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.succeeded .task-number {
		background: #22c55e;
	}

	.failed .task-number {
		background: #ef4444;
	}

	.running .task-number {
		background: #3b82f6;
	}

	.skipped .task-number {
		background: #eab308;
	}

	.task-content {
		min-width: 0;
	}

	.task-main {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.task-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.task-status {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.6875rem;
		font-weight: 500;
		text-transform: uppercase;
	}

	.succeeded .task-status {
		background: #dcfce7;
		color: #166534;
	}

	.failed .task-status {
		background: #fee2e2;
		color: #dc2626;
	}

	.running .task-status {
		background: #dbeafe;
		color: #1e40af;
	}

	.pending .task-status {
		background: #f1f5f9;
		color: #64748b;
	}

	.skipped .task-status {
		background: #fef3c7;
		color: #92400e;
	}

	.status-icon {
		font-size: 0.75rem;
	}

	.task-meta {
		display: flex;
		gap: 1rem;
		margin-top: 0.375rem;
		font-size: 0.75rem;
		color: #64748b;
	}

	.meta-item {
		display: flex;
		gap: 0.25rem;
	}

	.meta-label {
		color: #94a3b8;
	}

	.expand-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.375rem 0.625rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.6875rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		transition: all 0.15s;
	}

	.expand-button:hover {
		background: #f1f5f9;
		color: #1e293b;
	}

	.icon {
		font-weight: bold;
		font-size: 0.875rem;
	}

	.task-details {
		padding: 0.875rem;
		border-top: 1px solid #e2e8f0;
		background: white;
	}

	.error-section {
		margin-bottom: 0.875rem;
	}

	.error-section h5 {
		margin: 0 0 0.375rem;
		font-size: 0.75rem;
		font-weight: 600;
		color: #dc2626;
	}

	.error-message {
		padding: 0.625rem;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		color: #991b1b;
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
	}

	.data-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}
</style>
