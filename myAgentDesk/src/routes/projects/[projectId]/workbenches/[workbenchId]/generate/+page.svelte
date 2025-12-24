<!--
  Generate Page (/projects/:projectId/workbenches/:workbenchId/generate)
  Issue #291: Generate Page (Job Generation)
  Issue #305: 2-Phase Progress Display (Task Analysis + Workflow Generation)

  Job generation interface with:
  - Active RequirementVersion display
  - Generate Job button (disabled when no active version)
  - 2-Phase progress display (PhaseFlow component)
  - Task breakdown display (TaskBreakdownList component)
  - Polling for status updates (1 second interval)
  - Timeout handling (10 minutes)
  - Recent job versions history
  - Last generation result display (persistent after completion)
-->
<script lang="ts">
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import type { PageData, ActionData } from './$types';
	import { POLLING_CONFIG, JOB_VERSION_STATUS_CONFIG } from '$lib/types/job-version';
	import type {
		JobPhase,
		TaskBreakdownItem,
		WorkflowStatusItem
	} from '$lib/api/clients/expert-agent';
	import { PhaseFlow, TaskBreakdownList, GenerationSummary } from '$lib/components/generation';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	// Generation state
	let isGenerating = $state(false);
	let currentJobId = $state<string | null>(null);
	let pollingStartTime = $state<number | null>(null);
	let statusMessage = $state<string>('');
	let errorMessage = $state<string>('');

	// Issue #305: New generation state fields
	let currentPhase = $state<JobPhase | 'idle'>('idle');
	let currentProgress = $state<number>(0);
	let taskBreakdown = $state<TaskBreakdownItem[]>([]);
	let workflowStatuses = $state<WorkflowStatusItem[]>([]);
	let langfuseTraceId = $state<string | null>(null);

	// Issue #305: Last generation result (persisted after completion)
	let lastGenerationResult = $state<{
		phase: JobPhase | 'idle';
		progress: number;
		taskBreakdown: TaskBreakdownItem[];
		workflowStatuses: WorkflowStatusItem[];
		langfuseTraceId: string | null;
		versionLabel: string | null;
		completedAt: Date | null;
		hasFailures: boolean;
	} | null>(null);

	// Issue #305: Derived state for workflow failures
	let hasWorkflowFailures = $derived(
		workflowStatuses.some((ws) => ws.status === 'failed')
	);
	let successfulWorkflows = $derived(
		workflowStatuses.filter((ws) => ws.status === 'success').length
	);
	let failedWorkflows = $derived(
		workflowStatuses.filter((ws) => ws.status === 'failed').length
	);

	// Initialize from data
	$effect(() => {
		if (data.currentGeneratingJob) {
			currentJobId = data.currentGeneratingJob.id;
			isGenerating = true;
			pollingStartTime = new Date(data.currentGeneratingJob.createdAt).getTime();
			statusMessage = `Resuming generation: ${data.currentGeneratingJob.versionLabel}`;
			startPolling();
		}
	});

	// Derived states
	let canGenerate = $derived(
		data.activeRequirementVersion !== null && !isGenerating && !data.currentGeneratingJob
	);

	// Handle form result
	$effect(() => {
		if (form?.success && form?.jobVersionId) {
			currentJobId = form.jobVersionId;
			isGenerating = true;
			pollingStartTime = Date.now();
			statusMessage = form.message ?? 'Generation started';
			errorMessage = '';
			// Reset Issue #305 state
			currentPhase = 'task_analysis';
			currentProgress = 0;
			taskBreakdown = [];
			workflowStatuses = [];
			langfuseTraceId = null;
			// Clear last result when starting new generation
			lastGenerationResult = null;
			startPolling();
		} else if (form?.error) {
			errorMessage = form.error;
			isGenerating = false;
		}
	});

	let pollingInterval: ReturnType<typeof setInterval> | null = null;

	function startPolling() {
		if (pollingInterval) {
			clearInterval(pollingInterval);
		}

		pollingInterval = setInterval(async () => {
			if (!currentJobId) {
				stopPolling();
				return;
			}

			// Check for timeout
			if (pollingStartTime && Date.now() - pollingStartTime > POLLING_CONFIG.maxDurationMs) {
				await handleTimeout();
				return;
			}

			// Poll for status
			try {
				const response = await fetch(`/api/jobs/${currentJobId}/status`);
				if (!response.ok) {
					throw new Error('Failed to get status');
				}

				const status = await response.json();

				// Issue #305: Update new state fields
				if (status.phase) {
					currentPhase = status.phase;
				}
				if (typeof status.progress === 'number') {
					currentProgress = status.progress;
				}
				if (status.task_breakdown) {
					taskBreakdown = status.task_breakdown;
				}
				if (status.workflow_statuses) {
					workflowStatuses = status.workflow_statuses;
				}
				if (status.langfuseTraceId) {
					langfuseTraceId = status.langfuseTraceId;
				}

				if (status.status === 'success') {
					isGenerating = false;
					currentPhase = 'complete';
					currentProgress = 100;
					statusMessage = `Generation complete: ${status.versionLabel}`;

					// Issue #305: Save last generation result
					lastGenerationResult = {
						phase: 'complete',
						progress: 100,
						taskBreakdown: [...taskBreakdown],
						workflowStatuses: [...workflowStatuses],
						langfuseTraceId,
						versionLabel: status.versionLabel,
						completedAt: new Date(),
						hasFailures: workflowStatuses.some((ws) => ws.status === 'failed')
					};

					stopPolling();
					// Issue #305: Refresh data without full page reload to keep state
					await invalidateAll();
				} else if (status.status === 'failed') {
					isGenerating = false;
					errorMessage = status.errorMessage ?? 'Generation failed';
					statusMessage = '';
					// Issue #305: Clear last result on failure (don't persist failed state)
					lastGenerationResult = null;
					// Reset phase to idle on failure
					currentPhase = 'idle';
					stopPolling();
				}
			} catch (err) {
				console.error('Polling error:', err);
			}
		}, POLLING_CONFIG.intervalMs);
	}

	function stopPolling() {
		if (pollingInterval) {
			clearInterval(pollingInterval);
			pollingInterval = null;
		}
	}

	async function handleTimeout() {
		if (!currentJobId) return;

		try {
			await fetch(`/api/jobs/${currentJobId}/timeout`, { method: 'POST' });
			isGenerating = false;
			errorMessage = 'Generation timed out (exceeded 10 minutes)';
			statusMessage = '';
			stopPolling();
		} catch (err) {
			console.error('Timeout handling error:', err);
		}
	}

	// Cleanup on component destroy
	$effect(() => {
		return () => {
			stopPolling();
		};
	});

	function getStatusConfig(status: string) {
		return (
			JOB_VERSION_STATUS_CONFIG[status as keyof typeof JOB_VERSION_STATUS_CONFIG] ?? {
				label: status,
				color: '#64748b',
				bgColor: '#f1f5f9'
			}
		);
	}

	function formatDate(dateString: string | Date | null) {
		if (!dateString) return '-';
		const date = typeof dateString === 'string' ? new Date(dateString) : dateString;
		return date.toLocaleString();
	}

	// Issue #305: Clear last result
	function clearLastResult() {
		lastGenerationResult = null;
		currentPhase = 'idle';
		currentProgress = 0;
		taskBreakdown = [];
		workflowStatuses = [];
		langfuseTraceId = null;
		statusMessage = '';
	}
</script>

<div class="generate-page">
	<div class="page-header">
		<h2>Generate Job</h2>
		<p class="workbench-name">{data.workbench.name}</p>
	</div>

	<!-- Active Requirement Version Section -->
	<div class="section-card">
		<h3>Active Requirement Version</h3>
		{#if data.activeRequirementVersion}
			<div class="requirement-info">
				<span class="version-badge">v{data.activeRequirementVersion.version}</span>
				<span
					class="status-badge"
					style="color: {getStatusConfig(data.activeRequirementVersion.status)
						.color}; background: {getStatusConfig(data.activeRequirementVersion.status).bgColor}"
				>
					{getStatusConfig(data.activeRequirementVersion.status).label}
				</span>
				{#if data.activeRequirementVersion.changeSummary}
					<span class="change-summary">{data.activeRequirementVersion.changeSummary}</span>
				{/if}
			</div>
			<details class="requirement-content">
				<summary>View Content</summary>
				<pre>{data.activeRequirementVersion.content}</pre>
			</details>
		{:else}
			<div class="no-version-warning">
				<span class="warning-icon">!</span>
				<p>
					No active requirement version set. Please go to the Requirements tab and set an active
					version before generating a job.
				</p>
			</div>
		{/if}
	</div>

	<!-- Generation Status Section - Issue #305: Enhanced with PhaseFlow -->
	<div class="section-card">
		<div class="section-header">
			<h3>Generation Status</h3>
			{#if lastGenerationResult && !isGenerating}
				<button class="clear-button" onclick={clearLastResult}>Clear Result</button>
			{/if}
		</div>

		<!-- Issue #305: Error display takes priority over other states -->
		{#if errorMessage && !isGenerating}
			<div class="status-indicator error">
				<span class="error-icon">X</span>
				<div class="status-text">
					<span class="status-main">Generation Failed</span>
					<span class="status-detail">{errorMessage}</span>
				</div>
			</div>
		{:else if isGenerating || currentPhase === 'complete' || (lastGenerationResult && !errorMessage)}
			<!-- Issue #305: 2-Phase Progress Display -->
			<PhaseFlow
				phase={isGenerating ? currentPhase : (lastGenerationResult?.phase ?? 'idle')}
				progress={isGenerating ? currentProgress : (lastGenerationResult?.progress ?? 0)}
				hasFailures={isGenerating ? hasWorkflowFailures : (lastGenerationResult?.hasFailures ?? false)}
			/>

			<!-- Issue #305: Task Breakdown Display (shown after phase 1) -->
			{@const displayTasks = isGenerating ? taskBreakdown : (lastGenerationResult?.taskBreakdown ?? [])}
			{@const displayStatuses = isGenerating ? workflowStatuses : (lastGenerationResult?.workflowStatuses ?? [])}
			{#if displayTasks.length > 0}
				<TaskBreakdownList tasks={displayTasks} workflowStatuses={displayStatuses} />
			{/if}

			<!-- Issue #305: Generation Summary (shown on completion) -->
			{#if currentPhase === 'complete' || lastGenerationResult?.phase === 'complete'}
				{@const displaySuccessCount = isGenerating ? successfulWorkflows : displayStatuses.filter((ws) => ws.status === 'success').length}
				{@const displayFailedCount = isGenerating ? failedWorkflows : displayStatuses.filter((ws) => ws.status === 'failed').length}
				{@const displayTraceId = isGenerating ? langfuseTraceId : lastGenerationResult?.langfuseTraceId}
				<GenerationSummary
					successCount={displaySuccessCount}
					failedCount={displayFailedCount}
					totalTasks={displayTasks.length}
					traceId={displayTraceId}
				/>

				<!-- Last generation info -->
				{#if lastGenerationResult && !isGenerating}
					<div class="last-generation-info">
						<span class="info-label">Completed:</span>
						<span class="info-value">{formatDate(lastGenerationResult.completedAt)}</span>
						{#if lastGenerationResult.versionLabel}
							<span class="info-separator">|</span>
							<span class="info-label">Version:</span>
							<span class="info-value">{lastGenerationResult.versionLabel}</span>
						{/if}
					</div>
				{/if}
			{/if}
		{:else if statusMessage}
			<div class="status-indicator success">
				<span class="success-icon">OK</span>
				<div class="status-text">
					<span class="status-main">Complete</span>
					<span class="status-detail">{statusMessage}</span>
				</div>
			</div>
		{:else}
			<div class="status-indicator idle">Ready to generate</div>
		{/if}
	</div>

	<!-- Generate Action Section -->
	<div class="section-card action-card">
		<h3>Start Generation</h3>
		<p>Generate a new job based on the active requirements.</p>
		<form method="POST" action="?/generateJob" use:enhance>
			<button type="submit" class="generate-button" disabled={!canGenerate}>
				{#if isGenerating}
					<span class="button-spinner"></span>
					Generating...
				{:else if !data.activeRequirementVersion}
					No Active Version
				{:else}
					Generate Job
				{/if}
			</button>
		</form>
		{#if !data.activeRequirementVersion}
			<p class="help-text">Set an active requirement version to enable generation.</p>
		{/if}
	</div>

	<!-- Recent Job Versions Section -->
	{#if data.recentJobVersions.length > 0}
		<div class="section-card">
			<h3>Recent Job Versions</h3>
			<div class="job-history">
				{#each data.recentJobVersions as job (job.id)}
					{@const workflowStatuses = job.workflows ? JSON.parse(job.workflows) : []}
					<details class="job-item-details">
						<summary class="job-item">
							<div class="job-version">{job.versionLabel}</div>
							<span
								class="status-badge"
								style="color: {getStatusConfig(job.status).color}; background: {getStatusConfig(
									job.status
								).bgColor}"
							>
								{getStatusConfig(job.status).label}
							</span>
							{#if workflowStatuses.length > 0}
								<span class="workflow-count">
									{workflowStatuses.filter((ws: WorkflowStatusItem) => ws.status === 'success').length}/{workflowStatuses.length} tasks
								</span>
							{/if}
							<span class="job-date">{formatDate(job.generatedAt ?? job.createdAt)}</span>
							{#if job.externalTraceId}
								<a
									href="http://localhost:3001/trace/{job.externalTraceId}"
									target="_blank"
									rel="noopener noreferrer"
									class="trace-link"
									onclick={(e) => e.stopPropagation()}
								>
									Main Trace
								</a>
							{/if}
						</summary>
						<!-- Issue #305: Per-task workflow traces -->
						{#if workflowStatuses.length > 0}
							<div class="workflow-traces">
								<div class="workflow-traces-header">Task Workflow Traces</div>
								{#each workflowStatuses as ws (ws.task_id)}
									<div class="workflow-trace-item">
										<span class="task-name">{ws.task_name ?? ws.task_id}</span>
										<span
											class="status-badge small"
											style="color: {ws.status === 'success' ? '#166534' : '#dc2626'}; background: {ws.status === 'success' ? '#dcfce7' : '#fee2e2'}"
										>
											{ws.status}
										</span>
										{#if ws.workflow_name}
											<span class="workflow-name">{ws.workflow_name}</span>
										{/if}
										{#if ws.langfuse_trace_id}
											<a
												href="http://localhost:3001/trace/{ws.langfuse_trace_id}"
												target="_blank"
												rel="noopener noreferrer"
												class="trace-link small"
											>
												Trace
											</a>
										{/if}
										{#if ws.error_message}
											<span class="error-hint" title={ws.error_message}>Error</span>
										{/if}
									</div>
								{/each}
							</div>
						{/if}
					</details>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	.generate-page {
		max-width: 800px;
		padding: 1rem;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.workbench-name {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0.25rem 0 0;
	}

	.section-card {
		padding: 1.5rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.section-header h3 {
		margin: 0;
	}

	.section-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.clear-button {
		font-size: 0.75rem;
		color: #64748b;
		background: none;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		padding: 0.25rem 0.5rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.clear-button:hover {
		background: #f1f5f9;
		color: #475569;
	}

	.requirement-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.version-badge {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e40af;
		background: #dbeafe;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
	}

	.status-badge {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
	}

	.change-summary {
		font-size: 0.875rem;
		color: #64748b;
		margin-left: 0.5rem;
	}

	.requirement-content {
		margin-top: 1rem;
	}

	.requirement-content summary {
		cursor: pointer;
		font-size: 0.875rem;
		color: #3b82f6;
	}

	.requirement-content pre {
		margin: 0.5rem 0 0;
		padding: 1rem;
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		overflow-x: auto;
		white-space: pre-wrap;
		word-wrap: break-word;
	}

	.no-version-warning {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		background: #fef3c7;
		border-radius: 0.25rem;
	}

	.warning-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #f59e0b;
		color: white;
		border-radius: 50%;
		font-size: 0.875rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.no-version-warning p {
		margin: 0;
		font-size: 0.875rem;
		color: #92400e;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-indicator.idle {
		background: #eff6ff;
		color: #1e40af;
	}

	.status-indicator.success {
		background: #dcfce7;
		color: #166534;
	}

	.status-indicator.error {
		background: #fee2e2;
		color: #dc2626;
	}

	.status-text {
		display: flex;
		flex-direction: column;
	}

	.status-main {
		font-weight: 600;
	}

	.status-detail {
		font-size: 0.75rem;
		font-weight: 400;
		opacity: 0.8;
	}

	.error-icon,
	.success-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		font-size: 0.625rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.error-icon {
		background: #dc2626;
		color: white;
	}

	.success-icon {
		background: #166534;
		color: white;
	}

	.action-card p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 1rem;
	}

	.generate-button {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s;
	}

	.generate-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.generate-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	/* Button spinner */
	.button-spinner {
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.help-text {
		font-size: 0.75rem;
		color: #94a3b8;
		margin: 0.5rem 0 0;
	}

	/* Last generation info */
	.last-generation-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1rem;
		padding: 0.75rem;
		background: #f1f5f9;
		border-radius: 0.25rem;
		font-size: 0.75rem;
	}

	.info-label {
		color: #64748b;
	}

	.info-value {
		color: #1e293b;
		font-weight: 500;
	}

	.info-separator {
		color: #cbd5e1;
	}

	.job-history {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.job-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
	}

	.job-version {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.job-date {
		font-size: 0.75rem;
		color: #94a3b8;
		margin-left: auto;
	}

	.trace-link {
		font-size: 0.75rem;
		color: #3b82f6;
		text-decoration: none;
	}

	.trace-link:hover {
		text-decoration: underline;
	}

	/* Issue #305: Job item with expandable workflow traces */
	.job-item-details {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
	}

	.job-item-details summary {
		list-style: none;
		cursor: pointer;
	}

	.job-item-details summary::-webkit-details-marker {
		display: none;
	}

	.job-item-details[open] .job-item {
		border-bottom: 1px solid #e2e8f0;
	}

	.workflow-count {
		font-size: 0.75rem;
		color: #64748b;
		background: #f1f5f9;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
	}

	.workflow-traces {
		padding: 0.75rem;
		background: #f8fafc;
	}

	.workflow-traces-header {
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		margin-bottom: 0.5rem;
	}

	.workflow-trace-item {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		margin-bottom: 0.25rem;
		font-size: 0.75rem;
	}

	.workflow-trace-item:last-child {
		margin-bottom: 0;
	}

	.task-name {
		font-weight: 500;
		color: #1e293b;
		flex: 1;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.workflow-name {
		color: #64748b;
		font-size: 0.675rem;
		flex-shrink: 0;
	}

	.status-badge.small {
		font-size: 0.625rem;
		padding: 0.0625rem 0.25rem;
	}

	.trace-link.small {
		font-size: 0.675rem;
	}

	.error-hint {
		font-size: 0.675rem;
		color: #dc2626;
		background: #fee2e2;
		padding: 0.0625rem 0.25rem;
		border-radius: 0.125rem;
		cursor: help;
	}
</style>
