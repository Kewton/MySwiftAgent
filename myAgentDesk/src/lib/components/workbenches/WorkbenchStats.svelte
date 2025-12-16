<!--
  WorkbenchStats Component
  Issue #289: Workbench List/Detail Screens

  Displays statistical information for a workbench.
  Used in the workbench detail overview panel.
-->
<script lang="ts">
	import type { WorkbenchStats } from '$lib/types/workbench';

	interface Props {
		stats: WorkbenchStats;
	}

	let { stats }: Props = $props();

	const successRateClass = $derived(
		stats.successRate >= 80
			? 'text-success'
			: stats.successRate >= 50
				? 'text-warning'
				: 'text-danger'
	);

	const formatDate = (date: Date | null): string => {
		if (!date) return 'Never';
		return new Date(date).toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};
</script>

<div class="stats-container" data-testid="workbench-stats">
	<div class="stats-grid">
		<div class="stat-card" data-testid="stat-total-runs">
			<span class="stat-label">Total Runs</span>
			<span class="stat-value">{stats.totalRuns}</span>
		</div>

		<div class="stat-card" data-testid="stat-success-rate">
			<span class="stat-label">Success Rate</span>
			<span class="stat-value {successRateClass}">{stats.successRate}%</span>
		</div>

		<div class="stat-card" data-testid="stat-active-schedules">
			<span class="stat-label">Active Schedules</span>
			<span class="stat-value">{stats.activeSchedules}</span>
		</div>

		<div class="stat-card" data-testid="stat-pending-runs">
			<span class="stat-label">Pending Runs</span>
			<span class="stat-value">{stats.pendingRuns}</span>
		</div>
	</div>

	<div class="stats-detail">
		<div class="detail-row">
			<span class="detail-label">Successful Runs</span>
			<span class="detail-value text-success">{stats.successfulRuns}</span>
		</div>
		<div class="detail-row">
			<span class="detail-label">Failed Runs</span>
			<span class="detail-value text-danger">{stats.failedRuns}</span>
		</div>
		<div class="detail-row">
			<span class="detail-label">Last Run</span>
			<span class="detail-value">{formatDate(stats.lastRunAt)}</span>
		</div>
	</div>
</div>

<style>
	.stats-container {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.75rem;
	}

	@media (min-width: 640px) {
		.stats-grid {
			grid-template-columns: repeat(4, 1fr);
		}
	}

	.stat-card {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.stat-label {
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 600;
		color: #1e293b;
	}

	.stats-detail {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.detail-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.detail-label {
		font-size: 0.875rem;
		color: #64748b;
	}

	.detail-value {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.text-success {
		color: #16a34a;
	}

	.text-warning {
		color: #d97706;
	}

	.text-danger {
		color: #dc2626;
	}
</style>
