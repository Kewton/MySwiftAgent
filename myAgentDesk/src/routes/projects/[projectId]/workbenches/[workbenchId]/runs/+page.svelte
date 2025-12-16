<!--
  Runs Page (/projects/:projectId/workbenches/:workbenchId/runs)
  Issue #285: SvelteKit Routing Foundation

  Lists execution history.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Mock runs - will be loaded from API in future iterations
	const runs = $state([
		{ id: 'run_001', jobVersion: 'v1.2', status: 'completed', startedAt: '2024-01-15 15:00' },
		{ id: 'run_002', jobVersion: 'v1.2', status: 'running', startedAt: '2024-01-16 09:30' }
	]);
</script>

<div class="runs-page">
	<div class="page-header">
		<h2>Runs</h2>
		<button class="start-button">New Run</button>
	</div>

	<div class="runs-list">
		{#each runs as run (run.id)}
			<a href="/projects/{projectId}/workbenches/{workbenchId}/runs/{run.id}" class="run-item">
				<div class="run-info">
					<span class="run-id">{run.id}</span>
					<span class="run-version">Job {run.jobVersion}</span>
					<span class="run-date">{run.startedAt}</span>
				</div>
				<span class="run-status" data-status={run.status}>{run.status}</span>
			</a>
		{:else}
			<div class="empty-state">
				<p>No runs yet. Start a run from a reviewed job version.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.runs-page {
		max-width: 800px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.start-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.start-button:hover {
		background: #2563eb;
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
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		text-decoration: none;
		transition: border-color 0.15s;
	}

	.run-item:hover {
		border-color: #3b82f6;
	}

	.run-info {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.run-id {
		font-weight: 600;
		color: #1e293b;
		font-family: monospace;
	}

	.run-version {
		font-size: 0.875rem;
		color: #64748b;
	}

	.run-date {
		font-size: 0.875rem;
		color: #94a3b8;
	}

	.run-status {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: capitalize;
	}

	.run-status[data-status='completed'] {
		background: #dcfce7;
		color: #166534;
	}

	.run-status[data-status='running'] {
		background: #fef3c7;
		color: #92400e;
	}

	.run-status[data-status='failed'] {
		background: #fee2e2;
		color: #991b1b;
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
</style>
