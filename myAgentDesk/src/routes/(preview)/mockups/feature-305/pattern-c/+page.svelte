<script lang="ts">
	// Pattern C: リッチ・高機能
	// 詳細なワークフロー情報とYAMLプレビュー。

	interface TaskStatus {
		id: string;
		name: string;
		status: 'pending' | 'generating' | 'success' | 'failed';
		workflowName?: string;
		yamlContent?: string;
		errorMessage?: string;
		generationTimeMs?: number;
		retryCount?: number;
		validationResult?: {
			valid: boolean;
			warnings?: string[];
		};
	}

	let currentState = $state<'idle' | 'analyzing' | 'workflow' | 'success' | 'partial_success'>('idle');
	let progress = $state(0);
	let expandedTask = $state<string | null>(null);
	let traceId = $state<string | null>(null);

	let tasks = $state<TaskStatus[]>([
		{
			id: 'tm_001',
			name: 'Gmail未読メール取得',
			status: 'pending',
			yamlContent: `nodes:
  fetchGmail:
    type: gmail_fetch
    params:
      query: "is:unread"
      maxResults: 10
    outputs:
      - emails

  formatEmails:
    type: transform
    inputs:
      - :fetchGmail.emails
    params:
      template: "{{subject}}: {{snippet}}"
    outputs:
      - formatted`
		},
		{
			id: 'tm_002',
			name: 'Claude要約生成',
			status: 'pending',
			yamlContent: `nodes:
  summarize:
    type: llm_call
    inputs:
      - :formatted
    params:
      model: claude-sonnet-4-20250514
      prompt: "Summarize these emails concisely"
    outputs:
      - summary`
		},
		{
			id: 'tm_003',
			name: 'Slack投稿',
			status: 'pending',
			yamlContent: `nodes:
  postSlack:
    type: slack_post
    inputs:
      - :summary
    params:
      channel: "#general"
      format: "markdown"`
		}
	]);

	function startGeneration() {
		currentState = 'analyzing';
		progress = 0;
		traceId = 'trace_' + Math.random().toString(36).substring(7);
		tasks = tasks.map((t) => ({
			...t,
			status: 'pending' as const,
			errorMessage: undefined,
			retryCount: undefined,
			validationResult: undefined
		}));
		simulateProgress();
	}

	async function simulateProgress() {
		await animate(0, 70, 1500);
		currentState = 'workflow';

		for (let i = 0; i < tasks.length; i++) {
			tasks[i].status = 'generating';
			await animate(70 + (i * 25) / tasks.length, 70 + ((i + 1) * 25) / tasks.length, 2000);

			tasks[i].status = 'success';
			tasks[i].workflowName = `workflow_${tasks[i].id}`;
			tasks[i].generationTimeMs = 28000 + Math.random() * 10000;
			tasks[i].validationResult = {
				valid: true,
				warnings: i === 1 ? ['Consider adding error handling for API timeout'] : undefined
			};
		}

		currentState = 'success';
		progress = 100;
	}

	function animate(from: number, to: number, duration: number): Promise<void> {
		return new Promise((resolve) => {
			const start = performance.now();
			function step(now: number) {
				const elapsed = now - start;
				const ratio = Math.min(elapsed / duration, 1);
				progress = from + (to - from) * ratio;
				if (ratio < 1) {
					requestAnimationFrame(step);
				} else {
					resolve();
				}
			}
			requestAnimationFrame(step);
		});
	}

	function reset() {
		currentState = 'idle';
		progress = 0;
		traceId = null;
		expandedTask = null;
		tasks = tasks.map((t) => ({
			...t,
			status: 'pending' as const,
			errorMessage: undefined,
			retryCount: undefined,
			validationResult: undefined
		}));
	}

	function showPartialSuccess() {
		currentState = 'partial_success';
		progress = 100;
		traceId = 'trace_demo456';

		tasks[0].status = 'success';
		tasks[0].workflowName = 'workflow_tm_001';
		tasks[0].generationTimeMs = 28500;
		tasks[0].validationResult = { valid: true };

		tasks[1].status = 'success';
		tasks[1].workflowName = 'workflow_tm_002';
		tasks[1].generationTimeMs = 32100;
		tasks[1].validationResult = { valid: true, warnings: ['Consider adding retry logic'] };

		tasks[2].status = 'failed';
		tasks[2].errorMessage = 'API rate limit exceeded after 3 retries';
		tasks[2].retryCount = 3;
	}

	function toggleExpand(taskId: string) {
		expandedTask = expandedTask === taskId ? null : taskId;
	}

	function retryTask(taskId: string) {
		const task = tasks.find((t) => t.id === taskId);
		if (task) {
			task.status = 'generating';
			task.errorMessage = undefined;
			setTimeout(() => {
				task.status = 'success';
				task.workflowName = `workflow_${taskId}`;
				task.generationTimeMs = 30000;
				task.validationResult = { valid: true };
				currentState = 'success';
			}, 2000);
		}
	}

	const successCount = $derived(tasks.filter((t) => t.status === 'success').length);
	const failedCount = $derived(tasks.filter((t) => t.status === 'failed').length);
</script>

<div class="pattern-c">
	<div class="demo-controls">
		<span class="demo-label">Demo Controls:</span>
		<button onclick={startGeneration} disabled={currentState !== 'idle'}>Full Success</button>
		<button onclick={showPartialSuccess}>Partial Success</button>
		<button onclick={reset}>Reset</button>
	</div>

	<div class="generate-page">
		<div class="page-header">
			<h2>Generate Job</h2>
			<p class="workbench-name">Email Summarizer</p>
		</div>

		<!-- Two Column Layout -->
		<div class="two-column">
			<!-- Left Column: Status & Control -->
			<div class="left-column">
				<!-- Active Requirement -->
				<div class="section-card compact">
					<div class="card-header">
						<h3>Requirement</h3>
						<span class="version-badge">v1 active</span>
					</div>
					<p class="requirement-preview">Gmailから未読メールを取得し、Claude APIで要約してSlackに投稿する</p>
				</div>

				<!-- Overall Status -->
				<div class="section-card">
					<h3>Generation Progress</h3>

					{#if currentState === 'idle'}
						<div class="status-idle">Ready to generate workflows</div>
					{:else}
						<div class="progress-section">
							<div class="phase-indicator">
								<span class="phase" class:active={currentState === 'analyzing'}>Analysis</span>
								<span class="phase-arrow">-</span>
								<span class="phase" class:active={currentState === 'workflow'}>Workflow Gen</span>
								<span class="phase-arrow">-</span>
								<span
									class="phase"
									class:active={currentState === 'success' || currentState === 'partial_success'}
									>Complete</span
								>
							</div>

							<div class="progress-bar">
								<div
									class="progress-fill"
									class:warning={currentState === 'partial_success'}
									style="width: {progress}%"
								></div>
							</div>

							<div class="progress-stats">
								<span>{Math.round(progress)}%</span>
								{#if traceId}
									<a href="http://localhost:3001/trace/{traceId}" target="_blank" class="trace-link">
										Trace: {traceId}
									</a>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<!-- Summary Stats -->
				{#if currentState === 'success' || currentState === 'partial_success'}
					<div class="section-card stats-card">
						<div class="stat-grid">
							<div class="stat-item success">
								<span class="stat-value">{successCount}</span>
								<span class="stat-label">Success</span>
							</div>
							<div class="stat-item failed">
								<span class="stat-value">{failedCount}</span>
								<span class="stat-label">Failed</span>
							</div>
							<div class="stat-item total">
								<span class="stat-value">{tasks.length}</span>
								<span class="stat-label">Total</span>
							</div>
						</div>
					</div>
				{/if}

				<!-- Action Button -->
				<button
					class="generate-button"
					disabled={currentState === 'analyzing' || currentState === 'workflow'}
					onclick={startGeneration}
				>
					{#if currentState === 'analyzing' || currentState === 'workflow'}
						Generating...
					{:else}
						Generate Job
					{/if}
				</button>
			</div>

			<!-- Right Column: Task Details -->
			<div class="right-column">
				<div class="section-card tasks-card">
					<h3>Workflow Tasks</h3>

					<div class="tasks-list">
						{#each tasks as task}
							<div
								class="task-card"
								class:expanded={expandedTask === task.id}
								class:generating={task.status === 'generating'}
								class:success={task.status === 'success'}
								class:failed={task.status === 'failed'}
							>
								<div class="task-header" onclick={() => toggleExpand(task.id)}>
									<div class="task-status-icon">
										{#if task.status === 'pending'}
											<span class="icon pending">-</span>
										{:else if task.status === 'generating'}
											<span class="icon spinner"></span>
										{:else if task.status === 'success'}
											<span class="icon success">OK</span>
										{:else}
											<span class="icon failed">X</span>
										{/if}
									</div>
									<div class="task-title">
										<span class="task-name">{task.name}</span>
										{#if task.workflowName}
											<span class="workflow-name">{task.workflowName}</span>
										{/if}
									</div>
									<span class="expand-icon">{expandedTask === task.id ? '-' : '+'}</span>
								</div>

								{#if expandedTask === task.id}
									<div class="task-details">
										{#if task.status === 'success'}
											<!-- Validation Result -->
											{#if task.validationResult}
												<div class="validation-result" class:has-warnings={task.validationResult.warnings}>
													<span class="validation-status">
														{task.validationResult.valid ? 'Valid' : 'Invalid'}
													</span>
													{#if task.validationResult.warnings}
														<ul class="warnings">
															{#each task.validationResult.warnings as warning}
																<li>{warning}</li>
															{/each}
														</ul>
													{/if}
												</div>
											{/if}

											<!-- YAML Preview -->
											<div class="yaml-preview">
												<div class="yaml-header">
													<span>YAML Preview</span>
													<button class="copy-btn">Copy</button>
												</div>
												<pre><code>{task.yamlContent}</code></pre>
											</div>

											<!-- Meta Info -->
											<div class="task-meta">
												<span>Generated in {((task.generationTimeMs ?? 0) / 1000).toFixed(1)}s</span>
											</div>
										{:else if task.status === 'failed'}
											<div class="error-details">
												<p class="error-message">{task.errorMessage}</p>
												<p class="retry-info">Retried {task.retryCount} times</p>
												<button class="retry-btn" onclick={() => retryTask(task.id)}>Retry Now</button>
											</div>
										{:else}
											<div class="pending-info">
												<p>Workflow will be generated for this task.</p>
											</div>
										{/if}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<style>
	.pattern-c {
		padding: 1rem;
	}

	.demo-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #fce7f3;
		border: 1px solid #f472b6;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
	}

	.demo-label {
		font-weight: 600;
		color: #9d174d;
	}

	.demo-controls button {
		padding: 0.25rem 0.5rem;
		background: white;
		border: 1px solid #ec4899;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.demo-controls button:hover:not(:disabled) {
		background: #fdf2f8;
	}

	.demo-controls button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.generate-page {
		max-width: 1100px;
	}

	.page-header {
		margin-bottom: 1rem;
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

	.two-column {
		display: grid;
		grid-template-columns: 320px 1fr;
		gap: 1rem;
	}

	@media (max-width: 900px) {
		.two-column {
			grid-template-columns: 1fr;
		}
	}

	.section-card {
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		margin-bottom: 0.75rem;
	}

	.section-card.compact {
		padding: 0.75rem;
	}

	.section-card h3 {
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.5rem;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.card-header h3 {
		margin: 0;
	}

	.version-badge {
		font-size: 0.625rem;
		padding: 0.125rem 0.375rem;
		background: #dcfce7;
		color: #166534;
		border-radius: 0.25rem;
		font-weight: 500;
	}

	.requirement-preview {
		font-size: 0.75rem;
		color: #475569;
		margin: 0;
		line-height: 1.4;
	}

	.status-idle {
		font-size: 0.875rem;
		color: #64748b;
		padding: 1rem;
		text-align: center;
		background: #f8fafc;
		border-radius: 0.25rem;
	}

	.phase-indicator {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.phase {
		font-size: 0.75rem;
		color: #94a3b8;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		background: #f1f5f9;
	}

	.phase.active {
		background: #3b82f6;
		color: white;
	}

	.phase-arrow {
		color: #cbd5e1;
	}

	.progress-bar {
		height: 8px;
		background: #e2e8f0;
		border-radius: 4px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		transition: width 0.1s ease;
	}

	.progress-fill.warning {
		background: #f59e0b;
	}

	.progress-stats {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 0.5rem;
		font-size: 0.75rem;
	}

	.trace-link {
		color: #3b82f6;
		text-decoration: none;
	}

	.trace-link:hover {
		text-decoration: underline;
	}

	.stats-card {
		padding: 0.75rem;
	}

	.stat-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.5rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.5rem;
		background: #f8fafc;
		border-radius: 0.25rem;
	}

	.stat-value {
		font-size: 1.25rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.625rem;
		color: #64748b;
		text-transform: uppercase;
	}

	.stat-item.success .stat-value {
		color: #10b981;
	}

	.stat-item.failed .stat-value {
		color: #ef4444;
	}

	.stat-item.total .stat-value {
		color: #1e293b;
	}

	.generate-button {
		width: 100%;
		padding: 0.75rem;
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

	.tasks-card {
		padding: 0;
	}

	.tasks-card h3 {
		padding: 1rem 1rem 0.75rem;
		margin: 0;
		border-bottom: 1px solid #e2e8f0;
	}

	.tasks-list {
		padding: 0.5rem;
	}

	.task-card {
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		margin-bottom: 0.5rem;
		overflow: hidden;
	}

	.task-card.generating {
		border-color: #fcd34d;
		background: #fefce8;
	}

	.task-card.success {
		border-color: #86efac;
	}

	.task-card.failed {
		border-color: #fca5a5;
		background: #fef2f2;
	}

	.task-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		cursor: pointer;
		background: white;
	}

	.task-card.generating .task-header {
		background: #fefce8;
	}

	.task-card.failed .task-header {
		background: #fef2f2;
	}

	.task-status-icon .icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		border-radius: 50%;
		font-size: 0.625rem;
		font-weight: 700;
	}

	.icon.pending {
		background: #e2e8f0;
		color: #64748b;
	}

	.icon.spinner {
		border: 2px solid #f59e0b;
		border-top-color: transparent;
		animation: spin 0.75s linear infinite;
	}

	.icon.success {
		background: #10b981;
		color: white;
	}

	.icon.failed {
		background: #ef4444;
		color: white;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.task-title {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.125rem;
	}

	.task-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: #1e293b;
	}

	.workflow-name {
		font-size: 0.75rem;
		color: #64748b;
	}

	.expand-icon {
		font-size: 1rem;
		color: #94a3b8;
	}

	.task-details {
		padding: 0.75rem;
		border-top: 1px solid #e2e8f0;
		background: #f8fafc;
	}

	.validation-result {
		padding: 0.5rem;
		background: #dcfce7;
		border-radius: 0.25rem;
		margin-bottom: 0.75rem;
	}

	.validation-result.has-warnings {
		background: #fef3c7;
	}

	.validation-status {
		font-size: 0.75rem;
		font-weight: 600;
		color: #166534;
	}

	.has-warnings .validation-status {
		color: #92400e;
	}

	.warnings {
		margin: 0.5rem 0 0;
		padding-left: 1rem;
		font-size: 0.75rem;
		color: #92400e;
	}

	.yaml-preview {
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		overflow: hidden;
	}

	.yaml-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem;
		background: #e2e8f0;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.copy-btn {
		padding: 0.125rem 0.375rem;
		background: white;
		border: 1px solid #cbd5e1;
		border-radius: 0.25rem;
		font-size: 0.625rem;
		cursor: pointer;
	}

	.yaml-preview pre {
		margin: 0;
		padding: 0.75rem;
		background: #1e293b;
		font-size: 0.6875rem;
		line-height: 1.5;
		overflow-x: auto;
	}

	.yaml-preview code {
		color: #e2e8f0;
	}

	.task-meta {
		margin-top: 0.5rem;
		font-size: 0.75rem;
		color: #64748b;
	}

	.error-details {
		padding: 0.5rem;
		background: #fee2e2;
		border-radius: 0.25rem;
	}

	.error-message {
		margin: 0 0 0.5rem;
		font-size: 0.875rem;
		color: #dc2626;
	}

	.retry-info {
		margin: 0 0 0.75rem;
		font-size: 0.75rem;
		color: #7f1d1d;
	}

	.retry-btn {
		padding: 0.375rem 0.75rem;
		background: #ef4444;
		color: white;
		border: none;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.retry-btn:hover {
		background: #dc2626;
	}

	.pending-info {
		font-size: 0.75rem;
		color: #64748b;
	}

	.pending-info p {
		margin: 0;
	}
</style>
