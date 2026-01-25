# MySwiftAgent ドキュメントインデックス

このページは、MySwiftAgentプロジェクトの全ドキュメントへのナビゲーションを提供します。

---

## はじめに

| ドキュメント | 説明 |
|-------------|------|
| [クイックスタート](./getting-started/quick-start.md) | 5分で始めるMySwiftAgent |
| [インストール](./getting-started/installation.md) | 環境構築手順 |
| [初めてのワークフロー](./getting-started/first-workflow.md) | 最初のワークフローを作成 |

---

## アーキテクチャ

| ドキュメント | 説明 |
|-------------|------|
| [システム概要](./architecture/overview.md) | 全体アーキテクチャと設計思想 |
| [サービス間依存関係](./architecture/service-dependencies.md) | マイクロサービス間の連携 |
| [myVault連携](./architecture/myvault-integration.md) | シークレット管理の仕組み |
| [Valkey連携](./architecture/valkey-integration.md) | キャッシュ・セッション管理 |
| [Langfuse連携](./architecture/langfuse-integration.md) | LLM Observabilityの設定 |
| [Job生成ワークフロー](./architecture/job-generation-workflow.md) | LangGraphエージェント設計 |

---

## 開発ガイド

| ドキュメント | 説明 |
|-------------|------|
| [開発ワークフロー](./development/workflow.md) | アジャイル開発プロセス |
| [ブランチ戦略](./development/branch-strategy.md) | Git運用ルール |
| [品質基準](./development/quality-standards.md) | テスト・静的解析の基準 |
| [スラッシュコマンド](./development/slash-commands.md) | Claude Code スラッシュコマンド一覧 |
| [Issue分割ガイド](./development/issue-split.md) | FeatureからIssueへの分割方法 |
| [Worktreeガイド](./development/worktree-guide.md) | 並列開発の進め方 |
| [CI/CDエラー防止](./development/ci-cd-prevention.md) | GitHub Actionsエラー対策 |
| [ドキュメントルール](./development/documentation-rules.md) | 作業ドキュメント管理 |
| [ロギングポリシー](./development/logging-policy.md) | ログ出力の規約 |
| [テストガイド](./development/testing-guide.md) | テスト戦略と受入テスト |
| [アジャイルワークフロー](./development/agile-workflow.md) | アジャイル開発プロセス詳細 |
| [開発ガイド](./development/development-guide.md) | 開発環境・手順の詳細 |

---

## 運用ガイド

| ドキュメント | 説明 |
|-------------|------|
| [ローカル開発環境](./operations/local-development.md) | 開発環境の構築と起動 |
| [デプロイガイド](./operations/deployment.md) | 本番環境へのデプロイ |
| [新規プロジェクト追加](./operations/new-project-setup.md) | マイクロサービスの追加手順 |
| [Valkey運用](./operations/valkey-operations.md) | Valkeyの運用手順 |
| [プロンプト運用](./operations/prompt-operations.md) | プロンプト管理・更新 |
| [トラブルシューティング](./operations/troubleshooting.md) | よくある問題と解決方法 |
| [並列開発ワークフロー](./operations/parallel-development.md) | 複数ブランチでの並行作業 |
| [Dockerガイド](./operations/docker-guide.md) | コンテナ運用の詳細 |
| [統一起動スクリプト](./operations/unified-start-usage.md) | 開発環境起動の統一方法 |
| [環境移行ガイド](./operations/env-migration-guide.md) | 環境変数移行手順 |

---

## リファレンス

| ドキュメント | 説明 |
|-------------|------|
| [環境変数一覧](./reference/environment-variables.md) | 全サービスの環境変数 |
| [設定ファイル](./reference/configuration.md) | 設定ファイルの構成 |
| [用語集](./reference/glossary.md) | プロジェクト用語の定義 |
| [TaskFlow形式仕様](./reference/taskflow-format.md) | ワークフロー定義形式 |
| [TaskChain契約](./reference/taskchain-contract.md) | サービス間データ契約 |
| [GraphAI環境変数](./reference/graphai-env-vars.md) | GraphAI固有の環境変数 |
| [ヘルスチェック仕様](./reference/health-check-spec.md) | ヘルスチェックエンドポイント仕様 |
| [ユーザーシナリオ](./reference/user-scenarios.md) | ユースケース集 |

---

## API仕様

| ドキュメント | 説明 |
|-------------|------|
| [TaskFlow Generator API](./reference/api/taskflow-generator-api.yaml) | API仕様（OpenAPI） |

---

## プロジェクト別ドキュメント

| プロジェクト | 概要 | API仕様 | 詳細ドキュメント |
|-------------|------|---------|----------------|
| [mySwiftAgentCore](../mySwiftAgentCore/README.md) | **メインワークフロー実行エンジン（推奨）** | [API](../mySwiftAgentCore/docs/API_REFERENCE.md) | [docs/](../mySwiftAgentCore/docs/) |
| [expertAgent](../expertAgent/README.md) | AIエージェント基盤・Job Generator | [API](../expertAgent/docs/API_REFERENCE.md) | [docs/](../expertAgent/docs/) |
| [graphAiServer](../graphAiServer/README.md) | GraphAI OSS連携 | [API](../graphAiServer/docs/API_ENDPOINTS.md) | [docs/](../graphAiServer/docs/) |
| [myAgentDesk](../myAgentDesk/README.md) | Web UI (SvelteKit) | [API](../myAgentDesk/docs/API_REFERENCE.md) | [docs/](../myAgentDesk/docs/) |
| [jobqueue](../jobqueue/README.md) | ジョブキュー管理 | - | [docs/](../jobqueue/docs/) |
| [myVault](../myVault/README.md) | シークレット管理 | - | [docs/](../myVault/docs/) |
| [myscheduler](../myscheduler/README.md) | ジョブスケジューリング | [API](../myscheduler/docs/API_REFERENCE.md) | [docs/](../myscheduler/docs/) |
| [commonUI](../commonUI/README.md) | 共通UIコンポーネント | - | [docs/](../commonUI/docs/) |

---

## 関連リンク

- [CLAUDE.md](../CLAUDE.md) - Claude Code向けガイドライン
- [README.md](../README.md) - プロジェクト概要

---

**最終更新**: 2026-01-25
