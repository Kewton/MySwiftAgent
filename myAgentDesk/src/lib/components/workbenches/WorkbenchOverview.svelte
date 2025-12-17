<!--
  WorkbenchOverview Component
  Issue #289: Workbench List/Detail Screens

  Overview panel for workbench detail view.
  Displays workbench info, versions, and statistics.
-->
<script lang="ts">
	import type { WorkbenchDetail } from '$lib/types/workbench';
	import WorkbenchStats from './WorkbenchStats.svelte';
	import EditableText from '$lib/components/ui/EditableText.svelte';

	interface Props {
		workbench: WorkbenchDetail;
	}

	let { workbench }: Props = $props();

	const statusBadgeClass = $derived(
		{
			draft: 'badge-draft',
			active: 'badge-active',
			archived: 'badge-archived'
		}[workbench.status]
	);

	const formatDate = (date: Date | null): string => {
		if (!date) return 'N/A';
		return new Date(date).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	};
</script>

<div class="overview-container" data-testid="workbench-overview">
	<div class="overview-header">
		<div class="header-content">
			<h2 class="workbench-title">{workbench.name}</h2>
			<span class="status-badge {statusBadgeClass}" data-testid="overview-status">
				{workbench.status}
			</span>
		</div>
		<div class="description-container">
			<EditableText
				value={workbench.description}
				action="?/updateDescription"
				placeholder="Add a workbench description..."
				emptyText="Click to add description"
				multiline={true}
			/>
		</div>
	</div>

	<div class="overview-sections">
		<!-- Statistics Section -->
		<section class="overview-section">
			<h3 class="section-title">Statistics</h3>
			<WorkbenchStats stats={workbench.stats} />
		</section>

		<!-- Version Information Section -->
		<section class="overview-section">
			<h3 class="section-title">Version Information</h3>
			<div class="version-grid">
				<div class="version-card" data-testid="active-requirement">
					<span class="version-label">Active Requirements</span>
					{#if workbench.activeRequirementVersion}
						<div class="version-info">
							<span class="version-number">v{workbench.activeRequirementVersion.version}</span>
							<span class="version-status status-{workbench.activeRequirementVersion.status}">
								{workbench.activeRequirementVersion.status}
							</span>
						</div>
					{:else}
						<span class="version-empty">No requirements set</span>
					{/if}
				</div>

				<div class="version-card" data-testid="current-job">
					<span class="version-label">Current Job Version</span>
					{#if workbench.currentJobVersion}
						<div class="version-info">
							<span class="version-number">{workbench.currentJobVersion.versionLabel}</span>
							<span class="version-status status-{workbench.currentJobVersion.status}">
								{workbench.currentJobVersion.status}
							</span>
						</div>
					{:else}
						<span class="version-empty">No job generated</span>
					{/if}
				</div>
			</div>
		</section>

		<!-- Metadata Section -->
		<section class="overview-section">
			<h3 class="section-title">Details</h3>
			<div class="metadata-grid">
				<div class="metadata-item">
					<span class="metadata-label">Created</span>
					<span class="metadata-value">{formatDate(workbench.createdAt)}</span>
				</div>
				<div class="metadata-item">
					<span class="metadata-label">Last Updated</span>
					<span class="metadata-value">{formatDate(workbench.updatedAt)}</span>
				</div>
			</div>
		</section>
	</div>
</div>

<style>
	.overview-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.overview-header {
		padding-bottom: 1rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.header-content {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.workbench-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.status-badge {
		display: inline-block;
		padding: 0.25rem 0.625rem;
		font-size: 0.75rem;
		font-weight: 500;
		text-transform: capitalize;
		border-radius: 9999px;
	}

	.badge-draft {
		background: #f1f5f9;
		color: #64748b;
	}

	.badge-active {
		background: #dcfce7;
		color: #16a34a;
	}

	.badge-archived {
		background: #fef3c7;
		color: #d97706;
	}

	.description-container {
		margin-top: 0.5rem;
	}

	.overview-sections {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.overview-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
		margin: 0;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.version-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
	}

	.version-card {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.version-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
	}

	.version-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.version-number {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
	}

	.version-status {
		font-size: 0.75rem;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		text-transform: capitalize;
	}

	.status-draft {
		background: #f1f5f9;
		color: #64748b;
	}

	.status-active {
		background: #dcfce7;
		color: #16a34a;
	}

	.status-submitted {
		background: #dbeafe;
		color: #2563eb;
	}

	.status-deprecated {
		background: #fef3c7;
		color: #d97706;
	}

	.status-generating {
		background: #dbeafe;
		color: #2563eb;
	}

	.status-success {
		background: #dcfce7;
		color: #16a34a;
	}

	.status-failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.version-empty {
		font-size: 0.875rem;
		color: #94a3b8;
		font-style: italic;
	}

	.metadata-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.metadata-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.metadata-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
	}

	.metadata-value {
		font-size: 0.875rem;
		color: #1e293b;
	}
</style>
