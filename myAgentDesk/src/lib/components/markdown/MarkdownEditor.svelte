<!--
  MarkdownEditor Component
  Issue #290: Requirements List and Version Management

  Split-view Markdown editor with live preview.
  Includes unsaved changes warning.
-->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import MarkdownViewer from './MarkdownViewer.svelte';

	interface Props {
		content: string;
		placeholder?: string;
		onchange?: (content: string) => void;
		class?: string;
	}

	let {
		content = $bindable(),
		placeholder = 'Enter Markdown content...',
		onchange,
		class: className = ''
	}: Props = $props();

	let initialContent = $state('');

	// Track unsaved changes using derived
	const hasUnsavedChanges = $derived(content !== initialContent);

	// Setup beforeunload warning
	function handleBeforeUnload(event: BeforeUnloadEvent) {
		if (hasUnsavedChanges) {
			event.preventDefault();
			event.returnValue = '';
		}
	}

	onMount(() => {
		initialContent = content;
		if (browser) {
			window.addEventListener('beforeunload', handleBeforeUnload);
		}
	});

	onDestroy(() => {
		if (browser) {
			window.removeEventListener('beforeunload', handleBeforeUnload);
		}
	});

	function handleInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		content = target.value;
		onchange?.(content);
	}

	/**
	 * Mark content as saved (reset initial content).
	 * Call this after successful save.
	 */
	export function markAsSaved() {
		initialContent = content;
	}
</script>

<div class="markdown-editor {className}" data-testid="markdown-editor">
	<div class="editor-toolbar" data-testid="editor-toolbar">
		<span class="toolbar-title">Markdown Editor</span>
		{#if hasUnsavedChanges}
			<span class="unsaved-indicator" data-testid="unsaved-indicator">Unsaved changes</span>
		{/if}
	</div>

	<div class="editor-split" data-testid="editor-split">
		<div class="editor-pane edit-pane">
			<div class="pane-header">
				<span>Edit</span>
			</div>
			<textarea
				class="editor-textarea"
				value={content}
				oninput={handleInput}
				{placeholder}
				data-testid="editor-textarea"
			></textarea>
		</div>

		<div class="editor-pane preview-pane">
			<div class="pane-header">
				<span>Preview</span>
			</div>
			<div class="preview-content" data-testid="preview-content">
				<MarkdownViewer {content} />
			</div>
		</div>
	</div>
</div>

<style>
	.markdown-editor {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 400px;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow: hidden;
	}

	.editor-toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 1rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.toolbar-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.unsaved-indicator {
		font-size: 0.75rem;
		color: #f59e0b;
		background: #fef3c7;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
	}

	.editor-split {
		display: grid;
		grid-template-columns: 1fr 1fr;
		flex: 1;
		min-height: 0;
	}

	.editor-pane {
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.edit-pane {
		border-right: 1px solid #e2e8f0;
	}

	.pane-header {
		padding: 0.5rem 1rem;
		background: #f1f5f9;
		border-bottom: 1px solid #e2e8f0;
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.editor-textarea {
		flex: 1;
		padding: 1rem;
		border: none;
		resize: none;
		font-family: 'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace;
		font-size: 0.875rem;
		line-height: 1.6;
		color: #1e293b;
		background: white;
	}

	.editor-textarea:focus {
		outline: none;
	}

	.editor-textarea::placeholder {
		color: #94a3b8;
	}

	.preview-content {
		flex: 1;
		padding: 1rem;
		overflow-y: auto;
		background: white;
	}

	/* Responsive: stack on smaller screens */
	@media (max-width: 768px) {
		.editor-split {
			grid-template-columns: 1fr;
			grid-template-rows: 1fr 1fr;
		}

		.edit-pane {
			border-right: none;
			border-bottom: 1px solid #e2e8f0;
		}
	}
</style>
