<!--
  RequirementVersionCard Component
  Issue #290: Requirements List and Version Management

  Displays a single requirement version in a card format.
  Shows version number, status, change summary, and timestamps.
-->
<script lang="ts">
	import { REQUIREMENT_STATUS_CONFIG } from '$lib/types/requirement';
	import type { RequirementVersionStatus } from '$lib/server/db/schema';

	interface Props {
		version: {
			id: string;
			version: number;
			status: RequirementVersionStatus;
			changeSummary: string | null;
			createdAt: Date;
			updatedAt: Date;
		};
		projectId: string;
		workbenchId: string;
		isActive: boolean;
	}

	let { version, projectId, workbenchId, isActive }: Props = $props();

	const statusConfig = $derived(REQUIREMENT_STATUS_CONFIG[version.status]);

	const formattedDate = $derived(
		new Date(version.createdAt).toLocaleDateString('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit'
		})
	);

	const detailHref = $derived(
		`/projects/${projectId}/workbenches/${workbenchId}/requirements/${version.id}`
	);
</script>

<a href={detailHref} class="version-card" class:is-active={isActive} data-testid="version-card">
	<div class="card-main">
		<div class="version-info">
			<span class="version-number" data-testid="version-number">v{version.version}</span>
			{#if isActive}
				<span class="active-indicator" data-testid="active-indicator">Current</span>
			{/if}
		</div>
		<span
			class="status-badge"
			style="background-color: {statusConfig.bgColor}; color: {statusConfig.color}"
			data-testid="status-badge"
		>
			{statusConfig.label}
		</span>
	</div>

	{#if version.changeSummary}
		<p class="change-summary" data-testid="change-summary">{version.changeSummary}</p>
	{/if}

	<div class="card-footer">
		<span class="date" data-testid="created-date">{formattedDate}</span>
	</div>
</a>

<style>
	.version-card {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		text-decoration: none;
		transition:
			border-color 0.15s,
			background-color 0.15s;
	}

	.version-card:hover {
		border-color: #3b82f6;
		background: #ffffff;
	}

	.version-card.is-active {
		border-color: #22c55e;
		border-width: 2px;
		background: #f0fdf4;
	}

	.card-main {
		display: flex;
		justify-content: space-between;
		align-items: center;
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

	.active-indicator {
		padding: 0.125rem 0.375rem;
		font-size: 0.625rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.025em;
		color: #166534;
		background: #dcfce7;
		border-radius: 0.25rem;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.change-summary {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
		line-height: 1.4;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.card-footer {
		display: flex;
		justify-content: flex-end;
	}

	.date {
		font-size: 0.75rem;
		color: #94a3b8;
	}
</style>
