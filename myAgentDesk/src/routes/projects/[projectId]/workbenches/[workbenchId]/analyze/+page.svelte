<!--
  Analyze Page (/projects/:projectId/workbenches/:workbenchId/analyze)
  Issue #285: SvelteKit Routing Foundation

  Analysis dashboard with Langfuse integration.
-->
<script lang="ts">
	// Analyze page - params available via parent layout
</script>

<div class="analyze-page">
	<div class="page-header">
		<h2>Analyze Results</h2>
	</div>

	<div class="analyze-content">
		<div class="content-section">
			<h3>Recent Runs Summary</h3>
			<div class="summary-grid">
				<div class="summary-card">
					<span class="summary-value">5</span>
					<span class="summary-label">Total Runs</span>
				</div>
				<div class="summary-card">
					<span class="summary-value">4</span>
					<span class="summary-label">Successful</span>
				</div>
				<div class="summary-card">
					<span class="summary-value">1</span>
					<span class="summary-label">Failed</span>
				</div>
				<div class="summary-card">
					<span class="summary-value">2m 15s</span>
					<span class="summary-label">Avg Duration</span>
				</div>
			</div>
		</div>

		<div class="content-section">
			<h3>Langfuse Integration</h3>
			<div class="langfuse-card">
				<p>View detailed traces and analytics in Langfuse.</p>
				<button class="external-link">Open Langfuse Dashboard</button>
			</div>
		</div>

		<div class="content-section">
			<h3>Insights</h3>
			<div class="placeholder-content">
				<p>Analysis insights will be displayed here.</p>
			</div>
		</div>
	</div>
</div>

<style>
	.analyze-page {
		max-width: 900px;
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

	.analyze-content {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.content-section {
		padding: 1rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
	}

	.content-section h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
	}

	.summary-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
	}

	.summary-card {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 1rem;
		background: white;
		border-radius: 0.25rem;
	}

	.summary-value {
		font-size: 1.5rem;
		font-weight: 700;
		color: #1e293b;
	}

	.summary-label {
		font-size: 0.75rem;
		color: #64748b;
		margin-top: 0.25rem;
	}

	.langfuse-card {
		padding: 1rem;
		background: white;
		border-radius: 0.25rem;
		text-align: center;
	}

	.langfuse-card p {
		color: #64748b;
		margin: 0 0 1rem;
	}

	.external-link {
		display: inline-block;
		padding: 0.5rem 1rem;
		background: #8b5cf6;
		color: white;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.375rem;
		border: none;
		cursor: pointer;
	}

	.external-link:hover {
		background: #7c3aed;
	}

	.placeholder-content {
		padding: 1.5rem;
		background: white;
		border: 1px dashed #e2e8f0;
		border-radius: 0.25rem;
		text-align: center;
	}

	.placeholder-content p {
		color: #94a3b8;
		font-style: italic;
		margin: 0;
	}
</style>
