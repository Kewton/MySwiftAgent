<!--
  Workbench List Page (/projects/:projectId/workbenches)
  Issue #285: SvelteKit Routing Foundation

  Lists all workbenches for the current project.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const projectId = $derived($page.params.projectId);

	// Mock workbenches - will be loaded from API in future iterations
	const workbenches = $state([
		{
			id: 'wb_001',
			name: 'Data Analysis Workflow',
			description: 'Automated data analysis and reporting'
		},
		{
			id: 'wb_002',
			name: 'Content Generation',
			description: 'AI-powered content creation pipeline'
		}
	]);
</script>

<div class="workbenches-page">
	<div class="page-header">
		<h1>Workbenches</h1>
		<button class="create-button">New Workbench</button>
	</div>

	<div class="workbenches-list">
		{#each workbenches as workbench}
			<a href="/projects/{projectId}/workbenches/{workbench.id}" class="workbench-card">
				<h3>{workbench.name}</h3>
				<p>{workbench.description}</p>
			</a>
		{:else}
			<div class="empty-state">
				<p>No workbenches yet. Create your first workbench to get started.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.workbenches-page {
		max-width: 1000px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 1.5rem;
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

	.workbenches-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.workbench-card {
		display: block;
		padding: 1.5rem;
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

	.workbench-card h3 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.workbench-card p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	.empty-state {
		grid-column: 1 / -1;
		text-align: center;
		padding: 3rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0;
	}
</style>
