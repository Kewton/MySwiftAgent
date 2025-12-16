<!--
  ProjectStats Component
  Issue #288: Project screens implementation

  Displays project statistics in a dashboard grid.
-->
<script lang="ts">
	import type { ProjectStats as ProjectStatsType } from '$lib/types/project';

	interface Props {
		stats: ProjectStatsType;
	}

	let { stats }: Props = $props();
</script>

<div class="stats-grid">
	<div class="stat-card">
		<h3 class="stat-label">Workbenches</h3>
		<p class="stat-value">{stats.workbenchCount}</p>
	</div>
	<div class="stat-card">
		<h3 class="stat-label">Recent Runs</h3>
		<p class="stat-value">{stats.recentRunCount}</p>
		<span class="stat-note">Last 7 days</span>
	</div>
	<div class="stat-card">
		<h3 class="stat-label">Active Schedules</h3>
		<p class="stat-value">{stats.activeScheduleCount}</p>
		<span class="stat-note">Enabled</span>
	</div>
</div>

<style>
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 1rem;
	}

	.stat-card {
		background: white;
		padding: 1.25rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.stat-label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #64748b;
		margin: 0 0 0.5rem;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0;
	}

	.stat-note {
		font-size: 0.75rem;
		color: #94a3b8;
	}
</style>
