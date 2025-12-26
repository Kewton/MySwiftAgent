<!--
  TaskAccordion Component
  Issue #292: Review Page (JobVersion Detail)

  Displays a task from the task breakdown in an expandable accordion format.
  Shows task name, description, recommended APIs, and input/output interfaces.

  Props:
  - task: Task object with id, name, description, recommended_apis, interfaces
  - index: 0-based index of the task
  - expanded: Optional initial expanded state (default: false)
-->
<script lang="ts">
	import { formatJson, getLangfuseUrl } from '$lib/utils';
	import WorkflowViewer from './WorkflowViewer.svelte';

	interface TaskInterface {
		type?: string;
		properties?: Record<string, unknown>;
		required?: string[];
		[key: string]: unknown;
	}

	interface Task {
		task_id: string;
		name: string;
		description: string;
		recommended_apis?: string[];
		inputInterface?: TaskInterface | null;
		outputInterface?: TaskInterface | null;
	}

	interface WorkflowStatus {
		task_id: string;
		task_name: string;
		status: string;
		workflow_name: string | null;
		generation_time_ms: number | null;
		langfuse_trace_id: string | null;
		summary?: {
			yaml_preview?: string;
			yaml_content?: string;
			sample_input?: Record<string, unknown>;
			test_result?: Record<string, unknown>;
		} | null;
	}

	interface Props {
		task: Task;
		index: number;
		expanded?: boolean;
		workflow?: WorkflowStatus | null;
	}

	let { task, index, expanded = false, workflow = null }: Props = $props();

	// Local toggle state, managed separately for user interaction
	let localExpanded = $state<boolean | null>(null);

	// Effective expanded state: use local state if set, otherwise use prop
	const isExpanded = $derived(localExpanded !== null ? localExpanded : expanded);

	function toggleExpand() {
		localExpanded = !isExpanded;
	}
</script>

<article class="task-accordion" role="region" aria-labelledby="task-header-{task.task_id}">
	<div class="task-header" id="task-header-{task.task_id}">
		<div class="task-number" aria-hidden="true">{index + 1}</div>
		<div class="task-content">
			<div class="task-main">
				<span class="task-name">{task.name}</span>
				<p class="task-description">{task.description}</p>
			</div>
			{#if task.recommended_apis && task.recommended_apis.length > 0}
				<div class="task-apis">
					{#each task.recommended_apis as api, idx (idx)}
						<span class="api-tag">{api}</span>
					{/each}
				</div>
			{/if}
		</div>
		<button
			type="button"
			class="expand-button"
			onclick={toggleExpand}
			aria-expanded={isExpanded}
			aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
		>
			{isExpanded ? 'Hide' : 'Details'}
			<span class="icon" aria-hidden="true">{isExpanded ? '-' : '+'}</span>
		</button>
	</div>

	{#if isExpanded}
		<div class="task-details" role="region" aria-label="Task details">
			<!-- Workflow Section -->
			{#if workflow}
				<div class="workflow-section">
					<div class="workflow-header">
						<h4>Workflow</h4>
						<span
							class="workflow-status"
							class:success={workflow.status === 'success'}
							class:failed={workflow.status === 'failed'}
							class:pending={workflow.status === 'pending'}
						>
							{workflow.status}
						</span>
						{#if workflow.generation_time_ms}
							<span class="workflow-time">
								{(workflow.generation_time_ms / 1000).toFixed(1)}s
							</span>
						{/if}
						{#if workflow.langfuse_trace_id}
							<a
								href={getLangfuseUrl(workflow.langfuse_trace_id)}
								target="_blank"
								rel="noopener noreferrer"
								class="trace-link"
							>
								Trace
							</a>
						{/if}
					</div>
					{#if workflow.summary?.yaml_content}
						<WorkflowViewer
							yaml={workflow.summary.yaml_content}
							title={workflow.workflow_name ? `${workflow.workflow_name}.yaml` : 'Workflow YAML'}
							collapsible={false}
							collapsed={false}
							showLineNumbers={true}
						/>
					{:else}
						<p class="no-workflow">Workflow YAML not available.</p>
					{/if}
				</div>
			{:else}
				<p class="no-workflow">No workflow generated for this task.</p>
			{/if}

			<!-- Interface Section (hidden by default, shown for debugging) -->
			{#if task.inputInterface || task.outputInterface}
				<details class="interface-details">
					<summary>Interface Schemas</summary>
					{#if task.inputInterface}
						<div class="interface-section">
							<h4>Input Interface</h4>
							<pre class="json-display"><code class="language-json"
									>{formatJson(task.inputInterface)}</code
								></pre>
						</div>
					{/if}
					{#if task.outputInterface}
						<div class="interface-section">
							<h4>Output Interface</h4>
							<pre class="json-display"><code class="language-json"
									>{formatJson(task.outputInterface)}</code
								></pre>
						</div>
					{/if}
				</details>
			{/if}
		</div>
	{/if}
</article>

<style>
	.task-accordion {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: white;
		overflow: hidden;
	}

	.task-header {
		display: grid;
		grid-template-columns: 2.5rem 1fr auto;
		gap: 0.75rem;
		padding: 1rem;
		background: #f8fafc;
		align-items: start;
	}

	.task-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		background: #3b82f6;
		color: white;
		border-radius: 50%;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.task-content {
		min-width: 0;
	}

	.task-main {
		margin-bottom: 0.5rem;
	}

	.task-name {
		font-size: 0.9375rem;
		font-weight: 600;
		color: #1e293b;
	}

	.task-description {
		font-size: 0.8125rem;
		color: #64748b;
		margin: 0.25rem 0 0;
		line-height: 1.4;
	}

	.task-apis {
		display: flex;
		flex-wrap: wrap;
		gap: 0.375rem;
	}

	.api-tag {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		background: #dbeafe;
		color: #1e40af;
		font-size: 0.6875rem;
		font-family: monospace;
		border-radius: 0.25rem;
	}

	.expand-button {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.375rem 0.75rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
		transition: all 0.15s;
	}

	.expand-button:hover {
		background: #f1f5f9;
		color: #1e293b;
	}

	.icon {
		font-weight: bold;
		font-size: 0.875rem;
	}

	.task-details {
		padding: 1rem;
		border-top: 1px solid #e2e8f0;
		background: white;
	}

	.interface-section {
		margin-bottom: 1rem;
	}

	.interface-section:last-child {
		margin-bottom: 0;
	}

	.interface-section h4 {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #475569;
		margin: 0 0 0.5rem;
	}

	.json-display {
		margin: 0;
		padding: 0.75rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow-x: auto;
		font-size: 0.75rem;
		line-height: 1.5;
	}

	.json-display code {
		font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
		color: #334155;
	}

	.no-interfaces {
		font-size: 0.8125rem;
		color: #94a3b8;
		font-style: italic;
		margin: 0;
	}

	.workflow-section {
		margin-bottom: 1rem;
	}

	.workflow-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.workflow-header h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #334155;
	}

	.workflow-status {
		padding: 0.125rem 0.5rem;
		font-size: 0.6875rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: uppercase;
	}

	.workflow-status.success {
		background: #dcfce7;
		color: #166534;
	}

	.workflow-status.failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.workflow-status.pending {
		background: #fef3c7;
		color: #92400e;
	}

	.workflow-time {
		font-size: 0.75rem;
		color: #64748b;
	}

	.trace-link {
		display: inline-flex;
		align-items: center;
		padding: 0.125rem 0.375rem;
		background: #f0fdf4;
		border: 1px solid #86efac;
		border-radius: 0.25rem;
		font-size: 0.625rem;
		font-weight: 500;
		color: #15803d;
		text-decoration: none;
	}

	.trace-link:hover {
		background: #dcfce7;
	}

	.no-workflow {
		font-size: 0.8125rem;
		color: #94a3b8;
		font-style: italic;
		margin: 0;
		padding: 1rem;
		background: #f8fafc;
		border: 1px dashed #e2e8f0;
		border-radius: 0.375rem;
		text-align: center;
	}

	.interface-details {
		margin-top: 1rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow: hidden;
	}

	.interface-details summary {
		padding: 0.5rem 0.75rem;
		background: #f8fafc;
		font-size: 0.8125rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
	}

	.interface-details summary:hover {
		background: #f1f5f9;
		color: #334155;
	}

	.interface-details[open] summary {
		border-bottom: 1px solid #e2e8f0;
	}

	.interface-details .interface-section {
		padding: 0.75rem;
	}
</style>
