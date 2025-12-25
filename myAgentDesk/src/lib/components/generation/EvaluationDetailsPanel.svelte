<!--
  EvaluationDetailsPanel Component
  Issue #305: Task Workflow Traces Summary Feature

  Displays LLM evaluation results with:
  - Overall score with color coding
  - 5 component scores with progress bars
  - Strengths list
  - Weaknesses list
  - Suggestions list
  - Confidence indicator
-->
<script lang="ts">
	import type { EvaluationSummary } from '$lib/types/workflow-summary';
	import { getScoreRange } from '$lib/types/workflow-summary';

	interface Props {
		evaluation: EvaluationSummary;
	}

	let { evaluation }: Props = $props();

	const scoreRange = $derived(getScoreRange(evaluation.score));

	const componentScores = $derived([
		{ label: 'Structural', value: evaluation.structural_score },
		{ label: 'Requirement', value: evaluation.requirement_score },
		{ label: 'Output Quality', value: evaluation.output_quality_score },
		{ label: 'Error Handling', value: evaluation.error_handling_score },
		{ label: 'Test Data', value: evaluation.test_data_quality_score }
	]);

	function getScoreColorClass(score: number | null): string {
		if (score === null) return 'score-unknown';
		if (score >= 90) return 'score-excellent';
		if (score >= 70) return 'score-good';
		if (score >= 50) return 'score-fair';
		return 'score-poor';
	}

	function formatConfidence(confidence: number | null): string {
		if (confidence === null) return 'N/A';
		return `${(confidence * 100).toFixed(0)}%`;
	}
</script>

<section class="evaluation-panel" aria-label="Evaluation Details">
	<!-- Overall Score -->
	<div class="overall-score">
		<h3>LLM Evaluation</h3>
		<div class="score-display {getScoreColorClass(evaluation.score)}">
			<span class="score-value">{evaluation.score ?? 'N/A'}</span>
			<span class="score-max">/100</span>
		</div>
		{#if scoreRange}
			<span class="score-label">{scoreRange.label}</span>
		{/if}
	</div>

	<!-- Component Scores -->
	<div class="component-scores">
		<h4>Score Breakdown</h4>
		{#each componentScores as score}
			<div class="score-row">
				<span class="score-label">{score.label}</span>
				<div class="progress-container">
					<div
						class="progress-bar {getScoreColorClass(score.value)}"
						role="progressbar"
						aria-valuenow={score.value ?? 0}
						aria-valuemin={0}
						aria-valuemax={100}
						style="width: {score.value ?? 0}%"
					></div>
				</div>
				<span class="score-number">{score.value ?? '--'}</span>
			</div>
		{/each}
	</div>

	<!-- Strengths -->
	{#if evaluation.strengths.length > 0}
		<div class="strengths feedback-section">
			<h4>Strengths</h4>
			<ul role="list" aria-label="Strengths">
				{#each evaluation.strengths as strength}
					<li>
						<span class="icon success">+</span>
						{strength}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Weaknesses -->
	{#if evaluation.weaknesses.length > 0}
		<div class="weaknesses feedback-section">
			<h4>Weaknesses</h4>
			<ul role="list" aria-label="Weaknesses">
				{#each evaluation.weaknesses as weakness}
					<li>
						<span class="icon warning">!</span>
						{weakness}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Suggestions -->
	{#if evaluation.suggestions.length > 0}
		<div class="suggestions feedback-section">
			<h4>Suggestions</h4>
			<ul role="list" aria-label="Suggestions">
				{#each evaluation.suggestions as suggestion}
					<li>
						<span class="icon info">i</span>
						{suggestion}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Confidence -->
	<div class="confidence">
		<span class="confidence-label">Confidence:</span>
		<span class="confidence-value">{formatConfidence(evaluation.confidence)}</span>
	</div>
</section>

<style>
	.evaluation-panel {
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.overall-score {
		text-align: center;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.overall-score h3 {
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
		color: #64748b;
		font-weight: 600;
	}

	.score-display {
		display: inline-flex;
		align-items: baseline;
		padding: 0.5rem 1rem;
		border-radius: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.score-value {
		font-size: 2rem;
		font-weight: 700;
	}

	.score-max {
		font-size: 1rem;
		color: #64748b;
		margin-left: 0.25rem;
	}

	.score-label {
		display: block;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	/* Score color classes */
	.score-excellent {
		background: #dcfce7;
		color: #166534;
	}

	.score-good {
		background: #dbeafe;
		color: #1e40af;
	}

	.score-fair {
		background: #fef3c7;
		color: #92400e;
	}

	.score-poor {
		background: #fee2e2;
		color: #dc2626;
	}

	.score-unknown {
		background: #f1f5f9;
		color: #64748b;
	}

	/* Component Scores */
	.component-scores {
		margin-bottom: 1rem;
	}

	.component-scores h4 {
		margin: 0 0 0.75rem 0;
		font-size: 0.75rem;
		color: #64748b;
		font-weight: 600;
		text-transform: uppercase;
	}

	.score-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.score-row .score-label {
		width: 100px;
		font-size: 0.75rem;
		color: #475569;
		text-transform: none;
	}

	.progress-container {
		flex: 1;
		height: 0.5rem;
		background: #e2e8f0;
		border-radius: 0.25rem;
		overflow: hidden;
	}

	.progress-bar {
		height: 100%;
		transition: width 0.3s ease;
		border-radius: 0.25rem;
	}

	.score-number {
		width: 2rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-align: right;
		color: #475569;
	}

	/* Feedback sections */
	.feedback-section {
		margin-bottom: 1rem;
	}

	.feedback-section h4 {
		margin: 0 0 0.5rem 0;
		font-size: 0.75rem;
		color: #64748b;
		font-weight: 600;
		text-transform: uppercase;
	}

	.feedback-section ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.feedback-section li {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		font-size: 0.8125rem;
		color: #334155;
		margin-bottom: 0.375rem;
		line-height: 1.4;
	}

	.icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		font-size: 0.625rem;
		font-weight: 700;
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.icon.success {
		background: #dcfce7;
		color: #166534;
	}

	.icon.warning {
		background: #fef3c7;
		color: #92400e;
	}

	.icon.info {
		background: #dbeafe;
		color: #1e40af;
	}

	/* Confidence */
	.confidence {
		display: flex;
		justify-content: flex-end;
		align-items: center;
		gap: 0.5rem;
		padding-top: 0.75rem;
		border-top: 1px solid #e2e8f0;
		font-size: 0.75rem;
	}

	.confidence-label {
		color: #64748b;
	}

	.confidence-value {
		font-weight: 600;
		color: #475569;
	}
</style>
