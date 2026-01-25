# ドキュメント体系の改善案

## 1. 現状分析

### 1.1 現在のドキュメント配置場所

| 場所 | 目的 | 問題点 |
|------|------|--------|
| `docs/` | プロジェクト全体のドキュメント | カテゴリが多すぎて分かりにくい（claude, design, spec, ops, arch, rule, guide, procedures, workflows, scripts） |
| `{project}/docs/` | プロジェクト固有ドキュメント | 一部プロジェクトにしか存在しない |
| `dev-reports/` | Issue開発中の作業ドキュメント | docs/への移行が不完全 |
| `workspace/` | 一時的な作業メモ | 整理されていない、古いファイルが残存 |
| `.claude/` | Claude Code設定 | 適切 |
| `README.md`（各所） | プロジェクト概要 | 内容がバラバラ |

### 1.2 主要な問題点

1. **カテゴリの重複・不明確**
   - `docs/design/` vs `docs/arch/` の違いが不明確
   - `docs/rule/` vs `docs/guide/` vs `docs/procedures/` の違いが不明確

2. **ドキュメントの陳腐化**
   - 実装と乖離したドキュメントが存在
   - 更新責任者が不明確

3. **発見性の低さ**
   - 中央インデックスがない
   - 関連ドキュメントへのリンクが不足

4. **開発ドキュメントと完成ドキュメントの境界が曖昧**
   - dev-reports/ から docs/ への移行プロセスが形骸化

---

## 2. あるべき姿

### 2.1 ドキュメント階層構造

```
MySwiftAgent/
├── README.md                           # プロジェクト概要（エントリーポイント）
├── CLAUDE.md                           # Claude Code向けガイドライン
│
├── docs/                               # 【完成ドキュメント】恒久的なドキュメント
│   ├── INDEX.md                        # 📚 ドキュメントインデックス【新規】
│   │
│   ├── getting-started/                # 🚀 はじめに【統合】
│   │   ├── quick-start.md              # クイックスタート
│   │   ├── installation.md             # インストール手順
│   │   └── first-workflow.md           # 初めてのワークフロー作成
│   │
│   ├── architecture/                   # 🏗️ アーキテクチャ【統合: arch + design】
│   │   ├── overview.md                 # システム全体構成
│   │   ├── service-dependencies.md     # サービス間依存関係
│   │   ├── data-flow.md                # データフロー
│   │   └── tech-stack.md               # 技術スタック
│   │
│   ├── development/                    # 💻 開発ガイド【統合: claude + guide + rule】
│   │   ├── workflow.md                 # 開発フロー
│   │   ├── branch-strategy.md          # ブランチ戦略
│   │   ├── quality-standards.md        # 品質基準
│   │   ├── testing-guide.md            # テストガイド
│   │   ├── coding-conventions.md       # コーディング規約
│   │   └── slash-commands.md           # スラッシュコマンド
│   │
│   ├── specifications/                 # 📋 仕様書【統合: spec】
│   │   ├── job-generation.md           # ジョブ生成仕様
│   │   ├── workflow-execution.md       # ワークフロー実行仕様
│   │   ├── taskflow-format.md          # TaskFlow形式仕様
│   │   └── api/                        # API仕様
│   │       └── taskflow-generator.yaml
│   │
│   ├── operations/                     # 🔧 運用ガイド【統合: ops + procedures】
│   │   ├── local-development.md        # ローカル開発環境
│   │   ├── deployment.md               # デプロイ手順
│   │   ├── troubleshooting.md          # トラブルシューティング
│   │   └── new-project-setup.md        # 新規プロジェクト追加
│   │
│   └── reference/                      # 📖 リファレンス【新規】
│       ├── environment-variables.md    # 環境変数一覧
│       ├── configuration.md            # 設定ファイル
│       └── glossary.md                 # 用語集
│
├── {project}/                          # 各マイクロサービス
│   ├── README.md                       # プロジェクト概要（標準化）
│   └── docs/                           # プロジェクト固有ドキュメント
│       ├── API_REFERENCE.md            # API仕様（必須）
│       └── {feature}.md                # 機能固有ドキュメント
│
├── dev-reports/                        # 【作業ドキュメント】Issue開発中のみ
│   └── feature/issue/{number}/
│       ├── design-policy.md
│       ├── work-plan.md
│       ├── acceptance-plan.md
│       └── progress-report.md
│
└── .archive/                           # 【アーカイブ】不要になったドキュメント【新規】
    └── workspace/                      # workspaceの移行先
```

### 2.2 カテゴリ定義

| カテゴリ | 目的 | 対象読者 | 更新頻度 |
|---------|------|---------|---------|
| **getting-started** | 新規参加者向けの導入 | 新規開発者 | 低 |
| **architecture** | システム設計の理解 | アーキテクト、シニア開発者 | 中 |
| **development** | 日常の開発ガイド | 全開発者 | 高 |
| **specifications** | 機能仕様の詳細 | 開発者、QA | 中 |
| **operations** | 運用・デプロイ手順 | DevOps、開発者 | 中 |
| **reference** | 設定・環境変数の参照 | 全員 | 高 |

### 2.3 プロジェクト別README.md標準化

各プロジェクトのREADME.mdは以下の構造を持つこと：

```markdown
# {プロジェクト名}

## 概要
{1-2文でプロジェクトの目的を説明}

## 役割
{システム内での役割を説明}

## 技術スタック
- 言語: {言語}
- フレームワーク: {フレームワーク}
- データベース: {あれば}

## クイックスタート
```bash
# 起動コマンド
```

## API概要
→ 詳細は [API_REFERENCE.md](./docs/API_REFERENCE.md) を参照

## 設定
| 環境変数 | 説明 | デフォルト |
|---------|------|-----------|

## 関連ドキュメント
- [全体アーキテクチャ](../docs/architecture/overview.md)
- [サービス間依存関係](../docs/architecture/service-dependencies.md)
```

---

## 3. ドキュメントライフサイクル

### 3.1 ドキュメントの状態遷移

```
[Issue作成]
    ↓
[dev-reports/ に作業ドキュメント作成]
    ├── design-policy.md
    ├── work-plan.md
    ├── acceptance-plan.md
    └── progress-report.md
    ↓
[Issue完了]
    ↓
[/doc-register でdocs/に統合] ← 【必須化】
    ↓
[dev-reports/ をアーカイブまたは削除]
```

### 3.2 ドキュメント更新トリガー

| トリガー | 更新対象 | 責任者 |
|---------|---------|--------|
| 新機能追加 | specifications/, {project}/docs/ | 実装者 |
| API変更 | {project}/docs/API_REFERENCE.md | 実装者 |
| 設定変更 | reference/environment-variables.md | 実装者 |
| アーキテクチャ変更 | architecture/ | 実装者 + レビュアー |
| バグ修正（重大） | operations/troubleshooting.md | 実装者 |

### 3.3 ドキュメント鮮度管理

```yaml
# 各ドキュメントのフロントマター
---
title: ドキュメントタイトル
last_updated: 2026-01-25
last_reviewed: 2026-01-25
owner: @username
status: current | needs_review | deprecated
related_issues: [#123, #456]
---
```

**ステータス定義**:
- `current`: 最新で正確
- `needs_review`: 実装と乖離している可能性あり（3ヶ月以上更新なし）
- `deprecated`: 非推奨、削除予定

---

## 4. 移行計画

### Phase 1: 構造整理

| タスク | 対象 | 優先度 |
|--------|------|--------|
| docs/INDEX.md 作成 | 新規 | 高 |
| docs/claude/ → docs/development/ 移行 | 移行 | 高 |
| docs/arch/ + docs/design/ → docs/architecture/ 統合 | 統合 | 高 |
| docs/rule/ + docs/guide/ → docs/development/ 統合 | 統合 | 中 |
| docs/procedures/ → docs/operations/ 移行 | 移行 | 中 |

### Phase 2: コンテンツ整理

| タスク | 対象 | 優先度 |
|--------|------|--------|
| 重複ドキュメントの統合 | 全体 | 高 |
| 陳腐化ドキュメントの更新または削除 | 全体 | 中 |
| 各プロジェクトREADME.md標準化 | 各プロジェクト | 中 |
| docs/getting-started/ 作成 | 新規 | 中 |

### Phase 3: プロセス整備

| タスク | 対象 | 優先度 |
|--------|------|--------|
| /doc-register の必須化（pm-auto-devに組み込み） | pm-auto-dev | 高 |
| ドキュメントレビューの仕組み導入 | 新規 | 中 |
| workspace/ の .archive/ への移行 | 移行 | 低 |

---

## 5. 具体的な統合マッピング

### 現在 → あるべき姿

| 現在のパス | 移行先 | 備考 |
|-----------|--------|------|
| `docs/claude/01-development-workflow.md` | `docs/development/workflow.md` | |
| `docs/claude/02-slash-commands.md` | `docs/development/slash-commands.md` | |
| `docs/claude/03-branch-strategy.md` | `docs/development/branch-strategy.md` | |
| `docs/claude/04-quality-standards.md` | `docs/development/quality-standards.md` | |
| `docs/claude/05-worktree-guide.md` | `docs/development/worktree-guide.md` | |
| `docs/claude/06-ci-cd-prevention.md` | `docs/development/ci-cd-guide.md` | |
| `docs/claude/07-documentation-rules.md` | `docs/development/documentation-rules.md` | |
| `docs/claude/08-issue-split.md` | `docs/development/issue-split.md` | |
| `docs/arch/service-dependencies.md` | `docs/architecture/service-dependencies.md` | |
| `docs/design/architecture-overview.md` | `docs/architecture/overview.md` | |
| `docs/design/environment-variables.md` | `docs/reference/environment-variables.md` | |
| `docs/design/myvault-integration.md` | `docs/architecture/myvault-integration.md` | |
| `docs/design/langfuse-integration.md` | `docs/architecture/langfuse-integration.md` | |
| `docs/spec/job-generation-workflow.md` | `docs/specifications/job-generation.md` | |
| `docs/spec/acceptance-testing.md` | `docs/development/testing-guide.md` | 統合 |
| `docs/ops/local-development.md` | `docs/operations/local-development.md` | |
| `docs/ops/deployment-guide.md` | `docs/operations/deployment.md` | |
| `docs/procedures/NEW_PROJECT_SETUP.md` | `docs/operations/new-project-setup.md` | |
| `docs/guide/DEVELOPMENT_GUIDE.md` | `docs/getting-started/` に分割 | |
| `workspace/*` | `.archive/workspace/` | アーカイブ |

---

## 6. docs/INDEX.md の構成案

```markdown
# 📚 MySwiftAgent ドキュメントインデックス

## 🚀 はじめに
- [クイックスタート](./getting-started/quick-start.md)
- [インストール](./getting-started/installation.md)
- [初めてのワークフロー](./getting-started/first-workflow.md)

## 🏗️ アーキテクチャ
- [システム概要](./architecture/overview.md)
- [サービス間依存関係](./architecture/service-dependencies.md)
- [技術スタック](./architecture/tech-stack.md)

## 💻 開発ガイド
- [開発フロー](./development/workflow.md)
- [ブランチ戦略](./development/branch-strategy.md)
- [品質基準](./development/quality-standards.md)
- [テストガイド](./development/testing-guide.md)
- [スラッシュコマンド](./development/slash-commands.md)

## 📋 仕様書
- [ジョブ生成](./specifications/job-generation.md)
- [ワークフロー実行](./specifications/workflow-execution.md)
- [TaskFlow形式](./specifications/taskflow-format.md)

## 🔧 運用ガイド
- [ローカル開発環境](./operations/local-development.md)
- [デプロイ](./operations/deployment.md)
- [トラブルシューティング](./operations/troubleshooting.md)

## 📖 リファレンス
- [環境変数一覧](./reference/environment-variables.md)
- [設定ファイル](./reference/configuration.md)
- [用語集](./reference/glossary.md)

## 📦 プロジェクト別ドキュメント
| プロジェクト | 概要 | API仕様 |
|-------------|------|---------|
| [expertAgent](../expertAgent/README.md) | AIエージェント基盤 | [API](../expertAgent/docs/API_REFERENCE.md) |
| [mySwiftAgentCore](../mySwiftAgentCore/README.md) | ワークフロー実行エンジン | - |
| [graphAiServer](../graphAiServer/README.md) | GraphAI OSS連携 | - |
| [jobqueue](../jobqueue/README.md) | ジョブキュー管理 | - |
| [myVault](../myVault/README.md) | シークレット管理 | - |
| [myAgentDesk](../myAgentDesk/README.md) | Web UI | - |
```

---

## 7. Issue #400 への追加受入条件

### AC-5: ドキュメント体系の整備
- [ ] `docs/INDEX.md` が作成されている
- [ ] `docs/` のカテゴリが整理されている（getting-started, architecture, development, specifications, operations, reference）
- [ ] 各プロジェクトのREADME.mdが標準化されている
- [ ] 移行マッピングが文書化されている

### AC-6: ドキュメント鮮度管理
- [ ] ドキュメントのフロントマター形式が定義されている
- [ ] ステータス（current, needs_review, deprecated）が定義されている
- [ ] 更新トリガーが明確化されている

### AC-7: /doc-register の必須化
- [ ] pm-auto-devのPhase 6で/doc-registerが必須実行されている
- [ ] dev-reports/ から docs/ への移行フローが確立されている

---

**作成日**: 2026-01-25
