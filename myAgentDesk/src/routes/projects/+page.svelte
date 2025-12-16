<!--
  Project List Page (/projects)
  Issue #288: Project screens implementation

  Displays list of projects and allows creating new ones.
-->
<script lang="ts">
	import ProjectCard from '$lib/components/projects/ProjectCard.svelte';
	import CreateProjectModal from '$lib/components/projects/CreateProjectModal.svelte';
	import type { ProjectListItem } from '$lib/types/project';

	interface Props {
		data: {
			projects: ProjectListItem[];
		};
	}

	let { data }: Props = $props();

	let isCreateModalOpen = $state(false);

	function openCreateModal() {
		isCreateModalOpen = true;
	}

	function closeCreateModal() {
		isCreateModalOpen = false;
	}
</script>

<div class="projects-page">
	<div class="page-header">
		<h1>Projects</h1>
		<button class="create-button" onclick={openCreateModal}>New Project</button>
	</div>

	<div class="projects-list">
		{#each data.projects as project (project.id)}
			<ProjectCard {project} />
		{:else}
			<div class="empty-state">
				<p>No projects yet. Create your first project to get started.</p>
				<button class="create-button empty-state-button" onclick={openCreateModal}>
					Create Project
				</button>
			</div>
		{/each}
	</div>
</div>

<CreateProjectModal isOpen={isCreateModalOpen} onClose={closeCreateModal} />

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

	.empty-state {
		grid-column: 1 / -1;
		text-align: center;
		padding: 3rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0 0 1.5rem;
	}

	.empty-state-button {
		margin-top: 0;
	}
</style>
