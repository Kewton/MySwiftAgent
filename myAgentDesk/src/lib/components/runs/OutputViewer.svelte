<!--
  OutputViewer Component
  Issue #293: Runs Screen - Task Output Display

  Displays JSON output/input data with copy and download functionality.
  Supports formatted and raw display modes.

  Props:
  - data: JSON data to display (Record<string, unknown> or null)
  - title: Title for the viewer section
  - taskId: Task ID for download filename
  - type: 'input' | 'output' for filename prefix
-->
<script lang="ts">
	interface Props {
		data: Record<string, unknown> | null;
		title: string;
		taskId?: string;
		type?: 'input' | 'output';
	}

	let { data, title, taskId = 'task', type = 'output' }: Props = $props();

	type DisplayMode = 'formatted' | 'raw';
	let displayMode = $state<DisplayMode>('formatted');
	let copyFeedback = $state(false);

	const formattedData = $derived(() => {
		if (!data) return 'No data available';
		try {
			if (displayMode === 'raw') {
				return JSON.stringify(data);
			}
			return JSON.stringify(data, null, 2);
		} catch {
			return 'Invalid JSON data';
		}
	});

	async function copyToClipboard() {
		if (!data) return;
		try {
			await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
			copyFeedback = true;
			setTimeout(() => {
				copyFeedback = false;
			}, 2000);
		} catch (error) {
			console.error('Failed to copy:', error);
		}
	}

	function downloadAsJson() {
		if (!data) return;
		try {
			const jsonString = JSON.stringify(data, null, 2);
			const blob = new Blob([jsonString], { type: 'application/json' });
			const url = URL.createObjectURL(blob);

			const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
			const filename = `${taskId}_${type}_${timestamp}.json`;

			const link = document.createElement('a');
			link.href = url;
			link.download = filename;
			document.body.appendChild(link);
			link.click();
			document.body.removeChild(link);
			URL.revokeObjectURL(url);
		} catch (error) {
			console.error('Failed to download:', error);
		}
	}

	function toggleDisplayMode() {
		displayMode = displayMode === 'formatted' ? 'raw' : 'formatted';
	}
</script>

<div class="output-viewer" class:no-data={!data}>
	<div class="header">
		<h4>{title}</h4>
		{#if data}
			<div class="actions">
				<button
					type="button"
					class="mode-toggle"
					onclick={toggleDisplayMode}
					aria-label="Toggle display mode"
				>
					{displayMode === 'formatted' ? 'Raw' : 'Format'}
				</button>
				<button
					type="button"
					class="action-button"
					onclick={copyToClipboard}
					aria-label="Copy to clipboard"
				>
					{#if copyFeedback}
						<span class="feedback">Copied!</span>
					{:else}
						Copy
					{/if}
				</button>
				<button
					type="button"
					class="action-button download"
					onclick={downloadAsJson}
					aria-label="Download as JSON"
				>
					Download
				</button>
			</div>
		{/if}
	</div>

	<div class="content">
		{#if data}
			<pre class="json-code" class:raw={displayMode === 'raw'}><code>{formattedData()}</code></pre>
		{:else}
			<div class="no-data-message">No data available</div>
		{/if}
	</div>
</div>

<style>
	.output-viewer {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		overflow: hidden;
		background: white;
	}

	.output-viewer.no-data {
		background: #fafafa;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.625rem 0.875rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
		gap: 0.5rem;
	}

	h4 {
		margin: 0;
		font-size: 0.8125rem;
		font-weight: 600;
		color: #334155;
	}

	.actions {
		display: flex;
		gap: 0.375rem;
	}

	.action-button,
	.mode-toggle {
		display: inline-flex;
		align-items: center;
		padding: 0.1875rem 0.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.625rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		transition: all 0.15s;
	}

	.action-button:hover,
	.mode-toggle:hover {
		background: #f1f5f9;
		color: #334155;
	}

	.action-button.download {
		background: #f0f9ff;
		border-color: #bae6fd;
		color: #0369a1;
	}

	.action-button.download:hover {
		background: #e0f2fe;
	}

	.feedback {
		color: #16a34a;
	}

	.content {
		padding: 0;
	}

	.json-code {
		margin: 0;
		padding: 0.75rem;
		background: #fafafa;
		overflow-x: auto;
		font-size: 0.6875rem;
		line-height: 1.6;
		max-height: 400px;
		overflow-y: auto;
	}

	.json-code.raw {
		white-space: pre-wrap;
		word-break: break-all;
	}

	.json-code code {
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
		color: #334155;
	}

	.no-data-message {
		padding: 1.5rem;
		text-align: center;
		font-size: 0.8125rem;
		color: #94a3b8;
		font-style: italic;
	}
</style>
