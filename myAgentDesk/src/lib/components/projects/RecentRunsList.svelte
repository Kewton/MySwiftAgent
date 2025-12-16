<!--
  RecentRunsList Component
  Issue #288: Project screens implementation

  Displays a list of recent runs for a project.
-->
<script lang="ts">
	import type { RunWithWorkbench } from '$lib/types/project';

	interface Props {
		runs: RunWithWorkbench[];
		projectId: string;
	}

	let { runs, projectId }: Props = $props();

	function getStatusColor(status: string): string {
		switch (status) {
			case 'success':
				return 'status-success';
			case 'running':
				return 'status-running';
			case 'failed':
				return 'status-failed';
			case 'queued':
				return 'status-queued';
			case 'canceled':
				return 'status-canceled';
			case 'timeout':
				return 'status-timeout';
			default:
				return 'status-default';
		}
	}

	function formatDate(date: Date | null): string {
		if (!date) return '-';
		return date.toLocaleString();
	}
</script>

<div class="runs-section">
	<div class="section-header">
		<h2>Recent Runs</h2>
	</div>

	{#if runs.length === 0}
		<div class="empty-state">
			<p>No recent runs found.</p>
		</div>
	{:else}
		<div class="runs-list">
			{#each runs as run (run.id)}
				<a
					href="/projects/{projectId}/workbenches/{run.workbenchId}/runs/{run.id}"
					class="run-item"
				>
					<div class="run-info">
						<span class="workbench-name">{run.workbench.name}</span>
						<span class="run-time">{formatDate(run.createdAt)}</span>
					</div>
					<span class="status-badge {getStatusColor(run.status)}">{run.status}</span>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.runs-section {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.section-header h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0;
	}

	.runs-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.run-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 0.375rem;
		text-decoration: none;
		transition: background 0.15s;
	}

	.run-item:hover {
		background: #f1f5f9;
	}

	.run-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.workbench-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.run-time {
		font-size: 0.75rem;
		color: #64748b;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.status-success {
		background: #dcfce7;
		color: #166534;
	}

	.status-running {
		background: #dbeafe;
		color: #1e40af;
	}

	.status-failed {
		background: #fee2e2;
		color: #991b1b;
	}

	.status-queued {
		background: #f3f4f6;
		color: #374151;
	}

	.status-canceled {
		background: #fef3c7;
		color: #92400e;
	}

	.status-timeout {
		background: #fecaca;
		color: #b91c1c;
	}

	.status-default {
		background: #e5e7eb;
		color: #4b5563;
	}
</style>
