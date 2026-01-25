# 🚀 アジャイル開発ワークフロー

本チームは「**フィーチャー駆動開発**」と「**継続的インテグレーション（CI）**」を組み合わせたワークフローを採用します。詳細は[AGILE_WORKFLOW.md](../procedures/AGILE_WORKFLOW.md)を参照してください。

## 📋 開発フロー概要

```mermaid
graph LR
    A[Feature定義] --> B[仕様ドラフト<br/>AI活用]
    B --> C[レビュー・承認]
    C --> D[Issue分割]
    D --> E[開発<br/>Issue単位]
    E --> F[PR・CI]
    F --> G[フィーチャーフラグ]
    G --> H[Wiki文書化]

    style A fill:#e1f5e1
    style B fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#e3f2fd
    style E fill:#f3e5f5
    style F fill:#fce4ec
    style G fill:#fff9c4
    style H fill:#e0f2f1
```

## 🤖 開発フローとスラッシュコマンドマッピング

各開発フェーズで利用可能なClaude Code Skills（スキルを使用しないフェーズも含む）：

### 📍 セッション区分
- **フェーズ 1-6**: メインセッション（develop ブランチ） - Feature計画
- **フェーズ 7-15**: worktree セッション（issue ブランチ） - Issue開発
- **フェーズ 16-19**: メインセッション（develop ブランチ） - **Featureクローズ処理**

| フェーズ | 利用スキル | モデル | コマンド | セッション | 用途 |
|---------|-----------|--------|----------|-----------|------|
| **1. Feature定義** | 要件定義 | Opus | `/requirements` | メイン | ユーザーストーリー、受入条件作成 |
| **2. UIモックアップ** 🆕 | UIデザイン | Opus | `/ui-mockup` | メイン | UI必要時のみ、4パターン生成 |
| **3. 仕様ドラフト** | 設計方針 | Opus | `/design-policy` | メイン | アーキテクチャ設計、技術選定 |
| **4. レビュー・承認** | アーキテクチャレビュー | Opus | `/architecture-review` | メイン | 設計レビュー、リスク評価 |
| **5. Issue分割** | Issue分割 | Opus | `/issue-split` | メイン | FeatureをIssueに分割（計画書作成） |
| **6. Issue登録** 🆕 | Issue一括作成 | Opus | `/issue-create` | メイン | GitHub Issueに一括登録、親子関連付け |
| **7. 作業計画** | 作業計画 | Opus | `/work-plan` | メイン | Issue単位の詳細作業計画 |
| **8. ブランチ作成** | Worktree自動セットアップ | Opus | `/worktree-setup` | **→ worktree** | Issue番号から自動でworktree環境構築 |
| **9. 開発（TDD実装）** | TDD実装 | Opus | `/tdd-impl` または `/pm-auto-dev` | worktree | テスト駆動開発による実装 |
| **10. 品質保証** | 受入テスト | Opus | `/acceptance-test` または `/pm-auto-dev` | worktree | 受入テスト実行・分析 |
| **11. リファクタリング** | リファクタリング | Opus | `/refactoring` または `/pm-auto-dev` | worktree | コード品質改善（必要時） |
| **12. 進捗管理** | 進捗報告 | Opus | `/progress-report` または `/pm-auto-dev` | worktree | 進捗サマリ、ブロッカー報告 |
| **13. PR作成** | - | Opus | - | worktree | Pull Request作成（手動作業） |
| **14. コードレビュー** | アーキテクチャレビュー | Opus | `/architecture-review` | worktree | コードレビュー支援（必要時） |
| **15. CI/CD実行** | - | Opus | - | worktree | 自動テスト・ビルド（自動処理） |
| **16. マージ** | - | Opus | - | worktree | developブランチへマージ（手動作業） |
| 🏁 **Featureクローズ処理** ||||| |
| **17. フィーチャーフラグ設定** | - | Opus | - | **← メイン** | フラグ設定（手動作業） |
| **18. Wiki文書化** | - | Opus | - | メイン推奨 | 仕様確定・文書化（両セッション可） |
| **19. リリース準備** | - | Opus | - | メイン | リリースノート作成等（手動作業） |

---

### 🤖 フェーズ9-12の実行方式

フェーズ9（TDD実装）〜フェーズ12（進捗報告）には、**2つの実行方式**があります：

#### 📋 実行パターン比較

| 項目 | パターンA: 個別実行 | パターンB: 一括委託 |
|------|-------------------|-------------------|
| **実行方法** | 各スラッシュコマンドを手動実行<br/>`/tdd-impl` → `/acceptance-test` → `/refactoring` → `/progress-report` | PM Auto-Devに一括委託<br/>`/pm-auto-dev [Issue番号]` |
| **制御方法** | ユーザーがフェーズごとに判断・実行 | PM Auto-Devが自動でフェーズを進行 |
| **エラー時** | ユーザーが対処を判断 | 最大3回まで自動リトライ |
| **適用場面** | 複雑なIssue、実験的な実装 | 標準的なIssue、定型的な実装 |

#### ✅ パターンA: 個別実行（手動ステップ実行）

**実行コマンド**:
```bash
/tdd-impl [Issue番号]
# 結果確認後、手動で次へ
/acceptance-test [Issue番号]
# 結果確認後、手動で次へ
/refactoring [Issue番号]
# 結果確認後、手動で次へ
/progress-report [Issue番号]
```

**メリット**:
- ✅ **きめ細かい制御**: 各フェーズの結果を確認してから次に進める
- ✅ **柔軟な対処**: 問題発生時に即座にユーザーが介入・対処可能
- ✅ **学習効果**: 各フェーズの動作を観察しながら進められる
- ✅ **複雑な要件対応**: 標準プロセスから外れる実装に適している

**デメリット**:
- ❌ **手動作業**: 各フェーズで手動でコマンド実行が必要
- ❌ **待機時間**: フェーズ間でユーザーが結果確認・判断する時間が必要
- ❌ **一貫性**: ユーザーの判断により実行品質にばらつきが生じる可能性

**推奨ケース**:
- 新しい技術スタックの導入
- アーキテクチャに影響する大きな変更
- 実験的な実装やプロトタイプ開発
- 複雑な依存関係のあるIssue

#### 🚀 パターンB: 一括委託（PM Auto-Dev自動実行）

**実行コマンド**:
```bash
/pm-auto-dev [Issue番号]
```

**メリット**:
- ✅ **完全自動化**: Issue情報取得 → TDD → 受入テスト → リファクタリング → 進捗報告を自動実行
- ✅ **リトライロジック**: 受入テスト失敗時、最大3回まで自動でTDD実装に戻る
- ✅ **時間効率**: ユーザーの待機時間なしで完結
- ✅ **品質保証**: 統一されたプロセスで一貫した品質を担保
- ✅ **ファイルベースI/O**: 各フェーズの結果がJSONファイルとして保存され、デバッグ可能

**デメリット**:
- ❌ **制御の喪失**: フェーズ間でユーザーが介入できない
- ❌ **ブラックボックス化**: 内部でサブエージェントが動作するため、途中経過が見えにくい
- ❌ **最大リトライ制限**: 3回の自動リトライで解決しない場合はエスカレーション（手動対応）
- ❌ **標準外対応**: カスタムな実装フローには対応困難

**推奨ケース**:
- 標準的なCRUD実装
- 既存パターンに従った機能追加
- 定型的なバグ修正
- 明確な仕様が確定しているIssue

#### 🔄 実行フローの違い

**パターンA（個別実行）**:
```mermaid
graph LR
    A["TDD実装<br/>/tdd-impl"] --> U1{ユーザー<br/>判断}
    U1 -->|OK| B["受入テスト<br/>/acceptance-test"]
    U1 -->|NG| A
    B --> U2{ユーザー<br/>判断}
    U2 -->|Pass| C["リファクタリング<br/>/refactoring"]
    U2 -->|Fail| A
    C --> U3{ユーザー<br/>判断}
    U3 -->|OK| D["進捗報告<br/>/progress-report"]

    style A fill:#fff3e0
    style B fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#fff3e0
    style U1 fill:#fce4ec
    style U2 fill:#fce4ec
    style U3 fill:#fce4ec
```

**パターンB（一括委託）**:
```mermaid
graph LR
    Start["PM Auto-Dev起動<br/>/pm-auto-dev"] --> Phase1[Issue情報収集]
    Phase1 --> Phase2[TDD実装<br/>サブエージェント]
    Phase2 --> Check1{結果?}
    Check1 -->|success| Phase3[受入テスト<br/>サブエージェント]
    Check1 -->|failed| Retry{リトライ<br/>回数}
    Retry -->|3回未満| Phase2
    Retry -->|3回以上| Escalate[エスカレーション]
    Phase3 --> Check2{結果?}
    Check2 -->|passed| Phase4[リファクタリング<br/>サブエージェント]
    Check2 -->|failed| Retry
    Phase4 --> Phase5[進捗報告<br/>サブエージェント]
    Phase5 --> End[完了]

    style Start fill:#c8e6c9
    style Phase2 fill:#fff3e0
    style Phase3 fill:#e3f2fd
    style Phase4 fill:#fff3e0
    style Phase5 fill:#fff3e0
    style Check1 fill:#fce4ec
    style Check2 fill:#fce4ec
    style Retry fill:#ffccbc
    style Escalate fill:#ffccbc
```

#### 💡 実装の内部構造

PM Auto-Devは、各フェーズで専門のサブエージェントを呼び出します：

| フェーズ | サブエージェント | 入力ファイル | 出力ファイル |
|---------|----------------|------------|------------|
| Phase 2 | `tdd-impl-agent` | `tdd-context.json` | `tdd-result.json` |
| Phase 3 | `acceptance-test-agent` | `acceptance-context.json` | `acceptance-result.json` |
| Phase 4 | `refactoring-agent` | `refactor-context.json` | `refactor-result.json` |
| Phase 5 | `progress-report-agent` | `progress-context.json` | `progress-report.md` |

**ファイル配置例**:
```
dev-reports/feature/issue/166/pm-auto-dev/iteration-1/
├── tdd-context.json          ← PM Auto-Devが作成（入力）
├── tdd-result.json           ← tdd-impl-agentが作成（出力）
├── acceptance-context.json   ← PM Auto-Devが作成
├── acceptance-result.json    ← acceptance-test-agentが作成
├── refactor-context.json     ← PM Auto-Devが作成
├── refactor-result.json      ← refactoring-agentが作成
├── progress-context.json     ← PM Auto-Devが作成
└── progress-report.md        ← progress-report-agentが作成
```

#### 🎯 どちらを選ぶべきか？

**パターンAを選ぶべき状況**:
- 💡 新技術の検証・学習を兼ねた開発
- 🔬 実験的な実装や概念実証（PoC）
- 🏗️ アーキテクチャに影響する大規模変更
- 🎨 UI/UXの試行錯誤が必要な機能
- 🐛 原因不明のバグ修正（試行錯誤が必要）

**パターンBを選ぶべき状況**:
- 🏃 時間効率を重視したい場合
- 📋 要件が明確で標準パターンに従う実装
- 🔄 定型的なCRUD操作の追加
- 🐞 原因が明確なバグ修正
- ✅ 既存コードベースのパターンを踏襲する機能追加

**関連ドキュメント**:
- [PM Auto-Dev移行完了レポート](../../workspace/pm-auto-dev-design/10-pm-auto-dev-migration-complete.md)
- [サブエージェント実装仕様](../../workspace/pm-auto-dev-design/06-official-subagent-implementation.md)

---

### スキル実行フローの例

```mermaid
graph TD
    Start[新機能要求] --> Req["要件定義<br/>(/requirements - Opus)"]
    Req --> UICheck{UI開発<br/>必要?}
    UICheck -->|Yes| Mockup["UIモックアップ<br/>(/ui-mockup - Opus)<br/>4パターン生成"]
    UICheck -->|No| Design["設計方針<br/>(/design-policy - Opus)"]
    Mockup --> Design
    Design --> Review1["設計レビュー<br/>(/architecture-review - Opus)"]
    Review1 -->|承認| IssueSplit["Issue分割<br/>(/issue-split - Opus)<br/>計画書作成"]
    Review1 -->|要修正| Design
    IssueSplit --> IssueCreate["Issue登録<br/>(/issue-create - Opus)<br/>GitHub一括作成"]
    IssueCreate --> Plan["作業計画<br/>(/work-plan - Opus)<br/>Issue単位"]

    Plan --> SessionSwitch["🔄 セッション切替<br/>worktree作成"]
    SessionSwitch --> Branch["Worktree自動セットアップ<br/>(/worktree-setup - Opus)"]

    Branch --> Dev["開発（TDD実装）<br/>(/tdd-impl - Opus)"]
    Dev --> QA["品質保証<br/>(/acceptance-test - Opus)"]
    QA --> QAResult{テスト<br/>合格?}
    QAResult -->|No| Dev
    QAResult -->|Yes| Refactor{"リファクタ<br/>必要?"}
    Refactor -->|Yes| RefactorExec["リファクタリング<br/>(/refactoring - Opus)"]
    Refactor -->|No| Progress["進捗報告<br/>(/progress-report - Opus)"]
    RefactorExec --> Progress
    Progress --> Done{完了?}
    Done -->|No| Dev
    Done -->|Yes| PR["PR作成<br/>(手動 - Opus)"]
    PR --> Review2["コードレビュー<br/>(/architecture-review - Opus)"]
    Review2 --> CI["CI/CD<br/>(自動 - Opus)"]
    CI --> Merge["マージ<br/>(手動 - Opus)"]

    Merge --> SessionReturn["🔄 セッション戻し<br/>メインに戻る"]
    SessionReturn --> Flag["フラグ設定<br/>(手動 - Opus)"]
    Flag --> Wiki["Wiki文書化<br/>(手動 - Opus)"]
    Wiki --> End[リリース]

    style Req fill:#e3f2fd
    style UICheck fill:#ffccbc
    style Mockup fill:#c8e6c9
    style Design fill:#e3f2fd
    style Review1 fill:#e3f2fd
    style IssueSplit fill:#e3f2fd
    style IssueCreate fill:#c8e6c9
    style Plan fill:#e3f2fd
    style RefactorExec fill:#fff3e0
    style Progress fill:#fff3e0
    style Review2 fill:#e3f2fd
    style SessionSwitch fill:#ffccbc
    style SessionReturn fill:#ffccbc
    style Branch fill:#e8f5e9
    style Dev fill:#fff3e0
    style QA fill:#e3f2fd
    style QAResult fill:#fce4ec
    style PR fill:#e8f5e9
    style CI fill:#fce4ec
    style Merge fill:#e8f5e9
    style Flag fill:#fff9c4
    style Wiki fill:#e0f2f1
```

## 🎯 Feature（フィーチャー）管理

### Feature チケットの要件

Featureは「**ユーザーに価値を届ける単位**」として、以下を必須記載：

1. **ユーザー価値（WHAT & WHY）**
   ```
   As a [ユーザー種別]
   I want to [達成したいこと]
   So that [期待される価値]
   ```

2. **仕様・設計ドラフト（HOW）**
   - AI（LLM）を活用して要件定義と設計方針のドラフトを作成
   - レビューを経て変更されることを前提とする

### レビュープロセス（リファイメント）

- シニアエンジニア/アーキテクトによるレビュー
- 技術的最適性と既存アーキテクチャとの整合性確認
- 承認後「**Ready**」状態へ遷移

## 🎨 UIモックアップ作成プロセス

### UIモックアップスキル (`/ui-mockup`)

**目的**: Feature定義後、UI開発が必要な場合に4つのデザインパターンを生成

**適用条件**:
- myAgentDeskプロジェクトでUI追加/改修が必要な場合
- Feature定義で画面要素が含まれる場合
- ユーザーインタラクションが発生する機能

**プロセス**:
1. **UI要件抽出**: Feature定義からUI要件を分析
2. **パターン生成**: 4つの異なるデザインアプローチを作成
3. **プレビュー環境構築**: SvelteKitで実際に操作可能な環境を提供
4. **比較資料作成**: 各パターンの特徴と推奨理由をまとめ

**4つのデザインパターンの観点**:
- **パターンA**: シンプル・ミニマル（基本機能のみ）
- **パターンB**: 標準・バランス型（推奨機能含む）
- **パターンC**: リッチ・高機能（全機能搭載）
- **パターンD**: 革新的・実験的（新しいUXパターン）

**出力物**:
```
myAgentDesk/src/routes/(preview)/mockups/feature-[番号]/
├── pattern-a/+page.svelte  # パターンA
├── pattern-b/+page.svelte  # パターンB
├── pattern-c/+page.svelte  # パターンC
├── pattern-d/+page.svelte  # パターンD
├── +layout.svelte          # 共通レイアウト
├── comparison/+page.svelte # 比較ページ
└── data.json              # モックデータ
```

**レビュープロセス**:
1. プレビュー環境で4パターンを実際に操作
2. 比較ページで並べて確認
3. 選定後、選択したパターンを本実装の基盤とする

## 🎯 新スキルによる品質向上プロセス

### TDD実装スキル (`/tdd-impl`)

**目的**: テスト駆動開発により品質を作り込みながら実装

**プロセス**:
1. **Red Phase**: 失敗するテストを先に作成
2. **Green Phase**: テストを通る最小限のコードを実装
3. **Refactor Phase**: コードを整理・最適化
4. **Coverage Check**: 単体テストカバレッジ90%以上を確認

**出力**:
- 実装コード
- 単体テストコード
- カバレッジレポート

### 受入テストスキル (`/acceptance-test`)

**目的**: Issue要件の自動検証と品質保証

**プロセス**:
1. **テストケース生成**: Issueの受入条件から自動生成
2. **E2Eテスト実行**: PlaywrightによるGUIテスト
3. **結果分析**: テスト結果の詳細レポート生成
4. **フィードバック**: 不合格時は具体的な修正点を提示

**出力**:
- テスト実行結果
- スクリーンショット/動画（失敗時）
- 修正推奨事項

### フィードバックループ

```mermaid
graph LR
    TDD[TDD実装] --> AT[受入テスト]
    AT --> Pass{合格?}
    Pass -->|Yes| Next[次工程へ]
    Pass -->|No| FB[フィードバック]
    FB --> TDD

    style TDD fill:#fff3e0
    style AT fill:#e3f2fd
    style Pass fill:#fce4ec
    style FB fill:#ffccbc
```

**差し戻し条件**:
- 受入テスト不合格
- カバレッジ基準未達
- パフォーマンス基準未達

**最大イテレーション**: 3回（超過時はエスカレーション）

## 🧪 Issue種別ごとのテストフロー

### Issue種別判定

Issueの内容に応じて、適用するテストレベルが異なります：

```mermaid
graph TD
    Start[Issueの変更内容] --> Q1{ユーザーに見える<br/>変更か？}
    Q1 -->|Yes| Q2{UI/UXの<br/>変更か？}
    Q1 -->|No| LabelCheck{ラベルを<br/>確認}

    Q2 -->|Yes| L4[L4: PO受入テスト必須]
    Q2 -->|No| L3[L3: 開発者受入テスト]

    LabelCheck -->|docs-only| Skip[受入テストスキップ]
    LabelCheck -->|internal| Skip
    LabelCheck -->|test-only| Skip
    LabelCheck -->|ci-only| Skip
    LabelCheck -->|その他| L3

    style L4 fill:#fce4ec
    style L3 fill:#e3f2fd
    style Skip fill:#c8e6c9
```

### スキップ条件ラベル

| ラベル | 説明 | 受入テスト |
|-------|------|-----------|
| `docs-only` | ドキュメントのみの変更 | スキップ可 |
| `internal` | 内部リファクタリング | スキップ可 |
| `test-only` | テストコードのみの変更 | スキップ可 |
| `ci-only` | CI/CD設定のみの変更 | スキップ可 |
| （上記以外） | 機能変更、バグ修正など | 必須 |

> **注意**: スキップ可能であっても、影響範囲が不明確な場合はL3テストを推奨

### 通常Issue と 重要Issue

**通常Issue**（L3テストで完了）:
- バックエンドAPIの内部ロジック変更
- パフォーマンス改善
- エラーハンドリング追加
- ログ出力の改善

**重要Issue**（L4テスト必須）:
- UI/UX変更（ボタン追加、レイアウト変更）
- 新機能の追加
- ユーザーフローの変更
- エラーメッセージの変更
- 課金・認証に関わる変更

## 📝 Issue管理

### Issue分割の原則

- **縦割り（Vertical Slice）**: UI + API等の機能単位で分割
- **横割り禁止**: フェーズ（要件定義→設計→実装）での分割は行わない
- **並列作業**: 依存関係を明確化し、並列実行可能な作業を識別
- **受入基準の2層構造** 🆕: `/pm-auto-dev`が検証できる基準と、手動検証が必要な基準を明確に分離

**詳細**: [Issue分割ガイド](./08-issue-split.md)を参照

### Issue記載内容

```markdown
## 依存関係
- [ ] #123 先行Issueの完了が必要

## 受入基準 (Acceptance Criteria)

### 🤖 自動検証可能な基準（pm-auto-devが実施）
- [ ] 単体テストカバレッジ 90%以上
- [ ] APIエンドポイントが実装される
- [ ] バリデーションエラーが適切に返される

### 👤 手動検証が必要な基準（ユーザーが実施）
- [ ] 画面のレイアウトが仕様通り
- [ ] 実際のデータで動作確認

## 作業計画
- [ ] 実装タスク
- [ ] テストタスク
- [ ] ドキュメント更新タスク
```

## 🌿 ブランチ・PR戦略

### ブランチルール

- **作成元**: 常に最新の`develop`ブランチから作成
- **単位**: **Issue単位**でブランチ作成（Feature単位は禁止）
- **命名**: `issue/[Issue番号]-[内容]` (例: `issue/123-add-profile-ui`)

### PR戦略

- **作成タイミング**: Issue完了後即座に作成
- **ターゲット**: 常に`develop`ブランチ
- **方針**: 小さく頻繁に（Small & Frequent）
- **マージ条件**:
  - CIテスト全パス
  - 1名以上のレビュー承認

## 🎛️ フィーチャーフラグ管理

### 基本原則

- `develop`ブランチは常にデプロイ可能状態を維持
- 未完成機能はフィーチャーフラグでデフォルトOFF制御
- Issue単位の高速マージを実現

### アーキテクチャ変更の導入

- ラッパーやエントリーポイントにフラグを仕込む
- 機能本体のコードを先行マージ（動作しない状態で）
- 巨大な変更は小さく分割して段階的に導入

### クリーンアップ

- 機能安定後、フラグ削除用のクリーンアップIssueを作成
- 不要なフラグを定期的に削除

## 📚 ドキュメント（ナレッジ）管理

### ハイブリッド・アプローチ

| 種別 | 配置場所 | 内容 | 用途 |
|------|---------|------|------|
| **一時的情報** | GitHub Issue | ドラフト、議論 | 開発中の速度優先 |
| **永続的情報** | GitHub Wiki | 確定仕様、設計図 | 未来の資産化 |

### Wiki運用ルール

- リポジトリ: `.wiki.git` (別管理)
- 編集方法: ローカルclone + VS Code（Web UI非推奨）
- 構成: `_Sidebar.md`でナビゲーション整備

### Feature完了時のPO最終受入テスト

全Issueがdevelopにマージされた後、Feature全体としてのPO受入テストを実施します：

```mermaid
graph TD
    subgraph "Issue開発（worktreeセッション）"
        I1[Issue #1] --> PR1[PR #1]
        I2[Issue #2] --> PR2[PR #2]
        I3[Issue #3] --> PR3[PR #3]
    end

    PR1 --> Develop[develop<br/>ブランチ]
    PR2 --> Develop
    PR3 --> Develop

    Develop --> POTest[PO最終受入テスト<br/>Feature全体]

    POTest --> Pass{合格?}
    Pass -->|Yes| Wiki[Wiki文書化]
    Pass -->|No| Hotfix[Hotfix Issue作成]
    Hotfix --> I4[修正Issue]
    I4 --> PR4[修正PR]
    PR4 --> Develop

    Wiki --> Close[Feature Close]

    style POTest fill:#fce4ec
    style Wiki fill:#e0f2f1
    style Close fill:#c8e6c9
```

**PO最終受入テストの確認項目**:
- [ ] 全Issue機能が統合されて動作する
- [ ] ユーザージャーニー全体を通したテスト
- [ ] 実際のデータでの動作確認
- [ ] 他機能への影響がないこと

### Feature完了時の必須タスク

1. Featureチケットのドラフトをレビュー
2. 最新決定を反映し清書
3. GitHub Wikiへ転記または新規作成
4. Wiki転記完了後にFeatureチケットをClose

---

[← CLAUDE.mdに戻る](../../CLAUDE.md) | [次: スラッシュコマンド →](./02-slash-commands.md) | [Issue分割ガイド →](./08-issue-split.md)