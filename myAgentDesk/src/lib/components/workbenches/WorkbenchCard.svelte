<!--
  WorkbenchCard Component
  Issue #289: Workbench List/Detail Screens

  Displays a workbench card with status badge, run statistics,
  and schedule information. Used in the workbench list view.
-->
<script lang="ts">
	import type { WorkbenchListItem } from '$lib/types/workbench';

	interface Props {
		workbench: WorkbenchListItem;
		projectId: string;
	}

	let { workbench, projectId }: Props = $props();

	const statusBadgeClass = $derived(
		{
			draft: 'badge-draft',
			active: 'badge-active',
			archived: 'badge-archived'
		}[workbench.status]
	);

	const lastRunStatusClass = $derived(() => {
		if (!workbench.lastRunStatus) return '';
		return (
			{
				success: 'run-success',
				failed: 'run-failed',
				running: 'run-running',
				queued: 'run-queued',
				canceled: 'run-canceled',
				timeout: 'run-timeout'
			}[workbench.lastRunStatus] || ''
		);
	});

	const formatDate = (date: Date | null): string => {
		if (!date) return 'Never';
		return new Date(date).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};
</script>

<a
	href="/projects/{projectId}/workbenches/{workbench.id}"
	class="workbench-card"
	data-testid="workbench-card"
>
	<div class="card-header">
		<h3 class="card-title">{workbench.name}</h3>
		<span class="status-badge {statusBadgeClass}" data-testid="status-badge"
			>{workbench.status}</span
		>
	</div>

	{#if workbench.description}
		<p class="card-description">{workbench.description}</p>
	{/if}

	<div class="card-stats">
		<div class="stat" data-testid="run-count">
			<span class="stat-label">Runs</span>
			<span class="stat-value">{workbench.runCount}</span>
		</div>
		<div class="stat" data-testid="schedule-count">
			<span class="stat-label">Schedules</span>
			<span class="stat-value">{workbench.scheduleCount}</span>
		</div>
		<div class="stat" data-testid="last-run">
			<span class="stat-label">Last Run</span>
			<span class="stat-value {lastRunStatusClass()}">{formatDate(workbench.lastRunAt)}</span>
		</div>
	</div>
</a>

<style>
	.workbench-card {
		display: block;
		padding: 1.25rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		text-decoration: none;
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
	}

	.workbench-card:hover {
		border-color: #3b82f6;
		box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.card-title {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
		line-height: 1.4;
	}

	.status-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: capitalize;
		border-radius: 9999px;
		flex-shrink: 0;
	}

	.badge-draft {
		background: #f1f5f9;
		color: #64748b;
	}

	.badge-active {
		background: #dcfce7;
		color: #16a34a;
	}

	.badge-archived {
		background: #fef3c7;
		color: #d97706;
	}

	.card-description {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 0.75rem;
		line-height: 1.5;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.card-stats {
		display: flex;
		gap: 1rem;
		padding-top: 0.75rem;
		border-top: 1px solid #f1f5f9;
	}

	.stat {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.stat-label {
		font-size: 0.75rem;
		color: #94a3b8;
	}

	.stat-value {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.run-success {
		color: #16a34a;
	}

	.run-failed {
		color: #dc2626;
	}

	.run-running {
		color: #2563eb;
	}

	.run-queued {
		color: #64748b;
	}

	.run-canceled {
		color: #d97706;
	}

	.run-timeout {
		color: #9333ea;
	}
</style>
