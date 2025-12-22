<script lang="ts">
	// Overview page for Issue #305 mockups
</script>

<div class="overview-page">
	<div class="overview-header">
		<h1>Issue #305: ワークフロー自動生成UI</h1>
		<p class="subtitle">Job生成完了時に各タスクのGraphAIワークフローを自動生成する機能のUIモックアップ</p>
	</div>

	<!-- Flow Diagram -->
	<div class="flow-section">
		<h2>処理フロー</h2>
		<div class="flow-diagram">
			<div class="flow-phase">
				<div class="phase-header">
					<span class="phase-number">Input</span>
					<span class="phase-title">要件定義</span>
				</div>
				<div class="phase-content input">
					<div class="data-box">
						<span class="data-label">RequirementVersion</span>
						<span class="data-example">"Gmailから未読メールを取得し、Claude APIで要約してSlackに投稿する"</span>
					</div>
				</div>
			</div>

			<div class="flow-arrow">
				<svg width="40" height="24" viewBox="0 0 40 24" fill="none">
					<path d="M0 12H36M36 12L24 4M36 12L24 20" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>

			<div class="flow-phase">
				<div class="phase-header">
					<span class="phase-number">Phase 1</span>
					<span class="phase-title">Task Analysis</span>
					<span class="phase-progress">0-70%</span>
				</div>
				<div class="phase-content analysis">
					<div class="sub-step">要件分析</div>
					<div class="sub-step">タスク分解</div>
					<div class="sub-step">API選定</div>
					<div class="sub-step">Job登録</div>
				</div>
				<div class="phase-output">
					<span class="output-label">出力:</span>
					<div class="output-items">
						<span class="output-item">JobMaster</span>
						<span class="output-item">TaskMaster x N</span>
					</div>
				</div>
			</div>

			<div class="flow-arrow">
				<svg width="40" height="24" viewBox="0 0 40 24" fill="none">
					<path d="M0 12H36M36 12L24 4M36 12L24 20" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>

			<div class="flow-phase highlight">
				<div class="phase-header">
					<span class="phase-number new">Phase 2 (New)</span>
					<span class="phase-title">Workflow Generation</span>
					<span class="phase-progress">70-95%</span>
				</div>
				<div class="phase-content workflow">
					<div class="workflow-gen">
						<div class="task-workflow">
							<span class="task-label">Task 1</span>
							<span class="arrow">-</span>
							<span class="workflow-label">workflow_1.yaml</span>
						</div>
						<div class="task-workflow">
							<span class="task-label">Task 2</span>
							<span class="arrow">-</span>
							<span class="workflow-label">workflow_2.yaml</span>
						</div>
						<div class="task-workflow">
							<span class="task-label">Task N</span>
							<span class="arrow">-</span>
							<span class="workflow-label">workflow_N.yaml</span>
						</div>
					</div>
				</div>
				<div class="phase-output">
					<span class="output-label">出力:</span>
					<div class="output-items">
						<span class="output-item highlight">WorkflowMaster x N</span>
					</div>
				</div>
			</div>

			<div class="flow-arrow">
				<svg width="40" height="24" viewBox="0 0 40 24" fill="none">
					<path d="M0 12H36M36 12L24 4M36 12L24 20" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>

			<div class="flow-phase">
				<div class="phase-header">
					<span class="phase-number">Output</span>
					<span class="phase-title">Review画面</span>
				</div>
				<div class="phase-content output">
					<div class="result-preview">
						<div class="result-item">
							<span class="result-icon ok">OK</span>
							<span>Job実行可能</span>
						</div>
						<div class="result-item">
							<span class="result-icon">YAML</span>
							<span>Workflow確認</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Pattern Cards -->
	<div class="patterns-section">
		<h2>デザインパターン</h2>
		<div class="patterns-grid">
			<a href="/mockups/feature-305/pattern-a" class="pattern-card">
				<div class="pattern-icon">A</div>
				<div class="pattern-info">
					<h3>シンプル・ミニマル</h3>
					<p>最小限のUI。全体進捗のみ表示。高速レスポンス重視。</p>
					<ul>
						<li>2段階プログレスバー</li>
						<li>全体ステータスのみ</li>
						<li>シンプルな完了表示</li>
					</ul>
				</div>
			</a>

			<a href="/mockups/feature-305/pattern-b" class="pattern-card recommended">
				<span class="recommended-badge">推奨</span>
				<div class="pattern-icon">B</div>
				<div class="pattern-info">
					<h3>標準・バランス型</h3>
					<p>Task Breakdown結果を表示し、各タスクのWorkflow生成状況を可視化。</p>
					<ul>
						<li>Phase表示（2段階）</li>
						<li>Task Breakdown結果</li>
						<li>タスク別Workflow状況</li>
					</ul>
				</div>
			</a>

			<a href="/mockups/feature-305/pattern-c" class="pattern-card">
				<div class="pattern-icon">C</div>
				<div class="pattern-info">
					<h3>リッチ・高機能</h3>
					<p>詳細なワークフロー情報とYAMLプレビュー。</p>
					<ul>
						<li>YAMLプレビュー</li>
						<li>詳細ステータス</li>
						<li>リトライ機能</li>
					</ul>
				</div>
			</a>

			<a href="/mockups/feature-305/pattern-d" class="pattern-card">
				<div class="pattern-icon">D</div>
				<div class="pattern-info">
					<h3>革新的・実験的</h3>
					<p>リアルタイムストリーミングとAIサジェスト。</p>
					<ul>
						<li>リアルタイムログ</li>
						<li>AI最適化提案</li>
						<li>ビジュアライザ</li>
					</ul>
				</div>
			</a>
		</div>
	</div>

	<a href="/mockups/feature-305/comparison" class="compare-link">
		全パターンを比較する
	</a>

	<!-- Data Model -->
	<div class="data-model-section">
		<h2>データモデル</h2>
		<div class="model-diagram">
			<div class="model-entity">
				<div class="entity-header">JobMaster</div>
				<div class="entity-fields">
					<span>id</span>
					<span>name</span>
					<span>status</span>
				</div>
			</div>
			<div class="model-relation">1 : N</div>
			<div class="model-entity">
				<div class="entity-header">TaskMaster</div>
				<div class="entity-fields">
					<span>id</span>
					<span>name</span>
					<span>description</span>
					<span>recommended_apis</span>
				</div>
			</div>
			<div class="model-relation new">1 : 1 (New)</div>
			<div class="model-entity new">
				<div class="entity-header">WorkflowMaster</div>
				<div class="entity-fields">
					<span>id</span>
					<span>yaml_content</span>
					<span>status</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Requirements Summary -->
	<div class="requirements-summary">
		<h2>UI要件サマリ</h2>
		<table>
			<thead>
				<tr>
					<th>要件</th>
					<th>説明</th>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td>2段階進捗表示</td>
					<td>Task Analysis（0-70%）→ Workflow Generation（70-95%）→ 完了（100%）</td>
				</tr>
				<tr>
					<td>Task Breakdown表示</td>
					<td>Phase 1完了後、分解されたタスク一覧と推奨APIを表示</td>
				</tr>
				<tr>
					<td>Workflow生成状況</td>
					<td>各タスクに対するWorkflow生成の進捗・結果を表示</td>
				</tr>
				<tr>
					<td>部分成功対応</td>
					<td>一部タスク失敗時も全体は成功として扱い、失敗リストを表示</td>
				</tr>
				<tr>
					<td>Langfuse連携</td>
					<td>trace_idをレスポンスに含め、トレースリンクを表示</td>
				</tr>
			</tbody>
		</table>
	</div>
</div>

<style>
	.overview-page {
		max-width: 1100px;
		margin: 0 auto;
		padding: 2rem;
	}

	.overview-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.subtitle {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
	}

	h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	/* Flow Diagram */
	.flow-section {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
	}

	.flow-diagram {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		overflow-x: auto;
		padding: 1rem 0;
	}

	.flow-phase {
		flex-shrink: 0;
		min-width: 180px;
		background: #f8fafc;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.flow-phase.highlight {
		border-color: #10b981;
		box-shadow: 0 0 0 1px #10b981;
	}

	.phase-header {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.75rem;
		background: #e2e8f0;
	}

	.flow-phase.highlight .phase-header {
		background: #dcfce7;
	}

	.phase-number {
		font-size: 0.625rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.phase-number.new {
		color: #166534;
	}

	.phase-title {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #1e293b;
	}

	.phase-progress {
		font-size: 0.625rem;
		color: #64748b;
	}

	.phase-content {
		padding: 0.75rem;
	}

	.phase-content.input .data-box {
		padding: 0.5rem;
		background: white;
		border-radius: 0.25rem;
	}

	.data-label {
		display: block;
		font-size: 0.625rem;
		font-weight: 600;
		color: #64748b;
		margin-bottom: 0.25rem;
	}

	.data-example {
		font-size: 0.6875rem;
		color: #475569;
		font-style: italic;
	}

	.sub-step {
		font-size: 0.6875rem;
		color: #475569;
		padding: 0.25rem 0.5rem;
		background: white;
		border-radius: 0.25rem;
		margin-bottom: 0.25rem;
	}

	.workflow-gen {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.task-workflow {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.6875rem;
		padding: 0.25rem 0.5rem;
		background: white;
		border-radius: 0.25rem;
	}

	.task-label {
		color: #1e293b;
		font-weight: 500;
	}

	.arrow {
		color: #94a3b8;
	}

	.workflow-label {
		color: #166534;
		font-family: monospace;
		font-size: 0.625rem;
	}

	.result-preview {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	.result-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		font-size: 0.6875rem;
		color: #475569;
	}

	.result-icon {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.125rem 0.25rem;
		background: #e2e8f0;
		color: #64748b;
		font-size: 0.5rem;
		font-weight: 600;
		border-radius: 0.125rem;
	}

	.result-icon.ok {
		background: #dcfce7;
		color: #166534;
	}

	.phase-output {
		padding: 0.5rem 0.75rem;
		background: #f1f5f9;
		border-top: 1px solid #e2e8f0;
	}

	.output-label {
		font-size: 0.625rem;
		color: #64748b;
	}

	.output-items {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		margin-top: 0.25rem;
	}

	.output-item {
		font-size: 0.625rem;
		padding: 0.125rem 0.375rem;
		background: white;
		border-radius: 0.25rem;
		color: #1e293b;
	}

	.output-item.highlight {
		background: #dcfce7;
		color: #166534;
		font-weight: 500;
	}

	.flow-arrow {
		display: flex;
		align-items: center;
		padding-top: 3rem;
	}

	/* Patterns Section */
	.patterns-section {
		margin-bottom: 1.5rem;
	}

	.patterns-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.pattern-card {
		display: flex;
		gap: 1rem;
		padding: 1.25rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		text-decoration: none;
		transition: all 0.15s;
		position: relative;
	}

	.pattern-card:hover {
		border-color: #10b981;
		box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
	}

	.pattern-card.recommended {
		border-color: #10b981;
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

	.pattern-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		background: #10b981;
		color: white;
		font-size: 1.125rem;
		font-weight: 700;
		border-radius: 0.5rem;
		flex-shrink: 0;
	}

	.pattern-info h3 {
		font-size: 0.9375rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.25rem;
	}

	.pattern-info p {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0 0 0.5rem;
	}

	.pattern-info ul {
		margin: 0;
		padding-left: 1rem;
		font-size: 0.6875rem;
		color: #475569;
	}

	.pattern-info li {
		margin-bottom: 0.125rem;
	}

	.compare-link {
		display: block;
		text-align: center;
		padding: 0.75rem;
		background: #0f172a;
		color: white;
		text-decoration: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		margin-bottom: 2rem;
	}

	.compare-link:hover {
		background: #1e293b;
	}

	/* Data Model */
	.data-model-section {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
	}

	.model-diagram {
		display: flex;
		align-items: center;
		gap: 1rem;
		overflow-x: auto;
		padding: 1rem 0;
	}

	.model-entity {
		flex-shrink: 0;
		min-width: 140px;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		overflow: hidden;
	}

	.model-entity.new {
		border-color: #10b981;
	}

	.entity-header {
		padding: 0.5rem 0.75rem;
		background: #f1f5f9;
		font-size: 0.8125rem;
		font-weight: 600;
		color: #1e293b;
	}

	.model-entity.new .entity-header {
		background: #dcfce7;
		color: #166534;
	}

	.entity-fields {
		padding: 0.5rem 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.entity-fields span {
		font-size: 0.6875rem;
		color: #64748b;
		font-family: monospace;
	}

	.model-relation {
		font-size: 0.75rem;
		color: #94a3b8;
		white-space: nowrap;
	}

	.model-relation.new {
		color: #10b981;
		font-weight: 500;
	}

	/* Requirements Summary */
	.requirements-summary {
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		padding: 1.5rem;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.8125rem;
	}

	th,
	td {
		text-align: left;
		padding: 0.75rem;
		border-bottom: 1px solid #e2e8f0;
	}

	th {
		font-weight: 600;
		color: #475569;
		background: #f8fafc;
	}

	td:first-child {
		font-weight: 500;
		color: #1e293b;
		width: 180px;
	}

	td:last-child {
		color: #64748b;
	}
</style>
