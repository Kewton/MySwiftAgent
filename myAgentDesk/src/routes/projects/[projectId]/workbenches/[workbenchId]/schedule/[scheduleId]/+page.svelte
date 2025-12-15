<!--
  Schedule Detail Page (/projects/:projectId/workbenches/:workbenchId/schedule/:scheduleId)
  Issue #285: SvelteKit Routing Foundation

  Shows schedule details and allows editing.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const scheduleId = $derived($page.params.scheduleId);
</script>

<div class="schedule-detail-page">
	<div class="page-header">
		<h2>Schedule: {scheduleId}</h2>
		<div class="actions">
			<button class="action-button secondary">Pause</button>
			<button class="action-button">Edit</button>
		</div>
	</div>

	<div class="schedule-content">
		<div class="content-section">
			<h3>Configuration</h3>
			<div class="details-grid">
				<div class="detail-item">
					<span class="label">Name</span>
					<span class="value">Daily Report</span>
				</div>
				<div class="detail-item">
					<span class="label">Cron Expression</span>
					<span class="value mono">0 9 * * *</span>
				</div>
				<div class="detail-item">
					<span class="label">Job Version</span>
					<span class="value">v1.2</span>
				</div>
				<div class="detail-item">
					<span class="label">Status</span>
					<span class="value">Active</span>
				</div>
			</div>
		</div>

		<div class="content-section">
			<h3>Next Runs</h3>
			<ul class="next-runs-list">
				<li>2024-01-17 09:00:00</li>
				<li>2024-01-18 09:00:00</li>
				<li>2024-01-19 09:00:00</li>
			</ul>
		</div>

		<div class="content-section">
			<h3>Recent Executions</h3>
			<div class="executions-list">
				<div class="execution-item">
					<span class="execution-time">2024-01-16 09:00:00</span>
					<span class="execution-status success">Success</span>
				</div>
				<div class="execution-item">
					<span class="execution-time">2024-01-15 09:00:00</span>
					<span class="execution-status success">Success</span>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.schedule-detail-page {
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

	.schedule-content {
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

	.next-runs-list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.next-runs-list li {
		padding: 0.5rem 0;
		font-size: 0.875rem;
		color: #1e293b;
		border-bottom: 1px solid #e2e8f0;
	}

	.next-runs-list li:last-child {
		border-bottom: none;
	}

	.executions-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.execution-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem;
		background: white;
		border-radius: 0.25rem;
	}

	.execution-time {
		font-size: 0.875rem;
		color: #1e293b;
	}

	.execution-status {
		padding: 0.125rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.execution-status.success {
		background: #dcfce7;
		color: #166534;
	}

	.execution-status.failed {
		background: #fee2e2;
		color: #991b1b;
	}
</style>
