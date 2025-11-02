# 設計方針 v2: myAgentDesk ドメインエキスパート向けUI完全実装

**作成日**: 2025-11-02
**Issue**: #120
**ブランチ**: feature/issue/120
**担当**: Claude Code

---

## 📋 Issue概要と目的

**タイトル**: myAgentDeskにドメインエキスパート向けUIを作成する

**ビジネス目的**:
ドメインエキスパートが自然言語でジョブを定義・実行・改善できる高度なUI機能を追加し、プログラミング知識がなくても自律的にAIエージェントを活用できる環境を提供する。

### ユーザーペルソナ
- **プログラミング知識**: 限定的
- **関心事**: What（やりたいこと）> How（実現方法）
- **学習スタイル**: 視覚的な情報理解を好む（スライド、図表）
- **作業スタイル**: 試行錯誤しながら要件を明確化

---

## 🎯 解決すべき課題

| No. | 課題 | 現状の問題 | 目指す姿 |
|-----|------|-----------|---------|
| 1 | **要件定義の困難さ** | 初期段階では自分のやりたいことが明確でない | チャット対話で段階的に要件を明確化 |
| 2 | **技術的な障壁** | プログラミングやワークフロー定義の知識が必要 | 自然言語のみでジョブ作成完了 |
| 3 | **全体把握の難しさ** | テキストベースの情報では理解しにくい | スライド形式でビジュアルに把握 |
| 4 | **継続的改善の手間** | 手動でワークフローを改善する必要がある | 人間が評価するだけでAIが自動改善 |
| 5 | **版数管理の必要性** | 変更履歴が追跡できない | Git風のバージョン管理で履歴追跡 |

---

## 📝 実装要件（requirements.md完全準拠）

### ✅ 完了済み（Phase 1-3）

#### 要件1: 自然言語によるジョブ要件定義 (80%完了)
- ✅ チャット形式の対話UI（ChatContainer, MessageInput）
- ✅ 要求状態の可視化（RequirementCard）
- ✅ expertAgent API連携（streamChatRequirementDefinition）
- ⏳ 対話履歴管理（conversationStore実装済み）
- ⏳ 要件のドラフト保存（会話単位で保存済み）

#### 要件2: What重視のジョブ作成 (70%完了)
- ✅ チャットUIでのWhat入力
- ✅ expertAgent Job Generator API連携（createJob）
- ✅ ジョブ作成結果表示
- ⏳ How（実現方法）の自動決定（expertAgent側実装済み）
- ⏳ 決定理由の表示（未実装）

### 🚧 未実装（Phase 4-8で実装）

#### 要件3: ジョブ実行方法の指定 (優先度: 中)
**Phase 4で実装**

- [ ] **実行方法選択UI**
  - オプション1: API公開のみ（On-demand実行）
  - オプション2: スケジュール実行（定期実行）
  - オプション3: 両方

- [ ] **スケジュール設定UI**
  - Cron式入力 or ビジュアル選択
  - プレビュー機能（次回実行日時表示）
  - タイムゾーン設定

- [ ] **myScheduler連携**
  - スケジュール登録API呼び出し
  - 実行履歴の確認
  - スケジュール変更/停止機能

**期待される成果物**:
- `ScheduleSelector.svelte` (実行方法選択)
- `CronEditor.svelte` (スケジュール設定)
- `schedule-api.ts` (myScheduler API連携)

---

#### 要件4: スライド形式のジョブ概要表示 (優先度: 高)
**Phase 5で実装** 🔥

- [ ] **Marpスライド表示**
  - expertAgent Marp Report API（既存: `/v1/marp-report`）連携
  - ブラウザ内でスライド表示（Marp Viewer統合）
  - スライド操作: 前後移動、全画面表示、PDF/PNG出力

- [ ] **スライド内容**
  - タイトル: ジョブ名、作成日時
  - サマリー: ジョブの目的、タスク数、ステータス
  - タスク詳細: 各タスクの説明、入出力、API使用状況
  - 要求緩和提案: infeasible_tasksがある場合の代替案

- [ ] **インタラクティブ機能**
  - スライドから直接編集モードへ遷移
  - 特定タスクの詳細ページへリンク
  - 実行結果との比較表示

**期待される成果物**:
- `MarpViewer.svelte` (Marpスライド表示)
- `marp-api.ts` (expertAgent Marp Report API連携)
- `SlideNavigation.svelte` (スライド操作UI)

**技術選定**:
- **Phase 5**: Marp CLI + iframe埋め込み（最速実装）
- **Phase 6以降**: marp-core ライブラリ直接統合（カスタマイズ性向上）

---

#### 要件5: 人間評価による自動改善 (優先度: 中)
**Phase 6で実装**

- [ ] **評価UI**
  - 実行結果ごとに評価ボタン（👍 Good / 👎 Bad）
  - コメント入力（任意）
  - 評価理由の選択肢（速度、精度、出力形式など）

- [ ] **評価データの蓄積**
  - 評価履歴の保存（ジョブID、タスクID、評価、コメント、タイムスタンプ）
  - 統計情報（Good率、改善回数、平均評価）

- [ ] **AIによる自動改善**
  - 評価データをexpertAgentにフィードバック
  - 低評価タスクの自動再生成
  - 改善提案の通知（Slack、メール）

**期待される成果物**:
- `EvaluationButton.svelte` (評価UI)
- `evaluation-api.ts` (評価データ保存API)
- `ImprovementPanel.svelte` (改善提案表示)

**データ構造設計**:
```typescript
interface Evaluation {
  id: string;
  job_id: string;
  task_id: string | null; // null = ジョブ全体の評価
  rating: 'good' | 'bad';
  reason: 'speed' | 'accuracy' | 'output_format' | 'other';
  comment: string | null;
  timestamp: string;
}
```

---

#### 要件6: 人間によるワークフロー編集 (優先度: 中)
**Phase 7で実装**

- [ ] **ワークフロー可視化**
  - GraphAIワークフローのビジュアル表示
  - ノード間の依存関係を矢印で表示
  - ノードタイプごとの色分け

- [ ] **ワークフロー編集UI**
  - ノードの追加/削除
  - ノード設定の編集（プロンプト、モデル、パラメータ）
  - エッジの追加/削除（依存関係変更）

- [ ] **バリデーション**
  - 循環依存の検出
  - 必須パラメータのチェック
  - GraphAIスキーマ準拠の検証

- [ ] **保存とデプロイ**
  - 編集内容の保存
  - graphAiServerへのデプロイ
  - ロールバック機能

**期待される成果物**:
- `WorkflowEditor.svelte` (ノードエディタ)
- `GraphViewer.svelte` (ワークフロー可視化)
- `workflow-api.ts` (graphAiServer連携)

**技術選定**:
- **Phase 7**: Svelte Flow（Svelte専用、学習コスト低）
- **将来**: React Flow（高機能、必要に応じて移行）

---

#### 要件7: 版数管理 (優先度: 低)
**Phase 8で実装**

- [ ] **バージョン履歴表示**
  - タスク定義の変更履歴
  - ワークフロー定義の変更履歴
  - 変更差分の表示（diff）

- [ ] **バージョン管理機能**
  - コミット（変更の保存）
  - タグ付け（v1.0.0形式）
  - ブランチ（実験的変更の並行管理）

- [ ] **ロールバック機能**
  - 過去バージョンへの復元
  - 特定バージョンのデプロイ
  - バージョン間の比較

**期待される成果物**:
- `VersionHistory.svelte` (バージョン履歴UI)
- `DiffViewer.svelte` (差分表示)
- `version-api.ts` (版数管理API)

**技術選定**:
- **Phase 8**: DB-based版数管理（jobqueue拡張）
- **将来**: Git-like実装（libgit2.js等）

---

## 🏗️ システムアーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                  myAgentDesk (Frontend - SvelteKit)         │
├─────────────────────────────────────────────────────────────┤
│  Phase 1-3 (完了)                                             │
│  ├── ChatContainer.svelte         # チャット表示             │
│  ├── MessageInput.svelte          # メッセージ入力           │
│  ├── RequirementCard.svelte       # 要求状態表示             │
│  ├── chat-api.ts                  # expertAgent API連携      │
│  └── job-api.ts                   # ジョブ作成API連携        │
│                                                               │
│  Phase 4 (要件3: ジョブ実行方法の指定)                         │
│  ├── ScheduleSelector.svelte      # 実行方法選択UI           │
│  ├── CronEditor.svelte            # スケジュール設定UI       │
│  └── schedule-api.ts              # myScheduler API連携      │
│                                                               │
│  Phase 5 (要件4: スライド形式のジョブ概要表示)                 │
│  ├── MarpViewer.svelte            # Marpスライド表示         │
│  ├── SlideNavigation.svelte       # スライド操作UI           │
│  └── marp-api.ts                  # Marp Report API連携      │
│                                                               │
│  Phase 6 (要件5: 人間評価による自動改善)                       │
│  ├── EvaluationButton.svelte      # 評価UI                  │
│  ├── ImprovementPanel.svelte      # 改善提案表示             │
│  └── evaluation-api.ts            # 評価データAPI連携        │
│                                                               │
│  Phase 7 (要件6: ワークフロー編集)                            │
│  ├── WorkflowEditor.svelte        # ノードエディタ           │
│  ├── GraphViewer.svelte           # ワークフロー可視化       │
│  └── workflow-api.ts              # graphAiServer連携        │
│                                                               │
│  Phase 8 (要件7: 版数管理)                                    │
│  ├── VersionHistory.svelte        # バージョン履歴UI         │
│  ├── DiffViewer.svelte            # 差分表示                │
│  └── version-api.ts               # 版数管理API連携          │
└─────────────────────────────────────────────────────────────┘
                            ↓ API連携
┌─────────────────────────────────────────────────────────────┐
│                  バックエンドサービス群                        │
├─────────────────────────────────────────────────────────────┤
│  expertAgent (FastAPI)                                      │
│  ├── Job Generator API        (既存)                        │
│  ├── Marp Report API          (既存: /v1/marp-report)       │
│  ├── Chat Requirement API     (既存: /chat/requirement-definition) │
│  └── Improvement Loop API     (新規: Phase 6で実装)          │
│                                                               │
│  graphAiServer (FastAPI)                                    │
│  ├── Workflow Executor        (既存)                        │
│  └── Workflow Management API  (拡張: Phase 7で実装)          │
│                                                               │
│  myScheduler (FastAPI)                                      │
│  └── Schedule Management API  (既存: Phase 4で連携)          │
│                                                               │
│  jobqueue (FastAPI)                                         │
│  ├── Job/Task Management      (既存)                        │
│  └── Version Management API   (拡張: Phase 8で実装)          │
└─────────────────────────────────────────────────────────────┘
```

### レイヤー分離

**UI層（Components）**:
- Atomic Design 簡易版を採用
- Atoms: Button, Input, Card等（既存）
- Molecules: ChatInput, RequirementCard等（Phase 1-3実装済み）
- Organisms: MarpViewer, WorkflowEditor等（Phase 4-8で実装）

**サービス層（Services）**:
- APIクライアント（chat-api.ts, job-api.ts等）
- エラーハンドリングの集約
- ビジネスロジックの分離

**状態管理層（Stores）**:
- conversationStore（会話履歴）
- chatSession（チャットセッション状態）
- 将来: evaluationStore（評価データ）, versionStore（バージョン管理）

---

## 🛠️ 技術選定

### フロントエンド技術スタック

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **フレームワーク** | SvelteKit | 既存プロジェクト、リアクティブ性、軽量 |
| **型システム** | TypeScript | 型安全性、開発効率向上 |
| **スタイリング** | Tailwind CSS | 既存プロジェクトと統一 |
| **テストフレームワーク** | Vitest + Testing Library | 既存プロジェクト、高速 |
| **E2Eテスト** | Playwright | SvelteKit公式推奨 |
| **Marpスライド表示** | Marp CLI + iframe（Phase 5） → marp-core（将来） | 段階的実装 |
| **ワークフローエディタ** | Svelte Flow（Phase 7） → React Flow（将来） | 学習コスト最小化 |
| **差分表示** | diff ライブラリ + カスタムUI | シンプル、軽量 |

### バックエンドAPI連携

| サービス | エンドポイント | Phase | 実装状況 |
|---------|-------------|-------|---------|
| **expertAgent** | `/chat/requirement-definition` | Phase 1-3 | ✅ 実装済み |
| **expertAgent** | `/chat/create-job` | Phase 1-3 | ✅ 実装済み |
| **expertAgent** | `/v1/marp-report` | Phase 5 | ⏳ 連携実装予定 |
| **expertAgent** | `/v1/improvement-loop` | Phase 6 | 🚧 新規実装必要 |
| **graphAiServer** | `/workflow/get` | Phase 7 | ⏳ 既存利用 |
| **graphAiServer** | `/workflow/update` | Phase 7 | 🚧 拡張必要 |
| **myScheduler** | `/schedule/create` | Phase 4 | ⏳ 既存利用 |
| **jobqueue** | `/version/history` | Phase 8 | 🚧 新規実装必要 |

---

## 📊 Phase構成と工数見積もり

### Phase 1-3: 基盤リファクタリング（完了）
**期間**: 2025-10-31（完了）
**工数**: 2時間

- [x] TypeScript型エラー解消、A11y警告解消
- [x] サービス層抽出（chat-api.ts, job-api.ts）
- [x] コンポーネント分割（RequirementCard, ChatContainer, MessageInput）
- [x] テスト追加（37テスト、カバレッジ高）

**成果**: 489行 → 282行（-42%）、保守性向上

---

### Phase 4: ジョブ実行方法の指定（要件3）
**期間**: 0.5日（4時間）
**優先度**: 中

#### 実装内容
1. **実行方法選択UI** (1.5時間)
   - ScheduleSelector.svelte: ラジオボタン（API公開のみ / スケジュール / 両方）
   - 選択状態の管理（Svelte store）

2. **スケジュール設定UI** (1.5時間)
   - CronEditor.svelte: Cron式入力 + ビジュアル選択
   - プレビュー機能（次回実行日時表示）
   - バリデーション（Cron式の妥当性チェック）

3. **myScheduler連携** (0.5時間)
   - schedule-api.ts: `/schedule/create` API呼び出し
   - エラーハンドリング

4. **テスト** (0.5時間)
   - ScheduleSelector.test.ts（5テスト）
   - CronEditor.test.ts（8テスト）
   - schedule-api.test.ts（6テスト）

**成果物**:
- `ScheduleSelector.svelte` (80行)
- `CronEditor.svelte` (150行)
- `schedule-api.ts` (100行)
- 19テスト追加

---

### Phase 5: スライド形式のジョブ概要表示（要件4）🔥
**期間**: 1日（8時間）
**優先度**: 高

#### 実装内容
1. **expertAgent Marp Report API連携** (2時間)
   - marp-api.ts: `/v1/marp-report` API呼び出し
   - レスポンス処理（Markdown → HTML変換）
   - エラーハンドリング

2. **Marpスライド表示** (3時間)
   - MarpViewer.svelte: iframe or marp-core統合
   - スライドレンダリング
   - レスポンシブ対応

3. **スライド操作UI** (2時間)
   - SlideNavigation.svelte: 前後移動ボタン、ページ番号表示
   - 全画面モード
   - PDF/PNG出力ボタン（expertAgent APIへの依頼）

4. **テスト** (1時間)
   - MarpViewer.test.ts（6テスト）
   - SlideNavigation.test.ts（5テスト）
   - marp-api.test.ts（6テスト）

**成果物**:
- `MarpViewer.svelte` (200行)
- `SlideNavigation.svelte` (100行)
- `marp-api.ts` (150行)
- 17テスト追加

**技術的課題**:
- Marp CLI vs marp-core選定
- スライド状態管理（現在のページ、全画面モード）

---

### Phase 6: 人間評価による自動改善（要件5）
**期間**: 1日（8時間）
**優先度**: 中

#### 実装内容
1. **評価UI** (2時間)
   - EvaluationButton.svelte: 👍👎ボタン、コメント入力
   - 評価理由の選択肢（ドロップダウン）
   - 送信後のフィードバック（Thank you メッセージ）

2. **評価データ蓄積** (2時間)
   - evaluation-api.ts: POST `/evaluation/submit`
   - 評価履歴の取得: GET `/evaluation/history`
   - 統計情報の取得: GET `/evaluation/stats`

3. **改善提案表示** (2.5時間)
   - ImprovementPanel.svelte: expertAgentからの改善提案を表示
   - 改善提案の承認/却下UI
   - expertAgent Improvement Loop API連携

4. **expertAgent改善ロジック実装** (1時間)
   - expertAgent側: `/v1/improvement-loop` エンドポイント新規作成
   - 評価データ分析ロジック
   - タスク再生成ロジック

5. **テスト** (0.5時間)
   - EvaluationButton.test.ts（6テスト）
   - ImprovementPanel.test.ts（5テスト）
   - evaluation-api.test.ts（6テスト）

**成果物**:
- `EvaluationButton.svelte` (120行)
- `ImprovementPanel.svelte` (150行)
- `evaluation-api.ts` (150行)
- expertAgent: `improvement_loop.py` (新規)
- 17テスト追加

**データ構造設計**:
```typescript
interface Evaluation {
  id: string;
  job_id: string;
  task_id: string | null;
  rating: 'good' | 'bad';
  reason: 'speed' | 'accuracy' | 'output_format' | 'other';
  comment: string | null;
  timestamp: string;
}

interface ImprovementProposal {
  id: string;
  job_id: string;
  task_id: string;
  proposal: string; // 改善提案の説明
  new_workflow: string; // 新しいワークフローYAML
  estimated_improvement: string; // 期待される改善効果
}
```

---

### Phase 7: 人間によるワークフロー編集（要件6）
**期間**: 1.5日（12時間）
**優先度**: 中

#### 実装内容
1. **ワークフロー取得・解析** (2時間)
   - workflow-api.ts: GET `/workflow/get/{job_id}`
   - GraphAI YAML → JSON変換
   - ノード・エッジ構造の解析

2. **ワークフロー可視化** (4時間)
   - GraphViewer.svelte: Svelte Flowを使用したノード表示
   - ノードタイプごとの色分け
   - エッジ（依存関係）の矢印表示
   - ズーム・パン操作

3. **ワークフロー編集UI** (4時間)
   - WorkflowEditor.svelte: ノード追加/削除/編集
   - ノード設定パネル（プロンプト、モデル、パラメータ）
   - エッジの追加/削除
   - ドラッグ&ドロップ

4. **バリデーションと保存** (1.5時間)
   - 循環依存の検出
   - 必須パラメータのチェック
   - JSON → GraphAI YAML変換
   - graphAiServer: POST `/workflow/update`

5. **テスト** (0.5時間)
   - GraphViewer.test.ts（5テスト）
   - WorkflowEditor.test.ts（8テスト）
   - workflow-api.test.ts（6テスト）

**成果物**:
- `GraphViewer.svelte` (250行)
- `WorkflowEditor.svelte` (350行)
- `workflow-api.ts` (200行)
- graphAiServer: `/workflow/update` エンドポイント拡張
- 19テスト追加

**技術的課題**:
- Svelte Flowの学習コスト
- GraphAI YAML ⇔ JSON変換の正確性
- 大規模ワークフロー（100ノード以上）のパフォーマンス

---

### Phase 8: 版数管理（要件7）
**期間**: 1日（8時間）
**優先度**: 低

#### 実装内容
1. **バージョン履歴取得** (2時間)
   - version-api.ts: GET `/version/history/{job_id}`
   - バージョンメタデータ（コミットメッセージ、タグ、作成日時）
   - 差分データの取得

2. **バージョン履歴表示** (2.5時間)
   - VersionHistory.svelte: GitHubスタイルの履歴リスト
   - タイムライン表示
   - バージョン詳細表示（モーダル）

3. **差分表示** (2時間)
   - DiffViewer.svelte: タスク定義/ワークフローの差分表示
   - diffライブラリ統合
   - 色分け表示（追加: 緑、削除: 赤、変更: 黄）

4. **ロールバック機能** (1時間)
   - バージョン選択 → ロールバック実行
   - jobqueue: POST `/version/rollback`
   - 確認ダイアログ

5. **テスト** (0.5時間)
   - VersionHistory.test.ts（6テスト）
   - DiffViewer.test.ts（5テスト）
   - version-api.test.ts（6テスト）

**成果物**:
- `VersionHistory.svelte` (200行)
- `DiffViewer.svelte` (150行)
- `version-api.ts` (150行)
- jobqueue: `/version/*` エンドポイント新規作成
- 17テスト追加

**データ構造設計**:
```typescript
interface Version {
  id: string;
  job_id: string;
  version_number: string; // v1.0.0形式
  commit_message: string;
  author: string;
  timestamp: string;
  tags: string[];
  is_current: boolean;
}

interface VersionDiff {
  job_id: string;
  from_version: string;
  to_version: string;
  task_diffs: TaskDiff[];
  workflow_diffs: WorkflowDiff[];
}
```

---

### Phase 9: E2Eテストと品質担保
**期間**: 0.5日（4時間）
**優先度**: 高

#### 実装内容
1. **E2Eテストシナリオ** (2.5時間)
   - シナリオ1: チャット → ジョブ作成 → スライド表示（Happy Path）
   - シナリオ2: スケジュール設定 → myScheduler連携確認
   - シナリオ3: 評価 → 改善提案受信
   - シナリオ4: ワークフロー編集 → 保存 → デプロイ
   - シナリオ5: バージョン履歴 → ロールバック

2. **カバレッジ確認** (0.5時間)
   - `npm run test -- --coverage`
   - 目標: 80%以上
   - 未カバー箇所の特定と追加テスト

3. **品質チェック** (0.5時間)
   - TypeScript型チェック: エラー 0件
   - ESLint: エラー 0件
   - Prettier: すべて適用済み
   - ビルド: 成功

4. **ドキュメント整備** (0.5時間)
   - README.md 更新（Phase 4-8の機能追加）
   - phase-9-progress.md 作成

**成果物**:
- `tests/e2e/full-flow.spec.ts` (5シナリオ、約250行)
- カバレッジレポート（80%以上）
- phase-9-progress.md

---

### Phase 10: PR作成とドキュメント整備
**期間**: 0.5日（4時間）
**優先度**: 高

#### 実装内容
1. **PR作成** (1時間)
   - PR タイトル: `feat(myAgentDesk): implement domain expert UI (Issue #120)`
   - PR 説明文: 要件1-7の実装内容、スクリーンショット
   - レビュアー指定
   - ラベル: `feature`, `myAgentDesk`

2. **CI/CD確認** (1時間)
   - GitHub Actions 実行確認
   - すべてのチェックが合格
   - エラー発生時の修正

3. **final-report.md作成** (1.5時間)
   - Phase 1-10の総括
   - 実装した機能一覧
   - 品質指標
   - 今後の改善提案

4. **レビュー対応** (0.5時間)
   - レビューコメントへの対応
   - 追加テスト・修正

**成果物**:
- GitHub Pull Request
- final-report.md
- スクリーンショット（10枚程度）

---

## 📊 全体工数見積もり

| Phase | 内容 | 工数 | 状態 |
|-------|------|------|------|
| Phase 1-3 | 基盤リファクタリング | 2時間 | ✅ 完了 |
| Phase 4 | ジョブ実行方法の指定 | 4時間 | 🔜 次 |
| Phase 5 | スライド形式のジョブ概要表示 | 8時間 | 🔜 |
| Phase 6 | 人間評価による自動改善 | 8時間 | 🔜 |
| Phase 7 | ワークフロー編集 | 12時間 | 🔜 |
| Phase 8 | 版数管理 | 8時間 | 🔜 |
| Phase 9 | E2Eテストと品質担保 | 4時間 | 🔜 |
| Phase 10 | PR作成とドキュメント整備 | 4時間 | 🔜 |

**合計**: 50時間（約6-7日）

---

## ✅ 制約条件チェック

### コード品質原則
- [x] **SOLID原則**: コンポーネント単一責任、依存性逆転（Phase 1-3で実証済み）
- [x] **KISS原則**: 段階的実装（Marp CLI → marp-core、Svelte Flow → React Flow）
- [x] **YAGNI原則**: 認証機能は将来実装、今は実装しない
- [x] **DRY原則**: 既存コンポーネント（Button, Card）を再利用

### アーキテクチャガイドライン
- [x] `architecture-overview.md`: 準拠（TypeScript フロントエンド）
- [x] **レイヤー分離**: UI層 / サービス層 / 状態管理層（Phase 1-3で確立）

### 設定管理ルール
- [x] **環境変数**: API_BASE（expertAgent, graphAiServer, myScheduler）
- [ ] **myVault**: API認証キー管理（将来実装）

### 品質担保方針
- [x] TypeScript 型チェック: エラー 0件（Phase 1-3達成）
- [x] ESLint: エラー 0件（Phase 1-3達成）
- [x] Prettier: すべて適用済み（Phase 1-3達成）
- [x] テストカバレッジ: 80%以上目標（Phase 9で最終確認）

### CI/CD準拠
- [x] PRラベル: `feature` ラベル付与予定
- [x] コミットメッセージ: Conventional Commits 規約準拠
- [x] pre-push チェック: TypeScript プロジェクト用チェック

### 参照ドキュメント遵守
- [x] CLAUDE.md: 開発ルール遵守
- [x] requirements.md: 7要件を完全実装（Issue #120完全準拠）
- [ ] GRAPHAI_WORKFLOW_GENERATION_RULES.md: Phase 7で参照必須

### 違反・要検討項目
なし

---

## 📝 設計上の決定事項

### 1. Marp Viewer実装方式（Phase 5）
**決定**: Marp CLI + iframe埋め込み（Phase 5） → marp-core直接統合（将来）

**理由**:
- Phase 5では最速実装を優先（Marp CLI + iframe = 3時間で実装可能）
- marp-core直接統合は高カスタマイズ性だが学習コストが高い（+5時間）
- 段階的実装により早期フィードバックを得られる

### 2. ワークフローエディタ実装方式（Phase 7）
**決定**: Svelte Flow（Phase 7） → React Flow（将来移行検討）

**理由**:
- Svelte Flowは学習コスト低、SvelteKitとの親和性高
- React Flowは高機能だがSvelte wrapperが必要
- Phase 7で基本機能を実装、必要に応じてPhase 11以降でReact Flowへ移行

### 3. 評価データ保存先（Phase 6）
**決定**: jobqueue拡張（新規テーブル `evaluations`）

**理由**:
- 既存のjobqueue DBにテーブル追加が最速（新規サービス立ち上げ不要）
- job_id, task_idとの関連が明確
- 将来的に独立サービス化も可能（マイグレーション容易）

### 4. 版数管理実装方式（Phase 8）
**決定**: DB-based版数管理（jobqueue拡張）

**理由**:
- Git-likeは実装コスト高（libgit2.js統合、コンフリクト解決UI等）
- DB-basedはシンプル、クエリ容易、ロールバック高速
- 将来的にGit連携も可能（export to Git機能追加）

### 5. バックエンドAPI新規実装の優先順位
**決定**: expertAgent拡張 > graphAiServer拡張 > jobqueue拡張

**理由**:
- expertAgent: Marp Report API（既存）、Improvement Loop API（Phase 6新規）
- graphAiServer: Workflow Update API（Phase 7拡張）
- jobqueue: Version Management API（Phase 8新規）

---

## 🚨 リスク管理

### リスク1: Marp Viewer統合の複雑さ（Phase 5）
**発生確率**: 中
**影響度**: 高

**対策**:
- iframe方式で最速実装（リスク回避）
- expertAgent Marp Report APIの事前動作確認（Phase 4で実施）
- エラーハンドリングの充実（スライド生成失敗時のフォールバック）

### リスク2: Svelte Flow学習コスト（Phase 7）
**発生確率**: 中
**影響度**: 中

**対策**:
- Phase 7開始前にSvelte Flow公式ドキュメント精読（1時間）
- 最小限の機能実装（ノード表示 → 編集 → 保存の順に段階的）
- React Flowへの移行オプション確保（技術的負債回避）

### リスク3: expertAgent改善ロジックの未定義（Phase 6）
**発生確率**: 高
**影響度**: 高

**対策**:
- Phase 6開始前にexpertAgent開発者とのミーティング（要件確認）
- 改善ロジックのプロトタイプ実装（簡易版: 低評価タスクを再生成）
- フィードバックループの設計レビュー

### リスク4: 工数超過（全Phase）
**発生確率**: 中
**影響度**: 中

**対策**:
- 各Phase完了時に進捗レビュー
- Phase 6-8は優先度中・低のため、時間不足時はPhase 11以降へ延期可能
- Phase 4-5（優先度高）を最優先で完了

---

## 📚 次のステップ

1. ✅ **設計方針レビュー**（本ドキュメント）← 今ここ
2. 📝 **作業計画立案**（work-plan.md更新）
3. 🚀 **Phase 4実装開始**（ジョブ実行方法の指定）

---

**レビューをお願いします。修正・追加要望があればお知らせください。**
