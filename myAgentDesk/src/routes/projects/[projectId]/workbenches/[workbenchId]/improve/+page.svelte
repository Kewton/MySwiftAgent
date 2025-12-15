<!--
  Improve Page (/projects/:projectId/workbenches/:workbenchId/improve)
  Issue #285: SvelteKit Routing Foundation

  Requirements improvement interface.
-->
<script lang="ts">
	// Improve page - params available via parent layout
</script>

<div class="improve-page">
	<div class="page-header">
		<h2>Improve Requirements</h2>
	</div>

	<div class="improve-content">
		<div class="content-section">
			<h3>Current Requirements (v2)</h3>
			<div class="requirements-preview">
				<p class="placeholder-text">Current requirements content will be displayed here.</p>
			</div>
		</div>

		<div class="content-section">
			<h3>Suggested Improvements</h3>
			<div class="suggestions-list">
				<div class="suggestion-item">
					<span class="suggestion-badge">AI Suggestion</span>
					<p>Consider adding error handling for API timeout scenarios.</p>
				</div>
				<div class="suggestion-item">
					<span class="suggestion-badge">From Analysis</span>
					<p>The data validation step could be optimized based on run logs.</p>
				</div>
			</div>
		</div>

		<div class="actions-section">
			<button class="action-button secondary">Discard Changes</button>
			<button class="action-button">Create New Version</button>
		</div>
	</div>
</div>

<style>
	.improve-page {
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

	.improve-content {
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

	.requirements-preview {
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		min-height: 100px;
	}

	.placeholder-text {
		color: #94a3b8;
		font-style: italic;
		margin: 0;
	}

	.suggestions-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.suggestion-item {
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
	}

	.suggestion-badge {
		display: inline-block;
		padding: 0.125rem 0.5rem;
		background: #eff6ff;
		color: #1e40af;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
		margin-bottom: 0.5rem;
	}

	.suggestion-item p {
		color: #1e293b;
		font-size: 0.875rem;
		margin: 0;
	}

	.actions-section {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 0.5rem;
	}

	.action-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
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
