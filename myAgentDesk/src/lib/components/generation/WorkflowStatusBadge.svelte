<!--
  WorkflowStatusBadge Component
  Issue #305: Workflow Generation Progress Display

  Status badge for workflow generation:
  - pending: gray
  - generating: yellow with spinner
  - success: green
  - failed: red

  Props:
  - status: 'pending' | 'generating' | 'success' | 'failed'
  - workflowName: Optional workflow name to display
  - generationTimeMs: Optional generation time in milliseconds
  - errorMessage: Optional error message for failed status
-->
<script lang="ts">
	type WorkflowStatus = 'pending' | 'generating' | 'success' | 'failed';

	interface Props {
		status: WorkflowStatus;
		workflowName?: string | null;
		generationTimeMs?: number | null;
		errorMessage?: string | null;
	}

	let { status, workflowName = null, generationTimeMs = null, errorMessage = null }: Props = $props();

	const statusLabels: Record<WorkflowStatus, string> = {
		pending: 'Pending',
		generating: 'Generating...',
		success: 'Workflow OK',
		failed: 'Failed'
	};

	const label = $derived(statusLabels[status]);
</script>

<span
	class="workflow-badge"
	class:pending={status === 'pending'}
	class:generating={status === 'generating'}
	class:success={status === 'success'}
	class:failed={status === 'failed'}
	role="status"
	aria-label={`Workflow status: ${label}`}
	title={errorMessage || (workflowName ? `${workflowName}` : undefined)}
>
	{#if status === 'generating'}
		<span class="mini-spinner" aria-hidden="true"></span>
	{/if}
	{label}
</span>

<style>
	.workflow-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.375rem;
		font-size: 0.625rem;
		font-weight: 600;
		border-radius: 0.25rem;
		white-space: nowrap;
	}

	.workflow-badge.pending {
		background: #f1f5f9;
		color: #64748b;
	}

	.workflow-badge.generating {
		background: #fef3c7;
		color: #92400e;
	}

	.workflow-badge.success {
		background: #dcfce7;
		color: #166534;
	}

	.workflow-badge.failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.mini-spinner {
		width: 0.625rem;
		height: 0.625rem;
		border: 1.5px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
