<!--
  Job Version Detail (/projects/:projectId/workbenches/:workbenchId/job-versions/:jobVersionId)
  Issue #285: SvelteKit Routing Foundation

  Shows job version details including tasks, interfaces, and workflows.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const jobVersionId = $derived($page.params.jobVersionId);
</script>

<div class="jv-detail-page">
	<div class="page-header">
		<h2>Job Version: {jobVersionId}</h2>
		<div class="actions">
			<button class="action-button">Start Run</button>
		</div>
	</div>

	<div class="jv-content">
		<div class="content-section">
			<h3>Tasks</h3>
			<div class="placeholder-content">
				<p>Task list will be displayed here.</p>
			</div>
		</div>

		<div class="content-section">
			<h3>Interfaces</h3>
			<div class="placeholder-content">
				<p>Interface definitions will be displayed here.</p>
			</div>
		</div>

		<div class="content-section">
			<h3>Workflow</h3>
			<div class="placeholder-content">
				<p>Workflow diagram will be displayed here.</p>
			</div>
		</div>
	</div>
</div>

<style>
	.jv-detail-page {
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

	.jv-content {
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

	.placeholder-content {
		padding: 1.5rem;
		background: white;
		border: 1px dashed #e2e8f0;
		border-radius: 0.25rem;
		text-align: center;
	}

	.placeholder-content p {
		color: #94a3b8;
		font-style: italic;
		margin: 0;
	}
</style>
