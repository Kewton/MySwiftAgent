<!--
  Runs Page (/projects/:projectId/workbenches/:workbenchId/runs)
  Issue #293: Runs Screen (Execution History / Monitoring)

  Lists execution history with real-time status updates.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { RUN_STATUS_CONFIG, getRunDuration, calculateProgress } from '$lib/types/run';
	import { getFirstTaskInputSchema } from '$lib/utils/interface-schema';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// State for new run modal
	let showNewRunModal = $state(false);
	let selectedJobVersionId = $state('');
	let isCreatingRun = $state(false);
	let executionParams = $state<Record<string, string>>({});

	// Get the input schema for the selected job version
	const selectedJobVersion = $derived(
		data.activeJobVersions.find((jv) => jv.id === selectedJobVersionId)
	);
	const inputSchema = $derived(
		selectedJobVersion ? getFirstTaskInputSchema(selectedJobVersion.interfaceDefinitions) : null
	);

	// Track previous job version to detect changes
	let previousJobVersionId = $state('');

	// Reset execution params when job version changes
	$effect(() => {
		// Only run when job version actually changes
		if (selectedJobVersionId !== previousJobVersionId) {
			previousJobVersionId = selectedJobVersionId;

			if (selectedJobVersionId) {
				// Create new params object based on schema
				const newParams: Record<string, string> = {};
				const schema = getFirstTaskInputSchema(
					data.activeJobVersions.find((jv) => jv.id === selectedJobVersionId)?.interfaceDefinitions
				);

				if (schema?.properties) {
					for (const key of Object.keys(schema.properties)) {
						newParams[key] = '';
					}
				}

				executionParams = newParams;
			} else {
				executionParams = {};
			}
		}
	});

	/**
	 * Format date for display
	 */
	function formatDate(date: Date | null): string {
		if (!date) return '-';
		return new Intl.DateTimeFormat('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		}).format(date);
	}

	/**
	 * Handle keyboard events for modal (Escape to close)
	 */
	function handleModalKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			showNewRunModal = false;
		}
	}

	/**
	 * Handle creating a new run
	 */
	async function handleCreateRun() {
		if (!selectedJobVersionId) return;

		isCreatingRun = true;
		try {
			// Build execution params from form values
			const paramsToSend =
				Object.keys(executionParams).length > 0 ? JSON.stringify(executionParams) : undefined;

			const response = await fetch('/api/runs', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					workbenchId,
					jobVersionId: selectedJobVersionId,
					executionParams: paramsToSend
				})
			});

			if (response.ok) {
				const run = await response.json();
				// Navigate to the new run detail page
				goto(`/projects/${projectId}/workbenches/${workbenchId}/runs/${run.id}`);
			} else {
				console.error('Failed to create run');
			}
		} catch (error) {
			console.error('Error creating run:', error);
		} finally {
			isCreatingRun = false;
			showNewRunModal = false;
		}
	}

	/**
	 * Check if all required fields are filled
	 */
	function areRequiredFieldsFilled(): boolean {
		if (!inputSchema?.required) return true;
		return inputSchema.required.every((field) => executionParams[field]?.trim() !== '');
	}
</script>

<div class="runs-page">
	<div class="page-header">
		<h2>Runs</h2>
		{#if data.activeJobVersions.length > 0}
			<button class="start-button" onclick={() => (showNewRunModal = true)}>New Run</button>
		{/if}
	</div>

	<div class="runs-list">
		{#each data.runs as run (run.id)}
			{@const statusConfig = RUN_STATUS_CONFIG[run.status]}
			{@const duration = getRunDuration(run.startedAt, run.completedAt)}
			{@const progress = calculateProgress(run.tasksCompleted, run.totalTasks)}
			<a href="/projects/{projectId}/workbenches/{workbenchId}/runs/{run.id}" class="run-item">
				<div class="run-info">
					<span class="run-id">{run.id.substring(0, 12)}...</span>
					<span class="run-version">Job {run.jobVersionLabel}</span>
					<span class="run-date">{formatDate(run.startedAt ?? run.createdAt)}</span>
					{#if duration}
						<span class="run-duration">{duration}</span>
					{/if}
				</div>
				<div class="run-status-container">
					{#if run.status === 'running' && run.totalTasks}
						<div class="progress-bar">
							<div class="progress-fill" style="width: {progress}%"></div>
						</div>
					{/if}
					<span
						class="run-status"
						style="background: {statusConfig.bgColor}; color: {statusConfig.color}"
					>
						{statusConfig.label}
					</span>
				</div>
			</a>
		{:else}
			<div class="empty-state">
				<p>No runs yet. Start a run from a reviewed job version.</p>
			</div>
		{/each}
	</div>
</div>

<!-- New Run Modal -->
{#if showNewRunModal}
	<div
		class="modal-overlay"
		onclick={() => (showNewRunModal = false)}
		onkeydown={handleModalKeydown}
		role="presentation"
	>
		<div
			class="modal"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
			tabindex="0"
		>
			<h3 id="modal-title">Start New Run</h3>
			<div class="form-group">
				<label for="jobVersion">Select Job Version</label>
				<select id="jobVersion" bind:value={selectedJobVersionId}>
					<option value="">-- Select a version --</option>
					{#each data.activeJobVersions as jv (jv.id)}
						<option value={jv.id}>{jv.versionLabel} ({jv.status})</option>
					{/each}
				</select>
			</div>

			<!-- Dynamic Input Fields based on Schema -->
			{#if inputSchema?.properties}
				<div class="params-section">
					<h4>Input Parameters</h4>
					{#each Object.entries(inputSchema.properties) as [fieldName, fieldDef] (fieldName)}
						{@const isRequired = inputSchema.required?.includes(fieldName)}
						<div class="form-group">
							<label for="param-{fieldName}">
								{fieldName}
								{#if isRequired}<span class="required">*</span>{/if}
							</label>
							{#if fieldDef.description}
								<span class="field-description">{fieldDef.description}</span>
							{/if}
							<input
								type="text"
								id="param-{fieldName}"
								bind:value={executionParams[fieldName]}
								placeholder={fieldDef.default?.toString() ?? ''}
								required={isRequired}
							/>
						</div>
					{/each}
				</div>
			{/if}

			<div class="modal-actions">
				<button class="btn-secondary" onclick={() => (showNewRunModal = false)}>Cancel</button>
				<button
					class="btn-primary"
					onclick={handleCreateRun}
					disabled={!selectedJobVersionId || isCreatingRun || !areRequiredFieldsFilled()}
				>
					{isCreatingRun ? 'Starting...' : 'Start Run'}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.runs-page {
		max-width: 800px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.start-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.start-button:hover {
		background: #2563eb;
	}

	.runs-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.run-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		text-decoration: none;
		transition: border-color 0.15s;
	}

	.run-item:hover {
		border-color: #3b82f6;
	}

	.run-info {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.run-id {
		font-weight: 600;
		color: #1e293b;
		font-family: monospace;
		font-size: 0.875rem;
	}

	.run-version {
		font-size: 0.875rem;
		color: #64748b;
	}

	.run-date {
		font-size: 0.875rem;
		color: #94a3b8;
	}

	.run-duration {
		font-size: 0.75rem;
		color: #64748b;
		background: #e2e8f0;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
	}

	.run-status-container {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.progress-bar {
		width: 60px;
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		transition: width 0.3s ease;
	}

	.run-status {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0;
	}

	/* Modal styles */
	.modal-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		width: 400px;
		max-width: 90%;
	}

	.modal h3 {
		margin: 0 0 1rem;
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-group label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		margin-bottom: 0.5rem;
	}

	.form-group select {
		width: 100%;
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		margin-top: 1rem;
	}

	.btn-primary,
	.btn-secondary {
		padding: 0.5rem 1rem;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.btn-primary {
		background: #3b82f6;
		color: white;
		border: none;
	}

	.btn-primary:hover:not(:disabled) {
		background: #2563eb;
	}

	.btn-primary:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
	}

	.btn-secondary:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	/* Input parameters section */
	.params-section {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.params-section h4 {
		margin: 0 0 0.75rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
	}

	.form-group input {
		width: 100%;
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	.form-group input:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
	}

	.required {
		color: #ef4444;
		margin-left: 0.125rem;
	}

	.field-description {
		display: block;
		font-size: 0.75rem;
		color: #6b7280;
		margin-bottom: 0.375rem;
	}
</style>
