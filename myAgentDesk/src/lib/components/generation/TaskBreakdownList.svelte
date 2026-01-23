<!--
  TaskBreakdownList Component
  Issue #305: Workflow Generation Progress Display

  Displays task breakdown results from Phase 1.

  Props:
  - tasks: Array of TaskBreakdownItem
  - workflowStatuses: Optional array of WorkflowStatusItem for status display
-->
<script lang="ts">
	import type { TaskBreakdownItem, WorkflowStatusItem } from '$lib/api/clients/expert-agent';
	import WorkflowStatusBadge from './WorkflowStatusBadge.svelte';

	interface Props {
		tasks: TaskBreakdownItem[];
		workflowStatuses?: WorkflowStatusItem[];
	}

	let { tasks, workflowStatuses = [] }: Props = $props();

	function getWorkflowStatus(taskId: string): WorkflowStatusItem | undefined {
		return workflowStatuses.find((ws) => ws.task_id === taskId);
	}
</script>

<div class="breakdown-section" role="region" aria-label="Task breakdown results">
	<h4 class="section-header">
		<span class="section-icon" aria-hidden="true">1</span>
		Task Breakdown Results
		<span class="task-count">{tasks.length} tasks</span>
	</h4>

	<div class="breakdown-list" role="list">
		{#each tasks as task, index (task.task_id)}
			{@const workflowStatus = getWorkflowStatus(task.task_id)}
			<div
				class="breakdown-item"
				class:generating={workflowStatus?.status === 'generating'}
				role="listitem"
			>
				<div class="task-number" aria-hidden="true">{index + 1}</div>
				<div class="task-info">
					<div class="task-header">
						<span class="task-name">{task.name}</span>
						{#if workflowStatus}
							<WorkflowStatusBadge
								status={workflowStatus.status}
								workflowName={workflowStatus.workflow_name}
								generationTimeMs={workflowStatus.generation_time_ms}
								errorMessage={workflowStatus.error_message}
							/>
						{/if}
					</div>
					<p class="task-description">{task.description}</p>
					{#if task.recommended_apis?.length > 0}
						<div class="task-apis">
							{#each task.recommended_apis as api}
								<span class="api-tag">{api}</span>
							{/each}
						</div>
					{/if}
				</div>
				<!-- Workflow Result -->
				{#if workflowStatus?.status === 'success' && workflowStatus.workflow_name}
					<div class="workflow-result">
						<span class="workflow-name">{workflowStatus.workflow_name}.yaml</span>
						{#if workflowStatus.generation_time_ms}
							<span class="workflow-time"
								>{(workflowStatus.generation_time_ms / 1000).toFixed(1)}s</span
							>
						{/if}
					</div>
				{:else if workflowStatus?.status === 'failed' && workflowStatus.error_message}
					<div class="workflow-error">
						<span class="error-message">{workflowStatus.error_message}</span>
					</div>
				{/if}
			</div>
		{/each}
	</div>
</div>

<style>
	.breakdown-section {
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

	.task-count {
		margin-left: auto;
		font-size: 0.75rem;
		font-weight: 400;
		color: #64748b;
	}

	.breakdown-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.breakdown-item {
		display: grid;
		grid-template-columns: 2rem 1fr auto;
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		transition: all 0.2s;
	}

	.breakdown-item.generating {
		background: #fefce8;
		border-color: #fcd34d;
	}

	.task-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #e2e8f0;
		color: #64748b;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.task-info {
		min-width: 0;
	}

	.task-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.25rem;
	}

	.task-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.task-description {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0 0 0.375rem;
	}

	.task-apis {
		display: flex;
		gap: 0.25rem;
		flex-wrap: wrap;
	}

	.api-tag {
		padding: 0.125rem 0.375rem;
		background: #dbeafe;
		color: #1e40af;
		font-size: 0.625rem;
		border-radius: 0.25rem;
	}

	.workflow-result {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 0.125rem;
	}

	.workflow-name {
		font-size: 0.75rem;
		font-weight: 500;
		color: #166534;
		font-family: monospace;
	}

	.workflow-time {
		font-size: 0.625rem;
		color: #64748b;
	}

	.workflow-error {
		display: flex;
		align-items: center;
	}

	.error-message {
		font-size: 0.6875rem;
		color: #dc2626;
		text-align: right;
	}
</style>
