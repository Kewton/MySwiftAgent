<!--
  New Requirement Page
  Issue #290: Requirements List and Version Management

  Create a new requirement version with Markdown editor.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import MarkdownEditor from '$lib/components/markdown/MarkdownEditor.svelte';

	interface Props {
		data: {
			workbenchDetail: {
				id: string;
				name: string;
			};
			nextVersion: number;
		};
		form: {
			error?: string;
			content?: string;
			changeSummary?: string;
		} | null;
	}

	let { data, form }: Props = $props();

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Initialize with form values (for validation errors) or empty values
	const initialContent = $derived(form?.content ?? '');
	const initialChangeSummary = $derived(form?.changeSummary ?? '');

	let content = $state('');
	let changeSummary = $state('');
	let isSubmitting = $state(false);
	let initialized = $state(false);

	// Initialize state once when component mounts or when form data changes
	$effect(() => {
		if (!initialized || form) {
			content = initialContent;
			changeSummary = initialChangeSummary;
			initialized = true;
		}
	});
</script>

<div class="new-requirement-page" data-testid="new-requirement-page">
	<div class="page-header">
		<div class="header-left">
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/requirements"
				class="back-link"
				data-testid="back-link"
			>
				&larr; Back to Requirements
			</a>
			<h2 data-testid="page-title">New Requirement v{data.nextVersion}</h2>
		</div>
	</div>

	{#if form?.error}
		<div class="error-message" data-testid="error-message">
			{form.error}
		</div>
	{/if}

	<form
		method="POST"
		use:enhance={() => {
			isSubmitting = true;
			return async ({ update }) => {
				isSubmitting = false;
				await update();
			};
		}}
		data-testid="create-form"
	>
		<div class="form-group">
			<label for="changeSummary">Change Summary (optional)</label>
			<input
				type="text"
				id="changeSummary"
				name="changeSummary"
				bind:value={changeSummary}
				placeholder="Brief description of changes..."
				data-testid="change-summary-input"
			/>
		</div>

		<div class="form-group editor-group">
			<label for="content-editor">Content (Markdown)</label>
			<input type="hidden" id="content-editor" name="content" value={content} />
			<MarkdownEditor
				bind:content
				placeholder="# Requirements

Write your requirements here using Markdown...

## Overview
Describe the main objectives.

## Details
- Point 1
- Point 2

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2"
			/>
		</div>

		<div class="form-actions">
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/requirements"
				class="cancel-button"
				data-testid="cancel-button"
			>
				Cancel
			</a>
			<button
				type="submit"
				class="submit-button"
				disabled={isSubmitting || !content.trim()}
				data-testid="submit-button"
			>
				{isSubmitting ? 'Creating...' : 'Create Requirement'}
			</button>
		</div>
	</form>
</div>

<style>
	.new-requirement-page {
		max-width: 1200px;
	}

	.page-header {
		margin-bottom: 1.5rem;
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
		font-size: 1.5rem;
		font-weight: 700;
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

	.form-group {
		margin-bottom: 1.5rem;
	}

	.form-group label {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.form-group input[type='text'] {
		width: 100%;
		padding: 0.5rem 0.75rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		color: #1e293b;
	}

	.form-group input[type='text']:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.editor-group {
		min-height: 500px;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid #e2e8f0;
	}

	.cancel-button {
		padding: 0.5rem 1rem;
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		text-decoration: none;
		cursor: pointer;
	}

	.cancel-button:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	.submit-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.submit-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.submit-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
