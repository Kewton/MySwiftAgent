<script lang="ts">
  import { onMount } from 'svelte';
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
      alert('フィードバックを送信しました。ありがとうございました!');
    }, 300);
  }
</script>

<div class="pattern-b">
  <header class="page-header">
    <h2>パターンB: 標準・バランス型</h2>
    <p class="description">使いやすさと機能のバランスを重視した、長期運用に適したデザインです。</p>
  </header>

  <!-- タブナビゲーション -->
  <div class="tabs">
    <a href="#candidates" class="tab active">候補選択</a>
    <a href="#feedback" class="tab">フィードバック</a>
    <a href="#metrics" class="tab">メトリクス</a>
  </div>

  <!-- 複数候補提示セクション -->
  <section class="section" id="candidates">
    <div class="section-header">
      <h3>要件候補の選択</h3>
      <span class="badge">2件の候補</span>
    </div>

    <div class="candidates-grid">
      {#each data.candidates as candidate}
        <div
          class="candidate-card"
          class:selected={selectedCandidate === candidate.id}
          class:recommended={candidate.recommended}
          on:click={() => selectCandidate(candidate.id)}
          on:keypress={(e) => e.key === 'Enter' && selectCandidate(candidate.id)}
          role="button"
          tabindex="0"
        >
          {#if candidate.recommended}
            <div class="recommended-banner">推奨</div>
          {/if}
          {#if selectedCandidate === candidate.id}
            <div class="selected-check">✓</div>
          {/if}

          <div class="card-body">
            <h4>{candidate.label}</h4>
            <p class="description-text">{candidate.description}</p>

            <div class="details-grid">
              <div class="detail-item">
                <div class="detail-icon">📊</div>
                <div class="detail-content">
                  <div class="detail-label">データソース</div>
                  <div class="detail-value">{candidate.data_source}</div>
                </div>
              </div>

              <div class="detail-item">
                <div class="detail-icon">⚙️</div>
                <div class="detail-content">
                  <div class="detail-label">処理内容</div>
                  <div class="detail-value">{candidate.process_description}</div>
                </div>
              </div>

              <div class="detail-item">
                <div class="detail-icon">📤</div>
                <div class="detail-content">
                  <div class="detail-label">出力形式</div>
                  <div class="detail-value">{candidate.output_format}</div>
                </div>
              </div>

              <div class="detail-item">
                <div class="detail-icon">🕐</div>
                <div class="detail-content">
                  <div class="detail-label">スケジュール</div>
                  <div class="detail-value">{candidate.schedule}</div>
                </div>
              </div>
            </div>

            <div class="progress-bar">
              <div class="progress-fill" style="width: {candidate.completeness * 100}%"></div>
            </div>
            <div class="progress-label">完成度: {Math.round(candidate.completeness * 100)}%</div>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- フィードバックセクション -->
  <section class="section" id="feedback">
    <div class="section-header">
      <h3>品質フィードバック</h3>
      {#if selectedCandidate}
        <span class="badge badge-success">候補選択済み</span>
      {:else}
        <span class="badge badge-warning">候補を選択してください</span>
      {/if}
    </div>

    {#if selectedCandidate}
      <form on:submit|preventDefault={submitFeedback} class="feedback-form">
        <div class="score-cards">
          {#each Object.entries(feedbackScores) as [key, value]}
            {@const labels = {
              requirement_clarity: '要件明確化の分かりやすさ',
              hypothesis_accuracy: '仮説の精度',
              response_naturalness: '応答の自然さ',
              overall_satisfaction: '総合満足度'
            }}
            <div class="score-card">
              <label for={key}>{labels[key]}</label>
              <div class="score-display">{value || '未評価'}</div>
              <input
                id={key}
                type="range"
                min="1"
                max="5"
                step="1"
                bind:value={feedbackScores[key]}
                class="score-slider"
              />
              <div class="score-labels">
                <span>1</span>
                <span>2</span>
                <span>3</span>
                <span>4</span>
                <span>5</span>
              </div>
            </div>
          {/each}
        </div>

        <button type="submit" class="btn btn-primary" disabled={feedbackSubmitted}>
          {feedbackSubmitted ? '✓ 送信完了' : 'フィードバックを送信'}
        </button>
      </form>
    {:else}
      <div class="empty-state">
        <p>候補を選択すると、フィードバックフォームが表示されます</p>
      </div>
    {/if}
  </section>

  <!-- メトリクスセクション -->
  <section class="section" id="metrics">
    <div class="section-header">
      <h3>品質メトリクス</h3>
      <span class="badge">過去30日間</span>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-value">{data.metrics.averageScores.requirement_clarity.toFixed(1)}</div>
        <div class="metric-label">要件明確化スコア</div>
        <div class="metric-change positive">+0.3</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{data.metrics.averageScores.hypothesis_accuracy.toFixed(1)}</div>
        <div class="metric-label">仮説精度スコア</div>
        <div class="metric-change positive">+0.2</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{data.metrics.averageTurns.toFixed(1)}</div>
        <div class="metric-label">平均対話ターン数</div>
        <div class="metric-change negative">-0.5</div>
      </div>

      <div class="metric-card">
        <div class="metric-value">{Math.round(data.metrics.completionRate * 100)}%</div>
        <div class="metric-label">完了率</div>
        <div class="metric-change positive">+2%</div>
      </div>
    </div>

    <div class="model-usage">
      <h4>モデル使用率</h4>
      <div class="usage-bars">
        {#each Object.entries(data.metrics.modelUsage) as [model, usage]}
          <div class="usage-item">
            <div class="usage-label">{model}</div>
            <div class="usage-bar">
              <div class="usage-fill" style="width: {usage * 100}%"></div>
            </div>
            <div class="usage-percentage">{Math.round(usage * 100)}%</div>
          </div>
        {/each}
      </div>
    </div>
  </section>
</div>

<style>
  .pattern-b {
    max-width: 1200px;
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

  /* タブナビゲーション */
  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 2px solid #dee2e6;
  }

  .tab {
    padding: 0.75rem 1.5rem;
    text-decoration: none;
    color: #6c757d;
    font-weight: 500;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
  }

  .tab:hover {
    color: #495057;
    border-bottom-color: #adb5bd;
  }

  .tab.active {
    color: #667eea;
    border-bottom-color: #667eea;
  }

  /* セクション */
  .section {
    background: white;
    border-radius: 0.5rem;
    padding: 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .section-header h3 {
    margin: 0;
    font-size: 1.4rem;
    color: #212529;
  }

  .badge {
    padding: 0.375rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.8rem;
    font-weight: 600;
    background: #e9ecef;
    color: #495057;
  }

  .badge-success {
    background: #d4edda;
    color: #155724;
  }

  .badge-warning {
    background: #fff3cd;
    color: #856404;
  }

  /* 候補カード */
  .candidates-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
    gap: 1.5rem;
  }

  .candidate-card {
    position: relative;
    border: 2px solid #dee2e6;
    border-radius: 0.75rem;
    padding: 0;
    transition: all 0.2s;
    cursor: pointer;
    overflow: hidden;
  }

  .candidate-card:hover {
    border-color: #adb5bd;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  .candidate-card.recommended {
    border-color: #28a745;
  }

  .candidate-card.selected {
    border-color: #667eea;
    background: #f8f9ff;
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.2);
  }

  .recommended-banner {
    position: absolute;
    top: 12px;
    right: -35px;
    background: #28a745;
    color: white;
    padding: 0.25rem 3rem;
    font-size: 0.75rem;
    font-weight: 600;
    transform: rotate(45deg);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  .selected-check {
    position: absolute;
    top: 1rem;
    right: 1rem;
    width: 32px;
    height: 32px;
    background: #667eea;
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    font-weight: bold;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  }

  .card-body {
    padding: 1.5rem;
  }

  .card-body h4 {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .description-text {
    margin: 0 0 1.5rem 0;
    color: #6c757d;
    font-size: 0.9rem;
  }

  .details-grid {
    display: grid;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .detail-item {
    display: flex;
    gap: 0.75rem;
  }

  .detail-icon {
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .detail-content {
    flex: 1;
  }

  .detail-label {
    font-size: 0.8rem;
    color: #6c757d;
    margin-bottom: 0.25rem;
  }

  .detail-value {
    font-size: 0.9rem;
    color: #212529;
    font-weight: 500;
  }

  .progress-bar {
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s;
  }

  .progress-label {
    text-align: right;
    font-size: 0.85rem;
    color: #6c757d;
    font-weight: 500;
  }

  /* フィードバックフォーム */
  .feedback-form {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .score-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
  }

  .score-card {
    background: #f8f9fa;
    border-radius: 0.5rem;
    padding: 1.25rem;
  }

  .score-card label {
    display: block;
    font-weight: 600;
    color: #495057;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
  }

  .score-display {
    font-size: 2rem;
    font-weight: 700;
    color: #667eea;
    text-align: center;
    margin-bottom: 0.75rem;
  }

  .score-slider {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    outline: none;
    -webkit-appearance: none;
    background: linear-gradient(to right, #dc3545 0%, #ffc107 50%, #28a745 100%);
    margin-bottom: 0.5rem;
  }

  .score-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    border: 3px solid #667eea;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  .score-slider::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: white;
    border: 3px solid #667eea;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  .score-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #6c757d;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    color: #6c757d;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    width: 100%;
  }

  .btn-primary:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }

  .btn-primary:disabled {
    background: #6c757d;
    cursor: not-allowed;
    transform: none;
  }

  /* メトリクス */
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .metric-card {
    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    border: 1px solid #dee2e6;
    border-radius: 0.5rem;
    padding: 1.5rem;
    text-align: center;
  }

  .metric-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: #667eea;
    margin-bottom: 0.5rem;
  }

  .metric-label {
    font-size: 0.9rem;
    color: #6c757d;
    margin-bottom: 0.5rem;
  }

  .metric-change {
    font-size: 0.85rem;
    font-weight: 600;
  }

  .metric-change.positive {
    color: #28a745;
  }

  .metric-change.negative {
    color: #dc3545;
  }

  .model-usage h4 {
    margin: 0 0 1rem 0;
    font-size: 1.1rem;
    color: #495057;
  }

  .usage-bars {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .usage-item {
    display: grid;
    grid-template-columns: 180px 1fr 60px;
    align-items: center;
    gap: 1rem;
  }

  .usage-label {
    font-size: 0.9rem;
    color: #495057;
    font-weight: 500;
  }

  .usage-bar {
    height: 24px;
    background: #e9ecef;
    border-radius: 12px;
    overflow: hidden;
  }

  .usage-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s;
  }

  .usage-percentage {
    text-align: right;
    font-size: 0.9rem;
    color: #495057;
    font-weight: 600;
  }

  @media (max-width: 768px) {
    .candidates-grid {
      grid-template-columns: 1fr;
    }

    .score-cards {
      grid-template-columns: 1fr;
    }

    .metrics-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
