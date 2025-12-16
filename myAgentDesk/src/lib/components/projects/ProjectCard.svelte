<!--
  ProjectCard Component
  Issue #288: Project screens implementation

  Displays a project card with name, description, and workbench count.
-->
<script lang="ts">
	import type { ProjectListItem } from '$lib/types/project';

	interface Props {
		project: ProjectListItem;
	}

	let { project }: Props = $props();
</script>

<a href="/projects/{project.id}" class="project-card">
	<div class="card-header">
		<h3 class="project-name">{project.name}</h3>
		<span class="workbench-count" aria-label="Workbench count">
			{project.workbenchCount}
			<span class="count-label">workbenches</span>
		</span>
	</div>
	{#if project.description}
		<p class="project-description">{project.description}</p>
	{/if}
	<div class="card-footer">
		<span class="updated-at">
			Updated {project.updatedAt.toLocaleDateString()}
		</span>
	</div>
</a>

<style>
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

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 0.75rem;
	}

	.project-name {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.workbench-count {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		font-size: 1.25rem;
		font-weight: 700;
		color: #3b82f6;
	}

	.count-label {
		font-size: 0.625rem;
		font-weight: 400;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.project-description {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 1rem;
		line-height: 1.5;
	}

	.card-footer {
		border-top: 1px solid #f1f5f9;
		padding-top: 0.75rem;
	}

	.updated-at {
		font-size: 0.75rem;
		color: #94a3b8;
	}
</style>
