<!--
  DiffViewer Component
  Issue #290: Requirements List and Version Management

  Displays diff between two text versions with highlighted additions and deletions.
-->
<script lang="ts">
	import type { DiffEntry } from '$lib/types/requirement';

	interface Props {
		diffs: DiffEntry[];
		fromVersion: number;
		toVersion: number;
		class?: string;
	}

	let { diffs, fromVersion, toVersion, class: className = '' }: Props = $props();

	/**
	 * Get CSS class for diff operation type.
	 */
	function getDiffClass(operation: -1 | 0 | 1): string {
		switch (operation) {
			case -1:
				return 'diff-deletion';
			case 1:
				return 'diff-insertion';
			default:
				return 'diff-equal';
		}
	}

	/**
	 * Get aria label for diff operation.
	 */
	function getAriaLabel(operation: -1 | 0 | 1): string {
		switch (operation) {
			case -1:
				return 'deleted';
			case 1:
				return 'added';
			default:
				return 'unchanged';
		}
	}
</script>

<div class="diff-viewer {className}" data-testid="diff-viewer">
	<div class="diff-header" data-testid="diff-header">
		<span class="diff-title">
			Comparing v{fromVersion} to v{toVersion}
		</span>
		<div class="diff-legend">
			<span class="legend-item deletion" data-testid="legend-deletion">
				<span class="legend-color"></span>
				Removed
			</span>
			<span class="legend-item insertion" data-testid="legend-insertion">
				<span class="legend-color"></span>
				Added
			</span>
		</div>
	</div>

	<div class="diff-content" data-testid="diff-content">
		{#each diffs as diff, index (index)}
			<span
				class="diff-segment {getDiffClass(diff.operation)}"
				aria-label={getAriaLabel(diff.operation)}
				data-testid="diff-segment-{index}"
				data-operation={diff.operation}>{diff.text}</span
			>
		{/each}
	</div>
</div>

<style>
	.diff-viewer {
		font-family: 'JetBrains Mono', 'Fira Code', 'Source Code Pro', monospace;
		font-size: 0.875rem;
		line-height: 1.5;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow: hidden;
	}

	.diff-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.diff-title {
		font-weight: 600;
		color: #1e293b;
	}

	.diff-legend {
		display: flex;
		gap: 1rem;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.75rem;
		color: #64748b;
	}

	.legend-color {
		width: 12px;
		height: 12px;
		border-radius: 2px;
	}

	.legend-item.deletion .legend-color {
		background: #fecaca;
		border: 1px solid #ef4444;
	}

	.legend-item.insertion .legend-color {
		background: #bbf7d0;
		border: 1px solid #22c55e;
	}

	.diff-content {
		padding: 1rem;
		background: white;
		white-space: pre-wrap;
		word-break: break-word;
		overflow-x: auto;
	}

	.diff-segment {
		display: inline;
	}

	.diff-segment.diff-equal {
		color: #1e293b;
	}

	.diff-segment.diff-deletion {
		background: #fecaca;
		color: #991b1b;
		text-decoration: line-through;
	}

	.diff-segment.diff-insertion {
		background: #bbf7d0;
		color: #166534;
	}
</style>
