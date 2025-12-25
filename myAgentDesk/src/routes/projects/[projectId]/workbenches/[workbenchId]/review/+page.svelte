<!--
  Review Page (/projects/:projectId/workbenches/:workbenchId/review)
  Issue #292: Review Page (JobVersion Detail)

  Lists generated JobVersions for review with status badges and actions.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { invalidateAll } from '$app/navigation';
	import type { PageData } from './$types';
	import { formatDate, getStatusConfig, canActivate, canStartRun } from '$lib/utils';

	const { data }: { data: PageData } = $props();

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	let activating = $state<string | null>(null);

	async function activateVersion(jobVersionId: string) {
		if (activating) return;

		activating = jobVersionId;
		try {
			const response = await fetch(`/api/job-versions/${jobVersionId}/activate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' }
			});

			if (response.ok) {
				await invalidateAll();
			} else {
				const error = await response.json();
				console.error('Activation failed:', error);
			}
		} catch (error) {
			console.error('Activation error:', error);
		} finally {
			activating = null;
		}
	}
</script>

<div class="review-page">
	<div class="page-header">
		<h2>Review Job Versions</h2>
		<p class="description">Review and activate generated job versions.</p>
	</div>

	{#if data.activeJobVersion}
		<div class="active-info">
			<span class="active-label">Active Version:</span>
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/job-versions/{data.activeJobVersion
					.id}"
				class="active-version-link"
			>
				{data.activeJobVersion.versionLabel}
			</a>
		</div>
	{/if}

	<div class="job-versions-list">
		{#each data.jobVersions as jv (jv.id)}
			{@const statusConfig = getStatusConfig(jv.status)}
			<div class="job-version-item" class:is-active={jv.status === 'active'}>
				<a
					href="/projects/{projectId}/workbenches/{workbenchId}/job-versions/{jv.id}"
					class="jv-link"
				>
					<div class="jv-main">
						<span class="jv-version">{jv.versionLabel}</span>
						<span class="jv-status {statusConfig.class}">{statusConfig.label}</span>
					</div>
					<div class="jv-meta">
						<span class="jv-source">from Req v{jv.sourceRequirementVersion}</span>
						<span class="jv-date">{formatDate(jv.generatedAt ?? jv.createdAt)}</span>
					</div>
				</a>
				<div class="jv-actions">
					{#if canActivate(jv.status)}
						<button
							type="button"
							class="activate-button"
							onclick={() => activateVersion(jv.id)}
							disabled={activating === jv.id}
						>
							{activating === jv.id ? 'Activating...' : 'Set Active'}
						</button>
					{/if}
					{#if canStartRun(jv.status)}
						<a
							href="/projects/{projectId}/workbenches/{workbenchId}/runs?start={jv.id}"
							class="start-run-button"
						>
							Start Run
						</a>
					{/if}
				</div>
			</div>
		{:else}
			<div class="empty-state">
				<p>No job versions generated yet.</p>
				<a href="/projects/{projectId}/workbenches/{workbenchId}/generate" class="generate-link">
					Generate from Requirements
				</a>
			</div>
		{/each}
	</div>
</div>

<style>
	.review-page {
		max-width: 900px;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.25rem;
	}

	.description {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	.active-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: #dbeafe;
		border: 1px solid #93c5fd;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.active-label {
		font-size: 0.8125rem;
		font-weight: 500;
		color: #1e40af;
	}

	.active-version-link {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1d4ed8;
		text-decoration: none;
	}

	.active-version-link:hover {
		text-decoration: underline;
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
		border-radius: 0.5rem;
		transition: border-color 0.15s;
	}

	.job-version-item:hover {
		border-color: #94a3b8;
	}

	.job-version-item.is-active {
		border-color: #3b82f6;
		background: #f0f9ff;
	}

	.jv-link {
		flex: 1;
		text-decoration: none;
	}

	.jv-main {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.375rem;
	}

	.jv-version {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
	}

	.jv-status {
		padding: 0.125rem 0.5rem;
		font-size: 0.6875rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.status-generating {
		background: #fef3c7;
		color: #92400e;
	}

	.status-success {
		background: #dcfce7;
		color: #166534;
	}

	.status-failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.status-active {
		background: #dbeafe;
		color: #1e40af;
	}

	.status-deprecated {
		background: #f1f5f9;
		color: #64748b;
	}

	.jv-meta {
		display: flex;
		align-items: center;
		gap: 1rem;
		font-size: 0.8125rem;
		color: #64748b;
	}

	.jv-source {
		color: #94a3b8;
	}

	.jv-actions {
		display: flex;
		gap: 0.5rem;
	}

	.activate-button {
		padding: 0.375rem 0.75rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		transition: all 0.15s;
	}

	.activate-button:hover:not(:disabled) {
		background: #f1f5f9;
		color: #1e293b;
	}

	.activate-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.start-run-button {
		padding: 0.375rem 0.75rem;
		background: #3b82f6;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: white;
		text-decoration: none;
		transition: background 0.15s;
	}

	.start-run-button:hover {
		background: #2563eb;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 2rem;
		background: #f8fafc;
		border: 1px dashed #e2e8f0;
		border-radius: 0.5rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0 0 1rem;
	}

	.generate-link {
		display: inline-block;
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		text-decoration: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.generate-link:hover {
		background: #2563eb;
	}
</style>
