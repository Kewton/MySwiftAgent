<!--
  Requirement Version Detail Page
  Issue #290: Requirements List and Version Management

  Shows requirement version details, Markdown content, and diff view.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import MarkdownViewer from '$lib/components/markdown/MarkdownViewer.svelte';
	import DiffViewer from '$lib/components/markdown/DiffViewer.svelte';
	import { REQUIREMENT_STATUS_CONFIG } from '$lib/types/requirement';
	import type { RequirementVersionDetail, DiffEntry } from '$lib/types/requirement';

	interface Props {
		data: {
			workbenchDetail: {
				id: string;
				name: string;
				activeRequirementVersion: { id: string; version: number } | null;
			};
			requirementVersion: RequirementVersionDetail;
			diff: {
				fromVersion: number;
				toVersion: number;
				diffs: DiffEntry[];
			} | null;
			compareVersion: RequirementVersionDetail | null;
			allVersions: Array<{
				id: string;
				version: number;
				status: string;
			}>;
		};
	}

	let { data }: Props = $props();

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);
	const version = $derived(data.requirementVersion);
	const statusConfig = $derived(REQUIREMENT_STATUS_CONFIG[version.status]);
	const isActive = $derived(data.workbenchDetail?.activeRequirementVersion?.id === version.id);

	// Compare mode state
	let showDiff = $state(!!data.diff);
	let selectedCompareVersionId = $state(data.compareVersion?.id ?? '');

	const formattedDate = $derived(
		new Date(version.createdAt).toLocaleDateString('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		})
	);

	// Versions available for comparison (exclude current version)
	const comparableVersions = $derived(data.allVersions.filter((v) => v.id !== version.id));

	function handleCompareChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		selectedCompareVersionId = select.value;
		if (selectedCompareVersionId) {
			goto(`${$page.url.pathname}?compare=${selectedCompareVersionId}`);
		} else {
			goto($page.url.pathname);
		}
	}
</script>

<div class="req-detail-page" data-testid="requirement-detail-page">
	<div class="page-header">
		<div class="header-left">
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/requirements"
				class="back-link"
				data-testid="back-link"
			>
				&larr; Back to Requirements
			</a>
			<h2 data-testid="version-title">
				v{version.version}
				{#if isActive}
					<span class="active-badge" data-testid="active-badge">Active</span>
				{/if}
			</h2>
		</div>
		<div class="actions">
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/requirements/{version.id}/edit"
				class="action-button secondary"
				data-testid="edit-button"
			>
				Edit
			</a>
			{#if !isActive && version.status !== 'active'}
				<form method="POST" action="?/setActive" use:enhance>
					<button type="submit" class="action-button" data-testid="set-active-button">
						Set as Active
					</button>
				</form>
			{/if}
		</div>
	</div>

	<div class="meta-info" data-testid="meta-info">
		<span
			class="status-badge"
			style="background-color: {statusConfig.bgColor}; color: {statusConfig.color}"
			data-testid="status-badge"
		>
			{statusConfig.label}
		</span>
		<span class="date" data-testid="created-date">Created: {formattedDate}</span>
		{#if version.changeSummary}
			<span class="change-summary" data-testid="change-summary">
				{version.changeSummary}
			</span>
		{/if}
	</div>

	{#if comparableVersions.length > 0}
		<div class="compare-section" data-testid="compare-section">
			<label for="compare-select">Compare with:</label>
			<select
				id="compare-select"
				value={selectedCompareVersionId}
				onchange={handleCompareChange}
				data-testid="compare-select"
			>
				<option value="">Select version...</option>
				{#each comparableVersions as v (v.id)}
					<option value={v.id}>v{v.version} ({v.status})</option>
				{/each}
			</select>
		</div>
	{/if}

	<div class="content-section" data-testid="content-section">
		{#if data.diff && showDiff}
			<DiffViewer
				diffs={data.diff.diffs}
				fromVersion={data.diff.fromVersion}
				toVersion={data.diff.toVersion}
			/>
		{:else}
			<div class="content-wrapper">
				<h3>Content</h3>
				<MarkdownViewer content={version.content} />
			</div>
		{/if}
	</div>
</div>

<style>
	.req-detail-page {
		max-width: 900px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 1rem;
	}

	.header-left {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.back-link {
		font-size: 0.875rem;
		color: #64748b;
		text-decoration: none;
	}

	.back-link:hover {
		color: #3b82f6;
	}

	h2 {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.5rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0;
	}

	.active-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		color: #166534;
		background: #dcfce7;
		border-radius: 0.25rem;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
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

	.action-button:hover {
		background: #2563eb;
	}

	.action-button.secondary {
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
	}

	.action-button.secondary:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	.meta-info {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
		flex-wrap: wrap;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.date {
		font-size: 0.875rem;
		color: #64748b;
	}

	.change-summary {
		font-size: 0.875rem;
		color: #64748b;
		font-style: italic;
	}

	.compare-section {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
		padding: 0.75rem 1rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.compare-section label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.compare-section select {
		padding: 0.375rem 0.75rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		color: #1e293b;
		background: white;
	}

	.content-section {
		margin-top: 1rem;
	}

	.content-wrapper {
		padding: 1.5rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
	}

	.content-wrapper h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid #e2e8f0;
	}
</style>
