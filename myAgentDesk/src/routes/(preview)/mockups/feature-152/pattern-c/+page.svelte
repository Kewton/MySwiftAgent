<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;

	type FeedbackKey =
		| 'requirement_clarity'
		| 'hypothesis_accuracy'
		| 'response_naturalness'
		| 'overall_satisfaction';

	const feedbackKeys: FeedbackKey[] = [
		'requirement_clarity',
		'hypothesis_accuracy',
		'response_naturalness',
		'overall_satisfaction'
	];

	const labels: Record<FeedbackKey, string> = {
		requirement_clarity: '要件明確化の分かりやすさ',
		hypothesis_accuracy: '仮説の精度',
		response_naturalness: '応答の自然さ',
		overall_satisfaction: '総合満足度'
	};

	const shortLabels: Record<FeedbackKey, string> = {
		requirement_clarity: '要件明確化',
		hypothesis_accuracy: '仮説精度',
		response_naturalness: '応答自然さ',
		overall_satisfaction: '総合満足度'
	};

	let activeTab = 'candidates';
	let selectedCandidate: string | null = null;
	let feedbackSubmitted = false;
	let selectedPromptVersion = 'v1';
	let feedbackScores: Record<FeedbackKey, number> = {
		requirement_clarity: 0,
		hypothesis_accuracy: 0,
		response_naturalness: 0,
		overall_satisfaction: 0
	};

	function selectCandidate(candidateId: string) {
		selectedCandidate = candidateId;
	}

	function submitFeedback() {
		console.log('フィードバック送信（モック）:', feedbackScores);
		feedbackSubmitted = true;
	}

	function switchTab(tab: string) {
		activeTab = tab;
	}

	function viewDiagnostics() {
		alert('診断情報の詳細ビューを表示（モック）');
	}
</script>

<div class="pattern-c">
	<header class="page-header">
		<div>
			<h2>パターンC: リッチ・高機能</h2>
			<p class="description">全機能を網羅した、パワーユーザー向けの高度なデザインです。</p>
		</div>
		<div class="header-actions">
			<button class="btn btn-outline" on:click={viewDiagnostics}>診断情報を表示</button>
		</div>
	</header>

	<!-- 高度なタブナビゲーション -->
	<nav class="advanced-tabs">
		<button
			class="tab"
			class:active={activeTab === 'candidates'}
			on:click={() => switchTab('candidates')}
		>
			<span class="tab-icon">📋</span>
			<span class="tab-label">候補選択</span>
		</button>
		<button
			class="tab"
			class:active={activeTab === 'feedback'}
			on:click={() => switchTab('feedback')}
		>
			<span class="tab-icon">⭐</span>
			<span class="tab-label">フィードバック</span>
		</button>
		<button
			class="tab"
			class:active={activeTab === 'metrics'}
			on:click={() => switchTab('metrics')}
		>
			<span class="tab-icon">📊</span>
			<span class="tab-label">メトリクス</span>
		</button>
		<button
			class="tab"
			class:active={activeTab === 'diagnostics'}
			on:click={() => switchTab('diagnostics')}
		>
			<span class="tab-icon">🔍</span>
			<span class="tab-label">診断情報</span>
		</button>
		<button
			class="tab"
			class:active={activeTab === 'prompts'}
			on:click={() => switchTab('prompts')}
		>
			<span class="tab-icon">⚙️</span>
			<span class="tab-label">プロンプト管理</span>
		</button>
	</nav>

	<div class="content-wrapper">
		<!-- 候補選択タブ -->
		{#if activeTab === 'candidates'}
			<section class="section">
				<div class="candidates-comparison">
					{#each data.candidates as candidate}
						<div class="candidate-column" class:selected={selectedCandidate === candidate.id}>
							<div class="candidate-header">
								<h3>{candidate.label}</h3>
								{#if candidate.recommended}
									<span class="badge-pro">推奨</span>
								{/if}
							</div>

							<div class="candidate-body">
								<p class="candidate-desc">{candidate.description}</p>

								<div class="specs">
									<div class="spec-item">
										<div class="spec-icon">📊</div>
										<div>
											<div class="spec-label">データソース</div>
											<div class="spec-value">{candidate.data_source}</div>
										</div>
									</div>

									<div class="spec-item">
										<div class="spec-icon">⚙️</div>
										<div>
											<div class="spec-label">処理内容</div>
											<div class="spec-value">{candidate.process_description}</div>
										</div>
									</div>

									<div class="spec-item">
										<div class="spec-icon">📤</div>
										<div>
											<div class="spec-label">出力形式</div>
											<div class="spec-value">{candidate.output_format}</div>
										</div>
									</div>

									<div class="spec-item">
										<div class="spec-icon">🕐</div>
										<div>
											<div class="spec-label">スケジュール</div>
											<div class="spec-value">{candidate.schedule}</div>
										</div>
									</div>
								</div>

								<div class="completeness-meter">
									<div class="meter-label">完成度</div>
									<div class="meter-bar">
										<div class="meter-fill" style="width: {candidate.completeness * 100}%"></div>
									</div>
									<div class="meter-value">{Math.round(candidate.completeness * 100)}%</div>
								</div>
							</div>

							<button
								class="btn-select-candidate"
								class:selected={selectedCandidate === candidate.id}
								on:click={() => selectCandidate(candidate.id)}
							>
								{selectedCandidate === candidate.id ? '✓ 選択中' : '選択する'}
							</button>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<!-- フィードバックタブ -->
		{#if activeTab === 'feedback'}
			<section class="section">
				{#if selectedCandidate}
					<form on:submit|preventDefault={submitFeedback} class="advanced-feedback">
						<div class="feedback-grid">
							{#each feedbackKeys as key (key)}
								<div class="feedback-card-advanced">
									<div class="feedback-header">
										<h4>{labels[key]}</h4>
										<div class="score-big">{feedbackScores[key] || '—'}</div>
									</div>
									<input
										type="range"
										min="1"
										max="5"
										step="1"
										bind:value={feedbackScores[key]}
										class="advanced-slider"
									/>
									<div class="feedback-scale">
										<span>非常に悪い</span>
										<span>非常に良い</span>
									</div>
								</div>
							{/each}
						</div>
						<button type="submit" class="btn btn-submit" disabled={feedbackSubmitted}>
							{feedbackSubmitted ? '✓ 送信完了' : 'フィードバックを送信'}
						</button>
					</form>
				{:else}
					<div class="empty-advanced">
						<p>候補を選択してください</p>
					</div>
				{/if}
			</section>
		{/if}

		<!-- メトリクスタブ -->
		{#if activeTab === 'metrics'}
			<section class="section">
				<div class="metrics-advanced">
					<div class="metrics-row">
						{#each feedbackKeys as key (key)}
							<div class="metric-advanced">
								<div class="metric-icon">📈</div>
								<div class="metric-data">
									<div class="metric-name">{shortLabels[key]}</div>
									<div class="metric-number">{data.metrics.averageScores[key].toFixed(2)}</div>
								</div>
							</div>
						{/each}
					</div>

					<div class="charts-grid">
						<div class="chart-card">
							<h4>平均対話ターン数</h4>
							<div class="chart-value">{data.metrics.averageTurns.toFixed(1)}</div>
							<p>ターン数が少ないほど効率的</p>
						</div>
						<div class="chart-card">
							<h4>完了率</h4>
							<div class="chart-value">{Math.round(data.metrics.completionRate * 100)}%</div>
							<p>completeness ≥ 0.8 到達率</p>
						</div>
						<div class="chart-card">
							<h4>平均完了時間</h4>
							<div class="chart-value">
								{Math.round(data.metrics.averageCompletionTimeSeconds)}秒
							</div>
							<p>初回メッセージから完了まで</p>
						</div>
					</div>

					<div class="model-section">
						<h4>モデル使用率</h4>
						{#each Object.entries(data.metrics.modelUsage) as [model, usage]}
							<div class="model-bar">
								<span class="model-name">{model}</span>
								<div class="bar">
									<div class="bar-fill" style="width: {usage * 100}%"></div>
								</div>
								<span class="model-percent">{Math.round(usage * 100)}%</span>
							</div>
						{/each}
					</div>
				</div>
			</section>
		{/if}

		<!-- 診断情報タブ -->
		{#if activeTab === 'diagnostics'}
			<section class="section">
				<div class="diagnostics-view">
					<div class="diag-header">
						<h3>会話診断情報</h3>
						<a href={data.diagnosticInfo.langfuseTraceUrl} target="_blank" class="link-external">
							Langfuseで開く →
						</a>
					</div>

					<div class="diag-meta">
						<div class="meta-item">
							<span class="meta-label">会話ID</span>
							<code>{data.diagnosticInfo.conversationId}</code>
						</div>
						<div class="meta-item">
							<span class="meta-label">トレースID</span>
							<code>{data.diagnosticInfo.traceId}</code>
						</div>
					</div>

					<div class="system-prompt-section">
						<h4>システムプロンプト</h4>
						<pre class="code-block">{data.diagnosticInfo.systemPrompt}</pre>
					</div>

					<div class="turns-section">
						<h4>対話ターン履歴</h4>
						{#each data.diagnosticInfo.turns as turn}
							<div class="turn-card">
								<div class="turn-header">
									<span class="turn-number">ターン {turn.turnNumber}</span>
									<span class="turn-model">{turn.model}</span>
								</div>
								<div class="turn-user">
									<strong>ユーザー:</strong>
									{turn.userMessage}
								</div>
								<div class="turn-llm">
									<strong>LLM:</strong>
									{turn.llmResponse}
								</div>
								<div class="turn-metrics">
									<span>入力トークン: {turn.inputTokens}</span>
									<span>出力トークン: {turn.outputTokens}</span>
									<span>実行時間: {turn.executionTimeMs}ms</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</section>
		{/if}

		<!-- プロンプト管理タブ -->
		{#if activeTab === 'prompts'}
			<section class="section">
				<div class="prompt-management">
					<h3>プロンプトバージョン管理</h3>
					<div class="version-selector">
						{#each data.promptVersions as version}
							<label class="version-card">
								<input
									type="radio"
									name="prompt-version"
									value={version.version}
									bind:group={selectedPromptVersion}
								/>
								<div class="version-info">
									<div class="version-label">{version.label}</div>
									{#if version.active}
										<span class="badge-active">現行</span>
									{/if}
								</div>
							</label>
						{/each}
					</div>
					<button class="btn btn-primary">プロンプトを切り替え</button>
				</div>
			</section>
		{/if}
	</div>
</div>

<style>
	.pattern-c {
		max-width: 1400px;
		margin: 0 auto;
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
		padding: 1.5rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		border-radius: 0.75rem;
		color: white;
	}

	.page-header h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.75rem;
	}

	.description {
		margin: 0;
		font-size: 0.95rem;
		opacity: 0.9;
	}

	.header-actions {
		display: flex;
		gap: 0.75rem;
	}

	.btn {
		padding: 0.625rem 1.25rem;
		border: none;
		border-radius: 0.5rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-outline {
		background: rgba(255, 255, 255, 0.2);
		color: white;
		border: 1px solid rgba(255, 255, 255, 0.4);
	}

	.btn-outline:hover {
		background: rgba(255, 255, 255, 0.3);
	}

	.advanced-tabs {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
		padding: 0.5rem;
		background: white;
		border-radius: 0.75rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.tab {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.375rem;
		padding: 0.75rem;
		background: transparent;
		border: none;
		border-radius: 0.5rem;
		cursor: pointer;
		transition: all 0.2s;
		color: #6c757d;
	}

	.tab:hover {
		background: #f8f9fa;
	}

	.tab.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.tab-icon {
		font-size: 1.5rem;
	}

	.tab-label {
		font-size: 0.85rem;
		font-weight: 600;
	}

	.content-wrapper {
		min-height: 600px;
	}

	.section {
		background: white;
		border-radius: 0.75rem;
		padding: 2rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	/* 候補比較レイアウト */
	.candidates-comparison {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 2rem;
	}

	.candidate-column {
		border: 3px solid #dee2e6;
		border-radius: 1rem;
		overflow: hidden;
		transition: all 0.3s;
	}

	.candidate-column:hover {
		border-color: #adb5bd;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
	}

	.candidate-column.selected {
		border-color: #667eea;
		box-shadow: 0 12px 32px rgba(102, 126, 234, 0.25);
	}

	.candidate-header {
		padding: 1.5rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.candidate-header h3 {
		margin: 0;
		font-size: 1.25rem;
	}

	.badge-pro {
		padding: 0.25rem 0.75rem;
		background: rgba(255, 255, 255, 0.3);
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.candidate-body {
		padding: 1.5rem;
	}

	.candidate-desc {
		margin: 0 0 1.5rem 0;
		color: #6c757d;
	}

	.specs {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.spec-item {
		display: flex;
		gap: 0.75rem;
	}

	.spec-icon {
		font-size: 1.5rem;
	}

	.spec-label {
		font-size: 0.8rem;
		color: #6c757d;
		margin-bottom: 0.25rem;
	}

	.spec-value {
		font-size: 0.9rem;
		color: #212529;
		font-weight: 500;
	}

	.completeness-meter {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: #f8f9fa;
		border-radius: 0.5rem;
	}

	.meter-label {
		font-size: 0.85rem;
		color: #6c757d;
		font-weight: 600;
	}

	.meter-bar {
		height: 10px;
		background: #e9ecef;
		border-radius: 5px;
		overflow: hidden;
	}

	.meter-fill {
		height: 100%;
		background: linear-gradient(90deg, #667eea 0%, #28a745 100%);
	}

	.meter-value {
		font-size: 1rem;
		color: #667eea;
		font-weight: 700;
	}

	.btn-select-candidate {
		width: 100%;
		padding: 1rem;
		border: none;
		background: #667eea;
		color: white;
		font-weight: 700;
		font-size: 1rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-select-candidate:hover {
		background: #5568d3;
	}

	.btn-select-candidate.selected {
		background: #28a745;
	}

	/* フィードバック */
	.advanced-feedback {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.feedback-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1.5rem;
	}

	.feedback-card-advanced {
		padding: 1.5rem;
		background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
	}

	.feedback-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.feedback-header h4 {
		margin: 0;
		font-size: 1rem;
		color: #495057;
	}

	.score-big {
		font-size: 2.5rem;
		font-weight: 700;
		color: #667eea;
	}

	.advanced-slider {
		width: 100%;
		height: 8px;
		border-radius: 4px;
		-webkit-appearance: none;
		background: linear-gradient(to right, #dc3545 0%, #ffc107 50%, #28a745 100%);
		margin-bottom: 0.5rem;
	}

	.advanced-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: white;
		border: 4px solid #667eea;
		cursor: pointer;
		box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
	}

	.feedback-scale {
		display: flex;
		justify-content: space-between;
		font-size: 0.75rem;
		color: #6c757d;
	}

	.btn-submit {
		padding: 1rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		font-size: 1.1rem;
	}

	.btn-submit:disabled {
		background: #6c757d;
	}

	.empty-advanced {
		text-align: center;
		padding: 4rem;
		color: #6c757d;
	}

	/* メトリクス */
	.metrics-advanced {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	.metrics-row {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
	}

	.metric-advanced {
		display: flex;
		gap: 1rem;
		padding: 1.5rem;
		background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
		border-radius: 0.75rem;
		border: 2px solid #dee2e6;
	}

	.metric-icon {
		font-size: 2rem;
	}

	.metric-name {
		font-size: 0.85rem;
		color: #6c757d;
		margin-bottom: 0.5rem;
	}

	.metric-number {
		font-size: 2rem;
		font-weight: 700;
		color: #667eea;
	}

	.charts-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1.5rem;
	}

	.chart-card {
		padding: 1.5rem;
		background: white;
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
		text-align: center;
	}

	.chart-card h4 {
		margin: 0 0 1rem 0;
		font-size: 1rem;
		color: #495057;
	}

	.chart-value {
		font-size: 2.5rem;
		font-weight: 700;
		color: #667eea;
		margin-bottom: 0.5rem;
	}

	.chart-card p {
		margin: 0;
		font-size: 0.85rem;
		color: #6c757d;
	}

	.model-section h4 {
		margin: 0 0 1rem 0;
		font-size: 1.1rem;
	}

	.model-bar {
		display: grid;
		grid-template-columns: 200px 1fr 80px;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.model-name {
		font-size: 0.9rem;
		font-weight: 600;
	}

	.bar {
		height: 28px;
		background: #e9ecef;
		border-radius: 14px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
	}

	.model-percent {
		text-align: right;
		font-weight: 700;
		color: #667eea;
	}

	/* 診断情報 */
	.diagnostics-view {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.diag-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.diag-header h3 {
		margin: 0;
		font-size: 1.5rem;
	}

	.link-external {
		color: #667eea;
		text-decoration: none;
		font-weight: 600;
	}

	.diag-meta {
		display: flex;
		gap: 2rem;
	}

	.meta-item {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.meta-label {
		font-size: 0.85rem;
		color: #6c757d;
	}

	code {
		padding: 0.5rem;
		background: #f8f9fa;
		border-radius: 0.25rem;
		font-family: 'Courier New', monospace;
		font-size: 0.85rem;
	}

	.system-prompt-section h4,
	.turns-section h4 {
		margin: 0 0 1rem 0;
		font-size: 1.1rem;
	}

	.code-block {
		padding: 1rem;
		background: #282c34;
		color: #abb2bf;
		border-radius: 0.5rem;
		overflow-x: auto;
		font-size: 0.875rem;
		line-height: 1.5;
	}

	.turn-card {
		padding: 1.5rem;
		background: #f8f9fa;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.turn-header {
		display: flex;
		justify-content: space-between;
		margin-bottom: 1rem;
		font-weight: 600;
	}

	.turn-number {
		color: #667eea;
	}

	.turn-model {
		color: #6c757d;
		font-size: 0.85rem;
	}

	.turn-user,
	.turn-llm {
		margin-bottom: 0.75rem;
		padding: 0.75rem;
		background: white;
		border-radius: 0.375rem;
	}

	.turn-metrics {
		display: flex;
		gap: 1rem;
		font-size: 0.8rem;
		color: #6c757d;
	}

	/* プロンプト管理 */
	.prompt-management {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.prompt-management h3 {
		margin: 0;
		font-size: 1.5rem;
	}

	.version-selector {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.version-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1.25rem;
		border: 2px solid #dee2e6;
		border-radius: 0.5rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.version-card:hover {
		border-color: #667eea;
		background: #f8f9ff;
	}

	.version-card input[type='radio'] {
		width: 20px;
		height: 20px;
		cursor: pointer;
	}

	.version-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex: 1;
	}

	.version-label {
		font-weight: 600;
	}

	.badge-active {
		padding: 0.25rem 0.75rem;
		background: #d4edda;
		color: #155724;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 700;
	}

	.btn-primary {
		padding: 1rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		font-size: 1.1rem;
	}

	@media (max-width: 1024px) {
		.candidates-comparison {
			grid-template-columns: 1fr;
		}

		.feedback-grid,
		.metrics-row,
		.charts-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
