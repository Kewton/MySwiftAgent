<script lang="ts">
	// Pattern B: 標準・バランス型
	// Task Breakdown → Workflow生成の動線を明確に表示

	interface TaskBreakdown {
		id: string;
		name: string;
		description: string;
		recommendedApis: string[];
	}

	interface WorkflowStatus {
		taskId: string;
		status: 'pending' | 'generating' | 'success' | 'failed';
		workflowName?: string;
		errorMessage?: string;
		generationTimeMs?: number;
	}

	let currentPhase = $state<'idle' | 'analyzing' | 'breakdown_complete' | 'workflow' | 'complete'>('idle');
	let progress = $state(0);
	let traceId = $state<string | null>(null);

	// Phase 1の結果: Task Breakdown
	let taskBreakdowns = $state<TaskBreakdown[]>([]);

	// Phase 2の結果: Workflow Status
	let workflowStatuses = $state<WorkflowStatus[]>([]);

	const mockTaskBreakdowns: TaskBreakdown[] = [
		{
			id: 'tm_001',
			name: 'Gmail未読メール取得',
			description: 'Gmail APIを使用して未読メールを最大10件取得する',
			recommendedApis: ['Gmail API (users.messages.list)']
		},
		{
			id: 'tm_002',
			name: 'Claude要約生成',
			description: '取得したメール内容をClaude APIで要約する',
			recommendedApis: ['Anthropic API (messages)']
		},
		{
			id: 'tm_003',
			name: 'Slack投稿',
			description: '要約結果をSlackチャンネルに投稿する',
			recommendedApis: ['Slack API (chat.postMessage)']
		}
	];

	function startGeneration() {
		currentPhase = 'analyzing';
		progress = 0;
		traceId = 'trace_' + Math.random().toString(36).substring(7);
		taskBreakdowns = [];
		workflowStatuses = [];
		simulateProgress();
	}

	async function simulateProgress() {
		// Phase 1: Task Analysis (0-70%)
		await animate(0, 35, 1000);
		await animate(35, 70, 1500);

		// Phase 1 Complete: Show Task Breakdown Results
		currentPhase = 'breakdown_complete';
		taskBreakdowns = [...mockTaskBreakdowns];
		workflowStatuses = mockTaskBreakdowns.map((t) => ({
			taskId: t.id,
			status: 'pending' as const
		}));

		// Brief pause to show breakdown results
		await delay(1000);

		// Phase 2: Workflow Generation (70-95%)
		currentPhase = 'workflow';

		for (let i = 0; i < workflowStatuses.length; i++) {
			workflowStatuses[i].status = 'generating';
			await animate(70 + (i * 25) / workflowStatuses.length, 70 + ((i + 1) * 25) / workflowStatuses.length, 1500);

			workflowStatuses[i].status = 'success';
			workflowStatuses[i].workflowName = `workflow_${workflowStatuses[i].taskId}`;
			workflowStatuses[i].generationTimeMs = 28000 + Math.random() * 10000;
		}

		// Complete
		currentPhase = 'complete';
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

	function delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}

	function reset() {
		currentPhase = 'idle';
		progress = 0;
		traceId = null;
		taskBreakdowns = [];
		workflowStatuses = [];
	}

	function showPartialSuccess() {
		currentPhase = 'complete';
		progress = 100;
		traceId = 'trace_demo456';
		taskBreakdowns = [...mockTaskBreakdowns];
		workflowStatuses = [
			{ taskId: 'tm_001', status: 'success', workflowName: 'workflow_tm_001', generationTimeMs: 28500 },
			{ taskId: 'tm_002', status: 'success', workflowName: 'workflow_tm_002', generationTimeMs: 32100 },
			{ taskId: 'tm_003', status: 'failed', errorMessage: 'API rate limit exceeded after 3 retries' }
		];
	}

	const successCount = $derived(workflowStatuses.filter((w) => w.status === 'success').length);
	const failedCount = $derived(workflowStatuses.filter((w) => w.status === 'failed').length);

	function getWorkflowStatus(taskId: string): WorkflowStatus | undefined {
		return workflowStatuses.find((w) => w.taskId === taskId);
	}
</script>

<div class="pattern-b">
	<div class="demo-controls">
		<span class="demo-label">Demo Controls:</span>
		<button onclick={startGeneration} disabled={currentPhase !== 'idle' && currentPhase !== 'complete'}>
			Start (Success)
		</button>
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
				<span class="status-badge active">active</span>
			</div>
			<p class="requirement-content">
				Gmailから未読メールを取得し、Claude APIで要約してSlackに投稿する
			</p>
		</div>

		<!-- Generation Status -->
		<div class="section-card">
			<h3>Generation Status</h3>

			{#if currentPhase === 'idle'}
				<div class="status-idle">
					<span class="idle-icon">-</span>
					<span>Ready to generate</span>
				</div>
			{:else}
				<!-- Phase Indicator -->
				<div class="phase-flow">
					<div class="phase-step" class:active={currentPhase === 'analyzing'} class:complete={currentPhase !== 'idle' && currentPhase !== 'analyzing'}>
						<span class="phase-number">1</span>
						<span class="phase-label">Task Analysis</span>
						<span class="phase-desc">要件分析 & タスク分解</span>
					</div>
					<div class="phase-arrow">
						<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
							<path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
						</svg>
					</div>
					<div class="phase-step" class:active={currentPhase === 'workflow'} class:complete={currentPhase === 'complete'}>
						<span class="phase-number">2</span>
						<span class="phase-label">Workflow Generation</span>
						<span class="phase-desc">各タスクのYAML生成</span>
					</div>
				</div>

				<!-- Progress Bar -->
				<div class="progress-section">
					<div class="progress-header">
						<span>
							{#if currentPhase === 'analyzing'}
								タスク分析中...
							{:else if currentPhase === 'breakdown_complete'}
								タスク分解完了 - ワークフロー生成準備中...
							{:else if currentPhase === 'workflow'}
								ワークフロー生成中...
							{:else}
								生成完了
							{/if}
						</span>
						<span class="progress-percent">{Math.round(progress)}%</span>
					</div>
					<div class="progress-bar">
						<div
							class="progress-fill"
							class:warning={failedCount > 0 && currentPhase === 'complete'}
							style="width: {progress}%"
						></div>
						<!-- Phase markers -->
						<div class="phase-marker" style="left: 70%">
							<span class="marker-label">Task分解完了</span>
						</div>
					</div>
				</div>

				<!-- Task Breakdown Results (Phase 1 Complete) -->
				{#if taskBreakdowns.length > 0}
					<div class="breakdown-section">
						<h4>
							<span class="section-icon">1</span>
							Task Breakdown Results
							<span class="task-count">{taskBreakdowns.length} tasks</span>
						</h4>
						<div class="breakdown-list">
							{#each taskBreakdowns as task, index}
								{@const workflow = getWorkflowStatus(task.id)}
								<div class="breakdown-item" class:generating={workflow?.status === 'generating'}>
									<div class="task-number">{index + 1}</div>
									<div class="task-info">
										<div class="task-header">
											<span class="task-name">{task.name}</span>
											{#if workflow?.status === 'success'}
												<span class="workflow-badge success">
													Workflow OK
												</span>
											{:else if workflow?.status === 'failed'}
												<span class="workflow-badge failed">
													Failed
												</span>
											{:else if workflow?.status === 'generating'}
												<span class="workflow-badge generating">
													<span class="mini-spinner"></span>
													Generating...
												</span>
											{:else}
												<span class="workflow-badge pending">
													Pending
												</span>
											{/if}
										</div>
										<p class="task-description">{task.description}</p>
										<div class="task-apis">
											{#each task.recommendedApis as api}
												<span class="api-tag">{api}</span>
											{/each}
										</div>
									</div>
									<!-- Workflow Result -->
									{#if workflow?.status === 'success'}
										<div class="workflow-result">
											<span class="workflow-name">{workflow.workflowName}.yaml</span>
											<span class="workflow-time">{((workflow.generationTimeMs ?? 0) / 1000).toFixed(1)}s</span>
										</div>
									{:else if workflow?.status === 'failed'}
										<div class="workflow-error">
											<span class="error-message">{workflow.errorMessage}</span>
										</div>
									{/if}
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Summary (Complete) -->
				{#if currentPhase === 'complete'}
					<div class="completion-section">
						<h4>
							<span class="section-icon">2</span>
							Generation Summary
						</h4>
						<div class="summary-content">
							<div class="summary-stats">
								<div class="stat success">
									<span class="stat-value">{successCount}</span>
									<span class="stat-label">Workflow Generated</span>
								</div>
								{#if failedCount > 0}
									<div class="stat failed">
										<span class="stat-value">{failedCount}</span>
										<span class="stat-label">Failed</span>
									</div>
								{/if}
								<div class="stat total">
									<span class="stat-value">{taskBreakdowns.length}</span>
									<span class="stat-label">Total Tasks</span>
								</div>
							</div>
							{#if traceId}
								<a
									href="http://localhost:3001/trace/{traceId}"
									target="_blank"
									rel="noopener noreferrer"
									class="trace-link"
								>
									View in Langfuse ({traceId})
								</a>
							{/if}
						</div>
					</div>
				{/if}
			{/if}
		</div>

		<!-- Generate Button -->
		<div class="section-card action-card">
			<button
				class="generate-button"
				disabled={currentPhase !== 'idle' && currentPhase !== 'complete'}
				onclick={startGeneration}
			>
				{#if currentPhase === 'analyzing' || currentPhase === 'breakdown_complete' || currentPhase === 'workflow'}
					Generating...
				{:else}
					Generate Job
				{/if}
			</button>
			<p class="action-hint">
				要件からタスクを分解し、各タスクのGraphAIワークフロー(YAML)を自動生成します
			</p>
		</div>
	</div>
</div>

<style>
	.pattern-b {
		padding: 1rem;
	}

	.demo-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #dbeafe;
		border: 1px solid #60a5fa;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
	}

	.demo-label {
		font-weight: 600;
		color: #1e40af;
	}

	.demo-controls button {
		padding: 0.25rem 0.5rem;
		background: white;
		border: 1px solid #3b82f6;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.demo-controls button:hover:not(:disabled) {
		background: #eff6ff;
	}

	.demo-controls button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

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
		margin-bottom: 0.5rem;
	}

	.version-badge {
		padding: 0.125rem 0.5rem;
		background: #dbeafe;
		color: #1e40af;
		font-size: 0.75rem;
		font-weight: 600;
		border-radius: 0.25rem;
	}

	.status-badge.active {
		padding: 0.125rem 0.5rem;
		background: #dcfce7;
		color: #166534;
		font-size: 0.75rem;
		font-weight: 500;
		border-radius: 0.25rem;
	}

	.requirement-content {
		font-size: 0.875rem;
		color: #475569;
		margin: 0;
		padding: 0.75rem;
		background: #f8fafc;
		border-radius: 0.25rem;
	}

	.status-idle {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: #f1f5f9;
		border-radius: 0.25rem;
		color: #64748b;
	}

	.idle-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #94a3b8;
		color: white;
		border-radius: 50%;
		font-size: 0.875rem;
	}

	/* Phase Flow */
	.phase-flow {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.phase-step {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.75rem 1rem;
		background: white;
		border: 2px solid #e2e8f0;
		border-radius: 0.5rem;
		min-width: 160px;
		transition: all 0.2s;
	}

	.phase-step.active {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.phase-step.complete {
		border-color: #10b981;
		background: #f0fdf4;
	}

	.phase-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #e2e8f0;
		color: #64748b;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 700;
		margin-bottom: 0.375rem;
	}

	.phase-step.active .phase-number {
		background: #3b82f6;
		color: white;
	}

	.phase-step.complete .phase-number {
		background: #10b981;
		color: white;
	}

	.phase-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #1e293b;
	}

	.phase-desc {
		font-size: 0.625rem;
		color: #64748b;
		margin-top: 0.125rem;
	}

	.phase-arrow {
		color: #cbd5e1;
	}

	.phase-arrow svg {
		width: 1.5rem;
		height: 1.5rem;
	}

	/* Progress */
	.progress-section {
		margin-bottom: 1rem;
	}

	.progress-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 0.5rem;
		font-size: 0.875rem;
		color: #475569;
	}

	.progress-percent {
		font-weight: 600;
		color: #1e293b;
	}

	.progress-bar {
		position: relative;
		height: 8px;
		background: #e2e8f0;
		border-radius: 4px;
		overflow: visible;
	}

	.progress-fill {
		height: 100%;
		background: #3b82f6;
		border-radius: 4px;
		transition: width 0.1s ease;
	}

	.progress-fill.warning {
		background: #f59e0b;
	}

	.phase-marker {
		position: absolute;
		top: -4px;
		transform: translateX(-50%);
	}

	.marker-label {
		display: block;
		position: absolute;
		top: 16px;
		left: 50%;
		transform: translateX(-50%);
		font-size: 0.625rem;
		color: #64748b;
		white-space: nowrap;
	}

	/* Breakdown Section */
	.breakdown-section {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.breakdown-section h4,
	.completion-section h4 {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.8125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.75rem;
	}

	.section-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.25rem;
		height: 1.25rem;
		background: #3b82f6;
		color: white;
		border-radius: 50%;
		font-size: 0.6875rem;
		font-weight: 700;
	}

	.task-count {
		margin-left: auto;
		font-size: 0.75rem;
		font-weight: 400;
		color: #64748b;
	}

	.breakdown-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.breakdown-item {
		display: grid;
		grid-template-columns: 2rem 1fr auto;
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		transition: all 0.2s;
	}

	.breakdown-item.generating {
		background: #fefce8;
		border-color: #fcd34d;
	}

	.task-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #e2e8f0;
		color: #64748b;
		border-radius: 50%;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.task-info {
		min-width: 0;
	}

	.task-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		margin-bottom: 0.25rem;
	}

	.task-name {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
	}

	.workflow-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.125rem 0.375rem;
		font-size: 0.625rem;
		font-weight: 600;
		border-radius: 0.25rem;
	}

	.workflow-badge.pending {
		background: #f1f5f9;
		color: #64748b;
	}

	.workflow-badge.generating {
		background: #fef3c7;
		color: #92400e;
	}

	.workflow-badge.success {
		background: #dcfce7;
		color: #166534;
	}

	.workflow-badge.failed {
		background: #fee2e2;
		color: #dc2626;
	}

	.mini-spinner {
		width: 0.625rem;
		height: 0.625rem;
		border: 1.5px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.task-description {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0 0 0.375rem;
	}

	.task-apis {
		display: flex;
		gap: 0.25rem;
		flex-wrap: wrap;
	}

	.api-tag {
		padding: 0.125rem 0.375rem;
		background: #dbeafe;
		color: #1e40af;
		font-size: 0.625rem;
		border-radius: 0.25rem;
	}

	.workflow-result {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 0.125rem;
	}

	.workflow-name {
		font-size: 0.75rem;
		font-weight: 500;
		color: #166534;
		font-family: monospace;
	}

	.workflow-time {
		font-size: 0.625rem;
		color: #64748b;
	}

	.workflow-error {
		display: flex;
		align-items: center;
	}

	.error-message {
		font-size: 0.6875rem;
		color: #dc2626;
		text-align: right;
	}

	/* Completion Section */
	.completion-section {
		margin-top: 1.5rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
	}

	.summary-content {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.summary-stats {
		display: flex;
		gap: 1.5rem;
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 700;
	}

	.stat-label {
		font-size: 0.75rem;
		color: #64748b;
	}

	.stat.success .stat-value {
		color: #10b981;
	}

	.stat.failed .stat-value {
		color: #ef4444;
	}

	.stat.total .stat-value {
		color: #1e293b;
	}

	.trace-link {
		font-size: 0.875rem;
		color: #3b82f6;
		text-decoration: none;
	}

	.trace-link:hover {
		text-decoration: underline;
	}

	/* Action Card */
	.action-card {
		text-align: center;
	}

	.generate-button {
		padding: 0.75rem 2rem;
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

	.action-hint {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0.5rem 0 0;
	}
</style>
