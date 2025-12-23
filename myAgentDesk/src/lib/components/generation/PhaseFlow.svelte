<!--
  PhaseFlow Component
  Issue #305: Workflow Generation Progress Display

  Visual 2-phase progress indicator:
  - Phase 1: Task Analysis (0-70%)
  - Phase 2: Workflow Generation (70-95%)

  Props:
  - phase: Current phase ('idle' | 'task_analysis' | 'workflow_generation' | 'complete')
  - progress: Current progress percentage (0-100)
  - hasFailures: Whether there are workflow generation failures

  Issue #305 Enhancement:
  - Added spinner animation for active phases
  - Added pulse animation for better visual feedback
  - Added striped progress bar animation during generation
-->
<script lang="ts">
	import type { JobPhase } from '$lib/api/clients/expert-agent';

	interface Props {
		phase: JobPhase | 'idle';
		progress: number;
		hasFailures?: boolean;
	}

	let { phase, progress, hasFailures = false }: Props = $props();

	// Determine phase states
	const isPhase1Active = $derived(phase === 'task_analysis');
	const isPhase1Complete = $derived(
		phase === 'workflow_generation' || phase === 'complete'
	);
	const isPhase2Active = $derived(phase === 'workflow_generation');
	const isPhase2Complete = $derived(phase === 'complete');
	const isGenerating = $derived(phase === 'task_analysis' || phase === 'workflow_generation');

	// Get phase status message
	const statusMessage = $derived(() => {
		switch (phase) {
			case 'task_analysis':
				return 'Analyzing requirements and breaking down tasks...';
			case 'workflow_generation':
				return 'Generating workflows for each task...';
			case 'complete':
				return hasFailures ? 'Generation completed with some failures' : 'Generation complete';
			default:
				return 'Ready to generate';
		}
	});
</script>

<div class="phase-flow" role="group" aria-label="Generation progress phases">
	<!-- Phase 1: Task Analysis -->
	<div
		class="phase-step"
		class:active={isPhase1Active}
		class:complete={isPhase1Complete}
		aria-current={isPhase1Active ? 'step' : undefined}
	>
		<span class="phase-number" aria-hidden="true">
			{#if isPhase1Active}
				<span class="spinner"></span>
			{:else if isPhase1Complete}
				<svg class="checkmark" viewBox="0 0 24 24" fill="none">
					<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			{:else}
				1
			{/if}
		</span>
		<span class="phase-label">Task Analysis</span>
		<span class="phase-desc">Requirements analysis & task breakdown</span>
	</div>

	<!-- Arrow -->
	<div class="phase-arrow" class:active={isPhase1Complete} aria-hidden="true">
		<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
			<path
				d="M5 12H19M19 12L12 5M19 12L12 19"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		</svg>
	</div>

	<!-- Phase 2: Workflow Generation -->
	<div
		class="phase-step"
		class:active={isPhase2Active}
		class:complete={isPhase2Complete}
		class:has-failures={hasFailures && isPhase2Complete}
		aria-current={isPhase2Active ? 'step' : undefined}
	>
		<span class="phase-number" aria-hidden="true">
			{#if isPhase2Active}
				<span class="spinner"></span>
			{:else if isPhase2Complete}
				{#if hasFailures}
					<svg class="warning-icon" viewBox="0 0 24 24" fill="none">
						<path d="M12 9v4M12 17h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
					</svg>
				{:else}
					<svg class="checkmark" viewBox="0 0 24 24" fill="none">
						<path d="M5 13l4 4L19 7" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
					</svg>
				{/if}
			{:else}
				2
			{/if}
		</span>
		<span class="phase-label">Workflow Generation</span>
		<span class="phase-desc">Generate YAML for each task</span>
	</div>
</div>

<!-- Progress Bar -->
{#if phase !== 'idle'}
	<div class="progress-section">
		<div class="progress-header">
			<span class="status-message">
				{#if isGenerating}
					<span class="status-spinner"></span>
				{/if}
				{statusMessage()}
			</span>
			<span class="progress-percent">{Math.round(progress)}%</span>
		</div>
		<div class="progress-bar" class:generating={isGenerating} role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
			<div
				class="progress-fill"
				class:warning={hasFailures && phase === 'complete'}
				class:animated={isGenerating}
				style="width: {progress}%"
			></div>
			<!-- Phase marker at 70% -->
			<div class="phase-marker" style="left: 70%">
				<span class="marker-line"></span>
				<span class="marker-label">Task breakdown</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.phase-flow {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.phase-step {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.75rem 1rem;
		background: white;
		border: 2px solid #e2e8f0;
		border-radius: 0.5rem;
		min-width: 160px;
		transition: all 0.2s;
	}

	.phase-step.active {
		border-color: #3b82f6;
		background: #eff6ff;
		animation: pulse 2s ease-in-out infinite;
	}

	.phase-step.complete {
		border-color: #10b981;
		background: #f0fdf4;
	}

	.phase-step.has-failures {
		border-color: #f59e0b;
		background: #fffbeb;
	}

	@keyframes pulse {
		0%, 100% {
			box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4);
		}
		50% {
			box-shadow: 0 0 0 8px rgba(59, 130, 246, 0);
		}
	}

	.phase-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #e2e8f0;
		color: #64748b;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 700;
		margin-bottom: 0.375rem;
	}

	.phase-step.active .phase-number {
		background: #3b82f6;
		color: white;
	}

	.phase-step.complete .phase-number {
		background: #10b981;
		color: white;
	}

	.phase-step.has-failures .phase-number {
		background: #f59e0b;
		color: white;
	}

	/* Spinner animation for active phases */
	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid transparent;
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.status-spinner {
		display: inline-block;
		width: 12px;
		height: 12px;
		border: 2px solid #e2e8f0;
		border-top-color: #3b82f6;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		margin-right: 0.5rem;
		vertical-align: middle;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Checkmark and icons */
	.checkmark, .warning-icon {
		width: 14px;
		height: 14px;
	}

	.phase-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #1e293b;
	}

	.phase-desc {
		font-size: 0.625rem;
		color: #64748b;
		margin-top: 0.125rem;
		text-align: center;
	}

	.phase-arrow {
		color: #cbd5e1;
		transition: color 0.2s;
	}

	.phase-arrow.active {
		color: #10b981;
	}

	.phase-arrow svg {
		width: 1.5rem;
		height: 1.5rem;
	}

	/* Progress Section */
	.progress-section {
		margin-bottom: 1rem;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		color: #475569;
	}

	.status-message {
		display: flex;
		align-items: center;
		font-weight: 500;
	}

	.progress-percent {
		font-weight: 600;
		color: #1e293b;
	}

	.progress-bar {
		position: relative;
		height: 8px;
		background: #e2e8f0;
		border-radius: 4px;
		overflow: visible;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		border-radius: 4px;
		transition: width 0.3s ease;
	}

	/* Animated striped progress bar during generation */
	.progress-fill.animated {
		background: linear-gradient(
			-45deg,
			#3b82f6 25%,
			#60a5fa 25%,
			#60a5fa 50%,
			#3b82f6 50%,
			#3b82f6 75%,
			#60a5fa 75%
		);
		background-size: 20px 20px;
		animation: stripes 0.5s linear infinite;
	}

	@keyframes stripes {
		from {
			background-position: 0 0;
		}
		to {
			background-position: 20px 0;
		}
	}

	.progress-fill.warning {
		background: #f59e0b;
	}

	.progress-fill.warning.animated {
		background: linear-gradient(
			-45deg,
			#f59e0b 25%,
			#fbbf24 25%,
			#fbbf24 50%,
			#f59e0b 50%,
			#f59e0b 75%,
			#fbbf24 75%
		);
		background-size: 20px 20px;
		animation: stripes 0.5s linear infinite;
	}

	.phase-marker {
		position: absolute;
		top: -4px;
		transform: translateX(-50%);
	}

	.marker-line {
		display: block;
		width: 2px;
		height: 16px;
		background: #94a3b8;
		margin: 0 auto;
	}

	.marker-label {
		display: block;
		position: absolute;
		top: 20px;
		left: 50%;
		transform: translateX(-50%);
		font-size: 0.625rem;
		color: #64748b;
		white-space: nowrap;
	}
</style>
