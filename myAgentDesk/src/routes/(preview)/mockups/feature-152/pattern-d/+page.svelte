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
		requirement_clarity: '要件明確化',
		hypothesis_accuracy: '仮説精度',
		response_naturalness: '応答自然さ',
		overall_satisfaction: '総合満足度'
	};

	let selectedCandidate: string | null = null;
	let feedbackSubmitted = false;
	let activeView = 'selection';
	let aiRecommendation = 'A';
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
		feedbackSubmitted = true;
	}

	function switchView(view: string) {
		activeView = view;
	}
</script>

<div class="pattern-d">
	<header class="futuristic-header">
		<div class="header-content">
			<h2>パターンD: 革新的・実験的</h2>
			<p class="subtitle">AIアシスト機能とABテストを搭載した次世代UI</p>
		</div>
		<div class="ai-badge">
			<span class="badge-icon">🤖</span>
			<span>AI推奨システム</span>
		</div>
	</header>

	<nav class="modern-nav">
		<button
			class="nav-item"
			class:active={activeView === 'selection'}
			on:click={() => switchView('selection')}
		>
			<span class="nav-icon">🎯</span>
			<span>AI候補選択</span>
		</button>
		<button
			class="nav-item"
			class:active={activeView === 'feedback'}
			on:click={() => switchView('feedback')}
		>
			<span class="nav-icon">⭐</span>
			<span>スマートフィードバック</span>
		</button>
		<button
			class="nav-item"
			class:active={activeView === 'dashboard'}
			on:click={() => switchView('dashboard')}
		>
			<span class="nav-icon">📊</span>
			<span>リアルタイムダッシュボード</span>
		</button>
		<button
			class="nav-item"
			class:active={activeView === 'abtest'}
			on:click={() => switchView('abtest')}
		>
			<span class="nav-icon">🧪</span>
			<span>ABテスト</span>
		</button>
	</nav>

	<div class="content-area">
		{#if activeView === 'selection'}
			<section class="ai-selection">
				<div class="ai-recommendation-banner">
					<div class="ai-avatar">🤖</div>
					<div class="ai-message">
						<strong>AI推奨:</strong> あなたの要件には「シンプル型」が最適です。
						<span class="confidence">信頼度: 92%</span>
					</div>
				</div>

				<div class="candidates-modern">
					{#each data.candidates as candidate}
						<div
							class="modern-card"
							class:selected={selectedCandidate === candidate.id}
							class:ai-recommended={candidate.id === aiRecommendation}
						>
							{#if candidate.id === aiRecommendation}
								<div class="ai-rec-badge">AI推奨</div>
							{/if}

							<div class="card-visual">
								<div class="visual-icon">{candidate.id === 'A' ? '🎯' : '🚀'}</div>
								<h3>{candidate.label}</h3>
							</div>

							<div class="card-content">
								<p class="card-description">{candidate.description}</p>

								<div class="smart-specs">
									<div class="spec-row">
										<span class="spec-emoji">📊</span>
										<div class="spec-text">
											<div class="spec-title">データソース</div>
											<div class="spec-detail">{candidate.data_source}</div>
										</div>
									</div>

									<div class="spec-row">
										<span class="spec-emoji">⚙️</span>
										<div class="spec-text">
											<div class="spec-title">処理内容</div>
											<div class="spec-detail">{candidate.process_description}</div>
										</div>
									</div>

									<div class="spec-row">
										<span class="spec-emoji">📤</span>
										<div class="spec-text">
											<div class="spec-title">出力形式</div>
											<div class="spec-detail">{candidate.output_format}</div>
										</div>
									</div>

									<div class="spec-row">
										<span class="spec-emoji">🕐</span>
										<div class="spec-text">
											<div class="spec-title">スケジュール</div>
											<div class="spec-detail">{candidate.schedule}</div>
										</div>
									</div>
								</div>

								<div class="score-visual">
									<div class="score-circle" style="--score: {candidate.completeness};">
										<div class="score-inner">
											<span class="score-number">{Math.round(candidate.completeness * 100)}</span>
											<span class="score-unit">%</span>
										</div>
									</div>
									<span class="score-label">完成度</span>
								</div>
							</div>

							<button
								class="futuristic-button"
								class:selected={selectedCandidate === candidate.id}
								on:click={() => selectCandidate(candidate.id)}
							>
								{selectedCandidate === candidate.id ? '✓ 選択済み' : '選択する'}
							</button>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		{#if activeView === 'feedback'}
			<section class="smart-feedback">
				{#if selectedCandidate}
					<div class="feedback-header">
						<h3>スマートフィードバック</h3>
						<p>AIがあなたの評価から学習し、サービスを改善します</p>
					</div>

					<form on:submit|preventDefault={submitFeedback} class="futuristic-form">
						<div class="feedback-items">
							{#each feedbackKeys as key (key)}
								<div class="smart-score-item">
									<div class="score-header">
										<span class="score-label">{labels[key]}</span>
										<span class="score-value-display">{feedbackScores[key] || '—'}/5</span>
									</div>
									<input
										type="range"
										min="1"
										max="5"
										step="1"
										bind:value={feedbackScores[key]}
										class="futuristic-slider"
									/>
									<div class="slider-marks">
										{#each [1, 2, 3, 4, 5] as mark}
											<span class="mark" class:active={feedbackScores[key] >= mark}>{mark}</span>
										{/each}
									</div>
								</div>
							{/each}
						</div>

						<button type="submit" class="submit-futuristic" disabled={feedbackSubmitted}>
							{feedbackSubmitted ? '✓ フィードバック完了' : '送信してAIに学習させる'}
						</button>
					</form>
				{:else}
					<div class="empty-futuristic">
						<div class="empty-icon">🎯</div>
						<p>候補を選択してフィードバックを送信</p>
					</div>
				{/if}
			</section>
		{/if}

		{#if activeView === 'dashboard'}
			<section class="realtime-dashboard">
				<h3>リアルタイムダッシュボード</h3>

				<div class="dashboard-grid">
					<div class="dashboard-card primary">
						<div class="card-icon">📈</div>
						<div class="card-data">
							<div class="card-value">
								{data.metrics.averageScores.overall_satisfaction.toFixed(2)}
							</div>
							<div class="card-label">総合満足度</div>
							<div class="card-trend positive">↑ 2.3%</div>
						</div>
					</div>

					<div class="dashboard-card">
						<div class="card-icon">⏱️</div>
						<div class="card-data">
							<div class="card-value">{data.metrics.averageTurns.toFixed(1)}</div>
							<div class="card-label">平均対話ターン</div>
							<div class="card-trend negative">↓ 0.7</div>
						</div>
					</div>

					<div class="dashboard-card">
						<div class="card-icon">✅</div>
						<div class="card-data">
							<div class="card-value">{Math.round(data.metrics.completionRate * 100)}%</div>
							<div class="card-label">完了率</div>
							<div class="card-trend positive">↑ 3%</div>
						</div>
					</div>

					<div class="dashboard-card">
						<div class="card-icon">⚡</div>
						<div class="card-data">
							<div class="card-value">{data.metrics.averageCompletionTimeSeconds}秒</div>
							<div class="card-label">平均完了時間</div>
							<div class="card-trend positive">↓ 12秒</div>
						</div>
					</div>
				</div>

				<div class="live-activity">
					<h4>🔴 ライブアクティビティ</h4>
					<div class="activity-feed">
						<div class="activity-item">
							<span class="activity-time">2秒前</span>
							<span class="activity-text">ユーザー #1234 が候補Aを選択</span>
						</div>
						<div class="activity-item">
							<span class="activity-time">5秒前</span>
							<span class="activity-text">フィードバック受信: スコア 4.5/5</span>
						</div>
						<div class="activity-item">
							<span class="activity-time">8秒前</span>
							<span class="activity-text">ユーザー #5678 が会話を完了</span>
						</div>
					</div>
				</div>
			</section>
		{/if}

		{#if activeView === 'abtest'}
			<section class="ab-test-view">
				<h3>ABテスト結果</h3>

				<div class="ab-comparison">
					<div class="version-column">
						<div class="version-header version-a">
							<h4>バージョン A</h4>
							<span class="sample-size">{data.abTestResults.versionA.sampleSize}サンプル</span>
						</div>

						<div class="version-metrics">
							{#each feedbackKeys as key (key)}
								<div class="metric-row">
									<span class="metric-name">{labels[key]}</span>
									<div class="metric-bar-container">
										<div
											class="metric-bar"
											style="width: {data.abTestResults.versionA.averageScores[key] * 20}%"
										></div>
									</div>
									<span class="metric-value"
										>{data.abTestResults.versionA.averageScores[key].toFixed(2)}</span
									>
								</div>
							{/each}
						</div>
					</div>

					<div class="comparison-indicator">
						<div class="vs-badge">VS</div>
						<div class="winner-badge">バージョンBが優勢</div>
					</div>

					<div class="version-column">
						<div class="version-header version-b">
							<h4>バージョン B</h4>
							<span class="sample-size">{data.abTestResults.versionB.sampleSize}サンプル</span>
						</div>

						<div class="version-metrics">
							{#each feedbackKeys as key (key)}
								<div class="metric-row">
									<span class="metric-name">{labels[key]}</span>
									<div class="metric-bar-container">
										<div
											class="metric-bar version-b-bar"
											style="width: {data.abTestResults.versionB.averageScores[key] * 20}%"
										></div>
									</div>
									<span class="metric-value"
										>{data.abTestResults.versionB.averageScores[key].toFixed(2)}</span
									>
								</div>
							{/each}
						</div>
					</div>
				</div>

				<div class="statistical-significance">
					<h4>統計的有意性</h4>
					<div class="significance-grid">
						{#each feedbackKeys as key (key)}
							<div
								class="significance-item"
								class:significant={data.abTestResults.statisticalSignificance[key].significant}
							>
								<span class="sig-label">{labels[key]}</span>
								<span class="sig-pvalue"
									>p = {data.abTestResults.statisticalSignificance[key].pValue.toFixed(3)}</span
								>
								<span class="sig-result"
									>{data.abTestResults.statisticalSignificance[key].significant
										? '✓ 有意'
										: '— 有意でない'}</span
								>
							</div>
						{/each}
					</div>
				</div>
			</section>
		{/if}
	</div>
</div>

<style>
	.pattern-d {
		max-width: 1400px;
		margin: 0 auto;
	}

	.futuristic-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 2rem;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
		border-radius: 1rem;
		color: white;
		margin-bottom: 1.5rem;
		box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
	}

	.header-content h2 {
		margin: 0 0 0.5rem 0;
		font-size: 2rem;
		font-weight: 700;
	}

	.subtitle {
		margin: 0;
		font-size: 1rem;
		opacity: 0.9;
	}

	.ai-badge {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1.25rem;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 2rem;
		backdrop-filter: blur(10px);
		font-weight: 600;
	}

	.badge-icon {
		font-size: 1.5rem;
	}

	.modern-nav {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.nav-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 1.25rem;
		background: white;
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
		cursor: pointer;
		transition: all 0.3s;
		font-weight: 600;
		color: #495057;
	}

	.nav-item:hover {
		border-color: #667eea;
		background: #f8f9ff;
		transform: translateY(-2px);
	}

	.nav-item.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		border-color: transparent;
		color: white;
		box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
	}

	.nav-icon {
		font-size: 2rem;
	}

	.content-area {
		background: white;
		border-radius: 1rem;
		padding: 2rem;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
		min-height: 600px;
	}

	/* AI候補選択 */
	.ai-recommendation-banner {
		display: flex;
		gap: 1rem;
		padding: 1.5rem;
		background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);
		border-radius: 0.75rem;
		margin-bottom: 2rem;
		border: 2px solid #4dd0e1;
	}

	.ai-avatar {
		font-size: 3rem;
		flex-shrink: 0;
	}

	.ai-message {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 1rem;
	}

	.confidence {
		font-size: 0.875rem;
		color: #00796b;
		font-weight: 600;
	}

	.candidates-modern {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 2rem;
	}

	.modern-card {
		position: relative;
		border: 3px solid #dee2e6;
		border-radius: 1.25rem;
		overflow: hidden;
		transition: all 0.3s;
		background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
	}

	.modern-card:hover {
		transform: translateY(-4px);
		box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
	}

	.modern-card.ai-recommended {
		border-color: #4dd0e1;
	}

	.modern-card.selected {
		border-color: #667eea;
		box-shadow: 0 16px 48px rgba(102, 126, 234, 0.3);
	}

	.ai-rec-badge {
		position: absolute;
		top: 1rem;
		right: -2rem;
		padding: 0.5rem 3rem;
		background: linear-gradient(135deg, #4dd0e1 0%, #00acc1 100%);
		color: white;
		font-size: 0.75rem;
		font-weight: 700;
		transform: rotate(45deg);
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
	}

	.card-visual {
		padding: 2rem;
		text-align: center;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.visual-icon {
		font-size: 4rem;
		margin-bottom: 1rem;
	}

	.card-visual h3 {
		margin: 0;
		font-size: 1.5rem;
	}

	.card-content {
		padding: 1.5rem;
	}

	.card-description {
		margin: 0 0 1.5rem 0;
		color: #6c757d;
	}

	.smart-specs {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.spec-row {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f8f9fa;
		border-radius: 0.5rem;
	}

	.spec-emoji {
		font-size: 1.5rem;
	}

	.spec-title {
		font-size: 0.75rem;
		color: #6c757d;
		margin-bottom: 0.25rem;
	}

	.spec-detail {
		font-size: 0.875rem;
		color: #212529;
		font-weight: 500;
	}

	.score-visual {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
	}

	.score-circle {
		width: 100px;
		height: 100px;
		border-radius: 50%;
		background: conic-gradient(
			#667eea 0deg,
			#667eea calc(var(--score) * 360deg),
			#e9ecef calc(var(--score) * 360deg)
		);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.score-inner {
		width: 70px;
		height: 70px;
		border-radius: 50%;
		background: white;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-direction: column;
	}

	.score-number {
		font-size: 1.75rem;
		font-weight: 700;
		color: #667eea;
		line-height: 1;
	}

	.score-unit {
		font-size: 0.875rem;
		color: #6c757d;
	}

	.score-label {
		font-size: 0.875rem;
		color: #6c757d;
		font-weight: 600;
	}

	.futuristic-button {
		width: 100%;
		padding: 1.25rem;
		border: none;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		font-size: 1.1rem;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.3s;
	}

	.futuristic-button:hover {
		transform: scale(1.02);
		box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
	}

	.futuristic-button.selected {
		background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
	}

	/* スマートフィードバック */
	.smart-feedback {
		padding: 1rem;
	}

	.feedback-header {
		margin-bottom: 2rem;
		text-align: center;
	}

	.feedback-header h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1.75rem;
	}

	.feedback-header p {
		margin: 0;
		color: #6c757d;
	}

	.futuristic-form {
		max-width: 800px;
		margin: 0 auto;
	}

	.feedback-items {
		display: flex;
		flex-direction: column;
		gap: 2rem;
		margin-bottom: 2rem;
	}

	.smart-score-item {
		padding: 1.5rem;
		background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
	}

	.score-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.score-label {
		font-weight: 600;
		color: #495057;
	}

	.score-value-display {
		font-size: 1.5rem;
		font-weight: 700;
		color: #667eea;
	}

	.futuristic-slider {
		width: 100%;
		height: 10px;
		border-radius: 5px;
		-webkit-appearance: none;
		background: linear-gradient(to right, #dc3545 0%, #ffc107 50%, #28a745 100%);
		margin-bottom: 0.75rem;
	}

	.futuristic-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: white;
		border: 4px solid #667eea;
		cursor: pointer;
		box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
	}

	.slider-marks {
		display: flex;
		justify-content: space-between;
	}

	.mark {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: #e9ecef;
		color: #6c757d;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.mark.active {
		background: #667eea;
		color: white;
	}

	.submit-futuristic {
		width: 100%;
		padding: 1.25rem;
		border: none;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		font-size: 1.25rem;
		font-weight: 700;
		border-radius: 0.75rem;
		cursor: pointer;
		transition: all 0.3s;
	}

	.submit-futuristic:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
	}

	.submit-futuristic:disabled {
		background: #6c757d;
	}

	.empty-futuristic {
		text-align: center;
		padding: 4rem;
	}

	.empty-icon {
		font-size: 5rem;
		margin-bottom: 1rem;
	}

	/* リアルタイムダッシュボード */
	.realtime-dashboard h3 {
		margin: 0 0 1.5rem 0;
		font-size: 1.75rem;
	}

	.dashboard-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 1.5rem;
		margin-bottom: 2rem;
	}

	.dashboard-card {
		display: flex;
		gap: 1rem;
		padding: 1.5rem;
		background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
		transition: all 0.3s;
	}

	.dashboard-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
	}

	.dashboard-card.primary {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}

	.card-icon {
		font-size: 2.5rem;
	}

	.card-value {
		font-size: 2rem;
		font-weight: 700;
		margin-bottom: 0.25rem;
	}

	.card-label {
		font-size: 0.875rem;
		opacity: 0.8;
		margin-bottom: 0.5rem;
	}

	.card-trend {
		font-size: 0.875rem;
		font-weight: 600;
	}

	.card-trend.positive {
		color: #28a745;
	}

	.card-trend.negative {
		color: #dc3545;
	}

	.live-activity {
		padding: 1.5rem;
		background: #f8f9fa;
		border-radius: 0.75rem;
	}

	.live-activity h4 {
		margin: 0 0 1rem 0;
		font-size: 1.1rem;
	}

	.activity-feed {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.activity-item {
		padding: 0.75rem;
		background: white;
		border-radius: 0.5rem;
		display: flex;
		gap: 1rem;
	}

	.activity-time {
		font-size: 0.8rem;
		color: #6c757d;
		flex-shrink: 0;
	}

	.activity-text {
		font-size: 0.9rem;
		color: #495057;
	}

	/* ABテスト */
	.ab-test-view h3 {
		margin: 0 0 1.5rem 0;
		font-size: 1.75rem;
	}

	.ab-comparison {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 2rem;
		margin-bottom: 2rem;
	}

	.version-column {
		border: 2px solid #dee2e6;
		border-radius: 0.75rem;
		overflow: hidden;
	}

	.version-header {
		padding: 1.5rem;
		color: white;
	}

	.version-header.version-a {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	}

	.version-header.version-b {
		background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
	}

	.version-header h4 {
		margin: 0 0 0.5rem 0;
		font-size: 1.25rem;
	}

	.sample-size {
		font-size: 0.875rem;
		opacity: 0.9;
	}

	.version-metrics {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.metric-row {
		display: grid;
		grid-template-columns: 120px 1fr 60px;
		align-items: center;
		gap: 0.75rem;
	}

	.metric-name {
		font-size: 0.875rem;
		color: #495057;
		font-weight: 600;
	}

	.metric-bar-container {
		height: 24px;
		background: #e9ecef;
		border-radius: 12px;
		overflow: hidden;
	}

	.metric-bar {
		height: 100%;
		background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
		transition: width 0.3s;
	}

	.metric-bar.version-b-bar {
		background: linear-gradient(90deg, #f093fb 0%, #f5576c 100%);
	}

	.metric-value {
		text-align: right;
		font-weight: 700;
		color: #495057;
	}

	.comparison-indicator {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
	}

	.vs-badge {
		width: 60px;
		height: 60px;
		border-radius: 50%;
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.25rem;
		font-weight: 700;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
	}

	.winner-badge {
		padding: 0.5rem 1rem;
		background: #d4edda;
		color: #155724;
		border-radius: 1rem;
		font-size: 0.85rem;
		font-weight: 600;
		text-align: center;
	}

	.statistical-significance {
		padding: 1.5rem;
		background: #f8f9fa;
		border-radius: 0.75rem;
	}

	.statistical-significance h4 {
		margin: 0 0 1rem 0;
		font-size: 1.1rem;
	}

	.significance-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 1rem;
	}

	.significance-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1rem;
		background: white;
		border: 2px solid #dee2e6;
		border-radius: 0.5rem;
	}

	.significance-item.significant {
		border-color: #28a745;
		background: #d4edda;
	}

	.sig-label {
		font-weight: 600;
		color: #495057;
	}

	.sig-pvalue {
		font-size: 0.875rem;
		color: #6c757d;
	}

	.sig-result {
		font-size: 0.875rem;
		font-weight: 600;
	}

	@media (max-width: 1024px) {
		.modern-nav {
			grid-template-columns: repeat(2, 1fr);
		}

		.candidates-modern,
		.dashboard-grid,
		.significance-grid {
			grid-template-columns: 1fr;
		}

		.ab-comparison {
			grid-template-columns: 1fr;
			gap: 1rem;
		}

		.comparison-indicator {
			flex-direction: row;
		}
	}
</style>
