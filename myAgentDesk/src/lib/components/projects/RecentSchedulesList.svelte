<!--
  RecentSchedulesList Component
  Issue #288: Project screens implementation

  Displays a list of schedules for a project.
-->
<script lang="ts">
	import type { ScheduleWithWorkbench } from '$lib/types/project';

	interface Props {
		schedules: ScheduleWithWorkbench[];
		projectId: string;
	}

	let { schedules, projectId }: Props = $props();
</script>

<div class="schedules-section">
	<div class="section-header">
		<h2>Schedules</h2>
	</div>

	{#if schedules.length === 0}
		<div class="empty-state">
			<p>No schedules configured.</p>
		</div>
	{:else}
		<div class="schedules-list">
			{#each schedules as schedule (schedule.id)}
				<a
					href="/projects/{projectId}/workbenches/{schedule.workbenchId}/schedule/{schedule.id}"
					class="schedule-item"
				>
					<div class="schedule-info">
						<span class="schedule-name">{schedule.name}</span>
						<span class="workbench-name">{schedule.workbench.name}</span>
						<span class="cron-expression">{schedule.cronExpression}</span>
					</div>
					<span class="status-badge {schedule.isEnabled ? 'enabled' : 'disabled'}">
						{schedule.isEnabled ? 'Enabled' : 'Disabled'}
					</span>
				</a>
			{/each}
		</div>
	{/if}
</div>

<style>
	.schedules-section {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.section-header h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
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

	.schedules-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.schedule-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 0.375rem;
		text-decoration: none;
		transition: background 0.15s;
	}

	.schedule-item:hover {
		background: #f1f5f9;
	}

	.schedule-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.schedule-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.workbench-name {
		font-size: 0.75rem;
		color: #64748b;
	}

	.cron-expression {
		font-size: 0.75rem;
		font-family: monospace;
		color: #64748b;
		background: #e2e8f0;
		padding: 0.125rem 0.375rem;
		border-radius: 0.25rem;
		width: fit-content;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.status-badge.enabled {
		background: #dcfce7;
		color: #166534;
	}

	.status-badge.disabled {
		background: #f3f4f6;
		color: #6b7280;
	}
</style>
