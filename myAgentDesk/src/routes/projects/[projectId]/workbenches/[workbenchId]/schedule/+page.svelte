<!--
  Schedule Page (/projects/:projectId/workbenches/:workbenchId/schedule)
  Issue #285: SvelteKit Routing Foundation

  Schedule management interface.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Mock schedules - will be loaded from API in future iterations
	const schedules = $state([
		{ id: 'sched_001', name: 'Daily Report', cron: '0 9 * * *', status: 'active' },
		{ id: 'sched_002', name: 'Weekly Analysis', cron: '0 6 * * 1', status: 'paused' }
	]);
</script>

<div class="schedule-page">
	<div class="page-header">
		<h2>Schedules</h2>
		<button class="create-button">New Schedule</button>
	</div>

	<div class="schedules-list">
		{#each schedules as schedule (schedule.id)}
			<a
				href="/projects/{projectId}/workbenches/{workbenchId}/schedule/{schedule.id}"
				class="schedule-item"
			>
				<div class="schedule-info">
					<span class="schedule-name">{schedule.name}</span>
					<span class="schedule-cron">{schedule.cron}</span>
				</div>
				<span class="schedule-status" data-status={schedule.status}>{schedule.status}</span>
			</a>
		{:else}
			<div class="empty-state">
				<p>No schedules configured yet. Create a schedule to automate runs.</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.schedule-page {
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

	.create-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.create-button:hover {
		background: #2563eb;
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
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		text-decoration: none;
		transition: border-color 0.15s;
	}

	.schedule-item:hover {
		border-color: #3b82f6;
	}

	.schedule-info {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.schedule-name {
		font-weight: 600;
		color: #1e293b;
	}

	.schedule-cron {
		font-family: monospace;
		font-size: 0.875rem;
		color: #64748b;
		background: #e2e8f0;
		padding: 0.125rem 0.5rem;
		border-radius: 0.25rem;
	}

	.schedule-status {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		text-transform: capitalize;
	}

	.schedule-status[data-status='active'] {
		background: #dcfce7;
		color: #166534;
	}

	.schedule-status[data-status='paused'] {
		background: #fef3c7;
		color: #92400e;
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
</style>
