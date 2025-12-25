<!--
  WorkflowViewer Component
  Issue #292: Review Page (JobVersion Detail)

  Displays YAML workflow content with syntax highlighting, copy, and collapse functionality.

  Props:
  - yaml: YAML string content to display
  - title: Title for the workflow section
  - collapsible: Whether the content can be collapsed (default: false)
  - collapsed: Initial collapsed state (default: false)
  - showLineNumbers: Whether to show line numbers (default: false)
-->
<script lang="ts">
	interface Props {
		yaml: string | null;
		title: string;
		collapsible?: boolean;
		collapsed?: boolean;
		showLineNumbers?: boolean;
	}

	let {
		yaml,
		title,
		collapsible = false,
		collapsed = false,
		showLineNumbers = false
	}: Props = $props();

	// Local toggle state, managed separately for user interaction
	let localCollapsed = $state<boolean | null>(null);

	// Effective collapsed state: use local state if set, otherwise use prop
	const isCollapsed = $derived(localCollapsed !== null ? localCollapsed : collapsed);

	let copyFeedback = $state(false);

	function toggleCollapse() {
		localCollapsed = !isCollapsed;
	}

	async function copyToClipboard() {
		if (!yaml) return;
		try {
			await navigator.clipboard.writeText(yaml);
			copyFeedback = true;
			setTimeout(() => {
				copyFeedback = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy:', error);
		}
	}

	const lines = $derived(yaml?.split('\n') || []);
</script>

<div class="workflow-viewer">
	<div class="header">
		<h4>{title}</h4>
		<div class="actions">
			{#if yaml}
				<button
					type="button"
					class="action-button"
					onclick={copyToClipboard}
					aria-label="Copy YAML to clipboard"
				>
					{#if copyFeedback}
						<span class="feedback">Copied!</span>
					{:else}
						<span>Copy</span>
					{/if}
				</button>
			{/if}
			{#if collapsible}
				<button
					type="button"
					class="action-button"
					onclick={toggleCollapse}
					aria-expanded={!isCollapsed}
					aria-label={isCollapsed ? 'Expand content' : 'Collapse content'}
				>
					{isCollapsed ? 'Show' : 'Hide'}
				</button>
			{/if}
		</div>
	</div>

	{#if !isCollapsed && yaml}
		<div class="content">
			<pre class="yaml-code"><code class="language-yaml"
					>{#each lines as line, lineIdx (lineIdx)}<span class="yaml-line"
							>{#if showLineNumbers}<span class="line-number">{lineIdx + 1}</span>{/if}{line}</span
						>
					{/each}</code
				></pre>
		</div>
	{:else if !yaml}
		<div class="empty-state">
			<p>No workflow content available.</p>
		</div>
	{/if}
</div>

<style>
	.workflow-viewer {
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

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
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

	.action-button:hover {
		background: #f1f5f9;
		color: #334155;
	}

	.feedback {
		color: #16a34a;
	}

	.content {
		padding: 0;
		position: relative;
	}

	.yaml-code {
		margin: 0;
		padding: 1rem;
		background: #1e293b;
		overflow-x: auto;
		font-size: 0.75rem;
		line-height: 1.6;
	}

	.yaml-code code {
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
		color: #e2e8f0;
		display: block;
		white-space: pre;
	}

	.line-number {
		display: inline-block;
		text-align: right;
		min-width: 2.5rem;
		margin-right: 1rem;
		padding-right: 0.75rem;
		border-right: 1px solid #475569;
		color: #64748b;
		user-select: none;
	}

	.line {
		/* Line content - inline display */
	}

	/* YAML syntax highlighting */
	.yaml-code :global(.yaml-key) {
		color: #38bdf8;
	}

	.yaml-code :global(.yaml-string) {
		color: #4ade80;
	}

	.yaml-code :global(.yaml-number) {
		color: #fb923c;
	}

	.yaml-code :global(.yaml-literal) {
		color: #c084fc;
	}

	.yaml-code :global(.yaml-comment) {
		color: #64748b;
		font-style: italic;
	}

	.empty-state {
		padding: 2rem;
		text-align: center;
	}

	.empty-state p {
		margin: 0;
		color: #94a3b8;
		font-size: 0.875rem;
	}
</style>
