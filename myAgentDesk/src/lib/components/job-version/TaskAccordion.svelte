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
	import { formatJson } from '$lib/utils';

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

	interface Props {
		task: Task;
		index: number;
		expanded?: boolean;
	}

	let { task, index, expanded = false }: Props = $props();

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
		<div class="task-details" role="region" aria-label="Task interface details">
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

			{#if !task.inputInterface && !task.outputInterface}
				<p class="no-interfaces">No interface definitions available.</p>
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
</style>
