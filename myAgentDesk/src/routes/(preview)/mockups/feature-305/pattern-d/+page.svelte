<script lang="ts">
	// Pattern D: 革新的・実験的
	// リアルタイムストリーミングとAIサジェスト。

	interface LogEntry {
		timestamp: string;
		level: 'info' | 'success' | 'warning' | 'error';
		message: string;
		details?: string;
	}

	interface TaskNode {
		id: string;
		name: string;
		status: 'pending' | 'active' | 'success' | 'failed';
		x: number;
		y: number;
	}

	interface AISuggestion {
		type: 'optimization' | 'warning' | 'tip';
		title: string;
		description: string;
		action?: string;
	}

	let currentState = $state<'idle' | 'generating' | 'complete'>('idle');
	let logs = $state<LogEntry[]>([]);
	let suggestions = $state<AISuggestion[]>([]);
	let activeTab = $state<'logs' | 'graph' | 'ai'>('logs');

	let nodes = $state<TaskNode[]>([
		{ id: 'start', name: 'Start', status: 'pending', x: 50, y: 100 },
		{ id: 'task1', name: 'Gmail取得', status: 'pending', x: 180, y: 50 },
		{ id: 'task2', name: 'Claude要約', status: 'pending', x: 180, y: 150 },
		{ id: 'task3', name: 'Slack投稿', status: 'pending', x: 310, y: 100 },
		{ id: 'end', name: 'End', status: 'pending', x: 430, y: 100 }
	]);

	function addLog(level: LogEntry['level'], message: string, details?: string) {
		const timestamp = new Date().toLocaleTimeString();
		logs = [...logs, { timestamp, level, message, details }];
	}

	function startGeneration() {
		currentState = 'generating';
		logs = [];
		suggestions = [];
		nodes = nodes.map((n) => ({ ...n, status: 'pending' as const }));

		simulateGeneration();
	}

	async function simulateGeneration() {
		addLog('info', 'Starting workflow generation...');
		await delay(500);

		nodes[0].status = 'success';
		addLog('info', 'Analyzing requirements...', 'Extracting task definitions from requirements');
		await delay(800);

		addLog('success', 'Found 3 tasks to generate workflows');

		// Task 1
		nodes[1].status = 'active';
		addLog('info', 'Generating workflow: Gmail未読メール取得');
		await delay(1000);
		addLog('info', '  -> Calling Claude API...', 'model: claude-sonnet-4-20250514, tokens: ~2000');
		await delay(1500);
		nodes[1].status = 'success';
		addLog('success', '  -> Workflow generated successfully (28.5s)');

		// AI Suggestion
		suggestions = [
			...suggestions,
			{
				type: 'optimization',
				title: 'Parallel Execution Possible',
				description: 'Tasks Gmail取得 and Claude要約 could run in parallel for 40% faster execution.',
				action: 'Apply Optimization'
			}
		];

		// Task 2
		nodes[2].status = 'active';
		addLog('info', 'Generating workflow: Claude要約生成');
		await delay(800);
		addLog('info', '  -> Calling Claude API...');
		await delay(1200);
		addLog('warning', '  -> Rate limit approaching (58/60 RPM)');
		await delay(500);
		nodes[2].status = 'success';
		addLog('success', '  -> Workflow generated successfully (32.1s)');

		suggestions = [
			...suggestions,
			{
				type: 'warning',
				title: 'Rate Limit Warning',
				description: 'You are approaching the API rate limit. Consider adding delays between requests.',
				action: 'View Details'
			}
		];

		// Task 3
		nodes[3].status = 'active';
		addLog('info', 'Generating workflow: Slack投稿');
		await delay(600);
		addLog('info', '  -> Calling Claude API...');
		await delay(1000);
		nodes[3].status = 'success';
		addLog('success', '  -> Workflow generated successfully (25.3s)');

		nodes[4].status = 'success';
		addLog('success', 'All workflows generated successfully!');

		suggestions = [
			...suggestions,
			{
				type: 'tip',
				title: 'Next Steps',
				description: 'Review the generated workflows and test them in the sandbox environment.',
				action: 'Open Review'
			}
		];

		currentState = 'complete';
	}

	function delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}

	function reset() {
		currentState = 'idle';
		logs = [];
		suggestions = [];
		nodes = nodes.map((n) => ({ ...n, status: 'pending' as const }));
	}

	function getLogIcon(level: LogEntry['level']): string {
		switch (level) {
			case 'info':
				return '~';
			case 'success':
				return '*';
			case 'warning':
				return '!';
			case 'error':
				return 'X';
		}
	}
</script>

<div class="pattern-d">
	<div class="demo-controls">
		<span class="demo-label">Demo Controls:</span>
		<button onclick={startGeneration} disabled={currentState === 'generating'}>
			Start Generation
		</button>
		<button onclick={reset}>Reset</button>
	</div>

	<div class="generate-page">
		<div class="header-row">
			<div class="page-header">
				<h2>Generate Job</h2>
				<p class="workbench-name">Email Summarizer</p>
			</div>
			<button
				class="generate-btn-main"
				disabled={currentState === 'generating'}
				onclick={startGeneration}
			>
				{#if currentState === 'generating'}
					<span class="btn-spinner"></span>
					Generating...
				{:else}
					Generate with AI
				{/if}
			</button>
		</div>

		<div class="main-content">
			<!-- Left: Visualization -->
			<div class="visualization-panel">
				<!-- Tabs -->
				<div class="panel-tabs">
					<button class="tab" class:active={activeTab === 'logs'} onclick={() => (activeTab = 'logs')}>
						Live Logs
					</button>
					<button
						class="tab"
						class:active={activeTab === 'graph'}
						onclick={() => (activeTab = 'graph')}
					>
						Workflow Graph
					</button>
					<button class="tab" class:active={activeTab === 'ai'} onclick={() => (activeTab = 'ai')}>
						AI Insights
						{#if suggestions.length > 0}
							<span class="badge">{suggestions.length}</span>
						{/if}
					</button>
				</div>

				<!-- Tab Content -->
				<div class="panel-content">
					{#if activeTab === 'logs'}
						<div class="logs-panel">
							{#if logs.length === 0}
								<div class="empty-logs">
									<span class="empty-icon">|</span>
									<p>Click "Generate with AI" to start</p>
									<p class="sub">Real-time generation logs will appear here</p>
								</div>
							{:else}
								<div class="log-entries">
									{#each logs as log}
										<div class="log-entry {log.level}">
											<span class="log-time">{log.timestamp}</span>
											<span class="log-icon">{getLogIcon(log.level)}</span>
											<div class="log-content">
												<span class="log-message">{log.message}</span>
												{#if log.details}
													<span class="log-details">{log.details}</span>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{:else if activeTab === 'graph'}
						<div class="graph-panel">
							<svg width="100%" height="200" viewBox="0 0 500 200">
								<!-- Edges -->
								<line x1="80" y1="100" x2="150" y2="50" stroke="#cbd5e1" stroke-width="2" />
								<line x1="80" y1="100" x2="150" y2="150" stroke="#cbd5e1" stroke-width="2" />
								<line x1="210" y1="50" x2="280" y2="100" stroke="#cbd5e1" stroke-width="2" />
								<line x1="210" y1="150" x2="280" y2="100" stroke="#cbd5e1" stroke-width="2" />
								<line x1="340" y1="100" x2="400" y2="100" stroke="#cbd5e1" stroke-width="2" />

								<!-- Nodes -->
								{#each nodes as node}
									<g transform="translate({node.x}, {node.y})">
										<circle
											r="25"
											fill={node.status === 'success'
												? '#10b981'
												: node.status === 'active'
													? '#f59e0b'
													: node.status === 'failed'
														? '#ef4444'
														: '#e2e8f0'}
											stroke={node.status === 'active' ? '#f59e0b' : 'none'}
											stroke-width="3"
											class:pulse={node.status === 'active'}
										/>
										<text
											y="4"
											text-anchor="middle"
											fill={node.status === 'pending' ? '#64748b' : 'white'}
											font-size="10"
											font-weight="500"
										>
											{node.name.length > 6 ? node.name.slice(0, 6) + '..' : node.name}
										</text>
									</g>
								{/each}
							</svg>
							<div class="graph-legend">
								<span class="legend-item">
									<span class="dot pending"></span>
									Pending
								</span>
								<span class="legend-item">
									<span class="dot active"></span>
									Active
								</span>
								<span class="legend-item">
									<span class="dot success"></span>
									Complete
								</span>
							</div>
						</div>
					{:else if activeTab === 'ai'}
						<div class="ai-panel">
							{#if suggestions.length === 0}
								<div class="empty-ai">
									<span class="empty-icon">*</span>
									<p>AI insights will appear during generation</p>
									<p class="sub">Optimizations, warnings, and tips</p>
								</div>
							{:else}
								<div class="suggestions-list">
									{#each suggestions as suggestion}
										<div class="suggestion-card {suggestion.type}">
											<div class="suggestion-header">
												<span class="suggestion-type">{suggestion.type.toUpperCase()}</span>
												<h4>{suggestion.title}</h4>
											</div>
											<p>{suggestion.description}</p>
											{#if suggestion.action}
												<button class="suggestion-action">{suggestion.action}</button>
											{/if}
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- Right: Status Summary -->
			<div class="status-panel">
				<div class="status-card">
					<h3>Generation Status</h3>
					<div class="status-indicator {currentState}">
						{#if currentState === 'idle'}
							Ready
						{:else if currentState === 'generating'}
							<span class="mini-spinner"></span>
							Generating
						{:else}
							Complete
						{/if}
					</div>
				</div>

				<div class="status-card">
					<h3>Tasks</h3>
					<div class="task-mini-list">
						{#each nodes.filter((n) => !['start', 'end'].includes(n.id)) as node}
							<div class="task-mini">
								<span
									class="task-dot"
									class:pending={node.status === 'pending'}
									class:active={node.status === 'active'}
									class:success={node.status === 'success'}
								></span>
								<span class="task-label">{node.name}</span>
							</div>
						{/each}
					</div>
				</div>

				{#if currentState === 'complete'}
					<div class="status-card success-card">
						<h3>Result</h3>
						<div class="success-message">
							<span class="success-icon">OK</span>
							<span>3/3 workflows generated</span>
						</div>
						<div class="action-buttons">
							<button class="action-btn primary">Review Workflows</button>
							<button class="action-btn secondary">View in Langfuse</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>

<style>
	.pattern-d {
		padding: 1rem;
		background: #0f172a;
		min-height: 100vh;
	}

	.demo-controls {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		background: #1e293b;
		border: 1px solid #334155;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
		font-size: 0.75rem;
	}

	.demo-label {
		font-weight: 600;
		color: #94a3b8;
	}

	.demo-controls button {
		padding: 0.25rem 0.5rem;
		background: #334155;
		border: 1px solid #475569;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		color: #e2e8f0;
		cursor: pointer;
	}

	.demo-controls button:hover:not(:disabled) {
		background: #475569;
	}

	.demo-controls button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.generate-page {
		max-width: 1100px;
	}

	.header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.page-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #f1f5f9;
		margin: 0;
	}

	.workbench-name {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0.25rem 0 0;
	}

	.generate-btn-main {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: linear-gradient(135deg, #8b5cf6, #6366f1);
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: transform 0.1s;
	}

	.generate-btn-main:hover:not(:disabled) {
		transform: scale(1.02);
	}

	.generate-btn-main:disabled {
		opacity: 0.7;
		cursor: not-allowed;
	}

	.btn-spinner {
		width: 1rem;
		height: 1rem;
		border: 2px solid white;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.main-content {
		display: grid;
		grid-template-columns: 1fr 280px;
		gap: 1rem;
	}

	@media (max-width: 900px) {
		.main-content {
			grid-template-columns: 1fr;
		}
	}

	.visualization-panel {
		background: #1e293b;
		border: 1px solid #334155;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.panel-tabs {
		display: flex;
		border-bottom: 1px solid #334155;
	}

	.tab {
		flex: 1;
		padding: 0.75rem;
		background: transparent;
		border: none;
		color: #64748b;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		position: relative;
	}

	.tab:hover {
		color: #94a3b8;
	}

	.tab.active {
		color: #f1f5f9;
		background: rgba(139, 92, 246, 0.1);
	}

	.tab.active::after {
		content: '';
		position: absolute;
		bottom: 0;
		left: 0;
		right: 0;
		height: 2px;
		background: #8b5cf6;
	}

	.badge {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		height: 1.25rem;
		padding: 0 0.375rem;
		background: #8b5cf6;
		color: white;
		border-radius: 0.625rem;
		font-size: 0.625rem;
		font-weight: 600;
		margin-left: 0.375rem;
	}

	.panel-content {
		height: 300px;
		overflow-y: auto;
	}

	.logs-panel {
		padding: 0.75rem;
		font-family: 'Monaco', 'Consolas', monospace;
	}

	.empty-logs,
	.empty-ai {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #64748b;
	}

	.empty-icon {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.empty-logs p,
	.empty-ai p {
		margin: 0;
		font-size: 0.875rem;
	}

	.sub {
		font-size: 0.75rem;
		color: #475569;
	}

	.log-entries {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.log-entry {
		display: flex;
		gap: 0.5rem;
		padding: 0.25rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
	}

	.log-entry.info {
		color: #94a3b8;
	}

	.log-entry.success {
		color: #10b981;
	}

	.log-entry.warning {
		color: #f59e0b;
		background: rgba(245, 158, 11, 0.1);
	}

	.log-entry.error {
		color: #ef4444;
		background: rgba(239, 68, 68, 0.1);
	}

	.log-time {
		color: #475569;
		flex-shrink: 0;
	}

	.log-icon {
		flex-shrink: 0;
		width: 1rem;
		text-align: center;
	}

	.log-content {
		display: flex;
		flex-direction: column;
	}

	.log-details {
		color: #64748b;
		font-size: 0.6875rem;
	}

	.graph-panel {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 1rem;
	}

	.graph-panel svg {
		max-width: 100%;
	}

	.pulse {
		animation: pulse-animation 1s ease-in-out infinite;
	}

	@keyframes pulse-animation {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.6;
		}
	}

	.graph-legend {
		display: flex;
		gap: 1rem;
		margin-top: 1rem;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.75rem;
		color: #94a3b8;
	}

	.dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
	}

	.dot.pending {
		background: #e2e8f0;
	}

	.dot.active {
		background: #f59e0b;
	}

	.dot.success {
		background: #10b981;
	}

	.ai-panel {
		padding: 0.75rem;
	}

	.suggestions-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.suggestion-card {
		padding: 0.75rem;
		border-radius: 0.375rem;
		border-left: 3px solid;
	}

	.suggestion-card.optimization {
		background: rgba(16, 185, 129, 0.1);
		border-color: #10b981;
	}

	.suggestion-card.warning {
		background: rgba(245, 158, 11, 0.1);
		border-color: #f59e0b;
	}

	.suggestion-card.tip {
		background: rgba(139, 92, 246, 0.1);
		border-color: #8b5cf6;
	}

	.suggestion-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.suggestion-type {
		font-size: 0.625rem;
		font-weight: 700;
		color: #64748b;
	}

	.suggestion-header h4 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #f1f5f9;
		margin: 0;
	}

	.suggestion-card p {
		font-size: 0.75rem;
		color: #94a3b8;
		margin: 0 0 0.75rem;
	}

	.suggestion-action {
		padding: 0.375rem 0.75rem;
		background: rgba(255, 255, 255, 0.1);
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 0.25rem;
		color: #f1f5f9;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.suggestion-action:hover {
		background: rgba(255, 255, 255, 0.15);
	}

	.status-panel {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.status-card {
		padding: 1rem;
		background: #1e293b;
		border: 1px solid #334155;
		border-radius: 0.5rem;
	}

	.status-card h3 {
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.75rem;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-indicator.idle {
		background: #334155;
		color: #94a3b8;
	}

	.status-indicator.generating {
		background: rgba(245, 158, 11, 0.2);
		color: #f59e0b;
	}

	.status-indicator.complete {
		background: rgba(16, 185, 129, 0.2);
		color: #10b981;
	}

	.mini-spinner {
		width: 0.875rem;
		height: 0.875rem;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.75s linear infinite;
	}

	.task-mini-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.task-mini {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.task-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
	}

	.task-dot.pending {
		background: #475569;
	}

	.task-dot.active {
		background: #f59e0b;
	}

	.task-dot.success {
		background: #10b981;
	}

	.task-label {
		font-size: 0.875rem;
		color: #e2e8f0;
	}

	.success-card {
		border-color: #10b981;
	}

	.success-message {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.success-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 1.5rem;
		height: 1.5rem;
		background: #10b981;
		color: white;
		border-radius: 50%;
		font-size: 0.625rem;
		font-weight: 700;
	}

	.success-message span:last-child {
		color: #10b981;
		font-weight: 500;
	}

	.action-buttons {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.action-btn {
		padding: 0.5rem;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		border: none;
	}

	.action-btn.primary {
		background: #8b5cf6;
		color: white;
	}

	.action-btn.primary:hover {
		background: #7c3aed;
	}

	.action-btn.secondary {
		background: transparent;
		border: 1px solid #475569;
		color: #94a3b8;
	}

	.action-btn.secondary:hover {
		background: #334155;
	}
</style>
