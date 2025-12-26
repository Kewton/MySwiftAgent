<!--
  TaskProgressList Component
  Issue #293: Runs Screen - Task Progress List Display

  Displays a list of task progress items with overall progress indicator.

  Props:
  - tasks: Array of TaskProgressItem objects
  - loading: Show loading state
  - error: Error message to display
-->
<script lang="ts">
	import type { TaskProgressItem } from '$lib/utils/interface-schema';
	import TaskProgressCard from './TaskProgressCard.svelte';

	interface Props {
		tasks: TaskProgressItem[];
		loading?: boolean;
		error?: string | null;
	}

	let { tasks, loading = false, error = null }: Props = $props();

	// Sort tasks by order
	const sortedTasks = $derived([...tasks].sort((a, b) => a.order - b.order));

	// Calculate progress statistics
	const stats = $derived(() => {
		const total = tasks.length;
		const succeeded = tasks.filter((t) => t.status === 'succeeded').length;
		const failed = tasks.filter((t) => t.status === 'failed').length;
		const running = tasks.filter((t) => t.status === 'running').length;
		const pending = tasks.filter((t) => t.status === 'pending').length;
		const skipped = tasks.filter((t) => t.status === 'skipped').length;

		const completed = succeeded + failed + skipped;
		const progressPercent = total > 0 ? Math.round((completed / total) * 100) : 0;

		return {
			total,
			succeeded,
			failed,
			running,
			pending,
			skipped,
			completed,
			progressPercent
		};
	});

	// Determine overall status
	const overallStatus = $derived(() => {
		const s = stats();
		if (s.failed > 0) return 'failed';
		if (s.running > 0) return 'running';
		if (s.completed === s.total && s.total > 0) return 'completed';
		return 'pending';
	});
</script>

<div class="task-progress-list">
	{#if loading}
		<div class="loading-state">
			<div class="spinner" aria-hidden="true"></div>
			<span>Loading tasks...</span>
		</div>
	{:else if error}
		<div class="error-state" role="alert">
			<span class="error-icon" aria-hidden="true">!</span>
			<span>{error}</span>
		</div>
	{:else if tasks.length === 0}
		<div class="empty-state">
			<span>No tasks available</span>
		</div>
	{:else}
		<!-- Progress Summary -->
		<div
			class="progress-summary"
			class:completed={overallStatus() === 'completed'}
			class:failed={overallStatus() === 'failed'}
			class:running={overallStatus() === 'running'}
		>
			<div class="progress-header">
				<span class="progress-title">Task Progress</span>
				<span class="progress-count">
					{stats().completed} / {stats().total} completed
				</span>
			</div>
			<div class="progress-bar-container">
				<div
					class="progress-bar"
					style="width: {stats().progressPercent}%"
					aria-valuenow={stats().progressPercent}
					aria-valuemin={0}
					aria-valuemax={100}
					role="progressbar"
				></div>
			</div>
			<div class="progress-stats">
				{#if stats().succeeded > 0}
					<span class="stat succeeded">{stats().succeeded} succeeded</span>
				{/if}
				{#if stats().running > 0}
					<span class="stat running">{stats().running} running</span>
				{/if}
				{#if stats().pending > 0}
					<span class="stat pending">{stats().pending} pending</span>
				{/if}
				{#if stats().failed > 0}
					<span class="stat failed">{stats().failed} failed</span>
				{/if}
				{#if stats().skipped > 0}
					<span class="stat skipped">{stats().skipped} skipped</span>
				{/if}
			</div>
		</div>

		<!-- Task List -->
		<div class="task-list">
			{#each sortedTasks as task (task.taskId)}
				<TaskProgressCard {task} expanded={task.status === 'failed'} />
			{/each}
		</div>
	{/if}
</div>

<style>
	.task-progress-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.loading-state,
	.error-state,
	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		padding: 2rem;
		border: 1px dashed #e2e8f0;
		border-radius: 0.5rem;
		background: #f8fafc;
		color: #64748b;
		font-size: 0.875rem;
	}

	.error-state {
		border-color: #fecaca;
		background: #fef2f2;
		color: #dc2626;
	}

	.error-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #dc2626;
		color: white;
		border-radius: 50%;
		font-weight: bold;
		font-size: 0.875rem;
	}

	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid #e2e8f0;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.progress-summary {
		padding: 1rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: white;
	}

	.progress-summary.running {
		border-color: #93c5fd;
		background: #eff6ff;
	}

	.progress-summary.completed {
		border-color: #86efac;
		background: #f0fdf4;
	}

	.progress-summary.failed {
		border-color: #fca5a5;
		background: #fef2f2;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.progress-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: #334155;
	}

	.progress-count {
		font-size: 0.75rem;
		color: #64748b;
	}

	.progress-bar-container {
		height: 0.5rem;
		background: #e2e8f0;
		border-radius: 0.25rem;
		overflow: hidden;
		margin-bottom: 0.625rem;
	}

	.progress-bar {
		height: 100%;
		background: #3b82f6;
		border-radius: 0.25rem;
		transition: width 0.3s ease;
	}

	.completed .progress-bar {
		background: #22c55e;
	}

	.failed .progress-bar {
		background: #ef4444;
	}

	.progress-stats {
		display: flex;
		flex-wrap: wrap;
		gap: 0.625rem;
	}

	.stat {
		font-size: 0.6875rem;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		font-weight: 500;
	}

	.stat.succeeded {
		background: #dcfce7;
		color: #166534;
	}

	.stat.running {
		background: #dbeafe;
		color: #1e40af;
	}

	.stat.pending {
		background: #f1f5f9;
		color: #64748b;
	}

	.stat.failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.stat.skipped {
		background: #fef3c7;
		color: #92400e;
	}

	.task-list {
		display: flex;
		flex-direction: column;
		gap: 0.625rem;
	}
</style>
