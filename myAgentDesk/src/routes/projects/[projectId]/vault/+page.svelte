<!--
  Vault Settings Page (/projects/:projectId/vault)
  Issue #288: Project screens implementation

  API key and secrets management for the project.
-->
<script lang="ts">
	import SecretsList from '$lib/components/projects/SecretsList.svelte';
	import type { VaultSecretItem, VaultConnectionStatus } from '$lib/types/project';
	import type { Project } from '$lib/server/db/schema';

	interface Props {
		data: {
			project: Project;
			secrets: VaultSecretItem[];
			connectionStatus: VaultConnectionStatus;
		};
	}

	let { data }: Props = $props();

	function getStatusClass(status: VaultConnectionStatus): string {
		switch (status) {
			case 'connected':
				return 'status-connected';
			case 'testing':
				return 'status-testing';
			case 'error':
				return 'status-error';
			default:
				return 'status-disconnected';
		}
	}

	function getStatusLabel(status: VaultConnectionStatus): string {
		switch (status) {
			case 'connected':
				return 'Connected';
			case 'testing':
				return 'Testing...';
			case 'error':
				return 'Error';
			default:
				return 'Not Connected';
		}
	}

	function handleTestConnection(key: string) {
		// TODO: Implement connection test via API
		console.log('Testing connection for:', key);
	}
</script>

<div class="vault-page">
	<div class="page-header">
		<h1>Vault Settings</h1>
		<p class="description">Manage API keys and secrets for {data.project.name}.</p>
	</div>

	<div class="vault-content">
		<SecretsList secrets={data.secrets} onTestConnection={handleTestConnection} />

		<div class="vault-section">
			<h2>Connection Status</h2>
			<div class="status-list">
				<div class="status-item">
					<span class="status-label">myVault Connection</span>
					<span class="status-badge {getStatusClass(data.connectionStatus)}">
						{getStatusLabel(data.connectionStatus)}
					</span>
				</div>
			</div>
			{#if data.connectionStatus === 'disconnected'}
				<div class="warning-banner">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="16"
						height="16"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path
							d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
						></path>
						<line x1="12" y1="9" x2="12" y2="13"></line>
						<line x1="12" y1="17" x2="12.01" y2="17"></line>
					</svg>
					<span>Vault connection is not configured. Some features may be unavailable.</span>
				</div>
			{/if}
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

	.status-connected {
		background: #dcfce7;
		color: #166534;
	}

	.status-disconnected {
		background: #fef3c7;
		color: #92400e;
	}

	.status-testing {
		background: #dbeafe;
		color: #1e40af;
	}

	.status-error {
		background: #fee2e2;
		color: #991b1b;
	}

	.warning-banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1rem;
		padding: 0.75rem;
		background: #fef3c7;
		color: #92400e;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	.warning-banner svg {
		flex-shrink: 0;
	}
</style>
