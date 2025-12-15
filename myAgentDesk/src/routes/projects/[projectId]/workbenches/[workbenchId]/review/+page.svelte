<!--
  Review Page (/projects/:projectId/workbenches/:workbenchId/review)
  Issue #285: SvelteKit Routing Foundation

  Lists generated JobVersions for review.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Mock job versions - will be loaded from API in future iterations
	const jobVersions = $state([
		{ id: 'jv_v1.1', version: 'v1.1', status: 'ready', createdAt: '2024-01-15 11:00' },
		{ id: 'jv_v1.2', version: 'v1.2', status: 'reviewed', createdAt: '2024-01-15 14:30' }
	]);
</script>

<div class="review-page">
	<div class="page-header">
		<h2>Review Job Versions</h2>
	</div>

	<div class="job-versions-list">
		{#each jobVersions as jv (jv.id)}
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/job-versions/{jv.id}"
				class="job-version-item"
			>
				<div class="jv-info">
					<span class="jv-version">{jv.version}</span>
					<span class="jv-date">{jv.createdAt}</span>
				</div>
				<span class="jv-status" data-status={jv.status}>{jv.status}</span>
			</a>
		{:else}
			<div class="empty-state">
				<p>No job versions generated yet. Generate a job from the requirements.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.review-page {
		max-width: 800px;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.job-versions-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.job-version-item {
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

	.job-version-item:hover {
		border-color: #3b82f6;
	}

	.jv-info {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.jv-version {
		font-weight: 600;
		color: #1e293b;
	}

	.jv-date {
		font-size: 0.875rem;
		color: #64748b;
	}

	.jv-status {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: capitalize;
	}

	.jv-status[data-status='ready'] {
		background: #eff6ff;
		color: #1e40af;
	}

	.jv-status[data-status='reviewed'] {
		background: #dcfce7;
		color: #166534;
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
