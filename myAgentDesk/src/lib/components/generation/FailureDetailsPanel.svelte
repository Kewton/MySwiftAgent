<!--
  FailureDetailsPanel Component
  Issue #305: Task Workflow Traces Summary Feature

  Displays failure details:
  - Failure stage badge
  - Error summary card
  - Cause analysis card (if available)
  - Recommendations list
  - Retry history timeline
-->
<script lang="ts">
	import type { FailureDetails } from '$lib/types/workflow-summary';
	import { FAILURE_STAGE_CONFIG } from '$lib/types/workflow-summary';

	interface Props {
		failureDetails: FailureDetails;
	}

	let { failureDetails }: Props = $props();

	const stageConfig = $derived(FAILURE_STAGE_CONFIG[failureDetails.failure_stage]);

	function formatTimestamp(timestamp: string): string {
		try {
			const date = new Date(timestamp);
			return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
		} catch {
			return timestamp;
		}
	}
</script>

<section class="failure-panel" aria-label="Failure Details">
	<!-- Failure Stage Badge -->
	<div class="stage-header">
		<span class="stage-badge stage-{stageConfig.color}">
			{failureDetails.failure_stage}
		</span>
		<span class="stage-description">{stageConfig.description}</span>
	</div>

	<!-- Error Summary Card -->
	<div class="error-summary card">
		<h4>Error Summary</h4>
		{#if failureDetails.error_summary.http_status !== null}
			<div class="error-row">
				<span class="error-label">HTTP Status:</span>
				<span class="error-value status-{failureDetails.error_summary.http_status >= 500 ? 'server' : 'client'}">
					{failureDetails.error_summary.http_status}
				</span>
			</div>
		{/if}
		{#if failureDetails.error_summary.error_code}
			<div class="error-row">
				<span class="error-label">Error Code:</span>
				<span class="error-value code">{failureDetails.error_summary.error_code}</span>
			</div>
		{/if}
		<div class="error-row">
			<span class="error-label">Message:</span>
			<span class="error-value message">{failureDetails.error_summary.error_message}</span>
		</div>
		{#if failureDetails.error_summary.error_detail}
			<div class="error-detail">
				{failureDetails.error_summary.error_detail}
			</div>
		{/if}
	</div>

	<!-- Cause Analysis Card -->
	{#if failureDetails.cause_analysis}
		<div class="cause-analysis card">
			<h4>Cause Analysis</h4>
			<div class="cause-row">
				<span class="cause-label">Category:</span>
				<span class="cause-value">{failureDetails.cause_analysis.category}</span>
			</div>
			{#if failureDetails.cause_analysis.problem_location}
				<div class="cause-row">
					<span class="cause-label">Problem Location:</span>
					<span class="cause-value location">{failureDetails.cause_analysis.problem_location}</span>
				</div>
			{/if}
			{#if failureDetails.cause_analysis.problem_field}
				<div class="cause-row">
					<span class="cause-label">Problem Field:</span>
					<span class="cause-value field">{failureDetails.cause_analysis.problem_field}</span>
				</div>
			{/if}
			{#if failureDetails.cause_analysis.actual_value}
				<div class="cause-row">
					<span class="cause-label">Actual Value:</span>
					<span class="cause-value actual">{failureDetails.cause_analysis.actual_value}</span>
				</div>
			{/if}
			{#if failureDetails.cause_analysis.expected_value}
				<div class="cause-row">
					<span class="cause-label">Expected Value:</span>
					<span class="cause-value expected">{failureDetails.cause_analysis.expected_value}</span>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Recommendations List -->
	{#if failureDetails.recommendations.length > 0}
		<div class="recommendations card">
			<h4>Recommendations</h4>
			<ul role="list" aria-label="Recommendations">
				{#each failureDetails.recommendations as recommendation, i}
					<li>
						<span class="rec-number">{i + 1}.</span>
						{recommendation}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Retry History Timeline -->
	{#if failureDetails.retry_history.length > 0}
		<div class="retry-history card">
			<h4>Retry History ({failureDetails.retry_history.length} attempts)</h4>
			<div class="timeline">
				{#each failureDetails.retry_history as entry}
					<div class="timeline-entry">
						<div class="timeline-marker">
							<span class="attempt-number">{entry.attempt}</span>
						</div>
						<div class="timeline-content">
							<div class="timeline-header">
								<span class="model-name">{entry.model_used ?? 'Unknown model'}</span>
								<span class="timestamp">{formatTimestamp(entry.timestamp)}</span>
							</div>
							<div class="timeline-message">{entry.error_message}</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</section>

<style>
	.failure-panel {
		padding: 1rem;
		background: #fef2f2;
		border-radius: 0.5rem;
		border: 1px solid #fecaca;
	}

	.stage-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 1rem;
	}

	.stage-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 600;
		border-radius: 0.25rem;
		text-transform: lowercase;
	}

	.stage-red {
		background: #fee2e2;
		color: #dc2626;
	}

	.stage-orange {
		background: #fed7aa;
		color: #c2410c;
	}

	.stage-yellow {
		background: #fef3c7;
		color: #92400e;
	}

	.stage-description {
		font-size: 0.8125rem;
		color: #64748b;
	}

	.card {
		background: white;
		padding: 0.75rem;
		border-radius: 0.375rem;
		margin-bottom: 0.75rem;
		border: 1px solid #e2e8f0;
	}

	.card h4 {
		margin: 0 0 0.5rem 0;
		font-size: 0.75rem;
		color: #64748b;
		font-weight: 600;
		text-transform: uppercase;
	}

	/* Error Summary */
	.error-row {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
		font-size: 0.8125rem;
	}

	.error-label {
		color: #64748b;
		min-width: 80px;
	}

	.error-value {
		color: #334155;
		font-weight: 500;
	}

	.error-value.status-client {
		color: #c2410c;
	}

	.error-value.status-server {
		color: #dc2626;
	}

	.error-value.code {
		font-family: monospace;
		background: #f1f5f9;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
	}

	.error-detail {
		margin-top: 0.5rem;
		padding: 0.5rem;
		background: #f8fafc;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		color: #475569;
		font-family: monospace;
		white-space: pre-wrap;
		word-break: break-word;
	}

	/* Cause Analysis */
	.cause-row {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
		font-size: 0.8125rem;
	}

	.cause-label {
		color: #64748b;
		min-width: 110px;
	}

	.cause-value {
		color: #334155;
	}

	.cause-value.location,
	.cause-value.field {
		font-family: monospace;
		background: #f1f5f9;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
	}

	.cause-value.actual {
		color: #dc2626;
		font-family: monospace;
	}

	.cause-value.expected {
		color: #16a34a;
		font-family: monospace;
	}

	/* Recommendations */
	.recommendations ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.recommendations li {
		display: flex;
		gap: 0.5rem;
		font-size: 0.8125rem;
		color: #334155;
		margin-bottom: 0.375rem;
		line-height: 1.4;
	}

	.rec-number {
		color: #1e40af;
		font-weight: 600;
		flex-shrink: 0;
	}

	/* Retry History */
	.timeline {
		position: relative;
		padding-left: 1.5rem;
	}

	.timeline::before {
		content: '';
		position: absolute;
		left: 0.5rem;
		top: 0;
		bottom: 0;
		width: 2px;
		background: #e2e8f0;
	}

	.timeline-entry {
		position: relative;
		margin-bottom: 0.75rem;
	}

	.timeline-entry:last-child {
		margin-bottom: 0;
	}

	.timeline-marker {
		position: absolute;
		left: -1.5rem;
		width: 1rem;
		height: 1rem;
		background: #fee2e2;
		border: 2px solid #fca5a5;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.attempt-number {
		font-size: 0.625rem;
		font-weight: 700;
		color: #dc2626;
	}

	.timeline-content {
		background: #f8fafc;
		padding: 0.5rem;
		border-radius: 0.25rem;
	}

	.timeline-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.25rem;
	}

	.model-name {
		font-size: 0.75rem;
		font-weight: 600;
		color: #475569;
	}

	.timestamp {
		font-size: 0.625rem;
		color: #94a3b8;
	}

	.timeline-message {
		font-size: 0.75rem;
		color: #64748b;
	}
</style>
