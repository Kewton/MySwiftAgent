<!--
  Improve Page (/projects/:projectId/workbenches/:workbenchId/improve)
  Issue #290: Requirements List and Version Management

  Requirements improvement interface with current requirements display
  and ability to create new versions.
-->
<script lang="ts">
	import { enhance } from '$app/forms';
	import MarkdownViewer from '$lib/components/markdown/MarkdownViewer.svelte';
	import type { RequirementVersionDetail } from '$lib/types/requirement';

	interface Props {
		data: {
			activeRequirement: RequirementVersionDetail | null;
			projectId: string;
			workbenchId: string;
		};
		form: {
			error?: string;
		} | null;
	}

	let { data, form }: Props = $props();

	const activeRequirement = $derived(data.activeRequirement);
	const hasRequirement = $derived(!!activeRequirement?.content);

	let isSubmitting = $state(false);
</script>

<div class="improve-page" data-testid="improve-page">
	<div class="page-header">
		<h2>Improve Requirements</h2>
	</div>

	{#if form?.error}
		<div class="error-message" data-testid="error-message">
			{form.error}
		</div>
	{/if}

	<div class="improve-content">
		<div class="content-section">
			<h3>
				Current Requirements
				{#if activeRequirement}
					<span class="version-badge">v{activeRequirement.version}</span>
					<span class="status-badge status-{activeRequirement.status}"
						>{activeRequirement.status}</span
					>
				{/if}
			</h3>
			<div class="requirements-preview" data-testid="requirements-preview">
				{#if hasRequirement && activeRequirement}
					<MarkdownViewer content={activeRequirement.content} />
				{:else}
					<p class="placeholder-text">
						No requirements defined yet.
						<a href="/projects/{data.projectId}/workbenches/{data.workbenchId}/requirements">
							Create requirements
						</a>
						to get started.
					</p>
				{/if}
			</div>
		</div>

		<div class="content-section">
			<h3>Suggested Improvements</h3>
			<div class="suggestions-list">
				<div class="suggestion-item">
					<span class="suggestion-badge">AI Suggestion</span>
					<p>Consider adding error handling for API timeout scenarios.</p>
				</div>
				<div class="suggestion-item">
					<span class="suggestion-badge">From Analysis</span>
					<p>The data validation step could be optimized based on run logs.</p>
				</div>
			</div>
		</div>

		<div class="actions-section">
			<a
				href="/projects/{data.projectId}/workbenches/{data.workbenchId}/requirements"
				class="action-button secondary"
			>
				View All Versions
			</a>
			{#if hasRequirement}
				<form
					method="POST"
					action="?/createVersion"
					use:enhance={() => {
						isSubmitting = true;
						return async ({ update }) => {
							isSubmitting = false;
							await update();
						};
					}}
				>
					<input type="hidden" name="content" value={activeRequirement?.content ?? ''} />
					<input type="hidden" name="changeSummary" value="Improvement based on analysis" />
					<button
						type="submit"
						class="action-button"
						disabled={isSubmitting}
						data-testid="create-version-button"
					>
						{isSubmitting ? 'Creating...' : 'Create New Version'}
					</button>
				</form>
			{:else}
				<a
					href="/projects/{data.projectId}/workbenches/{data.workbenchId}/requirements/new"
					class="action-button"
					data-testid="create-requirements-button"
				>
					Create Requirements
				</a>
			{/if}
		</div>
	</div>
</div>

<style>
	.improve-page {
		max-width: 800px;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.error-message {
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 0.375rem;
		color: #991b1b;
		font-size: 0.875rem;
	}

	.improve-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.content-section {
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
	}

	.content-section h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.version-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.125rem 0.375rem;
		background: #e0e7ff;
		color: #3730a3;
		border-radius: 0.25rem;
	}

	.status-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
	}

	.status-draft {
		background: #fef3c7;
		color: #92400e;
	}

	.status-active {
		background: #d1fae5;
		color: #065f46;
	}

	.status-submitted {
		background: #dbeafe;
		color: #1e40af;
	}

	.status-deprecated {
		background: #f3f4f6;
		color: #6b7280;
	}

	.requirements-preview {
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		min-height: 100px;
		max-height: 400px;
		overflow-y: auto;
	}

	.placeholder-text {
		color: #94a3b8;
		font-style: italic;
		margin: 0;
	}

	.placeholder-text a {
		color: #3b82f6;
		text-decoration: none;
	}

	.placeholder-text a:hover {
		text-decoration: underline;
	}

	.suggestions-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.suggestion-item {
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
	}

	.suggestion-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		background: #eff6ff;
		color: #1e40af;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		margin-bottom: 0.5rem;
	}

	.suggestion-item p {
		color: #1e293b;
		font-size: 0.875rem;
		margin: 0;
	}

	.actions-section {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
	}

	.actions-section form {
		display: inline;
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
		display: inline-block;
	}

	.action-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.action-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
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
</style>
