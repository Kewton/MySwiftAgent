<!--
  Project List Page (/projects)
  Issue #285: SvelteKit Routing Foundation

  Displays list of projects and allows creating new ones.
-->
<script lang="ts">
	// Project list - will be loaded from API in future iterations
	const projects = $state([
		{ id: 'proj_001', name: 'Demo Project', description: 'A demo project for testing' }
	]);
</script>

<div class="projects-page">
	<div class="page-header">
		<h1>Projects</h1>
		<button class="create-button">New Project</button>
	</div>

	<div class="projects-list">
		{#each projects as project}
			<a href="/projects/{project.id}" class="project-card">
				<h3>{project.name}</h3>
				<p>{project.description}</p>
			</a>
		{:else}
			<div class="empty-state">
				<p>No projects yet. Create your first project to get started.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.projects-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem 1rem;
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

	.projects-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
	}

	.project-card {
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

	.project-card:hover {
		border-color: #3b82f6;
		box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
	}

	.project-card h3 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.project-card p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	.empty-state {
		grid-column: 1 / -1;
		text-align: center;
		padding: 3rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0;
	}
</style>
