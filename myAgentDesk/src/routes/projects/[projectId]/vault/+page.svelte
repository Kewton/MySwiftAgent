<!--
  Vault Settings Page (/projects/:projectId/vault)
  Issue #285: SvelteKit Routing Foundation

  API key and secrets management for the project.
-->
<script lang="ts">
	// Vault page - projectId available via parent layout
</script>

<div class="vault-page">
	<div class="page-header">
		<h1>Vault Settings</h1>
		<p class="description">Manage API keys and secrets for this project.</p>
	</div>

	<div class="vault-content">
		<div class="vault-section">
			<h2>API Keys</h2>
			<div class="empty-state">
				<p>No API keys configured yet.</p>
				<button class="add-button">Add API Key</button>
			</div>
		</div>

		<div class="vault-section">
			<h2>Connection Status</h2>
			<div class="status-list">
				<div class="status-item">
					<span class="status-label">myVault Connection</span>
					<span class="status-badge pending">Not Connected</span>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.vault-page {
		max-width: 800px;
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

	.description {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	.vault-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.vault-section {
		background: white;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
	}

	.vault-section h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.empty-state {
		text-align: center;
		padding: 2rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.empty-state p {
		color: #64748b;
		margin: 0 0 1rem;
	}

	.add-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.add-button:hover {
		background: #2563eb;
	}

	.status-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.status-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.status-label {
		font-size: 0.875rem;
		color: #1e293b;
	}

	.status-badge {
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.status-badge.pending {
		background: #fef3c7;
		color: #92400e;
	}
</style>
