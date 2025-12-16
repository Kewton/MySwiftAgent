<!--
  Run Detail Page (/projects/:projectId/workbenches/:workbenchId/runs/:runId)
  Issue #285: SvelteKit Routing Foundation

  Shows run details, logs, and trace information.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const runId = $derived($page.params.runId);
</script>

<div class="run-detail-page">
	<div class="page-header">
		<h2>Run: {runId}</h2>
		<div class="actions">
			<button class="action-button secondary">View Trace</button>
			<button class="action-button secondary">Rerun</button>
		</div>
	</div>

	<div class="run-content">
		<div class="content-section">
			<h3>Status</h3>
			<div class="status-bar">
				<span class="status-badge completed">Completed</span>
				<span class="duration">Duration: 2m 34s</span>
			</div>
		</div>

		<div class="content-section">
			<h3>Details</h3>
			<div class="details-grid">
				<div class="detail-item">
					<span class="label">Job Version</span>
					<span class="value">v1.2</span>
				</div>
				<div class="detail-item">
					<span class="label">Started</span>
					<span class="value">2024-01-15 15:00:00</span>
				</div>
				<div class="detail-item">
					<span class="label">Completed</span>
					<span class="value">2024-01-15 15:02:34</span>
				</div>
				<div class="detail-item">
					<span class="label">Trace ID</span>
					<span class="value mono">trace_abc123xyz</span>
				</div>
			</div>
		</div>

		<div class="content-section">
			<h3>Logs</h3>
			<div class="logs-container">
				<pre class="logs">[15:00:00] Starting run...
[15:00:01] Loading workflow...
[15:00:05] Executing tasks...
[15:02:30] All tasks completed
[15:02:34] Run finished successfully</pre>
			</div>
		</div>
	</div>
</div>

<style>
	.run-detail-page {
		max-width: 900px;
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

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.action-button:hover {
		background: #2563eb;
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

	.status-badge.completed {
		background: #dcfce7;
		color: #166534;
	}

	.duration {
		font-size: 0.875rem;
		color: #64748b;
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
	}

	.logs-container {
		background: #1e293b;
		border-radius: 0.25rem;
		overflow: hidden;
	}

	.logs {
		margin: 0;
		padding: 1rem;
		font-family: monospace;
		font-size: 0.75rem;
		color: #94a3b8;
		line-height: 1.5;
		overflow-x: auto;
	}
</style>
