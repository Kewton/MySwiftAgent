<!--
  Requirements Page (/projects/:projectId/workbenches/:workbenchId/requirements)
  Issue #290: Requirements List and Version Management

  Lists and manages requirement versions with real data.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import RequirementVersionCard from '$lib/components/requirements/RequirementVersionCard.svelte';

	interface Props {
		data: {
			workbenchDetail: {
				id: string;
				name: string;
				activeRequirementVersion: { id: string; version: number } | null;
			};
			requirementVersions: Array<{
				id: string;
				version: number;
				status: 'draft' | 'submitted' | 'active' | 'deprecated';
				changeSummary: string | null;
				createdAt: Date;
				updatedAt: Date;
			}>;
		};
	}

	let { data }: Props = $props();

	const projectId = $derived($page.params.projectId ?? '');
	const workbenchId = $derived($page.params.workbenchId ?? '');
	const activeVersionId = $derived(data.workbenchDetail?.activeRequirementVersion?.id ?? null);
</script>

<div class="requirements-page" data-testid="requirements-page">
	<div class="page-header">
		<h2>Requirements</h2>
		<a
			href="/projects/{projectId}/workbenches/{workbenchId}/requirements/new"
			class="create-button"
			data-testid="create-button"
		>
			New Version
		</a>
	</div>

	<div class="requirements-list" data-testid="requirements-list">
		{#each data.requirementVersions as version (version.id)}
			<RequirementVersionCard
				{version}
				{projectId}
				{workbenchId}
				isActive={version.id === activeVersionId}
			/>
		{:else}
			<div class="empty-state" data-testid="empty-state">
				<p>No requirements defined yet. Create your first requirement version.</p>
				<a
					href="/projects/{projectId}/workbenches/{workbenchId}/requirements/new"
					class="create-first-button"
				>
					Create First Requirement
				</a>
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
		text-decoration: none;
	}

	.create-button:hover {
		background: #2563eb;
	}

	.requirements-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0 0 1rem;
	}

	.create-first-button {
		display: inline-block;
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		text-decoration: none;
	}

	.create-first-button:hover {
		background: #2563eb;
	}
</style>
