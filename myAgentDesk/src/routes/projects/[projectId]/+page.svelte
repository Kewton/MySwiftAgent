<!--
  Project Dashboard (/projects/:projectId)
  Issue #288: Project screens implementation

  Project overview and dashboard with statistics and recent activity.
-->
<script lang="ts">
	import ProjectStats from '$lib/components/projects/ProjectStats.svelte';
	import RecentRunsList from '$lib/components/projects/RecentRunsList.svelte';
	import RecentSchedulesList from '$lib/components/projects/RecentSchedulesList.svelte';
	import EditableText from '$lib/components/ui/EditableText.svelte';
	import type {
		ProjectStats as ProjectStatsType,
		RunWithWorkbench,
		ScheduleWithWorkbench
	} from '$lib/types/project';
	import type { Project } from '$lib/server/db/schema';

	interface Props {
		data: {
			project: Project;
			stats: ProjectStatsType;
			recentRuns: RunWithWorkbench[];
			recentSchedules: ScheduleWithWorkbench[];
		};
	}

	let { data }: Props = $props();
</script>

<div class="project-dashboard">
	<div class="page-header">
		<h1>{data.project.name}</h1>
		<div class="description-container">
			<EditableText
				value={data.project.description}
				action="?/updateDescription"
				placeholder="Add a project description..."
				emptyText="Click to add description"
				multiline={true}
			/>
		</div>
	</div>

	<ProjectStats stats={data.stats} />

	<div class="dashboard-content">
		<div class="content-section">
			<RecentRunsList runs={data.recentRuns} projectId={data.project.id} />
		</div>
		<div class="content-section">
			<RecentSchedulesList schedules={data.recentSchedules} projectId={data.project.id} />
		</div>
	</div>

	<div class="quick-actions">
		<h2>Quick Actions</h2>
		<div class="actions-list">
			<a href="/projects/{data.project.id}/workbenches" class="action-button"> Open Workbenches </a>
			<a href="/projects/{data.project.id}/vault" class="action-button secondary">
				Configure Vault
			</a>
		</div>
	</div>
</div>

<style>
	.project-dashboard {
		max-width: 1000px;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.description-container {
		margin-top: 0.5rem;
	}

	.dashboard-content {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.5rem;
		margin-top: 1.5rem;
	}

	@media (max-width: 768px) {
		.dashboard-content {
			grid-template-columns: 1fr;
		}
	}

	.content-section {
		min-width: 0;
	}

	.quick-actions {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
		margin-top: 1.5rem;
	}

	.quick-actions h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.actions-list {
		display: flex;
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.action-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.375rem;
	}

	.action-button:hover {
		background: #2563eb;
	}

	.action-button.secondary {
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
	}

	.action-button.secondary:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}
</style>
