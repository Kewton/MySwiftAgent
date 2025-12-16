<!--
  SecretsList Component
  Issue #288: Project screens implementation

  Displays a list of vault secrets for a project.
-->
<script lang="ts">
	import type { VaultSecretItem } from '$lib/types/project';

	interface Props {
		secrets: VaultSecretItem[];
		onTestConnection?: (key: string) => void;
	}

	let { secrets, onTestConnection }: Props = $props();

	function handleTestConnection(key: string) {
		if (onTestConnection) {
			onTestConnection(key);
		}
	}
</script>

<div class="secrets-section">
	<div class="section-header">
		<h2>API Keys & Secrets</h2>
	</div>

	{#if secrets.length === 0}
		<div class="empty-state">
			<p>No secrets configured yet.</p>
			<button class="add-button">Add Secret</button>
		</div>
	{:else}
		<div class="secrets-list">
			{#each secrets as secret (secret.key)}
				<div class="secret-item">
					<div class="secret-info">
						<span class="secret-key">{secret.key}</span>
						<span class="secret-description">{secret.description || 'No description'}</span>
					</div>
					<div class="secret-actions">
						<span class="connection-status {secret.isConnected ? 'connected' : 'disconnected'}">
							{secret.isConnected ? 'Connected' : 'Not Connected'}
						</span>
						<button
							class="test-button"
							onclick={() => handleTestConnection(secret.key)}
							aria-label="Test connection for {secret.key}"
						>
							Test
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.secrets-section {
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

	.secrets-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.secret-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.secret-info {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.secret-key {
		font-size: 0.875rem;
		font-weight: 500;
		font-family: monospace;
		color: #1e293b;
	}

	.secret-description {
		font-size: 0.75rem;
		color: #64748b;
	}

	.secret-actions {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.connection-status {
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
	}

	.connection-status.connected {
		background: #dcfce7;
		color: #166534;
	}

	.connection-status.disconnected {
		background: #fef3c7;
		color: #92400e;
	}

	.test-button {
		padding: 0.375rem 0.75rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
		color: #64748b;
		cursor: pointer;
	}

	.test-button:hover {
		border-color: #3b82f6;
		color: #3b82f6;
	}
</style>
