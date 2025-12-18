<!--
  Generate Page (/projects/:projectId/workbenches/:workbenchId/generate)
  Issue #291: Generate Page (Job Generation)

  Job generation interface with:
  - Active RequirementVersion display
  - Generate Job button (disabled when no active version)
  - Progress display during generation
  - Polling for status updates (2 second interval)
  - Timeout handling (5 minutes)
  - Recent job versions history
-->
<script lang="ts">
	import { enhance } from '$app/forms';
	import type { PageData, ActionData } from './$types';
	import { POLLING_CONFIG, JOB_VERSION_STATUS_CONFIG } from '$lib/types/job-version';

	let { data, form }: { data: PageData; form: ActionData } = $props();

	// Generation state
	let isGenerating = $state(false);
	let currentJobId = $state<string | null>(null);
	let pollingStartTime = $state<number | null>(null);
	let statusMessage = $state<string>('');
	let errorMessage = $state<string>('');

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

				if (status.status === 'success') {
					isGenerating = false;
					statusMessage = `Generation complete: ${status.versionLabel}`;
					stopPolling();
					// Refresh the page data
					window.location.reload();
				} else if (status.status === 'failed') {
					isGenerating = false;
					errorMessage = status.errorMessage ?? 'Generation failed';
					statusMessage = '';
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
			errorMessage = 'Generation timed out (exceeded 5 minutes)';
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

	function formatDate(dateString: string | null) {
		if (!dateString) return '-';
		return new Date(dateString).toLocaleString();
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

	<!-- Generation Status Section -->
	<div class="section-card">
		<h3>Generation Status</h3>
		{#if isGenerating}
			<div class="status-indicator running">
				<span class="spinner"></span>
				<div class="status-text">
					<span class="status-main">Generating...</span>
					{#if statusMessage}
						<span class="status-detail">{statusMessage}</span>
					{/if}
				</div>
			</div>
			<div class="progress-bar">
				<div class="progress-fill"></div>
			</div>
		{:else if errorMessage}
			<div class="status-indicator error">
				<span class="error-icon">X</span>
				<div class="status-text">
					<span class="status-main">Generation Failed</span>
					<span class="status-detail">{errorMessage}</span>
				</div>
			</div>
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
					<div class="job-item">
						<div class="job-version">{job.versionLabel}</div>
						<span
							class="status-badge"
							style="color: {getStatusConfig(job.status).color}; background: {getStatusConfig(
								job.status
							).bgColor}"
						>
							{getStatusConfig(job.status).label}
						</span>
						<span class="job-date">{formatDate(job.generatedAt ?? job.createdAt)}</span>
						{#if job.externalTraceId}
							<a
								href="http://localhost:3001/trace/{job.externalTraceId}"
								target="_blank"
								rel="noopener noreferrer"
								class="trace-link"
							>
								Open Trace
							</a>
						{/if}
					</div>
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

	.section-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
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

	.status-indicator.running {
		background: #fef3c7;
		color: #92400e;
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

	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
		flex-shrink: 0;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.progress-bar {
		margin-top: 0.75rem;
		height: 0.25rem;
		background: #e2e8f0;
		border-radius: 0.125rem;
		overflow: hidden;
	}

	.progress-fill {
		width: 30%;
		height: 100%;
		background: #f59e0b;
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%,
		100% {
			width: 30%;
			margin-left: 0;
		}
		50% {
			width: 50%;
			margin-left: 50%;
		}
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

	.help-text {
		font-size: 0.75rem;
		color: #94a3b8;
		margin: 0.5rem 0 0;
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
</style>
