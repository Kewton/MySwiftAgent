---
model: sonnet
description: "SvelteKitで4つのインタラクティブなUIプロトタイプを生成"
phase: "2. UIモックアップ"
session: "main"
---

# UIモックアップスキル

## 概要
Feature定義からUI要件を抽出し、SvelteKitで4つのインタラクティブなプロトタイプを生成するスキルです。

## 使用方法
- `/ui-mockup [Feature番号]`
- 「Feature #123のUIモックアップを作成してください」
- 「UIプロトタイプを4パターン生成してください」

## 実行内容

あなたは経験豊富なUIデザイナーとして、myAgentDesk（SvelteKit）用のインタラクティブなプロトタイプを作成します。

### 📋 前提条件の確認

1. **Feature要件の分析**
   - ユーザーストーリーの確認
   - 画面要素の洗い出し
   - インタラクション要件の整理

2. **技術環境の確認**
   - SvelteKit 最新版
   - Tailwind CSS（利用可能な場合）
   - 既存コンポーネントライブラリ

### 🎨 4つのデザインパターン生成

#### パターンA: シンプル・ミニマル
```
特徴：
- 必要最小限の機能のみ
- クリーンでシンプルなUI
- 高速な読み込み
- モバイルファースト

適用場面：
- MVP（Minimum Viable Product）
- パフォーマンス重視
- シンプルさを求めるユーザー向け
```

#### パターンB: 標準・バランス型
```
特徴：
- 標準的な機能セット
- 使いやすさと機能のバランス
- 一般的なUIパターン
- アクセシビリティ対応

適用場面：
- 一般的なユーザー向け
- 長期運用を想定
- 保守性重視
```

#### パターンC: リッチ・高機能
```
特徴：
- 全機能を網羅
- リッチなインタラクション
- 高度なカスタマイズ性
- データビジュアライゼーション

適用場面：
- パワーユーザー向け
- 複雑なワークフロー
- エンタープライズ向け
```

#### パターンD: 革新的・実験的
```
特徴：
- 新しいUIパターン
- 革新的なインタラクション
- AIアシスト機能
- 次世代UX

適用場面：
- 差別化を図る
- 早期採用者向け
- ブランディング重視
```

### 📁 ディレクトリ構造の生成

```
myAgentDesk/
├── src/
│   ├── routes/
│   │   ├── (preview)/          # プレビュー専用グループ
│   │   │   ├── +layout.svelte  # プレビュー共通レイアウト
│   │   │   └── mockups/
│   │   │       └── feature-[番号]/
│   │   │           ├── +layout.svelte      # Feature共通設定
│   │   │           ├── +layout.ts          # データローダー
│   │   │           ├── pattern-a/
│   │   │           │   ├── +page.svelte    # パターンA実装
│   │   │           │   └── +page.ts        # パターンA設定
│   │   │           ├── pattern-b/
│   │   │           │   ├── +page.svelte    # パターンB実装
│   │   │           │   └── +page.ts        # パターンB設定
│   │   │           ├── pattern-c/
│   │   │           │   ├── +page.svelte    # パターンC実装
│   │   │           │   └── +page.ts        # パターンC設定
│   │   │           ├── pattern-d/
│   │   │           │   ├── +page.svelte    # パターンD実装
│   │   │           │   └── +page.ts        # パターンD設定
│   │   │           ├── comparison/
│   │   │           │   ├── +page.svelte    # 比較ビュー
│   │   │           │   └── +page.ts        # 比較ロジック
│   │   │           └── data/
│   │   │               ├── mock.json       # モックデータ
│   │   │               └── config.json     # 設定情報
│   │   └── (app)/              # 本番アプリケーション
│   └── lib/
│       └── mockups/
│           └── feature-[番号]/
│               ├── components/  # 共通コンポーネント
│               ├── stores/      # 状態管理
│               └── styles/      # スタイル定義
```

### 🔨 実装テンプレート

#### 1. レイアウトファイル (`+layout.svelte`)
```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import type { LayoutData } from './$types';

  export let data: LayoutData;

  $: currentPattern = $page.url.pathname.split('/').pop();
  $: patterns = ['pattern-a', 'pattern-b', 'pattern-c', 'pattern-d'];
</script>

<div class="mockup-container">
  <!-- ナビゲーションバー -->
  <nav class="mockup-nav">
    <h1>Feature #{data.featureNumber} - UIモックアップ</h1>
    <div class="pattern-switcher">
      {#each patterns as pattern}
        <a
          href="/mockups/feature-{data.featureNumber}/{pattern}"
          class:active={currentPattern === pattern}
        >
          {pattern.replace('pattern-', 'パターン').toUpperCase()}
        </a>
      {/each}
      <a href="/mockups/feature-{data.featureNumber}/comparison">
        比較
      </a>
    </div>
  </nav>

  <!-- コンテンツエリア -->
  <main class="mockup-content">
    <slot />
  </main>

  <!-- メタ情報パネル -->
  <aside class="mockup-info">
    <h3>現在のパターン</h3>
    <p>{currentPattern}</p>
    <h3>特徴</h3>
    <ul>
      {#if data.patterns[currentPattern]}
        {#each data.patterns[currentPattern].features as feature}
          <li>{feature}</li>
        {/each}
      {/if}
    </ul>
  </aside>
</div>

<style>
  .mockup-container {
    display: grid;
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    min-height: 100vh;
  }

  .mockup-nav {
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #dee2e6;
  }

  .pattern-switcher {
    display: flex;
    gap: 1rem;
    margin-top: 1rem;
  }

  .pattern-switcher a {
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    text-decoration: none;
    color: #495057;
    background: white;
    border: 1px solid #dee2e6;
    transition: all 0.2s;
  }

  .pattern-switcher a:hover {
    background: #e9ecef;
  }

  .pattern-switcher a.active {
    background: #007bff;
    color: white;
    border-color: #007bff;
  }

  .mockup-content {
    padding: 2rem;
    overflow-y: auto;
  }

  .mockup-info {
    padding: 1rem;
    background: #f8f9fa;
    border-top: 1px solid #dee2e6;
  }

  @media (min-width: 1024px) {
    .mockup-container {
      grid-template-columns: 250px 1fr;
      grid-template-rows: auto 1fr;
    }

    .mockup-nav {
      grid-column: 1 / -1;
    }

    .mockup-info {
      border-top: none;
      border-right: 1px solid #dee2e6;
    }
  }
</style>
```

#### 2. パターン実装例 (`pattern-a/+page.svelte`)
```svelte
<script lang="ts">
  import type { PageData } from './$types';
  import { onMount } from 'svelte';

  export let data: PageData;

  // パターンA: シンプル・ミニマル実装
  let formData = {
    title: '',
    description: ''
  };

  function handleSubmit() {
    console.log('Submitting:', formData);
    // モックアップなので実際の送信は行わない
    alert('フォーム送信（モック）');
  }
</script>

<div class="pattern-a">
  <h2>パターンA: シンプル・ミニマル</h2>

  <!-- 最小限のフォーム -->
  <form on:submit|preventDefault={handleSubmit}>
    <div class="form-group">
      <label for="title">タイトル</label>
      <input
        id="title"
        type="text"
        bind:value={formData.title}
        required
      />
    </div>

    <div class="form-group">
      <label for="description">説明</label>
      <textarea
        id="description"
        bind:value={formData.description}
        rows="3"
      />
    </div>

    <button type="submit">保存</button>
  </form>

  <!-- データ表示 -->
  <div class="data-preview">
    <h3>プレビュー</h3>
    {#if formData.title}
      <h4>{formData.title}</h4>
      <p>{formData.description}</p>
    {:else}
      <p class="empty">データを入力してください</p>
    {/if}
  </div>
</div>

<style>
  .pattern-a {
    max-width: 600px;
    margin: 0 auto;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  label {
    display: block;
    margin-bottom: 0.25rem;
    font-weight: 500;
  }

  input, textarea {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ced4da;
    border-radius: 0.25rem;
    font-size: 1rem;
  }

  button {
    padding: 0.5rem 1.5rem;
    background: #28a745;
    color: white;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 1rem;
  }

  button:hover {
    background: #218838;
  }

  .data-preview {
    margin-top: 2rem;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 0.25rem;
  }

  .empty {
    color: #6c757d;
    font-style: italic;
  }
</style>
```

#### 3. 比較ビュー (`comparison/+page.svelte`)
```svelte
<script lang="ts">
  import type { PageData } from './$types';

  export let data: PageData;

  const patterns = [
    {
      id: 'pattern-a',
      name: 'シンプル・ミニマル',
      pros: ['高速読み込み', '使いやすい', 'モバイル最適'],
      cons: ['機能制限', 'カスタマイズ性低'],
      score: { ux: 9, features: 5, performance: 10 }
    },
    {
      id: 'pattern-b',
      name: '標準・バランス型',
      pros: ['バランスが良い', '保守性高', '拡張性あり'],
      cons: ['特徴が薄い', '平凡'],
      score: { ux: 7, features: 7, performance: 7 }
    },
    {
      id: 'pattern-c',
      name: 'リッチ・高機能',
      pros: ['全機能搭載', 'カスタマイズ性高', 'プロ向け'],
      cons: ['複雑', '学習コスト高', '重い'],
      score: { ux: 5, features: 10, performance: 5 }
    },
    {
      id: 'pattern-d',
      name: '革新的・実験的',
      pros: ['革新的', '差別化', '最新技術'],
      cons: ['リスク高', '互換性', '学習曲線'],
      score: { ux: 8, features: 8, performance: 6 }
    }
  ];

  let selectedPatterns = new Set(['pattern-a', 'pattern-b']);

  function togglePattern(id: string) {
    if (selectedPatterns.has(id)) {
      selectedPatterns.delete(id);
    } else {
      selectedPatterns.add(id);
    }
    selectedPatterns = selectedPatterns;
  }
</script>

<div class="comparison">
  <h2>パターン比較</h2>

  <!-- パターン選択 -->
  <div class="pattern-selector">
    {#each patterns as pattern}
      <label>
        <input
          type="checkbox"
          checked={selectedPatterns.has(pattern.id)}
          on:change={() => togglePattern(pattern.id)}
        />
        {pattern.name}
      </label>
    {/each}
  </div>

  <!-- 比較テーブル -->
  <div class="comparison-grid">
    {#each patterns.filter(p => selectedPatterns.has(p.id)) as pattern}
      <div class="pattern-card">
        <h3>{pattern.name}</h3>

        <!-- プレビューiframe -->
        <iframe
          src="/mockups/feature-{data.featureNumber}/{pattern.id}"
          title={pattern.name}
        />

        <!-- 評価 -->
        <div class="scores">
          <div class="score-item">
            <span>UX</span>
            <div class="score-bar">
              <div class="score-fill" style="width: {pattern.score.ux * 10}%"></div>
            </div>
            <span>{pattern.score.ux}/10</span>
          </div>
          <div class="score-item">
            <span>機能</span>
            <div class="score-bar">
              <div class="score-fill" style="width: {pattern.score.features * 10}%"></div>
            </div>
            <span>{pattern.score.features}/10</span>
          </div>
          <div class="score-item">
            <span>性能</span>
            <div class="score-bar">
              <div class="score-fill" style="width: {pattern.score.performance * 10}%"></div>
            </div>
            <span>{pattern.score.performance}/10</span>
          </div>
        </div>

        <!-- 長所短所 -->
        <div class="pros-cons">
          <div class="pros">
            <h4>✅ 長所</h4>
            <ul>
              {#each pattern.pros as pro}
                <li>{pro}</li>
              {/each}
            </ul>
          </div>
          <div class="cons">
            <h4>⚠️ 短所</h4>
            <ul>
              {#each pattern.cons as con}
                <li>{con}</li>
              {/each}
            </ul>
          </div>
        </div>

        <!-- アクション -->
        <div class="actions">
          <a
            href="/mockups/feature-{data.featureNumber}/{pattern.id}"
            target="_blank"
          >
            全画面で開く
          </a>
          <button class="select-btn">このパターンを選択</button>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .comparison {
    padding: 1rem;
  }

  .pattern-selector {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .pattern-selector label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }

  .comparison-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
  }

  .pattern-card {
    border: 1px solid #dee2e6;
    border-radius: 0.5rem;
    overflow: hidden;
    background: white;
  }

  .pattern-card h3 {
    padding: 1rem;
    background: #f8f9fa;
    margin: 0;
    border-bottom: 1px solid #dee2e6;
  }

  iframe {
    width: 100%;
    height: 400px;
    border: none;
  }

  .scores {
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
  }

  .score-item {
    display: grid;
    grid-template-columns: 80px 1fr 50px;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .score-bar {
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
  }

  .score-fill {
    height: 100%;
    background: linear-gradient(90deg, #28a745 0%, #ffc107 50%, #dc3545 100%);
    transition: width 0.3s;
  }

  .pros-cons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 1rem;
    gap: 1rem;
    border-bottom: 1px solid #dee2e6;
  }

  .pros h4 {
    color: #28a745;
  }

  .cons h4 {
    color: #ffc107;
  }

  .pros-cons ul {
    margin: 0;
    padding-left: 1.5rem;
  }

  .actions {
    padding: 1rem;
    display: flex;
    gap: 1rem;
    justify-content: space-between;
  }

  .actions a {
    color: #007bff;
    text-decoration: none;
  }

  .actions a:hover {
    text-decoration: underline;
  }

  .select-btn {
    padding: 0.5rem 1rem;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
  }

  .select-btn:hover {
    background: #0056b3;
  }
</style>
```

### 📊 出力フォーマット

#### 1. ディレクトリ構造
```bash
myAgentDesk/src/routes/(preview)/mockups/feature-[番号]/
```

#### 2. アクセスURL
```
開発環境: http://localhost:5173/mockups/feature-[番号]/pattern-[a-d]
比較ビュー: http://localhost:5173/mockups/feature-[番号]/comparison
```

#### 3. 選定記録 (`selected.json`)
```json
{
  "featureNumber": 123,
  "selectedPattern": "pattern-b",
  "selectionDate": "2024-11-07",
  "reasons": [
    "バランスが良い",
    "保守性が高い",
    "既存UIとの整合性"
  ],
  "reviewer": "ユーザー名",
  "notes": "追加の実装メモ"
}
```

## 成功基準

- [ ] 4つの異なるパターンが生成されている
- [ ] 各パターンがインタラクティブに動作する
- [ ] 比較ビューで並べて確認できる
- [ ] SvelteKitの最新バージョンに準拠
- [ ] レスポンシブデザイン対応
- [ ] アクセシビリティ基準を満たす

## 注意事項

- プレビュー環境は `(preview)` グループで隔離
- 本番環境には影響しない
- モックデータは実際のAPIを呼び出さない
- 選定後は選択パターンをベースに本実装を進める