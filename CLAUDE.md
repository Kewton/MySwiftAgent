# CLAUDE.md

このファイルは、このリポジトリでコードを扱う際のClaude Code (claude.ai/code) への指針を提供します。

# MySwiftAgent

🚀 **MySwiftAgent** は、手軽で小回りの効く **パーソナルAIエージェント／LLMワークフロー** です。
複雑な設定を避けつつ、日常タスクや開発支援をすばやく実行する「自分だけのAIエージェント」を目指しています。

## ✨ 特徴

- ⚡ **Swift**：軽快に動作し、小回りの効く応答
- 🧩 **Extensible**：モジュール的に機能を追加可能
- 🎯 **Personalized**：ユーザーの目的に合わせたカスタマイズ
- 🔄 **Workflow-oriented**：LLMを軸にした柔軟なワークフロー設計

---

## 🚀 クイックスタート

### 📋 必須制約条件

開発時は以下の原則を必ず遵守すること：

#### コード品質原則
- **SOLID原則** - 単一責任、開放/閉鎖、リスコフ置換、インターフェース分離、依存性逆転
- **KISS** - Keep It Simple, Stupid
- **YAGNI** - You Aren't Gonna Need It
- **DRY** - Don't Repeat Yourself

#### 品質基準
- 単体テストカバレッジ: **90%以上**
- 結合テストカバレッジ: **50%以上**
- 静的解析: **Ruff/MyPyエラーゼロ**
- プッシュ前: `./scripts/pre-push-check-all.sh` 実行

### テスト構造

テストは3層構造で、実行環境が異なります：

| テスト種別 | 場所 | 実行環境 | カバレッジ目標 |
|-----------|------|---------|--------------|
| **単体テスト** | `{project}/tests/unit/` | CI (GitHub Actions) | 90%以上 |
| **結合テスト** | `tests/integration/` | CI (GitHub Actions) | 50%以上 |
| **受入テスト** | `tests/acceptance/` | ローカルのみ | - |

#### 受入テスト実行方法

受入テストはAPIキーや実サービス接続が必要なため、**ローカル環境でのみ実行**します：

```bash
# Platform層テスト（myVault, jobqueue等）
make acceptance-test-platform

# Agent層テスト（expertAgent, graphAiServer）
make acceptance-test-agent

# Frontend層テスト（myAgentDesk - Playwright）
make acceptance-test-frontend

# 全受入テスト実行
make acceptance-test-all
```

> **注意**: 受入テストの実行には環境変数（APIキー等）の設定が必要です。
> 詳細は [acceptance-testing.md](./docs/spec/acceptance-testing.md) を参照してください。

#### 開発ワークフロー
1. 対策案を提示する
2. ユーザーが指示した対策案に対し実行計画を提示する
3. ユーザーからの承認を持って実行計画を実行する

---

## 📚 詳細ドキュメントインデックス

| カテゴリ | ドキュメント | 内容 | 優先度 |
|---------|------------|------|--------|
| **開発フロー** | [01-development-workflow.md](./docs/claude/01-development-workflow.md) | アジャイル開発、Feature/Issue管理 | 🔴 高 |
| **スラッシュコマンド** | [02-slash-commands.md](./docs/claude/02-slash-commands.md) | 利用可能なスラッシュコマンド一覧と使用方法 | 🔴 高 |
| **ブランチ戦略** | [03-branch-strategy.md](./docs/claude/03-branch-strategy.md) | ブランチルール、PR戦略、リリース | 🔴 高 |
| **品質基準** | [04-quality-standards.md](./docs/claude/04-quality-standards.md) | テスト方針、静的解析、CI/CD | 🔴 高 |
| **並列開発** | [05-worktree-guide.md](./docs/claude/05-worktree-guide.md) | git worktree による並列開発 | 🟡 中 |
| **エラー防止** | [06-ci-cd-prevention.md](./docs/claude/06-ci-cd-prevention.md) | GitHub Actions エラー再発防止 | 🟡 中 |
| **文書管理** | [07-documentation-rules.md](./docs/claude/07-documentation-rules.md) | 作業ドキュメント管理ルール | 🟡 中 |
| **Issue分割** | [08-issue-split.md](./docs/claude/08-issue-split.md) | Issue分割詳細ガイド、受入基準の2層構造 | 🔴 高 |

---

## 🚨 重要な参照ドキュメント

開発を開始する前に、以下のドキュメントが該当するか確認してください：

| 状況 | 参照ドキュメント | 必須度 |
|------|----------------|--------|
| **新プロジェクトを追加する** | [NEW_PROJECT_SETUP.md](./docs/procedures/NEW_PROJECT_SETUP.md) | 🔴 必須 |
| **GraphAI ワークフローを開発する** | [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) | 🔴 必須 |
| **アーキテクチャを理解する** | [architecture-overview.md](./docs/design/architecture-overview.md) | 🟡 推奨 |
| **環境変数を設定する** | [environment-variables.md](./docs/design/environment-variables.md) | 🟡 推奨 |
| **myVault連携を実装する** | [myvault-integration.md](./docs/design/myvault-integration.md) | 🟡 推奨 |
| **デプロイメントを行う** | [deployment-guide.md](./docs/ops/deployment-guide.md) | 🟡 推奨 |

**重要**: 該当するドキュメントは作業開始前に必ず全文を読み、作業計画書 (`work-plan.md`) に参照を明記してください。

### 📚 プロジェクト別必須ドキュメント

各マイクロサービスの開発時に参照すべきドキュメント:

| プロジェクト | 必須ドキュメント | 説明 |
|-------------|----------------|------|
| **expertAgent** | [API_REFERENCE.md](./expertAgent/docs/API_REFERENCE.md) | 全API仕様 (Job Generator, Workflow Generator, Chat, Marp Report, Observability) |
| **expertAgent** | [job-generation-workflow.md](./docs/spec/job-generation-workflow.md) | Job Generator仕様とLangGraphエージェント設計 |
| **graphAiServer** | [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) | ワークフロー生成ルール・利用可能Agent一覧 |
| **myAgentDesk** | [README.md](./myAgentDesk/README.md) | SvelteKitアーキテクチャ・API統合・トラブルシューティング |
| **全サービス** | [service-dependencies.md](./docs/arch/service-dependencies.md) | サービス間依存関係・起動順序・通信フロー |
| **全サービス** | [deployment-guide.md](./docs/ops/deployment-guide.md) | Docker Compose/Kubernetesデプロイ手順 |
| **全サービス** | [acceptance-testing.md](./docs/spec/acceptance-testing.md) | 統一起動スクリプト・受入テスト効率化 |

---

## 🔍 用途別クイックリンク

### 新機能開発を始める
→ [開発フロー](./docs/claude/01-development-workflow.md)、[スラッシュコマンド](./docs/claude/02-slash-commands.md)、[ブランチ戦略](./docs/claude/03-branch-strategy.md)

### FeatureをIssueに分割する
→ [Issue分割ガイド](./docs/claude/08-issue-split.md)、[開発フロー](./docs/claude/01-development-workflow.md)

### バグ修正を行う
→ [ブランチ戦略](./docs/claude/03-branch-strategy.md)、[品質基準](./docs/claude/04-quality-standards.md)

### CI/CDエラーを解決する
→ [エラー防止策](./docs/claude/06-ci-cd-prevention.md)

### 複数ブランチで並行作業する
→ [worktreeガイド](./docs/claude/05-worktree-guide.md)

### 作業ドキュメントを作成する
→ [ドキュメント管理](./docs/claude/07-documentation-rules.md)

### 完成した機能をドキュメント化する
→ [ドキュメント管理](./docs/claude/07-documentation-rules.md)、[スラッシュコマンド](./docs/claude/02-slash-commands.md)

---

## 🤖 Claude Code向けガイドライン

### 初回読み込み推奨ファイル

通常開発を開始する際は、以下のファイルを事前に読み込むことを推奨します：

1. **必須**: 本ファイル（CLAUDE.md）
2. **開発時**: [開発フロー](./docs/claude/01-development-workflow.md)、[品質基準](./docs/claude/04-quality-standards.md)
3. **新規プロジェクト時**: [NEW_PROJECT_SETUP.md](./docs/procedures/NEW_PROJECT_SETUP.md)

### パフォーマンス最適化

- 必要な詳細ドキュメントのみを参照することで、コンテキストウィンドウを効率的に利用
- 作業内容に応じて適切なドキュメントを選択的に読み込み
- 頻繁に使用するドキュメントはセッション中にキャッシュされる

---

## 📋 開発時チェックリスト

- [ ] コード品質原則（SOLID、KISS、YAGNI、DRY）に従っている
- [ ] テストカバレッジ要件を満たしている（単体90%、結合50%）
- [ ] 静的解析エラーがない（Ruff、MyPy）
- [ ] 適切なブランチで作業している
- [ ] PRラベルを正しく設定している
- [ ] コミット前に `./scripts/pre-push-check-all.sh` を実行している
- [ ] 必要なドキュメントを `./dev-reports/{branch_path}/` に作成している
- [ ] 受入テストが必要な機能の場合、ローカルで受入テストを実行している

---

## 📊 現在のプロジェクト一覧

| プロジェクト | 目的 | 技術スタック | 状態 |
|-------------|------|-------------|------|
| `expertAgent` | AIエージェント基盤 | FastAPI + LangGraph | ✅ 開発中 |
| `myscheduler` | ジョブスケジューリング | FastAPI + APScheduler | ✅ 本番運用中 |
| `jobqueue` | ジョブキュー管理 | FastAPI + Redis | 🚀 準備中 |
| `myVault` | シークレット管理 | FastAPI + SQLite | ✅ 本番運用中 |
| `graphAiServer` | ワークフロー実行 | FastAPI + GraphAI | ✅ 開発中 |
| `myAgentDesk` | Web UI | SvelteKit | ✅ 開発中 |
| `commonUI` | 共通UIコンポーネント | TypeScript | ✅ 開発中 |

---

**モジュール化により、このファイルのサイズを1,758行から約200行に削減しました。詳細情報は各モジュールファイルを参照してください。**
