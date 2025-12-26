<!--
  CollapsibleInterface Component
  Issue #310: Interface flow display

  Displays a JSON Schema interface definition with collapsible toggle.
  Used to show input/output interfaces between tasks in the workflow.

  Props:
  - schema: JSON Schema object to display
  - title: Title for the interface section (e.g., "Input Interface", "Task 1 → Task 2")
  - collapsed: Initial collapsed state (default: true)
  - variant: Visual variant - "input" (green) or "output" (blue)
-->
<script lang="ts">
	import { formatJson } from '$lib/utils';

	interface Props {
		schema: Record<string, unknown> | null;
		title: string;
		collapsed?: boolean;
		variant?: 'input' | 'output';
	}

	let { schema, title, collapsed = true, variant = 'output' }: Props = $props();

	let isCollapsed = $state(collapsed);
	let copyFeedback = $state(false);

	function toggle() {
		isCollapsed = !isCollapsed;
	}

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
	const hasSchema = $derived(schema && Object.keys(schema).length > 0);
</script>

<div class="collapsible-interface" class:input={variant === 'input'} class:output={variant === 'output'}>
	<button
		type="button"
		class="toggle-header"
		onclick={toggle}
		aria-expanded={!isCollapsed}
		aria-label={isCollapsed ? `Show ${title}` : `Hide ${title}`}
	>
		<span class="connector-line" aria-hidden="true"></span>
		<span class="toggle-icon" aria-hidden="true">{isCollapsed ? '▶' : '▼'}</span>
		<span class="title">{title}</span>
		{#if hasSchema}
			<span class="schema-hint">
				{#if schema?.properties}
					{Object.keys(schema.properties).length} properties
				{/if}
			</span>
		{:else}
			<span class="schema-hint empty">empty</span>
		{/if}
	</button>

	{#if !isCollapsed && hasSchema}
		<div class="content">
			<div class="content-header">
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
			<pre class="json-code"><code class="language-json">{formattedJson}</code></pre>
		</div>
	{/if}
</div>

<style>
	.collapsible-interface {
		position: relative;
		margin: 0.5rem 0 0.5rem 1.25rem;
		padding-left: 1.5rem;
	}

	.connector-line {
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		background: #e2e8f0;
	}

	.collapsible-interface.input .connector-line {
		background: #86efac;
	}

	.collapsible-interface.output .connector-line {
		background: #93c5fd;
	}

	.toggle-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.5rem 0.75rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.8125rem;
		color: #475569;
		cursor: pointer;
		transition: all 0.15s;
		text-align: left;
	}

	.toggle-header:hover {
		background: #f1f5f9;
		border-color: #cbd5e1;
	}

	.collapsible-interface.input .toggle-header {
		border-left: 3px solid #22c55e;
	}

	.collapsible-interface.output .toggle-header {
		border-left: 3px solid #3b82f6;
	}

	.toggle-icon {
		font-size: 0.625rem;
		color: #94a3b8;
		transition: transform 0.15s;
	}

	.title {
		font-weight: 500;
		color: #334155;
	}

	.schema-hint {
		margin-left: auto;
		font-size: 0.6875rem;
		color: #94a3b8;
	}

	.schema-hint.empty {
		font-style: italic;
	}

	.content {
		margin-top: 0.5rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow: hidden;
		background: white;
	}

	.content-header {
		display: flex;
		justify-content: flex-end;
		padding: 0.5rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.copy-button {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.5rem;
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

	.json-code {
		margin: 0;
		padding: 0.75rem;
		background: #fafafa;
		overflow-x: auto;
		font-size: 0.6875rem;
		line-height: 1.5;
	}

	.json-code code {
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
		color: #334155;
	}
</style>
