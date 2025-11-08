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

## 🤖 開発フローとClaude Code Skillsマッピング

各開発フェーズで利用可能なClaude Code Skills（スキルを使用しないフェーズも含む）：

### 📍 セッション区分
- **フェーズ 1-5**: メインセッション（develop ブランチ） - Feature計画
- **フェーズ 6-14**: worktree セッション（issue ブランチ） - Issue開発
- **フェーズ 15-17**: メインセッション（develop ブランチ） - **Featureクローズ処理**

| フェーズ | 利用スキル | モデル | コマンド | セッション | 用途 |
|---------|-----------|--------|----------|-----------|------|
| **1. Feature定義** | 要件定義 | Opus | `/requirements` | メイン | ユーザーストーリー、受入条件作成 |
| **2. UIモックアップ** 🆕 | UIデザイン | Sonnet | `/ui-mockup` | メイン | UI必要時のみ、4パターン生成 |
| **3. 仕様ドラフト** | 設計方針 | Opus | `/design` | メイン | アーキテクチャ設計、技術選定 |
| **4. レビュー・承認** | アーキテクチャレビュー | Opus | `/review-arch` | メイン | 設計レビュー、リスク評価 |
| **5. Issue分割** | Issue分割 | Opus | `/issue-split` | メイン | FeatureをIssueに分割 |
| **6. 作業計画** | 作業計画 | Opus | `/plan` | メイン | Issue単位の詳細作業計画 |
| **7. ブランチ作成** | Worktree自動セットアップ | Sonnet | `/worktree-setup` | **→ worktree** | Issue番号から自動でworktree環境構築 |
| **8. 開発（TDD実装）** | TDD実装 | Sonnet | `/tdd-impl` | worktree | テスト駆動開発による実装 |
| **9. 品質保証** | 受入テスト | Opus | `/acceptance-test` | worktree | 受入テスト実行・分析 |
| **10. リファクタリング** | リファクタリング | Sonnet | `/refactor` | worktree | コード品質改善（必要時） |
| **11. 進捗管理** | 進捗報告 | Sonnet | `/progress` | worktree | 進捗サマリ、ブロッカー報告 |
| **12. PR作成** | - | Sonnet | - | worktree | Pull Request作成（手動作業） |
| **13. コードレビュー** | アーキテクチャレビュー | Opus | `/review-arch` | worktree | コードレビュー支援（必要時） |
| **14. CI/CD実行** | - | Sonnet | - | worktree | 自動テスト・ビルド（自動処理） |
| **15. マージ** | - | Sonnet | - | worktree | developブランチへマージ（手動作業） |
| 🏁 **Featureクローズ処理** ||||| |
| **16. フィーチャーフラグ設定** | - | Sonnet | - | **← メイン** | フラグ設定（手動作業） |
| **17. Wiki文書化** | - | Sonnet | - | メイン推奨 | 仕様確定・文書化（両セッション可） |
| **18. リリース準備** | - | Sonnet | - | メイン | リリースノート作成等（手動作業） |

### スキル実行フローの例

```mermaid
graph TD
    Start[新機能要求] --> Req["要件定義<br/>(/requirements - Opus)"]
    Req --> UICheck{UI開発<br/>必要?}
    UICheck -->|Yes| Mockup["UIモックアップ<br/>(/ui-mockup - Sonnet)<br/>4パターン生成"]
    UICheck -->|No| Design["設計方針<br/>(/design - Opus)"]
    Mockup --> Design
    Design --> Review1["設計レビュー<br/>(/review-arch - Opus)"]
    Review1 -->|承認| IssueSplit["Issue分割<br/>(/issue-split - Opus)"]
    Review1 -->|要修正| Design
    IssueSplit --> Plan["作業計画<br/>(/plan - Opus)<br/>Issue単位"]

    Plan --> SessionSwitch["🔄 セッション切替<br/>worktree作成"]
    SessionSwitch --> Branch["Worktree自動セットアップ<br/>(/worktree-setup - Sonnet)"]

    Branch --> Dev["開発（TDD実装）<br/>(/tdd-impl - Sonnet)"]
    Dev --> QA["品質保証<br/>(/acceptance-test - Opus)"]
    QA --> QAResult{テスト<br/>合格?}
    QAResult -->|No| Dev
    QAResult -->|Yes| Refactor{"リファクタ<br/>必要?"}
    Refactor -->|Yes| RefactorExec["リファクタリング<br/>(/refactor - Sonnet)"]
    Refactor -->|No| Progress["進捗報告<br/>(/progress - Sonnet)"]
    RefactorExec --> Progress
    Progress --> Done{完了?}
    Done -->|No| Dev
    Done -->|Yes| PR["PR作成<br/>(手動 - Sonnet)"]
    PR --> Review2["コードレビュー<br/>(/review-arch - Opus)"]
    Review2 --> CI["CI/CD<br/>(自動 - Sonnet)"]
    CI --> Merge["マージ<br/>(手動 - Sonnet)"]

    Merge --> SessionReturn["🔄 セッション戻し<br/>メインに戻る"]
    SessionReturn --> Flag["フラグ設定<br/>(手動 - Sonnet)"]
    Flag --> Wiki["Wiki文書化<br/>(手動 - Sonnet)"]
    Wiki --> End[リリース]

    style Req fill:#e3f2fd
    style UICheck fill:#ffccbc
    style Mockup fill:#c8e6c9
    style Design fill:#e3f2fd
    style Review1 fill:#e3f2fd
    style IssueSplit fill:#e3f2fd
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

## 📝 Issue管理

### Issue分割の原則

- **縦割り（Vertical Slice）**: UI + API等の機能単位で分割
- **横割り禁止**: フェーズ（要件定義→設計→実装）での分割は行わない
- **並列作業**: 依存関係を明確化し、並列実行可能な作業を識別

### Issue記載内容

```markdown
## 依存関係
- [ ] #123 先行Issueの完了が必要

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

### Feature完了時の必須タスク

1. Featureチケットのドラフトをレビュー
2. 最新決定を反映し清書
3. GitHub Wikiへ転記または新規作成
4. Wiki転記完了後にFeatureチケットをClose

---

[← CLAUDE.mdに戻る](../../CLAUDE.md) | [次: Claude Code Skills →](./02-claude-skills.md)