# Phase 5 作業計画: スライド形式のジョブ概要表示

**Phase名**: Phase 5 - スライド形式のジョブ概要表示（要件4）
**優先度**: 高 🔥
**予定工数**: 8時間
**開始予定**: 2025-11-03
**完了予定**: 2025-11-03 EOD

---

## 📋 目的

expertAgent Marp Report APIと連携し、ジョブ概要をスライド形式でビジュアルに表示する。ユーザーが全体像を素早く理解できるようにする。

---

## 🎯 要件概要

### 要件4: スライド形式のジョブ概要表示

**ユーザーストーリー**:
> AIエージェントが作成したジョブの概要をスライド形式で把握したい。なぜなら、全体を理解するにはそれが一番速いインプット方法だからだ。

**主要機能**:
1. **Marpスライド表示**
   - expertAgent Marp Report API（既存: `/v1/marp-report`）との連携
   - ブラウザ内でスライド表示（iframe埋め込み）
   - スライド操作: 前後移動、全画面表示、PDF/PNG出力

2. **スライド内容**
   - タイトル: ジョブ名、作成日時
   - サマリー: ジョブの目的、タスク数、ステータス
   - タスク詳細: 各タスクの説明、入出力、API使用状況
   - 要求緩和提案: infeasible_tasksがある場合の代替案

3. **インタラクティブ機能**
   - スライドから直接編集モードへ遷移
   - 特定タスクの詳細ページへリンク
   - 実行結果との比較表示

---

## 📊 タスク分解

### Task 5.1: expertAgent Marp Report API連携 (2時間)

**実装内容**:
- `src/lib/services/marp-api.ts` を新規作成
- expertAgent の `/v1/marp-report/{jobId}` API を呼び出し
- HTML/PDF/PNG形式のレポート取得

**API仕様**:
```typescript
export interface MarpReportRequest {
  job_id: string;
  format: 'html' | 'pdf' | 'png';
}

export interface MarpReportResponse {
  job_id: string;
  markdown: string;           // 元のMarkdown
  html: string;               // Marp生成済みHTML
  pdf_url: string | null;     // PDFダウンロードURL
  png_urls: string[] | null;  // 各スライドのPNG URL
  slide_count: number;
}

export async function getMarpReport(
  jobId: string,
  format: 'html' | 'pdf' | 'png' = 'html'
): Promise<MarpReportResponse>
```

**エラーハンドリング**:
- ジョブ未作成時（404 Not Found）
- Marp生成失敗時（500 Internal Server Error）
- ネットワークエラー

**テスト** (6テスト):
1. HTML形式のレポート取得成功
2. PDF形式のレポート取得成功
3. PNG形式のレポート取得成功
4. 404エラー処理（ジョブ未作成）
5. 500エラー処理（Marp生成失敗）
6. ネットワークエラー処理

**成果物**:
- `src/lib/services/marp-api.ts` (150行)
- `src/lib/services/marp-api.test.ts` (90行)

---

### Task 5.2: Marpスライド表示コンポーネント (3時間)

**実装内容**:
- `src/lib/components/create_job/MarpViewer.svelte` を新規作成
- iframe でMarp生成HTMLを埋め込み表示
- ローディング状態、エラー状態の表示

**コンポーネント設計**:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { getMarpReport } from '$lib/services/marp-api';

  export let jobId: string;
  export let format: 'html' | 'pdf' | 'png' = 'html';

  let html = '';
  let isLoading = true;
  let error: string | null = null;
  let slideCount = 0;
  let currentSlide = 1;

  onMount(async () => {
    try {
      const report = await getMarpReport(jobId, format);
      html = report.html;
      slideCount = report.slide_count;
      isLoading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load slides';
      isLoading = false;
    }
  });

  function handleMessage(event: MessageEvent) {
    // iframe内のスライド変更イベントをリッスン
    if (event.data?.type === 'slide-change') {
      currentSlide = event.data.slideIndex + 1;
    }
  }
</script>

<svelte:window on:message={handleMessage} />

<div class="marp-viewer">
  {#if isLoading}
    <div class="loading">
      <div class="spinner"></div>
      <p>スライドを読み込み中...</p>
    </div>
  {:else if error}
    <div class="error">
      <p>⚠️ スライドの読み込みに失敗しました</p>
      <p class="text-sm text-gray-500">{error}</p>
    </div>
  {:else}
    <iframe
      title="Marp Slides"
      srcdoc={html}
      class="w-full h-full border-0"
      sandbox="allow-scripts allow-same-origin"
    />
  {/if}
</div>
```

**ダークモード対応**:
- Marp HTMLにカスタムCSSを注入してダークモード適応

**A11y対応**:
- iframe に title 属性を追加
- キーボードナビゲーション（左右矢印キー）

**テスト** (6テスト):
1. 正常にスライドが表示される
2. ローディング状態が表示される
3. エラー状態が表示される
4. スライドカウントが正しい
5. iframeのsandbox属性が設定されている
6. ダークモード対応

**成果物**:
- `src/lib/components/create_job/MarpViewer.svelte` (200行)
- `src/lib/components/create_job/MarpViewer.test.ts` (80行)

---

### Task 5.3: スライド操作UI (2時間)

**実装内容**:
- `src/lib/components/create_job/SlideNavigation.svelte` を新規作成
- スライド前後移動ボタン
- 全画面表示ボタン
- PDF/PNGエクスポートボタン

**コンポーネント設計**:
```svelte
<script lang="ts">
  export let currentSlide = 1;
  export let totalSlides = 1;
  export let onPrev: () => void;
  export let onNext: () => void;
  export let onFullscreen: () => void;
  export let onExportPdf: () => void;
  export let onExportPng: () => void;

  $: canGoPrev = currentSlide > 1;
  $: canGoNext = currentSlide < totalSlides;
</script>

<div class="slide-navigation flex items-center justify-between p-4 bg-white dark:bg-dark-card border-t border-gray-200 dark:border-gray-700">
  <!-- 前後移動 -->
  <div class="flex items-center space-x-3">
    <button
      on:click={onPrev}
      disabled={!canGoPrev}
      class="btn btn-sm"
      aria-label="前のスライド"
    >
      ← 前へ
    </button>
    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
      {currentSlide} / {totalSlides}
    </span>
    <button
      on:click={onNext}
      disabled={!canGoNext}
      class="btn btn-sm"
      aria-label="次のスライド"
    >
      次へ →
    </button>
  </div>

  <!-- 全画面・エクスポート -->
  <div class="flex items-center space-x-2">
    <button
      on:click={onFullscreen}
      class="btn btn-sm"
      aria-label="全画面表示"
    >
      🖥️ 全画面
    </button>
    <button
      on:click={onExportPdf}
      class="btn btn-sm"
      aria-label="PDFでエクスポート"
    >
      📄 PDF
    </button>
    <button
      on:click={onExportPng}
      class="btn btn-sm"
      aria-label="PNGでエクスポート"
    >
      🖼️ PNG
    </button>
  </div>
</div>
```

**機能詳細**:
1. **前後移動**:
   - iframe内のスライドを制御（`postMessage` 使用）
   - 最初/最後のスライドでボタン無効化

2. **全画面表示**:
   - Fullscreen API を使用
   - ESCキーで終了

3. **PDF/PNGエクスポート**:
   - expertAgent API を再度呼び出し（format: 'pdf' | 'png'）
   - ダウンロードリンクを生成してクリック

**キーボードショートカット**:
- `←` / `→` : 前後移動
- `f` : 全画面
- `p` : PDFエクスポート

**テスト** (6テスト):
1. 前へボタンのクリック
2. 次へボタンのクリック
3. ボタンのdisabled状態
4. 全画面表示ボタンのクリック
5. PDFエクスポートボタンのクリック
6. PNGエクスポートボタンのクリック

**成果物**:
- `src/lib/components/create_job/SlideNavigation.svelte` (150行)
- `src/lib/components/create_job/SlideNavigation.test.ts` (70行)

---

### Task 5.4: create_job ページ統合 (1時間)

**実装内容**:
- `src/routes/create_job/+page.svelte` にMarpViewer と SlideNavigation を統合
- ジョブ作成成功後、自動的にスライド表示
- タブで「チャット」「スライド」を切り替え

**統合設計**:
```svelte
<script lang="ts">
  import MarpViewer from '$lib/components/create_job/MarpViewer.svelte';
  import SlideNavigation from '$lib/components/create_job/SlideNavigation.svelte';

  let showSlides = false;
  let createdJobId: string | null = null;
  let currentSlide = 1;
  let totalSlides = 1;
  let viewerRef: any;

  async function handleCreateJob() {
    // ... (既存のジョブ作成処理)
    const jobResult = await chatSession.submitJob();

    if (jobResult && jobResult.job_id) {
      createdJobId = jobResult.job_id;
      showSlides = true; // スライドタブに自動切り替え
    }
  }

  function handlePrevSlide() {
    // iframe にメッセージ送信
    viewerRef?.postMessage({ type: 'prev-slide' }, '*');
  }

  function handleNextSlide() {
    viewerRef?.postMessage({ type: 'next-slide' }, '*');
  }

  function handleFullscreen() {
    const viewer = document.querySelector('.marp-viewer');
    viewer?.requestFullscreen();
  }

  async function handleExportPdf() {
    if (!createdJobId) return;
    const report = await getMarpReport(createdJobId, 'pdf');
    if (report.pdf_url) {
      window.open(report.pdf_url, '_blank');
    }
  }

  async function handleExportPng() {
    if (!createdJobId) return;
    const report = await getMarpReport(createdJobId, 'png');
    if (report.png_urls && report.png_urls.length > 0) {
      // 全スライドをZIPでダウンロード（または個別ダウンロード）
      report.png_urls.forEach((url, index) => {
        const link = document.createElement('a');
        link.href = url;
        link.download = `slide-${index + 1}.png`;
        link.click();
      });
    }
  }
</script>

<!-- タブ切り替え -->
<div class="tabs">
  <button
    class:active={!showSlides}
    on:click={() => showSlides = false}
  >
    💬 チャット
  </button>
  <button
    class:active={showSlides}
    on:click={() => showSlides = true}
    disabled={!createdJobId}
  >
    📊 スライド
  </button>
</div>

<!-- コンテンツ -->
{#if !showSlides}
  <!-- 既存のチャットUI -->
  <ChatContainer {messages} bind:containerRef={chatContainer} />
{:else if createdJobId}
  <!-- スライド表示 -->
  <MarpViewer
    jobId={createdJobId}
    bind:currentSlide={currentSlide}
    bind:totalSlides={totalSlides}
    bind:ref={viewerRef}
  />
  <SlideNavigation
    {currentSlide}
    {totalSlides}
    onPrev={handlePrevSlide}
    onNext={handleNextSlide}
    onFullscreen={handleFullscreen}
    onExportPdf={handleExportPdf}
    onExportPng={handleExportPng}
  />
{/if}
```

**UI/UX改善**:
- ジョブ作成成功時にスライドタブが自動的にハイライト
- スライド未作成時は「スライド」タブを無効化
- スライド読み込み中はスケルトンローダー表示

**成果物**:
- `src/routes/create_job/+page.svelte` (+80行修正)

---

## 📦 成果物

| ファイル | 行数 | 内容 |
|---------|------|------|
| **実装** | | |
| `marp-api.ts` | 150行 | expertAgent Marp Report API連携 |
| `MarpViewer.svelte` | 200行 | Marpスライド表示コンポーネント |
| `SlideNavigation.svelte` | 150行 | スライド操作UI |
| `create_job/+page.svelte` | +80行 | ページ統合 |
| **テスト** | | |
| `marp-api.test.ts` | 90行 | 6テスト |
| `MarpViewer.test.ts` | 80行 | 6テスト |
| `SlideNavigation.test.ts` | 70行 | 6テスト |

**合計**: 820行（実装: 580行、テスト: 240行）
**テスト**: 18テスト追加

---

## ✅ 成功条件

### 機能要件

- [ ] expertAgent Marp Report API連携が実装されている
- [ ] MarpViewer コンポーネントでスライドが表示される
- [ ] SlideNavigation コンポーネントで前後移動・全画面・エクスポートが機能する
- [ ] create_jobページにタブが追加され、チャット↔スライドの切り替えが可能
- [ ] ジョブ作成成功後、自動的にスライドタブに切り替わる

### 品質要件

- [ ] 18テスト追加、すべて合格（合計: 98 + 18 = 116テスト）
- [ ] TypeScript型チェック: エラー 0件
- [ ] ESLint: エラー 0件
- [ ] Build: 成功
- [ ] A11y: iframe title属性、ボタンaria-label設定済み

### パフォーマンス要件

- [ ] スライド読み込み時間: 2秒以内
- [ ] スライド切り替え: 即座（<100ms）
- [ ] PDFエクスポート: 5秒以内

---

## 🚨 リスクと対策

### リスク1: expertAgent Marp Report APIが未実装

**リスク**: `/v1/marp-report/{jobId}` APIがまだ実装されていない可能性

**対策**:
1. **Phase 5開始前に確認**: expertAgent APIのエンドポイント一覧を確認
2. **モックデータで先行開発**: API未実装でもフロントエンド実装を進める
3. **expertAgentチームと連携**: API仕様を確認し、実装スケジュールを調整

**モックデータ例**:
```typescript
// marp-api.test.tsで使用
const mockMarpReport: MarpReportResponse = {
  job_id: 'job-123',
  markdown: '# Job Overview\n\n## Task 1\n...',
  html: '<div class="marp">...</div>',
  pdf_url: null,
  png_urls: null,
  slide_count: 5
};
```

---

### リスク2: iframe セキュリティ制約

**リスク**: iframe の `sandbox` 属性により、JavaScript実行が制限される可能性

**対策**:
1. `sandbox="allow-scripts allow-same-origin"` を設定
2. Marp HTMLに外部スクリプトが含まれている場合、CSP（Content Security Policy）を調整
3. iframe内外の通信は `postMessage` のみを使用

---

### リスク3: 大規模ジョブのスライド生成遅延

**リスク**: タスク数が多いジョブでMarp生成に時間がかかる

**対策**:
1. **ローディング状態の明示**: プログレスバー表示
2. **バックグラウンド生成**: expertAgent側でジョブ作成時にスライドを事前生成
3. **キャッシュ**: 一度生成したスライドをキャッシュして再利用

---

## 🔄 Phase 5完了後の確認事項

### 動作確認

1. [ ] expertAgent APIとの連携が正常に動作する
2. [ ] ジョブ作成後、スライドが自動表示される
3. [ ] スライドの前後移動が正常に機能する
4. [ ] 全画面表示が正常に機能する
5. [ ] PDF/PNGエクスポートが正常に機能する
6. [ ] ダークモードでスライドが正しく表示される
7. [ ] レスポンシブデザイン（モバイル表示）が適切

### 品質チェック

```bash
# Type check
npm run type-check

# Linting
npm run lint

# Tests
npm test -- --run

# Build
npm run build
```

### ドキュメント更新

- [ ] `phase-5-progress.md` を作成
- [ ] `CHANGELOG.md` にPhase 5の変更を記録
- [ ] API連携部分のドキュメントを更新

---

## 📚 参考資料

- [Marp公式ドキュメント](https://marp.app/)
- [Marp Core API](https://github.com/marp-team/marp-core)
- [Fullscreen API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API)
- [postMessage API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage)

---

**Phase 5開始準備完了** ✅
