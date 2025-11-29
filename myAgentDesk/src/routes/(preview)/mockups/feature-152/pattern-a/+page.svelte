<script lang="ts">
	import type { PageData } from './$types';

	export let data: PageData;

	let selectedCandidate: string | null = null;
	let feedbackSubmitted = false;
	let feedbackScores = {
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
		setTimeout(() => {
			alert('フィードバックを送信しました。ありがとうございました！');
		}, 300);
	}
</script>

<div class="pattern-a">
	<header class="page-header">
		<h2>パターンA: シンプル・ミニマル</h2>
		<p class="description">必要最小限の機能で、使いやすさを重視したデザインです。</p>
	</header>

	<!-- 複数候補提示セクション -->
	<section class="section">
		<h3>要件候補の選択</h3>
		<p class="section-description">
			ご要望の解釈として、以下の候補をご用意しました。適したものをお選びください。
		</p>

		<div class="candidates">
			{#each data.candidates as candidate}
				<div
					class="candidate-card"
					class:selected={selectedCandidate === candidate.id}
					class:recommended={candidate.recommended}
				>
					<div class="card-header">
						<h4>{candidate.label}</h4>
						{#if candidate.recommended}
							<span class="badge badge-recommended">推奨</span>
						{/if}
					</div>
					<p class="candidate-description">{candidate.description}</p>

					<dl class="candidate-details">
						<dt>データソース</dt>
						<dd>{candidate.data_source}</dd>

						<dt>処理内容</dt>
						<dd>{candidate.process_description}</dd>

						<dt>出力形式</dt>
						<dd>{candidate.output_format}</dd>

						<dt>スケジュール</dt>
						<dd>{candidate.schedule}</dd>
					</dl>

					<div class="card-footer">
						<span class="completeness">完成度: {Math.round(candidate.completeness * 100)}%</span>
						<button
							class="btn btn-select"
							class:active={selectedCandidate === candidate.id}
							on:click={() => selectCandidate(candidate.id)}
						>
							{selectedCandidate === candidate.id ? '選択中' : '選択する'}
						</button>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- フィードバックセクション -->
	{#if selectedCandidate}
		<section class="section">
			<h3>品質フィードバック</h3>
			<p class="section-description">
				要件定義の品質向上のため、以下の項目について評価をお願いします。
			</p>

			<form on:submit|preventDefault={submitFeedback} class="feedback-form">
				<div class="score-group">
					<label for="requirement_clarity">
						要件明確化の分かりやすさ
						<span class="score-value">{feedbackScores.requirement_clarity || '未評価'}</span>
					</label>
					<input
						id="requirement_clarity"
						type="range"
						min="1"
						max="5"
						step="1"
						bind:value={feedbackScores.requirement_clarity}
						class="score-slider"
					/>
					<div class="score-labels">
						<span>1 (低)</span>
						<span>5 (高)</span>
					</div>
				</div>

				<div class="score-group">
					<label for="hypothesis_accuracy">
						仮説の精度
						<span class="score-value">{feedbackScores.hypothesis_accuracy || '未評価'}</span>
					</label>
					<input
						id="hypothesis_accuracy"
						type="range"
						min="1"
						max="5"
						step="1"
						bind:value={feedbackScores.hypothesis_accuracy}
						class="score-slider"
					/>
					<div class="score-labels">
						<span>1 (低)</span>
						<span>5 (高)</span>
					</div>
				</div>

				<div class="score-group">
					<label for="response_naturalness">
						応答の自然さ
						<span class="score-value">{feedbackScores.response_naturalness || '未評価'}</span>
					</label>
					<input
						id="response_naturalness"
						type="range"
						min="1"
						max="5"
						step="1"
						bind:value={feedbackScores.response_naturalness}
						class="score-slider"
					/>
					<div class="score-labels">
						<span>1 (低)</span>
						<span>5 (高)</span>
					</div>
				</div>

				<div class="score-group">
					<label for="overall_satisfaction">
						総合満足度
						<span class="score-value">{feedbackScores.overall_satisfaction || '未評価'}</span>
					</label>
					<input
						id="overall_satisfaction"
						type="range"
						min="1"
						max="5"
						step="1"
						bind:value={feedbackScores.overall_satisfaction}
						class="score-slider"
					/>
					<div class="score-labels">
						<span>1 (低)</span>
						<span>5 (高)</span>
					</div>
				</div>

				<button type="submit" class="btn btn-primary" disabled={feedbackSubmitted}>
					{feedbackSubmitted ? '送信済み' : 'フィードバックを送信'}
				</button>
			</form>
		</section>
	{/if}
</div>

<style>
	.pattern-a {
		max-width: 900px;
		margin: 0 auto;
	}

	.page-header {
		margin-bottom: 2rem;
	}

	.page-header h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.75rem;
		color: #212529;
	}

	.description {
		margin: 0;
		color: #6c757d;
		font-size: 0.95rem;
	}

	.section {
		background: white;
		border-radius: 0.5rem;
		padding: 1.5rem;
		margin-bottom: 1.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.section h3 {
		margin: 0 0 0.5rem 0;
		font-size: 1.25rem;
		color: #212529;
	}

	.section-description {
		margin: 0 0 1.5rem 0;
		color: #6c757d;
		font-size: 0.9rem;
	}

	/* 候補カード */
	.candidates {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 1rem;
	}

	.candidate-card {
		border: 2px solid #dee2e6;
		border-radius: 0.5rem;
		padding: 1.25rem;
		transition: all 0.2s;
		cursor: pointer;
	}

	.candidate-card:hover {
		border-color: #adb5bd;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
	}

	.candidate-card.recommended {
		border-color: #28a745;
	}

	.candidate-card.selected {
		border-color: #667eea;
		background: #f8f9ff;
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.card-header h4 {
		margin: 0;
		font-size: 1.1rem;
		color: #212529;
	}

	.badge {
		padding: 0.25rem 0.75rem;
		border-radius: 1rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.badge-recommended {
		background: #d4edda;
		color: #155724;
	}

	.candidate-description {
		margin: 0 0 1rem 0;
		color: #6c757d;
		font-size: 0.9rem;
	}

	.candidate-details {
		margin: 1rem 0;
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.5rem;
		font-size: 0.85rem;
	}

	.candidate-details dt {
		font-weight: 600;
		color: #495057;
	}

	.candidate-details dd {
		margin: 0;
		color: #6c757d;
	}

	.card-footer {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid #dee2e6;
	}

	.completeness {
		font-size: 0.85rem;
		color: #6c757d;
		font-weight: 500;
	}

	/* ボタン */
	.btn {
		padding: 0.5rem 1.25rem;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.9rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-select {
		background: #667eea;
		color: white;
	}

	.btn-select:hover {
		background: #5568d3;
	}

	.btn-select.active {
		background: #4c51bf;
	}

	.btn-primary {
		background: #28a745;
		color: white;
		width: 100%;
		padding: 0.75rem;
		font-size: 1rem;
		margin-top: 1rem;
	}

	.btn-primary:hover:not(:disabled) {
		background: #218838;
	}

	.btn-primary:disabled {
		background: #6c757d;
		cursor: not-allowed;
	}

	/* フィードバックフォーム */
	.feedback-form {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.score-group label {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
		font-weight: 500;
		color: #495057;
	}

	.score-value {
		font-size: 1.1rem;
		color: #667eea;
		font-weight: 600;
	}

	.score-slider {
		width: 100%;
		height: 8px;
		border-radius: 4px;
		outline: none;
		-webkit-appearance: none;
		background: linear-gradient(to right, #dc3545 0%, #ffc107 50%, #28a745 100%);
	}

	.score-slider::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: white;
		border: 3px solid #667eea;
		cursor: pointer;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.score-slider::-moz-range-thumb {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: white;
		border: 3px solid #667eea;
		cursor: pointer;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.score-labels {
		display: flex;
		justify-content: space-between;
		font-size: 0.8rem;
		color: #6c757d;
		margin-top: 0.25rem;
	}

	@media (max-width: 768px) {
		.candidates {
			grid-template-columns: 1fr;
		}
	}
</style>
