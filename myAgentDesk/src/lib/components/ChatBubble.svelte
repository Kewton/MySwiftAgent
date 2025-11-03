<script lang="ts">
	import 'highlight.js/styles/github-dark.css';
	import { renderMarkdown } from '$lib/utils/markdown';

	export let role: 'user' | 'assistant' = 'user';
	export let message: string;
	export let timestamp: string = '';

	const roleIcon: Record<typeof role, string> = {
		user: '',
		assistant: '🔥'
	};

	$: isUser = role === 'user';
	$: bubbleClasses = `chat-bubble max-w-3xl ${isUser ? 'ml-auto bg-primary-50 dark:bg-primary-900/20 text-right' : 'assistant-bubble w-full'}`;
	$: wrapperClasses = `mb-4 flex ${isUser ? 'justify-end' : 'justify-start w-full'}`;
	$: contentLayoutClasses = `flex gap-3 items-start ${isUser ? 'flex-row-reverse text-right' : 'text-left'}`;
	$: renderedMessage = isUser ? message : renderMarkdown(message);
	$: timestampClasses = `text-xs text-gray-500 dark:text-gray-400 mt-2 ${isUser ? 'text-right' : 'text-left'}`;
</script>

<div class={wrapperClasses}>
	<div class={bubbleClasses}>
		<div class={contentLayoutClasses}>
			{#if roleIcon[role]}
				<span class="text-xl flex-shrink-0">{roleIcon[role]}</span>
			{/if}
			{#if isUser}
				<div class="text-sm text-gray-900 dark:text-white whitespace-pre-wrap">
					{message}
				</div>
			{:else}
				<div class="markdown-content text-sm text-gray-900 dark:text-white">
					<!-- eslint-disable-next-line svelte/no-at-html-tags -->
					{@html renderedMessage}
				</div>
			{/if}
		</div>
		{#if timestamp}
			<div class={timestampClasses}>
				{timestamp}
			</div>
		{/if}
	</div>
</div>

<style>
	/* Markdown スタイリング */
	:global(.markdown-content) {
		line-height: 1.6;
	}

	:global(.markdown-content p) {
		margin-bottom: 0.75rem;
	}

	:global(.markdown-content p:last-child) {
		margin-bottom: 0;
	}

	:global(.markdown-content code) {
		background: #f5f5f5;
		padding: 2px 6px;
		border-radius: 3px;
		font-family: 'Monaco', 'Courier New', monospace;
		font-size: 0.9em;
	}

	:global(.dark .markdown-content code) {
		background: #2d2d2d;
	}

	:global(.markdown-content pre) {
		background: #f6f8fa;
		padding: 12px;
		border-radius: 6px;
		overflow-x: auto;
		margin: 0.75rem 0;
	}

	:global(.dark .markdown-content pre) {
		background: #1e1e1e;
	}

	:global(.markdown-content pre code) {
		background: transparent;
		padding: 0;
		border-radius: 0;
	}

	:global(.markdown-content ul),
	:global(.markdown-content ol) {
		margin-left: 1.5rem;
		margin-bottom: 0.75rem;
	}

	:global(.markdown-content li) {
		margin-bottom: 0.25rem;
	}

	:global(.markdown-content strong) {
		font-weight: 600;
	}

	:global(.markdown-content em) {
		font-style: italic;
	}

	:global(.markdown-content blockquote) {
		border-left: 4px solid #ddd;
		padding-left: 1rem;
		color: #666;
		margin: 0.75rem 0;
	}

	:global(.dark .markdown-content blockquote) {
		border-left-color: #555;
		color: #aaa;
	}

	:global(.markdown-content h1),
	:global(.markdown-content h2),
	:global(.markdown-content h3) {
		font-weight: 600;
		margin-top: 1rem;
		margin-bottom: 0.5rem;
	}

	:global(.markdown-content h1) {
		font-size: 1.5em;
	}

	:global(.markdown-content h2) {
		font-size: 1.3em;
	}

	:global(.markdown-content h3) {
		font-size: 1.1em;
	}

	:global(.markdown-content a) {
		color: #667eea;
		text-decoration: underline;
	}

	:global(.markdown-content a:hover) {
		color: #5568d3;
	}

	:global(.markdown-content table) {
		border-collapse: collapse;
		width: 100%;
		margin: 0.75rem 0;
	}

	:global(.markdown-content th),
	:global(.markdown-content td) {
		border: 1px solid #ddd;
		padding: 0.5rem;
		text-align: left;
	}

	:global(.dark .markdown-content th),
	:global(.dark .markdown-content td) {
		border-color: #444;
	}

	:global(.markdown-content th) {
		background: #f5f5f5;
		font-weight: 600;
	}

	:global(.dark .markdown-content th) {
		background: #2d2d2d;
	}
</style>
