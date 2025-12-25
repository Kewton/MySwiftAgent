<!--
  GenerationSummary Component
  Issue #305: Workflow Generation Progress Display

  Displays summary after generation completes.

  Props:
  - totalTasks: Total number of tasks
  - successCount: Number of successfully generated workflows
  - failedCount: Number of failed workflows
  - traceId: Optional Langfuse trace ID for link
-->
<script lang="ts">
	interface Props {
		totalTasks: number;
		successCount: number;
		failedCount: number;
		traceId?: string | null;
	}

	let { totalTasks, successCount, failedCount, traceId = null }: Props = $props();
</script>

<div class="completion-section" role="region" aria-label="Generation summary">
	<h4 class="section-header">
		<span class="section-icon" aria-hidden="true">2</span>
		Generation Summary
	</h4>
	<div class="summary-content">
		<div class="summary-stats">
			<div class="stat success">
				<span class="stat-value">{successCount}</span>
				<span class="stat-label">Workflow Generated</span>
			</div>
			{#if failedCount > 0}
				<div class="stat failed">
					<span class="stat-value">{failedCount}</span>
					<span class="stat-label">Failed</span>
				</div>
			{/if}
			<div class="stat total">
				<span class="stat-value">{totalTasks}</span>
				<span class="stat-label">Total Tasks</span>
			</div>
		</div>
		{#if traceId}
			<a
				href="http://localhost:3001/trace/{traceId}"
				target="_blank"
				rel="noopener noreferrer"
				class="trace-link"
			>
				View in Langfuse ({traceId})
			</a>
		{/if}
	</div>
</div>

<style>
	.completion-section {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.section-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
	}

	.section-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		background: #3b82f6;
		color: white;
		border-radius: 50%;
		font-size: 0.6875rem;
		font-weight: 700;
	}

	.summary-content {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.summary-stats {
		display: flex;
		gap: 1.5rem;
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.75rem;
		color: #64748b;
	}

	.stat.success .stat-value {
		color: #10b981;
	}

	.stat.failed .stat-value {
		color: #ef4444;
	}

	.stat.total .stat-value {
		color: #1e293b;
	}

	.trace-link {
		font-size: 0.875rem;
		color: #3b82f6;
		text-decoration: none;
	}

	.trace-link:hover {
		text-decoration: underline;
	}
</style>
