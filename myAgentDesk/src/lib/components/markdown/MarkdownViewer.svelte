<!--
  MarkdownViewer Component
  Issue #290: Requirements List and Version Management

  Renders Markdown content to HTML with XSS protection.
  Uses DOMPurify for sanitization (client-side only).
-->
<script lang="ts">
	import { browser } from '$app/environment';
	import { marked } from 'marked';
	import { DOMPURIFY_CONFIG, MARKED_OPTIONS } from './utils';

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	let renderedHtml = $state('');
	let isLoading = $state(true);
	let DOMPurify: typeof import('dompurify').default | null = null;

	// Configure marked for GFM support
	marked.setOptions(MARKED_OPTIONS);

	/**
	 * Renders markdown to sanitized HTML.
	 * Returns empty string on server-side rendering.
	 */
	async function renderMarkdown(markdown: string): Promise<string> {
		if (!browser) {
			return '';
		}

		// Dynamically import DOMPurify only on client-side
		if (!DOMPurify) {
			const module = await import('dompurify');
			DOMPurify = module.default;
		}

		// Parse markdown to HTML
		const rawHtml = await marked.parse(markdown);

		// Sanitize HTML to prevent XSS attacks
		return DOMPurify.sanitize(rawHtml, DOMPURIFY_CONFIG);
	}

	// Update rendered HTML when content changes (reactive to content prop)
	$effect(() => {
		if (browser) {
			// Capture content value for the async operation
			const currentContent = content;
			renderMarkdown(currentContent).then((html) => {
				renderedHtml = html;
				isLoading = false;
			});
		}
	});
</script>

<div class="markdown-viewer {className}" data-testid="markdown-viewer">
	{#if browser && !isLoading}
		<!-- eslint-disable-next-line svelte/no-at-html-tags -- Content is sanitized with DOMPurify -->
		{@html renderedHtml}
	{:else}
		<div class="loading" data-testid="markdown-loading">Loading...</div>
	{/if}
</div>

<style>
	.markdown-viewer {
		font-size: 0.9375rem;
		line-height: 1.6;
		color: #1e293b;
	}

	.markdown-viewer :global(h1) {
		font-size: 1.5rem;
		font-weight: 700;
		margin: 1.5rem 0 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.markdown-viewer :global(h2) {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 1.25rem 0 0.75rem;
	}

	.markdown-viewer :global(h3) {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 1rem 0 0.5rem;
	}

	.markdown-viewer :global(h4),
	.markdown-viewer :global(h5),
	.markdown-viewer :global(h6) {
		font-size: 1rem;
		font-weight: 600;
		margin: 0.75rem 0 0.5rem;
	}

	.markdown-viewer :global(p) {
		margin: 0 0 1rem;
	}

	.markdown-viewer :global(ul),
	.markdown-viewer :global(ol) {
		margin: 0 0 1rem;
		padding-left: 1.5rem;
	}

	.markdown-viewer :global(li) {
		margin: 0.25rem 0;
	}

	.markdown-viewer :global(code) {
		font-family: 'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace;
		font-size: 0.875em;
		padding: 0.125rem 0.25rem;
		background: #f1f5f9;
		border-radius: 0.25rem;
	}

	.markdown-viewer :global(pre) {
		margin: 0 0 1rem;
		padding: 1rem;
		background: #1e293b;
		border-radius: 0.375rem;
		overflow-x: auto;
	}

	.markdown-viewer :global(pre code) {
		padding: 0;
		background: transparent;
		color: #e2e8f0;
	}

	.markdown-viewer :global(blockquote) {
		margin: 0 0 1rem;
		padding: 0.5rem 1rem;
		border-left: 4px solid #3b82f6;
		background: #f8fafc;
		color: #64748b;
	}

	.markdown-viewer :global(a) {
		color: #3b82f6;
		text-decoration: none;
	}

	.markdown-viewer :global(a:hover) {
		text-decoration: underline;
	}

	.markdown-viewer :global(table) {
		width: 100%;
		margin: 0 0 1rem;
		border-collapse: collapse;
	}

	.markdown-viewer :global(th),
	.markdown-viewer :global(td) {
		padding: 0.5rem 0.75rem;
		border: 1px solid #e2e8f0;
		text-align: left;
	}

	.markdown-viewer :global(th) {
		background: #f8fafc;
		font-weight: 600;
	}

	.markdown-viewer :global(hr) {
		margin: 1.5rem 0;
		border: none;
		border-top: 1px solid #e2e8f0;
	}

	.markdown-viewer :global(img) {
		max-width: 100%;
		height: auto;
		border-radius: 0.375rem;
	}

	.loading {
		color: #94a3b8;
		font-style: italic;
	}
</style>
