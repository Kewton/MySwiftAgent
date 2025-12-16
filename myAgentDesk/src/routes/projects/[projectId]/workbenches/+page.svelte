<!--
  Workbench List Page (/projects/:projectId/workbenches)
  Issue #289: Workbench List/Detail Screens

  Lists all workbenches for the current project with filtering and statistics.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { invalidateAll } from '$app/navigation';
	import WorkbenchCard from '$lib/components/workbenches/WorkbenchCard.svelte';
	import WorkbenchStatusFilter from '$lib/components/workbenches/WorkbenchStatusFilter.svelte';
	import CreateWorkbenchModal from '$lib/components/workbenches/CreateWorkbenchModal.svelte';
	import type { CreateWorkbenchInput } from '$lib/types/workbench';

	interface Props {
		data: {
			workbenches: import('$lib/types/workbench').WorkbenchListItem[];
			statusCounts: import('$lib/types/workbench').WorkbenchStatusCounts;
			currentFilter: import('$lib/types/workbench').WorkbenchStatusFilter;
		};
	}

	let { data }: Props = $props();

	const projectId = $derived($page.params.projectId ?? '');

	let isModalOpen = $state(false);
	let createError = $state<string | null>(null);

	function openModal() {
		isModalOpen = true;
		createError = null;
	}

	function closeModal() {
		isModalOpen = false;
		createError = null;
	}

	async function handleCreate(input: CreateWorkbenchInput) {
		createError = null;

		try {
			const response = await fetch(`/api/projects/${projectId}/workbenches`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(input)
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.message || `Failed to create workbench: ${response.status}`);
			}

			// Invalidate server data to refresh the list
			await invalidateAll();

			closeModal();
		} catch (err) {
			createError = err instanceof Error ? err.message : 'Failed to create workbench';
			console.error('Create workbench error:', err);
		}
	}
</script>

<div class="workbenches-page">
	<div class="page-header">
		<h1>Workbenches</h1>
		<button class="create-button" onclick={openModal} data-testid="create-workbench-button">
			New Workbench
		</button>
	</div>

	{#if createError}
		<div class="error-banner" role="alert">
			<p>{createError}</p>
			<button onclick={() => (createError = null)}>Dismiss</button>
		</div>
	{/if}

	<div class="filter-section">
		<WorkbenchStatusFilter counts={data.statusCounts} />
	</div>

	<div class="workbenches-list">
		{#each data.workbenches as workbench (workbench.id)}
			<WorkbenchCard {workbench} {projectId} />
		{:else}
			<div class="empty-state">
				{#if data.currentFilter === 'all'}
					<p>No workbenches yet. Create your first workbench to get started.</p>
				{:else}
					<p>No {data.currentFilter} workbenches found.</p>
				{/if}
			</div>
		{/each}
	</div>
</div>

<CreateWorkbenchModal open={isModalOpen} onClose={closeModal} onCreate={handleCreate} />

<style>
	.workbenches-page {
		max-width: 1000px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
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

	.filter-section {
		margin-bottom: 1.5rem;
	}

	.workbenches-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1rem;
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

	.error-banner {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 0.375rem;
		color: #dc2626;
	}

	.error-banner p {
		margin: 0;
		font-size: 0.875rem;
	}

	.error-banner button {
		padding: 0.25rem 0.5rem;
		background: transparent;
		border: 1px solid #fecaca;
		border-radius: 0.25rem;
		color: #dc2626;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.error-banner button:hover {
		background: #fee2e2;
	}
</style>
