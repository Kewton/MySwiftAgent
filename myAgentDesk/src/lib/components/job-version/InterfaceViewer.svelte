<!--
  InterfaceViewer Component
  Issue #292: Review Page (JobVersion Detail)

  Displays a JSON Schema interface definition with syntax highlighting and copy functionality.

  Props:
  - schema: JSON Schema object to display
  - title: Title for the interface section
-->
<script lang="ts">
	import { formatJson } from '$lib/utils';

	interface Props {
		schema: Record<string, unknown> | null;
		title: string;
	}

	let { schema, title }: Props = $props();

	let copyFeedback = $state(false);

	async function copyToClipboard() {
		try {
			const content = formatJson(schema, '{}');
			await navigator.clipboard.writeText(content);
			copyFeedback = true;
			setTimeout(() => {
				copyFeedback = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy:', error);
		}
	}

	const formattedJson = $derived(formatJson(schema, '{}'));
</script>

<div class="interface-viewer">
	<div class="header">
		<h4>{title}</h4>
		<button
			type="button"
			class="copy-button"
			onclick={copyToClipboard}
			aria-label="Copy JSON to clipboard"
		>
			{#if copyFeedback}
				<span class="feedback">Copied!</span>
			{:else}
				<span class="copy-text">Copy</span>
			{/if}
		</button>
	</div>

	<div class="content">
		<pre class="json-code"><code class="language-json">{formattedJson}</code></pre>
	</div>
</div>

<style>
	.interface-viewer {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		overflow: hidden;
		background: white;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #334155;
	}

	.copy-button {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.625rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.6875rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		transition: all 0.15s;
	}

	.copy-button:hover {
		background: #f1f5f9;
		color: #334155;
	}

	.feedback {
		color: #16a34a;
	}

	.content {
		padding: 0;
	}

	.json-code {
		margin: 0;
		padding: 1rem;
		background: #fafafa;
		overflow-x: auto;
		font-size: 0.75rem;
		line-height: 1.6;
	}

	.json-code code {
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
		color: #334155;
	}

	/* Basic JSON syntax highlighting without external library */
	.json-code code :global(.hljs-string) {
		color: #059669;
	}

	.json-code code :global(.hljs-number) {
		color: #d97706;
	}

	.json-code code :global(.hljs-literal) {
		color: #8b5cf6;
	}

	.json-code code :global(.hljs-attr) {
		color: #0369a1;
	}
</style>
