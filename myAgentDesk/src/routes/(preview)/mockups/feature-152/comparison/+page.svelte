<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;

  let selectedPatterns = new Set(['pattern-a', 'pattern-b']);

  function togglePattern(patternId: string) {
    if (selectedPatterns.has(patternId)) {
      selectedPatterns.delete(patternId);
    } else {
      selectedPatterns.add(patternId);
    }
    selectedPatterns = selectedPatterns;
  }
</script>

<div class="comparison-view">
  <header class="comparison-header">
    <h2>パターン比較</h2>
    <p class="description">4つのUIパターンを並べて比較し、最適なデザインを選択できます。</p>
  </header>

  <!-- パターン選択 -->
  <section class="pattern-selector">
    <h3>表示するパターンを選択</h3>
    <div class="selector-grid">
      {#each data.patterns as pattern}
        <label class="selector-item">
          <input
            type="checkbox"
            checked={selectedPatterns.has(pattern.id)}
            on:change={() => togglePattern(pattern.id)}
          />
          <div class="selector-content">
            <div class="selector-icon">{pattern.icon}</div>
            <div class="selector-info">
              <div class="selector-name">{pattern.name}</div>
              <div class="selector-desc">{pattern.description}</div>
            </div>
          </div>
        </label>
      {/each}
    </div>
  </section>

  <!-- 比較テーブル -->
  <section class="comparison-table">
    <h3>機能比較</h3>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th class="feature-column">機能</th>
            {#each data.patterns.filter(p => selectedPatterns.has(p.id)) as pattern}
              <th class="pattern-column">{pattern.name}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each data.featureComparison as feature}
            <tr>
              <td class="feature-name">{feature.name}</td>
              {#each data.patterns.filter(p => selectedPatterns.has(p.id)) as pattern}
                <td class="feature-status">
                  {#if feature.support[pattern.id]}
                    <span class="status-supported">✓</span>
                  {:else}
                    <span class="status-unsupported">—</span>
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </section>

  <!-- スコア比較 -->
  <section class="score-comparison">
    <h3>評価スコア</h3>
    <div class="scores-grid">
      {#each data.patterns.filter(p => selectedPatterns.has(p.id)) as pattern}
        <div class="score-card">
          <div class="score-card-header">
            <div class="score-icon">{pattern.icon}</div>
            <h4>{pattern.name}</h4>
          </div>

          <div class="score-items">
            <div class="score-item">
              <span class="score-label">UX</span>
              <div class="score-bar-wrapper">
                <div class="score-bar" style="width: {pattern.scores.ux * 10}%"></div>
              </div>
              <span class="score-value">{pattern.scores.ux}/10</span>
            </div>

            <div class="score-item">
              <span class="score-label">機能</span>
              <div class="score-bar-wrapper">
                <div class="score-bar" style="width: {pattern.scores.features * 10}%"></div>
              </div>
              <span class="score-value">{pattern.scores.features}/10</span>
            </div>

            <div class="score-item">
              <span class="score-label">性能</span>
              <div class="score-bar-wrapper">
                <div class="score-bar" style="width: {pattern.scores.performance * 10}%"></div>
              </div>
              <span class="score-value">{pattern.scores.performance}/10</span>
            </div>

            <div class="score-item">
              <span class="score-label">保守性</span>
              <div class="score-bar-wrapper">
                <div class="score-bar" style="width: {pattern.scores.maintainability * 10}%"></div>
              </div>
              <span class="score-value">{pattern.scores.maintainability}/10</span>
            </div>
          </div>

          <div class="pros-cons">
            <div class="pros">
              <h5>✅ 長所</h5>
              <ul>
                {#each pattern.pros as pro}
                  <li>{pro}</li>
                {/each}
              </ul>
            </div>
            <div class="cons">
              <h5>⚠️ 短所</h5>
              <ul>
                {#each pattern.cons as con}
                  <li>{con}</li>
                {/each}
              </ul>
            </div>
          </div>

          <div class="card-actions">
            <a href="/mockups/feature-152/{pattern.id}" class="btn btn-preview" target="_blank">
              プレビュー
            </a>
            <button class="btn btn-select">このパターンを選択</button>
          </div>
        </div>
      {/each}
    </div>
  </section>

  <!-- 推奨事項 -->
  <section class="recommendations">
    <h3>推奨事項</h3>
    <div class="recommendation-cards">
      <div class="recommendation-card">
        <div class="rec-icon">🎯</div>
        <div class="rec-content">
          <h4>MVPリリース</h4>
          <p>パターンAをお勧めします。シンプルで使いやすく、素早くリリース可能です。</p>
        </div>
      </div>

      <div class="recommendation-card">
        <div class="rec-icon">⚖️</div>
        <div class="rec-content">
          <h4>長期運用</h4>
          <p>パターンBをお勧めします。機能と保守性のバランスが最適です。</p>
        </div>
      </div>

      <div class="recommendation-card">
        <div class="rec-icon">⚡</div>
        <div class="rec-content">
          <h4>パワーユーザー向け</h4>
          <p>パターンCをお勧めします。全機能を網羅し、高度なカスタマイズが可能です。</p>
        </div>
      </div>

      <div class="recommendation-card">
        <div class="rec-icon">🚀</div>
        <div class="rec-content">
          <h4>差別化戦略</h4>
          <p>パターンDをお勧めします。革新的なUI/UXで競合との差別化を図れます。</p>
        </div>
      </div>
    </div>
  </section>
</div>

<style>
  .comparison-view {
    max-width: 1400px;
    margin: 0 auto;
  }

  .comparison-header {
    margin-bottom: 2rem;
  }

  .comparison-header h2 {
    margin: 0 0 0.5rem 0;
    font-size: 2rem;
    color: #212529;
  }

  .description {
    margin: 0;
    color: #6c757d;
    font-size: 1rem;
  }

  /* パターン選択 */
  .pattern-selector {
    background: white;
    border-radius: 0.75rem;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .pattern-selector h3 {
    margin: 0 0 1.5rem 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .selector-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
  }

  .selector-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    border: 2px solid #dee2e6;
    border-radius: 0.5rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .selector-item:hover {
    border-color: #667eea;
    background: #f8f9ff;
  }

  .selector-item:has(input:checked) {
    border-color: #667eea;
    background: #f8f9ff;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  }

  .selector-item input[type="checkbox"] {
    width: 20px;
    height: 20px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .selector-content {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
  }

  .selector-icon {
    font-size: 2rem;
    flex-shrink: 0;
  }

  .selector-name {
    font-weight: 600;
    color: #212529;
    margin-bottom: 0.25rem;
  }

  .selector-desc {
    font-size: 0.85rem;
    color: #6c757d;
  }

  /* 比較テーブル */
  .comparison-table {
    background: white;
    border-radius: 0.75rem;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .comparison-table h3 {
    margin: 0 0 1.5rem 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .table-container {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th {
    padding: 1rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    font-weight: 600;
    text-align: left;
    font-size: 0.9rem;
  }

  th:first-child {
    border-top-left-radius: 0.5rem;
  }

  th:last-child {
    border-top-right-radius: 0.5rem;
  }

  .feature-column {
    width: 200px;
  }

  .pattern-column {
    text-align: center;
  }

  tbody tr {
    border-bottom: 1px solid #dee2e6;
  }

  tbody tr:hover {
    background: #f8f9fa;
  }

  td {
    padding: 1rem;
  }

  .feature-name {
    font-weight: 500;
    color: #495057;
  }

  .feature-status {
    text-align: center;
  }

  .status-supported {
    color: #28a745;
    font-size: 1.5rem;
    font-weight: bold;
  }

  .status-unsupported {
    color: #dc3545;
    font-size: 1.5rem;
  }

  /* スコア比較 */
  .score-comparison {
    background: white;
    border-radius: 0.75rem;
    padding: 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .score-comparison h3 {
    margin: 0 0 1.5rem 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .scores-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 1.5rem;
  }

  .score-card {
    border: 2px solid #dee2e6;
    border-radius: 0.75rem;
    overflow: hidden;
  }

  .score-card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    border-bottom: 2px solid #dee2e6;
  }

  .score-icon {
    font-size: 2.5rem;
  }

  .score-card-header h4 {
    margin: 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .score-items {
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .score-item {
    display: grid;
    grid-template-columns: 60px 1fr 50px;
    align-items: center;
    gap: 1rem;
  }

  .score-label {
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
  }

  .score-bar-wrapper {
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
  }

  .score-bar {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s;
  }

  .score-value {
    text-align: right;
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
  }

  .pros-cons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
    background: #f8f9fa;
    border-top: 2px solid #dee2e6;
  }

  .pros h5,
  .cons h5 {
    margin: 0 0 0.75rem 0;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .pros h5 {
    color: #28a745;
  }

  .cons h5 {
    color: #ffc107;
  }

  .pros ul,
  .cons ul {
    margin: 0;
    padding-left: 1.25rem;
    list-style: none;
  }

  .pros li,
  .cons li {
    position: relative;
    padding: 0.25rem 0;
    font-size: 0.85rem;
    color: #495057;
  }

  .pros li::before {
    content: '•';
    position: absolute;
    left: -1.25rem;
    color: #28a745;
    font-weight: bold;
  }

  .cons li::before {
    content: '•';
    position: absolute;
    left: -1.25rem;
    color: #ffc107;
    font-weight: bold;
  }

  .card-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
  }

  .btn {
    padding: 1rem;
    border: none;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    text-align: center;
    font-size: 0.9rem;
  }

  .btn-preview {
    background: #6c757d;
    color: white;
  }

  .btn-preview:hover {
    background: #5a6268;
  }

  .btn-select {
    background: #667eea;
    color: white;
  }

  .btn-select:hover {
    background: #5568d3;
  }

  /* 推奨事項 */
  .recommendations {
    background: white;
    border-radius: 0.75rem;
    padding: 2rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .recommendations h3 {
    margin: 0 0 1.5rem 0;
    font-size: 1.25rem;
    color: #212529;
  }

  .recommendation-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .recommendation-card {
    display: flex;
    gap: 1rem;
    padding: 1.5rem;
    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
    border: 2px solid #dee2e6;
    border-radius: 0.5rem;
    transition: all 0.2s;
  }

  .recommendation-card:hover {
    border-color: #667eea;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    transform: translateY(-2px);
  }

  .rec-icon {
    font-size: 2.5rem;
    flex-shrink: 0;
  }

  .rec-content h4 {
    margin: 0 0 0.5rem 0;
    font-size: 1rem;
    color: #212529;
  }

  .rec-content p {
    margin: 0;
    font-size: 0.875rem;
    color: #6c757d;
    line-height: 1.5;
  }

  @media (max-width: 1024px) {
    .selector-grid {
      grid-template-columns: 1fr;
    }

    .scores-grid {
      grid-template-columns: 1fr;
    }

    .recommendation-cards {
      grid-template-columns: 1fr;
    }
  }
</style>
