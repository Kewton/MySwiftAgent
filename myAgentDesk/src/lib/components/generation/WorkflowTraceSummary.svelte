<!--
  WorkflowTraceSummary Component
  Issue #305: Task Workflow Traces Summary Feature

  Main component for displaying workflow generation summary:
  - Compact view by default (status badge, score, time, retry count)
  - Expands to show full details on click
  - For success: shows YAML preview, test data, evaluation details
  - For failure: shows FailureDetailsPanel
-->
<script lang="ts">
	import type { WorkflowStatusItemExtended } from '$lib/types/workflow-summary';
	import { getScoreRange } from '$lib/types/workflow-summary';
	import WorkflowStatusBadge from './WorkflowStatusBadge.svelte';
	import EvaluationDetailsPanel from './EvaluationDetailsPanel.svelte';
	import FailureDetailsPanel from './FailureDetailsPanel.svelte';

	interface Props {
		workflowStatus: WorkflowStatusItemExtended;
		expanded?: boolean;
	}

	let { workflowStatus, expanded = false }: Props = $props();

	// Use the expanded prop directly - the warning can be safely ignored
	// as we intentionally only use it as the initial value
	let isExpanded = $state(false);
	let showFullYaml = $state(false);

	// Initialize from prop
	$effect(() => {
		if (expanded) {
			isExpanded = true;
		}
	});

	// Check if YAML is truncated (has full content longer than preview)
	const isYamlTruncated = $derived(
		workflowStatus.summary?.yaml_content &&
			workflowStatus.summary?.yaml_preview &&
			workflowStatus.summary.yaml_content.length > workflowStatus.summary.yaml_preview.length
	);

	// Get the YAML to display based on state
	const displayYaml = $derived(
		showFullYaml
			? workflowStatus.summary?.yaml_content ?? workflowStatus.summary?.yaml_preview
			: workflowStatus.summary?.yaml_preview
	);

	const score = $derived(workflowStatus.summary?.evaluation?.score ?? null);
	const scoreRange = $derived(getScoreRange(score));
	const hasDetails = $derived(workflowStatus.summary !== null);
	const retryCount = $derived(workflowStatus.summary?.retry_info?.retry_count ?? 0);
	const langfuseUrl = $derived(
		workflowStatus.langfuse_trace_id
			? `http://localhost:3001/trace/${workflowStatus.langfuse_trace_id}`
			: null
	);

	function formatTime(ms: number | null): string {
		if (ms === null) return '--';
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function formatJson(data: Record<string, unknown> | null): string {
		if (data === null) return '';
		return JSON.stringify(data, null, 2);
	}

	function toggleExpand() {
		isExpanded = !isExpanded;
	}
</script>

<article class="workflow-summary" class:expanded={isExpanded}>
	<!-- Compact Header -->
	<div class="summary-header">
		<div class="task-info">
			<span class="task-name">{workflowStatus.task_name ?? workflowStatus.task_id}</span>
			<WorkflowStatusBadge
				status={workflowStatus.status}
				workflowName={workflowStatus.workflow_name}
				errorMessage={workflowStatus.error_message}
			/>
		</div>

		<div class="summary-metrics">
			<!-- Score badge (success only) -->
			{#if workflowStatus.status === 'success' && score !== null}
				<span class="score-badge score-{scoreRange?.color ?? 'unknown'}">{score}</span>
			{/if}

			<!-- Generation time -->
			<span class="metric time">{formatTime(workflowStatus.generation_time_ms)}</span>

			<!-- Retry count -->
			{#if retryCount > 0}
				<span class="metric retry">{retryCount}</span>
			{/if}

			<!-- Langfuse trace link -->
			{#if langfuseUrl}
				<a href={langfuseUrl} target="_blank" rel="noopener noreferrer" class="trace-link" aria-label="View trace in Langfuse">
					Trace
				</a>
			{/if}

			<!-- Expand/Collapse button -->
			{#if hasDetails}
				<button
					class="expand-btn"
					onclick={toggleExpand}
					aria-expanded={isExpanded}
					aria-label={isExpanded ? 'Hide details' : 'Show details'}
				>
					{isExpanded ? 'Hide' : 'Show'}
				</button>
			{/if}
		</div>
	</div>

	<!-- Expanded Details -->
	{#if isExpanded && workflowStatus.summary}
		<div class="summary-details">
			<!-- YAML Preview / Full -->
			{#if displayYaml}
				<div class="detail-section yaml-section">
					<div class="section-header">
						<h4>Generated Workflow YAML</h4>
						{#if isYamlTruncated}
							<button
								class="yaml-toggle-btn"
								onclick={() => (showFullYaml = !showFullYaml)}
								aria-label={showFullYaml ? 'Show preview' : 'Show full YAML'}
							>
								{showFullYaml ? 'Show Preview' : 'Show Full'}
							</button>
						{/if}
					</div>
					<pre class="yaml-preview" class:yaml-full={showFullYaml}><code>{displayYaml}</code></pre>
					{#if !showFullYaml && isYamlTruncated}
						<div class="yaml-truncated-hint">
							... (truncated - click "Show Full" to see complete YAML)
						</div>
					{/if}
				</div>
			{/if}

			<!-- Test Data -->
			{#if workflowStatus.summary.sample_input}
				<div class="detail-section test-data-section">
					<h4>Test Data (sample_input)</h4>
					<pre class="test-data"><code>{formatJson(workflowStatus.summary.sample_input)}</code></pre>
				</div>
			{/if}

			<!-- Test Result -->
			{#if workflowStatus.summary.test_result}
				<div class="detail-section test-result-section">
					<h4>Test Execution</h4>
					<div class="test-result">
						<span class="result-item">
							<span class="result-label">HTTP Status:</span>
							<span class="result-value status-{workflowStatus.summary.test_result.http_status === 200 ? 'success' : 'error'}">
								{workflowStatus.summary.test_result.http_status ?? '--'}
							</span>
						</span>
						<span class="result-item">
							<span class="result-label">Valid:</span>
							<span class="result-value {workflowStatus.summary.test_result.is_valid ? 'valid' : 'invalid'}">
								{workflowStatus.summary.test_result.is_valid ? 'Yes' : 'No'}
							</span>
						</span>
						{#if workflowStatus.summary.test_result.execution_time_ms}
							<span class="result-item">
								<span class="result-label">Time:</span>
								<span class="result-value">{formatTime(workflowStatus.summary.test_result.execution_time_ms)}</span>
							</span>
						{/if}
					</div>
					{#if workflowStatus.summary.test_result.validation_errors.length > 0}
						<div class="validation-errors">
							<span class="errors-label">Validation Errors:</span>
							<ul>
								{#each workflowStatus.summary.test_result.validation_errors as error}
									<li>{error}</li>
								{/each}
							</ul>
						</div>
					{/if}
				</div>
			{/if}

			<!-- Evaluation Details (success) -->
			{#if workflowStatus.status === 'success' && workflowStatus.summary.evaluation}
				<div class="detail-section evaluation-section">
					<EvaluationDetailsPanel evaluation={workflowStatus.summary.evaluation} />
				</div>
			{/if}

			<!-- Failure Details (failed) -->
			{#if workflowStatus.status === 'failed' && workflowStatus.summary.failure_details}
				<div class="detail-section failure-section">
					<FailureDetailsPanel failureDetails={workflowStatus.summary.failure_details} />
				</div>
			{/if}
		</div>
	{/if}
</article>

<style>
	.workflow-summary {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: white;
		overflow: hidden;
	}

	.workflow-summary.expanded {
		border-color: #94a3b8;
	}

	.summary-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		gap: 1rem;
	}

	.task-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-width: 0;
	}

	.task-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.summary-metrics {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	.score-badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 2rem;
		padding: 0.125rem 0.375rem;
		font-size: 0.75rem;
		font-weight: 700;
		border-radius: 0.25rem;
	}

	.score-green {
		background: #dcfce7;
		color: #166534;
	}

	.score-blue {
		background: #dbeafe;
		color: #1e40af;
	}

	.score-yellow {
		background: #fef3c7;
		color: #92400e;
	}

	.score-red {
		background: #fee2e2;
		color: #dc2626;
	}

	.score-unknown {
		background: #f1f5f9;
		color: #64748b;
	}

	.metric {
		font-size: 0.75rem;
		color: #64748b;
	}

	.metric.time::before {
		content: '';
		margin-right: 0.25rem;
	}

	.metric.retry::before {
		content: '';
		margin-right: 0.25rem;
	}

	.trace-link {
		font-size: 0.75rem;
		color: #2563eb;
		text-decoration: none;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		background: #eff6ff;
	}

	.trace-link:hover {
		background: #dbeafe;
	}

	.expand-btn {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #475569;
		background: #f1f5f9;
		border: none;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.expand-btn:hover {
		background: #e2e8f0;
		color: #1e293b;
	}

	.expand-btn:focus {
		outline: 2px solid #2563eb;
		outline-offset: 1px;
	}

	/* Expanded Details */
	.summary-details {
		padding: 1rem;
		background: #f8fafc;
		border-top: 1px solid #e2e8f0;
	}

	.detail-section {
		margin-bottom: 1rem;
	}

	.detail-section:last-child {
		margin-bottom: 0;
	}

	.detail-section h4 {
		margin: 0 0 0.5rem 0;
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.section-header h4 {
		margin: 0;
	}

	.yaml-toggle-btn {
		padding: 0.25rem 0.5rem;
		font-size: 0.6875rem;
		font-weight: 500;
		color: #2563eb;
		background: #eff6ff;
		border: 1px solid #bfdbfe;
		border-radius: 0.25rem;
		cursor: pointer;
		transition: all 0.15s ease;
	}

	.yaml-toggle-btn:hover {
		background: #dbeafe;
		border-color: #93c5fd;
	}

	/* YAML Preview */
	.yaml-preview {
		margin: 0;
		padding: 0.75rem;
		background: #1e293b;
		color: #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		line-height: 1.5;
		overflow-x: auto;
		max-height: 200px;
	}

	.yaml-preview.yaml-full {
		max-height: none;
	}

	.yaml-preview code {
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
	}

	.yaml-truncated-hint {
		font-size: 0.6875rem;
		color: #94a3b8;
		font-style: italic;
		margin-top: 0.25rem;
		text-align: center;
	}

	/* Test Data */
	.test-data {
		margin: 0;
		padding: 0.75rem;
		background: #f1f5f9;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		line-height: 1.5;
		overflow-x: auto;
		max-height: 150px;
	}

	.test-data code {
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		color: #1e293b;
	}

	/* Test Result */
	.test-result {
		display: flex;
		gap: 1.5rem;
		flex-wrap: wrap;
	}

	.result-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.8125rem;
	}

	.result-label {
		color: #64748b;
	}

	.result-value {
		font-weight: 600;
		color: #334155;
	}

	.result-value.status-success {
		color: #16a34a;
	}

	.result-value.status-error {
		color: #dc2626;
	}

	.result-value.valid {
		color: #16a34a;
	}

	.result-value.invalid {
		color: #dc2626;
	}

	.validation-errors {
		margin-top: 0.5rem;
		padding: 0.5rem;
		background: #fef2f2;
		border-radius: 0.25rem;
	}

	.errors-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #dc2626;
	}

	.validation-errors ul {
		margin: 0.25rem 0 0 1rem;
		padding: 0;
		font-size: 0.75rem;
		color: #7f1d1d;
	}

	.validation-errors li {
		margin-bottom: 0.125rem;
	}
</style>
