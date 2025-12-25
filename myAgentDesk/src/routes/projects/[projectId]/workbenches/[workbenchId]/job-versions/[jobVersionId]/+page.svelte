<!--
  Job Version Detail (/projects/:projectId/workbenches/:workbenchId/job-versions/:jobVersionId)
  Issue #292: Review Page (JobVersion Detail)

  Shows job version details including tasks, interfaces, and workflows.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import TaskAccordion from '$lib/components/job-version/TaskAccordion.svelte';
	import InterfaceViewer from '$lib/components/job-version/InterfaceViewer.svelte';
	import WorkflowViewer from '$lib/components/job-version/WorkflowViewer.svelte';
	import { formatDate, getStatusConfig, getLangfuseUrl, canStartRun } from '$lib/utils';

	const { data }: { data: PageData } = $props();

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	const jv = $derived(data.jobVersion);
</script>

<div class="jv-detail-page">
	<div class="page-header">
		<div class="header-info">
			<a href="/projects/{projectId}/workbenches/{workbenchId}/review" class="back-link">
				&larr; Back to Review
			</a>
			<h2>Job Version: {jv.versionLabel}</h2>
			<div class="meta">
				<span class="jv-status {getStatusConfig(jv.status).class}"
					>{getStatusConfig(jv.status).label}</span
				>
				<span class="meta-item">
					from
					<a
						href="/projects/{projectId}/workbenches/{workbenchId}/requirements/{jv
							.sourceRequirementVersion.id}"
						class="req-link"
					>
						Requirement v{jv.sourceRequirementVersion.version}
					</a>
				</span>
				<span class="meta-item">Generated: {formatDate(jv.generatedAt)}</span>
				{#if jv.externalTraceId && getLangfuseUrl(jv.externalTraceId)}
					<a
						href={getLangfuseUrl(jv.externalTraceId)}
						target="_blank"
						rel="noopener noreferrer"
						class="trace-link"
					>
						View Trace
					</a>
				{/if}
			</div>
		</div>
		<div class="actions">
			{#if canStartRun(jv.status)}
				<a
					href="/projects/{projectId}/workbenches/{workbenchId}/runs?start={jv.id}"
					class="action-button primary"
				>
					Start Run
				</a>
			{/if}
		</div>
	</div>

	<!-- Tasks Section -->
	<section class="content-section">
		<h3>
			<span class="section-icon">1</span>
			Task Breakdown
			<span class="task-count">{jv.tasks.length} tasks</span>
		</h3>
		{#if jv.tasks.length > 0}
			<div class="tasks-list">
				{#each jv.tasks as task, index (task.task_id)}
					<TaskAccordion {task} {index} />
				{/each}
			</div>
		{:else}
			<div class="empty-content">
				<p>No task breakdown available.</p>
			</div>
		{/if}
	</section>

	<!-- Interface Definitions Section -->
	<section class="content-section">
		<h3>
			<span class="section-icon">2</span>
			Interface Definitions
		</h3>
		<div class="interface-grid">
			<InterfaceViewer schema={jv.interfaceDefinitions.inputSchema} title="Input Schema" />
			<InterfaceViewer schema={jv.interfaceDefinitions.outputSchema} title="Output Schema" />
		</div>
	</section>

	<!-- Workflows Section -->
	<section class="content-section">
		<h3>
			<span class="section-icon">3</span>
			Generated Workflows
			<span class="workflow-count">{jv.workflows.length} workflows</span>
		</h3>
		{#if jv.workflows.length > 0}
			<div class="workflows-list">
				{#each jv.workflows as workflow (workflow.task_id)}
					<div class="workflow-item">
						<div class="workflow-header">
							<span class="workflow-name">{workflow.task_name}</span>
							<span
								class="workflow-status"
								class:success={workflow.status === 'success'}
								class:failed={workflow.status === 'failed'}
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
									class="trace-link small"
								>
									Trace
								</a>
							{/if}
						</div>
						{#if workflow.summary?.yaml_content}
							<WorkflowViewer
								yaml={workflow.summary.yaml_content}
								title={workflow.workflow_name ? `${workflow.workflow_name}.yaml` : 'Workflow'}
								collapsible={true}
								collapsed={true}
								showLineNumbers={true}
							/>
						{/if}
					</div>
				{/each}
			</div>
		{:else}
			<div class="empty-content">
				<p>No workflows generated yet.</p>
			</div>
		{/if}
	</section>
</div>

<style>
	.jv-detail-page {
		max-width: 1000px;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 2rem;
		gap: 1rem;
	}

	.header-info {
		flex: 1;
	}

	.back-link {
		display: inline-block;
		font-size: 0.8125rem;
		color: #64748b;
		text-decoration: none;
		margin-bottom: 0.5rem;
	}

	.back-link:hover {
		color: #3b82f6;
	}

	h2 {
		font-size: 1.5rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.meta {
		display: flex;
		align-items: center;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.jv-status {
		padding: 0.25rem 0.625rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.status-generating {
		background: #fef3c7;
		color: #92400e;
	}

	.status-success {
		background: #dcfce7;
		color: #166534;
	}

	.status-failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.status-active {
		background: #dbeafe;
		color: #1e40af;
	}

	.status-deprecated {
		background: #f1f5f9;
		color: #64748b;
	}

	.meta-item {
		font-size: 0.8125rem;
		color: #64748b;
	}

	.req-link {
		color: #3b82f6;
		text-decoration: none;
	}

	.req-link:hover {
		text-decoration: underline;
	}

	.trace-link {
		display: inline-flex;
		align-items: center;
		padding: 0.25rem 0.5rem;
		background: #f0fdf4;
		border: 1px solid #86efac;
		border-radius: 0.25rem;
		font-size: 0.6875rem;
		font-weight: 500;
		color: #15803d;
		text-decoration: none;
	}

	.trace-link:hover {
		background: #dcfce7;
	}

	.trace-link.small {
		padding: 0.125rem 0.375rem;
		font-size: 0.625rem;
	}

	.actions {
		display: flex;
		gap: 0.5rem;
	}

	.action-button {
		padding: 0.5rem 1rem;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		text-decoration: none;
		cursor: pointer;
		transition: background 0.15s;
	}

	.action-button.primary {
		background: #3b82f6;
		color: white;
	}

	.action-button.primary:hover {
		background: #2563eb;
	}

	.content-section {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
	}

	.content-section h3 {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.section-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #3b82f6;
		color: white;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.task-count,
	.workflow-count {
		margin-left: auto;
		font-size: 0.8125rem;
		font-weight: 400;
		color: #64748b;
	}

	.tasks-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.interface-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 1rem;
	}

	.workflows-list {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.workflow-item {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.workflow-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: #f8fafc;
		border-bottom: 1px solid #e2e8f0;
	}

	.workflow-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.workflow-status {
		padding: 0.125rem 0.375rem;
		font-size: 0.625rem;
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

	.workflow-time {
		font-size: 0.75rem;
		color: #64748b;
		margin-left: auto;
	}

	.empty-content {
		padding: 2rem;
		background: #f8fafc;
		border: 1px dashed #e2e8f0;
		border-radius: 0.375rem;
		text-align: center;
	}

	.empty-content p {
		margin: 0;
		color: #94a3b8;
		font-size: 0.875rem;
	}
</style>
