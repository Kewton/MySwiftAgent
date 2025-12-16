<!--
  Project Dashboard (/projects/:projectId)
  Issue #285: SvelteKit Routing Foundation

  Project overview and dashboard.
-->
<script lang="ts">
	interface Props {
		data: {
			project: {
				id: string;
				name: string;
			};
		};
	}

	let { data }: Props = $props();
</script>

<div class="project-dashboard">
	<div class="page-header">
		<h1>{data.project.name}</h1>
	</div>

	<div class="dashboard-grid">
		<div class="dashboard-card">
			<h3>Workbenches</h3>
			<p class="stat">3</p>
			<a href="/projects/{data.project.id}/workbenches" class="card-link">View all</a>
		</div>
		<div class="dashboard-card">
			<h3>Recent Runs</h3>
			<p class="stat">12</p>
			<span class="card-note">Last 7 days</span>
		</div>
		<div class="dashboard-card">
			<h3>Active Schedules</h3>
			<p class="stat">2</p>
			<span class="card-note">Running</span>
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
		margin: 0;
	}

	.dashboard-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.dashboard-card {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.dashboard-card h3 {
		font-size: 0.875rem;
		font-weight: 500;
		color: #64748b;
		margin: 0 0 0.5rem;
	}

	.stat {
		font-size: 2rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.card-link {
		font-size: 0.875rem;
		color: #3b82f6;
		text-decoration: none;
	}

	.card-link:hover {
		text-decoration: underline;
	}

	.card-note {
		font-size: 0.75rem;
		color: #94a3b8;
	}

	.quick-actions {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
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
