<!--
  Requirement Version Detail (/projects/:projectId/workbenches/:workbenchId/requirements/:reqVersionId)
  Issue #285: SvelteKit Routing Foundation

  Shows requirement version details and diff.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const reqVersionId = $derived($page.params.reqVersionId);
</script>

<div class="req-detail-page">
	<div class="page-header">
		<h2>Requirement Version: {reqVersionId}</h2>
		<div class="actions">
			<button class="action-button secondary">Compare</button>
			<button class="action-button">Set as Active</button>
		</div>
	</div>

	<div class="req-content">
		<div class="content-section">
			<h3>Description</h3>
			<p class="placeholder-text">Requirement description will be displayed here.</p>
		</div>

		<div class="content-section">
			<h3>Details</h3>
			<div class="details-grid">
				<div class="detail-item">
					<span class="label">Created</span>
					<span class="value">2024-01-15 10:30</span>
				</div>
				<div class="detail-item">
					<span class="label">Status</span>
					<span class="value">Draft</span>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.req-detail-page {
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

	.req-content {
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

	.placeholder-text {
		color: #94a3b8;
		font-style: italic;
		margin: 0;
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
</style>
