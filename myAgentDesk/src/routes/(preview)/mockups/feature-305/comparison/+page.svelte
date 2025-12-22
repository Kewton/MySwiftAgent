<script lang="ts">
	// Comparison View for Issue #305 mockups

	const patterns = [
		{
			id: 'pattern-a',
			name: 'A: シンプル・ミニマル',
			description: '最小限のUI。全体進捗のみ表示。',
			pros: ['高速な読み込み', 'シンプルで直感的', 'モバイル最適', '実装コスト低'],
			cons: ['詳細情報の欠如', 'リトライ機能なし', '問題特定が困難'],
			scores: { ux: 9, features: 4, performance: 10, implementation: 10 },
			recommended: false
		},
		{
			id: 'pattern-b',
			name: 'B: 標準・バランス型',
			description: 'タスク単位の進捗表示。バランスの取れたUI。',
			pros: ['タスク単位の進捗可視化', '成功/失敗の明確な表示', 'Langfuse連携', '適度な情報量'],
			cons: ['YAMLプレビューなし', 'リトライはAPI経由のみ'],
			scores: { ux: 8, features: 7, performance: 8, implementation: 8 },
			recommended: true
		},
		{
			id: 'pattern-c',
			name: 'C: リッチ・高機能',
			description: '詳細なワークフロー情報とYAMLプレビュー。',
			pros: ['YAMLプレビュー', '検証結果表示', '即時リトライ', '詳細なエラー情報'],
			cons: ['複雑なUI', '読み込み負荷', '学習コスト'],
			scores: { ux: 6, features: 10, performance: 5, implementation: 5 },
			recommended: false
		},
		{
			id: 'pattern-d',
			name: 'D: 革新的・実験的',
			description: 'リアルタイムストリーミングとAIサジェスト。',
			pros: ['リアルタイムログ', 'AI最適化提案', 'ビジュアルグラフ', '高度なUX'],
			cons: ['実装コスト高', 'WebSocket必要', '保守が複雑'],
			scores: { ux: 9, features: 9, performance: 6, implementation: 3 },
			recommended: false
		}
	];

	let selectedPatterns = $state<Set<string>>(new Set(['pattern-a', 'pattern-b']));
	let sortBy = $state<'ux' | 'features' | 'performance' | 'implementation'>('ux');

	function togglePattern(id: string) {
		const newSet = new Set(selectedPatterns);
		if (newSet.has(id)) {
			if (newSet.size > 1) {
				newSet.delete(id);
			}
		} else {
			newSet.add(id);
		}
		selectedPatterns = newSet;
	}

	const filteredPatterns = $derived(patterns.filter((p) => selectedPatterns.has(p.id)));

	const sortedPatterns = $derived(
		[...filteredPatterns].sort((a, b) => b.scores[sortBy] - a.scores[sortBy])
	);
</script>

<div class="comparison-page">
	<div class="page-header">
		<h2>パターン比較</h2>
		<p class="subtitle">Issue #305: ワークフロー自動生成UIの4つのデザインパターンを比較</p>
	</div>

	<!-- Pattern Selector -->
	<div class="pattern-selector">
		<span class="selector-label">表示パターン:</span>
		{#each patterns as pattern}
			<button
				class="pattern-toggle"
				class:active={selectedPatterns.has(pattern.id)}
				onclick={() => togglePattern(pattern.id)}
			>
				{pattern.name}
			</button>
		{/each}
	</div>

	<!-- Sort Options -->
	<div class="sort-options">
		<span class="sort-label">並び替え:</span>
		<button class:active={sortBy === 'ux'} onclick={() => (sortBy = 'ux')}>UX</button>
		<button class:active={sortBy === 'features'} onclick={() => (sortBy = 'features')}>機能</button>
		<button class:active={sortBy === 'performance'} onclick={() => (sortBy = 'performance')}>
			性能
		</button>
		<button class:active={sortBy === 'implementation'} onclick={() => (sortBy = 'implementation')}>
			実装容易性
		</button>
	</div>

	<!-- Comparison Grid -->
	<div class="comparison-grid" style="--columns: {filteredPatterns.length}">
		{#each sortedPatterns as pattern}
			<div class="pattern-card" class:recommended={pattern.recommended}>
				{#if pattern.recommended}
					<div class="recommended-badge">推奨</div>
				{/if}

				<div class="card-header">
					<h3>{pattern.name}</h3>
					<p>{pattern.description}</p>
				</div>

				<!-- Preview Link -->
				<a href="/mockups/feature-305/{pattern.id}" class="preview-link" target="_blank">
					プレビューを開く
				</a>

				<!-- Scores -->
				<div class="scores-section">
					<h4>評価スコア</h4>
					<div class="score-item">
						<span class="score-label">UX</span>
						<div class="score-bar">
							<div class="score-fill" style="width: {pattern.scores.ux * 10}%"></div>
						</div>
						<span class="score-value">{pattern.scores.ux}/10</span>
					</div>
					<div class="score-item">
						<span class="score-label">機能</span>
						<div class="score-bar">
							<div class="score-fill" style="width: {pattern.scores.features * 10}%"></div>
						</div>
						<span class="score-value">{pattern.scores.features}/10</span>
					</div>
					<div class="score-item">
						<span class="score-label">性能</span>
						<div class="score-bar">
							<div class="score-fill" style="width: {pattern.scores.performance * 10}%"></div>
						</div>
						<span class="score-value">{pattern.scores.performance}/10</span>
					</div>
					<div class="score-item">
						<span class="score-label">実装容易性</span>
						<div class="score-bar">
							<div class="score-fill" style="width: {pattern.scores.implementation * 10}%"></div>
						</div>
						<span class="score-value">{pattern.scores.implementation}/10</span>
					</div>
				</div>

				<!-- Pros -->
				<div class="pros-section">
					<h4>長所</h4>
					<ul>
						{#each pattern.pros as pro}
							<li class="pro-item">{pro}</li>
						{/each}
					</ul>
				</div>

				<!-- Cons -->
				<div class="cons-section">
					<h4>短所</h4>
					<ul>
						{#each pattern.cons as con}
							<li class="con-item">{con}</li>
						{/each}
					</ul>
				</div>

				<!-- Select Button -->
				<button class="select-btn" class:primary={pattern.recommended}>
					{pattern.recommended ? 'このパターンを採用' : '選択する'}
				</button>
			</div>
		{/each}
	</div>

	<!-- Summary Table -->
	<div class="summary-section">
		<h3>総合比較表</h3>
		<div class="table-wrapper">
			<table>
				<thead>
					<tr>
						<th>項目</th>
						{#each patterns as pattern}
							<th class:recommended={pattern.recommended}>{pattern.name.split(':')[0]}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					<tr>
						<td>進捗表示</td>
						<td>全体のみ</td>
						<td class="highlight">タスク単位</td>
						<td>タスク詳細</td>
						<td>リアルタイム</td>
					</tr>
					<tr>
						<td>YAMLプレビュー</td>
						<td>-</td>
						<td>-</td>
						<td class="highlight">OK</td>
						<td>-</td>
					</tr>
					<tr>
						<td>リトライ機能</td>
						<td>-</td>
						<td>API経由</td>
						<td class="highlight">即時リトライ</td>
						<td>即時リトライ</td>
					</tr>
					<tr>
						<td>Langfuse連携</td>
						<td>リンクのみ</td>
						<td class="highlight">トレースリンク</td>
						<td class="highlight">トレースリンク</td>
						<td class="highlight">トレースリンク</td>
					</tr>
					<tr>
						<td>実装コスト</td>
						<td class="highlight">低</td>
						<td class="highlight">中</td>
						<td>高</td>
						<td>非常に高</td>
					</tr>
					<tr>
						<td>保守性</td>
						<td class="highlight">高</td>
						<td class="highlight">高</td>
						<td>中</td>
						<td>低</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>

	<!-- Recommendation -->
	<div class="recommendation-section">
		<h3>推奨事項</h3>
		<div class="recommendation-content">
			<div class="recommendation-card">
				<h4>MVP（初期リリース）向け</h4>
				<p>
					<strong>パターンB（標準・バランス型）</strong>を推奨します。
					タスク単位の進捗表示、成功/失敗の明確な表示、Langfuseトレースリンクなど、
					必要十分な機能を備えつつ、実装・保守コストを抑えられます。
				</p>
			</div>
			<div class="recommendation-card">
				<h4>将来拡張</h4>
				<p>
					ユーザーフィードバックに基づき、<strong>パターンC</strong>の機能（YAMLプレビュー、即時リトライ）
					を段階的に追加することを検討してください。
				</p>
			</div>
		</div>
	</div>
</div>

<style>
	.comparison-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 1.5rem;
	}

	.page-header {
		text-align: center;
		margin-bottom: 1.5rem;
	}

	h2 {
		font-size: 1.5rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0 0 0.25rem;
	}

	.subtitle {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	.pattern-selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
		padding: 1rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		margin-bottom: 1rem;
	}

	.selector-label {
		font-size: 0.875rem;
		font-weight: 500;
		color: #475569;
	}

	.pattern-toggle {
		padding: 0.375rem 0.75rem;
		background: #f1f5f9;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		color: #64748b;
		cursor: pointer;
	}

	.pattern-toggle:hover {
		background: #e2e8f0;
	}

	.pattern-toggle.active {
		background: #3b82f6;
		border-color: #3b82f6;
		color: white;
	}

	.sort-options {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.sort-label {
		font-size: 0.875rem;
		color: #64748b;
	}

	.sort-options button {
		padding: 0.25rem 0.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		color: #64748b;
		cursor: pointer;
	}

	.sort-options button:hover {
		background: #f1f5f9;
	}

	.sort-options button.active {
		background: #1e293b;
		border-color: #1e293b;
		color: white;
	}

	.comparison-grid {
		display: grid;
		grid-template-columns: repeat(var(--columns, 2), 1fr);
		gap: 1rem;
		margin-bottom: 2rem;
	}

	@media (max-width: 900px) {
		.comparison-grid {
			grid-template-columns: 1fr;
		}
	}

	.pattern-card {
		padding: 1.25rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		position: relative;
	}

	.pattern-card.recommended {
		border-color: #10b981;
		box-shadow: 0 0 0 1px #10b981;
	}

	.recommended-badge {
		position: absolute;
		top: -8px;
		right: 12px;
		padding: 0.125rem 0.5rem;
		background: #10b981;
		color: white;
		font-size: 0.625rem;
		font-weight: 700;
		border-radius: 0.25rem;
	}

	.card-header h3 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.25rem;
	}

	.card-header p {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0 0 0.75rem;
	}

	.preview-link {
		display: block;
		text-align: center;
		padding: 0.5rem;
		background: #f1f5f9;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		color: #3b82f6;
		text-decoration: none;
		margin-bottom: 1rem;
	}

	.preview-link:hover {
		background: #e2e8f0;
	}

	.scores-section,
	.pros-section,
	.cons-section {
		margin-bottom: 1rem;
	}

	.scores-section h4,
	.pros-section h4,
	.cons-section h4 {
		font-size: 0.75rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.5rem;
	}

	.score-item {
		display: grid;
		grid-template-columns: 80px 1fr 40px;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.375rem;
	}

	.score-label {
		font-size: 0.75rem;
		color: #475569;
	}

	.score-bar {
		height: 6px;
		background: #e2e8f0;
		border-radius: 3px;
		overflow: hidden;
	}

	.score-fill {
		height: 100%;
		background: linear-gradient(90deg, #10b981, #3b82f6);
		border-radius: 3px;
	}

	.score-value {
		font-size: 0.75rem;
		font-weight: 600;
		color: #1e293b;
		text-align: right;
	}

	.pros-section ul,
	.cons-section ul {
		margin: 0;
		padding-left: 1rem;
	}

	.pro-item,
	.con-item {
		font-size: 0.75rem;
		margin-bottom: 0.25rem;
	}

	.pro-item {
		color: #166534;
	}

	.con-item {
		color: #dc2626;
	}

	.select-btn {
		width: 100%;
		padding: 0.625rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: #475569;
		cursor: pointer;
	}

	.select-btn:hover {
		background: #f1f5f9;
	}

	.select-btn.primary {
		background: #10b981;
		border-color: #10b981;
		color: white;
	}

	.select-btn.primary:hover {
		background: #059669;
	}

	.summary-section {
		margin-bottom: 2rem;
	}

	.summary-section h3 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.table-wrapper {
		overflow-x: auto;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.75rem;
		background: white;
	}

	th,
	td {
		padding: 0.625rem;
		text-align: left;
		border: 1px solid #e2e8f0;
	}

	th {
		background: #f8fafc;
		font-weight: 600;
		color: #475569;
	}

	th.recommended {
		background: #dcfce7;
		color: #166534;
	}

	td {
		color: #64748b;
	}

	td:first-child {
		font-weight: 500;
		color: #1e293b;
		background: #f8fafc;
	}

	td.highlight {
		background: #f0fdf4;
		color: #166534;
		font-weight: 500;
	}

	.recommendation-section {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		padding: 1.5rem;
	}

	.recommendation-section h3 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.recommendation-content {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 1rem;
	}

	.recommendation-card {
		padding: 1rem;
		background: #f8fafc;
		border-radius: 0.375rem;
	}

	.recommendation-card h4 {
		font-size: 0.875rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.recommendation-card p {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0;
		line-height: 1.5;
	}

	.recommendation-card strong {
		color: #10b981;
	}
</style>
