<!--
  Generate Page (/projects/:projectId/workbenches/:workbenchId/generate)
  Issue #285: SvelteKit Routing Foundation

  Job generation interface.
-->
<script lang="ts">
	// Generate page - params available via parent layout
	let generating = $state(false);
</script>

<div class="generate-page">
	<div class="page-header">
		<h2>Generate Job</h2>
	</div>

	<div class="generate-content">
		<div class="status-card">
			<h3>Generation Status</h3>
			{#if generating}
				<div class="status-indicator running">
					<span class="spinner"></span>
					Generating...
				</div>
			{:else}
				<div class="status-indicator idle">Ready to generate</div>
			{/if}
		</div>

		<div class="action-card">
			<h3>Start Generation</h3>
			<p>Generate a new job based on the active requirements.</p>
			<button class="generate-button" disabled={generating} onclick={() => (generating = true)}>
				{generating ? 'Generating...' : 'Generate Job'}
			</button>
		</div>
	</div>
</div>

<style>
	.generate-page {
		max-width: 800px;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.generate-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.status-card,
	.action-card {
		padding: 1.5rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
	}

	.status-card h3,
	.action-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.action-card p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 1rem;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-indicator.idle {
		background: #eff6ff;
		color: #1e40af;
	}

	.status-indicator.running {
		background: #fef3c7;
		color: #92400e;
	}

	.spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.generate-button {
		padding: 0.75rem 1.5rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s;
	}

	.generate-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.generate-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
