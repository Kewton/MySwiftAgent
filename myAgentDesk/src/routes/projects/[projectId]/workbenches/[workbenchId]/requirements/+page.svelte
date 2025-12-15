<!--
  Requirements Page (/projects/:projectId/workbenches/:workbenchId/requirements)
  Issue #285: SvelteKit Routing Foundation

  Lists and manages requirement versions.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Mock requirements - will be loaded from API in future iterations
	const requirements = $state([
		{ id: 'rv_v1', version: 'v1', status: 'active', createdAt: '2024-01-15' },
		{ id: 'rv_v2', version: 'v2', status: 'draft', createdAt: '2024-01-16' }
	]);
</script>

<div class="requirements-page">
	<div class="page-header">
		<h2>Requirements</h2>
		<button class="create-button">New Version</button>
	</div>

	<div class="requirements-list">
		{#each requirements as req}
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/requirements/{req.id}"
				class="requirement-item"
			>
				<div class="req-info">
					<span class="req-version">{req.version}</span>
					<span class="req-date">{req.createdAt}</span>
				</div>
				<span class="req-status" data-status={req.status}>{req.status}</span>
			</a>
		{:else}
			<div class="empty-state">
				<p>No requirements defined yet. Create your first requirement version.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.requirements-page {
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

	.create-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.create-button:hover {
		background: #2563eb;
	}

	.requirements-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.requirement-item {
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

	.requirement-item:hover {
		border-color: #3b82f6;
	}

	.req-info {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.req-version {
		font-weight: 600;
		color: #1e293b;
	}

	.req-date {
		font-size: 0.875rem;
		color: #64748b;
	}

	.req-status {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: capitalize;
	}

	.req-status[data-status='active'] {
		background: #dcfce7;
		color: #166534;
	}

	.req-status[data-status='draft'] {
		background: #fef3c7;
		color: #92400e;
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
