<script lang="ts">
	// Pattern A: シンプル・ミニマル
	// 最小限のUI。全体進捗のみ表示。

	let currentState = $state<'idle' | 'analyzing' | 'workflow' | 'success' | 'partial_success'>('idle');
	let progress = $state(0);
	let statusMessage = $state('Ready to generate');

	const phases = {
		idle: { label: 'Ready', progress: 0, message: 'Ready to generate' },
		analyzing: { label: 'Analyzing', progress: 35, message: 'Analyzing requirements...' },
		workflow: { label: 'Generating', progress: 75, message: 'Generating workflows...' },
		success: { label: 'Complete', progress: 100, message: 'All workflows generated successfully' },
		partial_success: { label: 'Partial', progress: 100, message: '2/3 workflows generated' }
	};

	function startGeneration() {
		currentState = 'analyzing';
		progress = 0;
		simulateProgress();
	}

	function simulateProgress() {
		const states: Array<'analyzing' | 'workflow' | 'success'> = ['analyzing', 'workflow', 'success'];
		let stateIndex = 0;

		const interval = setInterval(() => {
			if (stateIndex < states.length) {
				currentState = states[stateIndex];
				progress = phases[currentState].progress;
				statusMessage = phases[currentState].message;
				stateIndex++;
			} else {
				clearInterval(interval);
			}
		}, 2000);
	}

	function reset() {
		currentState = 'idle';
		progress = 0;
		statusMessage = phases.idle.message;
	}

	function showPartialSuccess() {
		currentState = 'partial_success';
		progress = 100;
		statusMessage = phases.partial_success.message;
	}
</script>

<div class="pattern-a">
	<div class="demo-controls">
		<span class="demo-label">Demo Controls:</span>
		<button onclick={startGeneration} disabled={currentState !== 'idle'}>Start Generation</button>
		<button onclick={showPartialSuccess}>Partial Success</button>
		<button onclick={reset}>Reset</button>
	</div>

	<div class="generate-page">
		<div class="page-header">
			<h2>Generate Job</h2>
			<p class="workbench-name">Email Summarizer</p>
		</div>

		<!-- Active Requirement Version -->
		<div class="section-card">
			<h3>Active Requirement Version</h3>
			<div class="requirement-info">
				<span class="version-badge">v1</span>
				<span class="status-badge">active</span>
			</div>
		</div>

		<!-- Generation Status - Pattern A: Minimal -->
		<div class="section-card">
			<h3>Generation Status</h3>

			{#if currentState === 'idle'}
				<div class="status-indicator idle">
					<span class="status-icon">-</span>
					<span>Ready to generate</span>
				</div>
			{:else if currentState === 'analyzing' || currentState === 'workflow'}
				<div class="status-indicator running">
					<span class="spinner"></span>
					<div class="status-text">
						<span class="status-main">{statusMessage}</span>
						<span class="status-phase">
							Phase: {currentState === 'analyzing' ? 'Task Analysis' : 'Workflow Generation'}
						</span>
					</div>
				</div>
				<div class="progress-bar">
					<div class="progress-fill" style="width: {progress}%"></div>
				</div>
				<div class="progress-label">{progress}%</div>
			{:else if currentState === 'success'}
				<div class="status-indicator success">
					<span class="success-icon">OK</span>
					<div class="status-text">
						<span class="status-main">Generation Complete</span>
						<span class="status-detail">3 tasks, 3 workflows generated</span>
					</div>
				</div>
			{:else if currentState === 'partial_success'}
				<div class="status-indicator warning">
					<span class="warning-icon">!</span>
					<div class="status-text">
						<span class="status-main">Partial Success</span>
						<span class="status-detail">2/3 workflows generated, 1 failed</span>
					</div>
				</div>
			{/if}
		</div>

		<!-- Generate Button -->
		<div class="section-card action-card">
			<h3>Start Generation</h3>
			<p>Generate a new job with automatic workflow generation.</p>
			<button
				class="generate-button"
				disabled={currentState !== 'idle' && currentState !== 'success' && currentState !== 'partial_success'}
				onclick={startGeneration}
			>
				{#if currentState === 'analyzing' || currentState === 'workflow'}
					Generating...
				{:else}
					Generate Job
				{/if}
			</button>
		</div>

		<!-- Result Summary (shown after completion) -->
		{#if currentState === 'success' || currentState === 'partial_success'}
			<div class="section-card">
				<h3>Generation Result</h3>
				<div class="result-summary">
					<div class="result-item">
						<span class="result-label">Status</span>
						<span class="result-value {currentState}">
							{currentState === 'success' ? 'Success' : 'Partial Success'}
						</span>
					</div>
					<div class="result-item">
						<span class="result-label">Workflows</span>
						<span class="result-value">
							{currentState === 'success' ? '3/3' : '2/3'}
						</span>
					</div>
					<a href="#" class="trace-link">View in Langfuse</a>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.pattern-a {
		padding: 1rem;
	}

	.demo-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #fef3c7;
		border: 1px solid #fcd34d;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
	}

	.demo-label {
		font-weight: 600;
		color: #92400e;
	}

	.demo-controls button {
		padding: 0.25rem 0.5rem;
		background: white;
		border: 1px solid #d97706;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.demo-controls button:hover:not(:disabled) {
		background: #fef3c7;
	}

	.demo-controls button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.generate-page {
		max-width: 600px;
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

	.workbench-name {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0.25rem 0 0;
	}

	.section-card {
		padding: 1.25rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
	}

	.section-card h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
	}

	.requirement-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.version-badge {
		padding: 0.125rem 0.5rem;
		background: #dbeafe;
		color: #1e40af;
		font-size: 0.75rem;
		font-weight: 600;
		border-radius: 0.25rem;
	}

	.status-badge {
		padding: 0.125rem 0.5rem;
		background: #dcfce7;
		color: #166534;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
	}

	.status-indicator.idle {
		background: #f1f5f9;
		color: #64748b;
	}

	.status-indicator.running {
		background: #fef3c7;
		color: #92400e;
	}

	.status-indicator.success {
		background: #dcfce7;
		color: #166534;
	}

	.status-indicator.warning {
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

	.status-icon,
	.success-icon,
	.warning-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.status-icon {
		background: #94a3b8;
		color: white;
	}

	.success-icon {
		background: #166534;
		color: white;
	}

	.warning-icon {
		background: #d97706;
		color: white;
	}

	.status-text {
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.status-main {
		font-weight: 600;
	}

	.status-detail,
	.status-phase {
		font-size: 0.75rem;
		opacity: 0.8;
	}

	.progress-bar {
		margin-top: 0.75rem;
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #10b981;
		transition: width 0.3s ease;
	}

	.progress-label {
		margin-top: 0.25rem;
		font-size: 0.75rem;
		color: #64748b;
		text-align: right;
	}

	.action-card p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0 0 1rem;
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
	}

	.generate-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.generate-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.result-summary {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.result-item {
		display: flex;
		justify-content: space-between;
		padding: 0.5rem 0;
		border-bottom: 1px solid #f1f5f9;
	}

	.result-label {
		font-size: 0.875rem;
		color: #64748b;
	}

	.result-value {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.result-value.success {
		color: #166534;
	}

	.result-value.partial_success {
		color: #d97706;
	}

	.trace-link {
		display: inline-block;
		margin-top: 0.5rem;
		font-size: 0.875rem;
		color: #3b82f6;
		text-decoration: none;
	}

	.trace-link:hover {
		text-decoration: underline;
	}
</style>
