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

### 🧪 テスト構造

テストは4層構造で、実行環境が異なります：

| テスト種別 | 場所 | 実行環境 | カバレッジ目標 |
|-----------|------|---------|--------------|
| **単体テスト** | `{project}/tests/unit/` | CI (GitHub Actions) | 90%以上 |
| **結合テスト** | `tests/integration/` | CI (GitHub Actions) | 50%以上 |
| **受入テスト** | `tests/acceptance/` | ローカルのみ | - |
| **クロスサービスE2E** | `scripts/e2e/cross-service/` | ローカルのみ | - |

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

#### クロスサービスE2Eテスト実行方法

複数サービスを横断するフルスタックE2Eテストです：

```bash
# フルワークフローE2E（Job生成→実行→メール送信）
./scripts/e2e/cross-service/test_full_workflow_e2e.sh

# パラメータ指定での実行
./scripts/e2e/cross-service/test_full_workflow_e2e.sh \
  --keyword "検索キーワード" \
  --email "your-email@example.com"

# 全クロスサービステスト実行
./scripts/e2e/cross-service/run_all_tests.sh "検索キーワード" "your-email@example.com"
```

> **前提条件**: `./scripts/dev-hybrid.sh start --local-only` でサービス起動済みであること。
> 詳細は [クロスサービスE2Eテストガイド](./scripts/e2e/cross-service/README.md) を参照してください。

> **注意**: 受入テストの実行には環境変数（APIキー等）の設定が必要です。
> 詳細は [テストガイド](./docs/development/testing-guide.md) を参照してください。

#### 開発ワークフロー
1. 対策案を提示する
2. ユーザーが指示した対策案に対し実行計画を提示する
3. ユーザーからの承認を持って実行計画を実行する

---

## 🖥️ 開発環境の起動

開発を開始する前に、サービスを起動する必要があります。

### 推奨起動方法

| 状況 | コマンド | 説明 |
|------|---------|------|
| **Agent層開発** | `./scripts/dev-hybrid.sh` | Platform=Docker, Agent=ローカル（推奨） |
| **日常開発** | `make dev-all` | 全サービスをDocker環境で起動 |
| **全ローカル** | `./scripts/dev-start.sh` | 全サービスをローカル直接起動 |
| **本番検証** | `docker compose up -d` | コンテナ環境での動作確認 |

### 起動方法の選択フロー

```
Agent層（mySwiftAgentCore, ExpertAgent, GraphAiServer, myAgentDesk）を開発中？
    ↓ Yes
./scripts/dev-hybrid.sh（Platform=Docker, Agent=ローカル）
    ↓ No
全サービスDocker？ → Yes → make dev-all
    ↓ No
全サービスローカル → ./scripts/dev-start.sh
```

### サービスURL（標準ポート）

| サービス | URL | 用途 |
|---------|-----|------|
| JobQueue API | http://localhost:8001 | ジョブキュー管理 |
| MyScheduler API | http://localhost:8002 | スケジューリング |
| MyVault API | http://localhost:8003 | シークレット管理 |
| ExpertAgent API | http://localhost:8004 | AIエージェント・Job Generator |
| GraphAiServer API | http://localhost:8005 | GraphAI OSSワークフロー実行 |
| **mySwiftAgentCore API** | **http://localhost:8006** | **メインワークフロー実行（推奨）** |
| myAgentDesk | http://localhost:5173 | Web UI (SvelteKit) |
| CommonUI | http://localhost:8501 | 管理UI (Streamlit) |
| Langfuse | http://localhost:3001 | LLM Observability |

### 停止コマンド

```bash
make down        # 全サービス停止
# または
./scripts/dev-start.sh stop
```

**詳細**: [ローカル開発環境ガイド](./docs/operations/local-development.md)

---

## 📚 詳細ドキュメントインデックス

| カテゴリ | ドキュメント | 内容 | 優先度 |
|---------|------------|------|--------|
| **開発フロー** | [workflow.md](./docs/development/workflow.md) | アジャイル開発、Feature/Issue管理 | 🔴 高 |
| **スラッシュコマンド** | [slash-commands.md](./docs/development/slash-commands.md) | 利用可能なスラッシュコマンド一覧と使用方法 | 🔴 高 |
| **ブランチ戦略** | [branch-strategy.md](./docs/development/branch-strategy.md) | ブランチルール、PR戦略、リリース | 🔴 高 |
| **品質基準** | [quality-standards.md](./docs/development/quality-standards.md) | テスト方針、静的解析、CI/CD | 🔴 高 |
| **並列開発** | [worktree-guide.md](./docs/development/worktree-guide.md) | git worktree による並列開発 | 🟡 中 |
| **エラー防止** | [ci-cd-prevention.md](./docs/development/ci-cd-prevention.md) | GitHub Actions エラー再発防止 | 🟡 中 |
| **文書管理** | [documentation-rules.md](./docs/development/documentation-rules.md) | 作業ドキュメント管理ルール | 🟡 中 |
| **Issue分割** | [issue-split.md](./docs/development/issue-split.md) | Issue分割詳細ガイド、受入基準の2層構造 | 🔴 高 |
| **ローカル開発環境** | [local-development.md](./docs/operations/local-development.md) | 起動方法比較、ポート構成、トラブルシューティング | 🟡 中 |
| **クロスサービスE2E** | [cross-service/README.md](./scripts/e2e/cross-service/README.md) | サービス間統合E2Eテスト、フルワークフロー検証 | 🟡 中 |

---

## 🚨 重要な参照ドキュメント

開発を開始する前に、以下のドキュメントが該当するか確認してください：

| 状況 | 参照ドキュメント | 必須度 |
|------|----------------|--------|
| **新プロジェクトを追加する** | [new-project-setup.md](./docs/operations/new-project-setup.md) | 🔴 必須 |
| **TaskFlowワークフローを開発する** | [API_REFERENCE.md](./mySwiftAgentCore/docs/API_REFERENCE.md) | 🔴 必須 |
| **GraphAI OSSワークフローを開発する** | [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/features/GRAPHAI_WORKFLOW_GENERATION_RULES.md) | 🟡 条件付き |
| **クロスサービスE2Eテストを実行する** | [cross-service/README.md](./scripts/e2e/cross-service/README.md) | 🟡 条件付き |
| **アーキテクチャを理解する** | [overview.md](./docs/architecture/overview.md) | 🟡 推奨 |
| **環境変数を設定する** | [environment-variables.md](./docs/reference/environment-variables.md) | 🟡 推奨 |
| **myVault連携を実装する** | [myvault-integration.md](./docs/architecture/myvault-integration.md) | 🟡 推奨 |
| **デプロイメントを行う** | [deployment.md](./docs/operations/deployment.md) | 🟡 推奨 |

**重要**: 該当するドキュメントは作業開始前に必ず全文を読み、作業計画書 (`work-plan.md`) に参照を明記してください。

### 📚 プロジェクト別必須ドキュメント

各マイクロサービスの開発時に参照すべきドキュメント:

| プロジェクト | 必須ドキュメント | 説明 |
|-------------|----------------|------|
| **mySwiftAgentCore** | [API_REFERENCE.md](./mySwiftAgentCore/docs/API_REFERENCE.md) | メインワークフローAPI仕様（TaskFlow生成・実行） |
| **mySwiftAgentCore** | [taskflow-execution.md](./mySwiftAgentCore/docs/features/taskflow-execution.md) | TaskFlow実行エンジン仕様 |
| **expertAgent** | [API_REFERENCE.md](./expertAgent/docs/API_REFERENCE.md) | 全API仕様 (Job Generator, Workflow Generator, Chat, Marp Report, Observability) |
| **expertAgent** | [job-generation-workflow.md](./docs/architecture/job-generation-workflow.md) | Job Generator仕様とLangGraphエージェント設計 |
| **graphAiServer** | [GRAPHAI_WORKFLOW_GENERATION_RULES.md](./graphAiServer/docs/features/GRAPHAI_WORKFLOW_GENERATION_RULES.md) | GraphAI OSS用ワークフロー生成ルール |
| **myAgentDesk** | [README.md](./myAgentDesk/README.md) | SvelteKitアーキテクチャ・API統合・トラブルシューティング |
| **全サービス** | [service-dependencies.md](./docs/architecture/service-dependencies.md) | サービス間依存関係・起動順序・通信フロー |
| **全サービス** | [deployment.md](./docs/operations/deployment.md) | Docker Compose/Kubernetesデプロイ手順 |
| **全サービス** | [testing-guide.md](./docs/development/testing-guide.md) | 統一起動スクリプト・受入テスト効率化 |

---

## 🔍 用途別クイックリンク

### 新機能開発を始める
→ [開発フロー](./docs/development/workflow.md)、[スラッシュコマンド](./docs/development/slash-commands.md)、[ブランチ戦略](./docs/development/branch-strategy.md)

### FeatureをIssueに分割する
→ [Issue分割ガイド](./docs/development/issue-split.md)、[開発フロー](./docs/development/workflow.md)

### バグ修正を行う
→ [ブランチ戦略](./docs/development/branch-strategy.md)、[品質基準](./docs/development/quality-standards.md)

### CI/CDエラーを解決する
→ [エラー防止策](./docs/development/ci-cd-prevention.md)

### E2Eテストを実行する
→ [クロスサービスE2E](./scripts/e2e/cross-service/README.md)、[テストガイド](./docs/development/testing-guide.md)

### 複数ブランチで並行作業する
→ [worktreeガイド](./docs/development/worktree-guide.md)

### 作業ドキュメントを作成する
→ [ドキュメント管理](./docs/development/documentation-rules.md)

### 完成した機能をドキュメント化する
→ [ドキュメント管理](./docs/development/documentation-rules.md)、[スラッシュコマンド](./docs/development/slash-commands.md)

---

## 🤖 Claude Code向けガイドライン

### 初回読み込み推奨ファイル

通常開発を開始する際は、以下のファイルを事前に読み込むことを推奨します：

1. **必須**: 本ファイル（CLAUDE.md）
2. **開発時**: [開発フロー](./docs/development/workflow.md)、[品質基準](./docs/development/quality-standards.md)
3. **新規プロジェクト時**: [new-project-setup.md](./docs/operations/new-project-setup.md)

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

## ✅ Issue完遂チェックリスト【必須】

Issue完了前に以下をすべて確認すること。**1つでも未完了の場合、Issueは完了とみなさない。**

### 受入条件の完全検証

| チェック項目 | 確認方法 |
|-------------|---------|
| 全受入条件（AC-1〜AC-N）が実装されているか | Issue本文と実装を1つずつ照合 |
| 各受入条件に対応するテストが存在するか | テストファイルで確認 |
| 受入テストが全パスしているか | `pytest tests/acceptance/` 実行結果 |

### コード品質の確認

| チェック項目 | 確認コマンド |
|-------------|-------------|
| 静的解析エラーゼロ | `./scripts/pre-push-check-all.sh` |
| カバレッジ90%以上 | pytest --cov 出力 |
| デッドコードなし | Phase 2.7 実装検証結果 |
| **変更影響テスト全パス** | 下記「リグレッションテスト」参照（Issue #402教訓） |

### ドキュメント更新

| チェック項目 | 対象 |
|-------------|------|
| API変更時 → API_REFERENCE.md更新 | `{project}/docs/API_REFERENCE.md` |
| 設定変更時 → 環境変数ドキュメント更新 | `docs/reference/environment-variables.md` |
| 新機能追加時 → README更新 | `{project}/README.md` |

### 最終確認

```bash
# Issue完遂確認コマンド
./scripts/pre-push-check-all.sh && echo "✅ 品質チェック合格"

# 変更影響テスト実行（Issue #402教訓）
# 変更したファイルに依存するテストを検出・実行
uv run pytest tests/unit/ -v --ignore=tests/acceptance/

# 受入テスト実行
uv run pytest tests/acceptance/test_issue_{番号}_*.py -v

# 未対応の受入条件がないか確認
gh issue view {番号} --json body | jq -r '.body' | grep -E "^\s*-\s*\["
```

---

## 📚 ドキュメント配置ルール

### 基本原則

```
┌─────────────────────────────────────────────────────────────────┐
│                        docs/ (全体ドキュメント)                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 複数プロジェクトに関係する / プロジェクト横断的な内容          ││
│  │ • システム全体のアーキテクチャ                                ││
│  │ • 開発プロセス・ルール                                       ││
│  │ • サービス間連携・依存関係                                    ││
│  │ • 共通の運用手順                                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   {project}/docs/ (プロジェクト固有)              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ そのプロジェクトでしか使わない / 単独で完結する内容           ││
│  │ • API仕様（API_REFERENCE.md）                               ││
│  │ • プロジェクト固有の設計・アーキテクチャ                      ││
│  │ • プロジェクト固有の機能仕様                                  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 判断フローチャート

```
ドキュメントを作成する
    │
    ▼
このドキュメントは単一プロジェクトでのみ使用される？
    │
    ├─ Yes → {project}/docs/ に配置
    │
    └─ No → 複数プロジェクトに関係する
              │
              ▼
          プロジェクト間の連携・統合に関する内容？
              │
              ├─ Yes → docs/architecture/ に配置
              │
              └─ No → 開発プロセス・ルールに関する内容？
                        │
                        ├─ Yes → docs/development/ に配置
                        │
                        └─ No → docs/reference/ に配置
```

### 配置ルール詳細

| カテゴリ | 配置場所 | 内容例 |
|---------|---------|--------|
| **システム全体構成** | `docs/architecture/` | overview.md, service-dependencies.md |
| **開発プロセス** | `docs/development/` | workflow.md, quality-standards.md |
| **運用手順** | `docs/operations/` | local-development.md, deployment.md |
| **共通設定** | `docs/reference/` | environment-variables.md, glossary.md |
| **プロジェクトAPI** | `{project}/docs/API_REFERENCE.md` | エンドポイント仕様 |
| **プロジェクト機能** | `{project}/docs/features/` | 機能固有の仕様書 |

---

## 📊 プロジェクト構成

### アーキテクチャ概要

MySwiftAgentは以下の3層アーキテクチャで構成されています：

| 層 | プロジェクト | 説明 |
|----|------------|------|
| **Platform** | myVault, jobqueue, Valkey | インフラ・データ基盤 |
| **Agent** | expertAgent, mySwiftAgentCore, graphAiServer | AIエージェント・ワークフロー実行 |
| **Frontend** | myAgentDesk, commonUI | ユーザーインターフェース |

### プロジェクト別役割

| プロジェクト | 役割 | 技術スタック | 備考 |
|-------------|------|-------------|------|
| **mySwiftAgentCore** | **メインワークフロー実行エンジン** | TypeScript + TaskFlow | **基本的にこちらを使用** |
| graphAiServer | GraphAI OSS連携用ワークフロー実行 | TypeScript + GraphAI | GraphAI OSSを使用する場合のみ |
| expertAgent | AIエージェント基盤・Job Generator | FastAPI + LangGraph | ジョブ生成・管理 |
| myAgentDesk | Web UI | SvelteKit | フロントエンド |
| jobqueue | ジョブキュー管理 | FastAPI + SQLite | ジョブの永続化・実行管理 |
| myVault | シークレット管理 | FastAPI + SQLite | APIキー等の安全な管理 |
| myscheduler | ジョブスケジューリング | FastAPI + APScheduler | 定期実行 |
| commonUI | 共通UIコンポーネント | Streamlit | 再利用可能なUI部品 |

### mySwiftAgentCore vs graphAiServer の使い分け

| 条件 | 使用するプロジェクト |
|------|---------------------|
| 通常のワークフロー実行 | **mySwiftAgentCore** |
| TaskFlow形式のワークフロー | **mySwiftAgentCore** |
| GraphAI OSS形式のワークフロー | graphAiServer |
| 新規ワークフロー開発（デフォルト） | **mySwiftAgentCore** |

**原則**: 基本的に**mySwiftAgentCore**を使用。GraphAI OSSを使用する場合に限りgraphAiServerを使用する。

---

## 🚨 サブエージェント利用時の必須検証ルール

### 原則: 「成功報告を信頼しない」

サブエージェントが `status: "success"` を報告しても、以下を必ず検証すること：

#### TDD実装後の検証チェックリスト

| 検証項目 | 確認方法 |
|---------|---------|
| 全タスクが実行されたか | `files_modified` に期待ファイルが含まれるか確認 |
| 統合ファイルが更新されたか | `agent.py`, `__init__.py` 等の変更を確認 |
| 定数/関数が実際に使用されているか | Grep で参照箇所を確認 |
| グラフ/ワークフローに組み込まれたか | 該当ファイルを Read して確認 |

```bash
# 例: 新規ノードがグラフに組み込まれたか確認
grep -n "new_node_name" path/to/agent.py
```

#### 受入テスト後の検証チェックリスト

| 検証項目 | 確認方法 |
|---------|---------|
| E2Eで機能が動作したか | 単体テスト結果ではなく、実際のAPI呼び出し結果を確認 |
| 受入条件が実際に検証されたか | 「単体テストで確認済み」は不可。実動作を確認 |
| スキップされたテストがないか | skipped が 0 であることを確認 |

### 禁止事項

- ❌ サブエージェントの `status: "success"` だけで次フェーズに進む
- ❌ 「単体テストで検証済み」を受入テスト合格とみなす
- ❌ 定数/関数の「存在確認」だけで「統合確認」をスキップ
- ❌ 結果ファイルの `files_modified` を確認せずに完了とする

---

## 🧪 テスト設計の必須要件

### 単体テストの2層構造

| 層 | 目的 | 例 |
|----|------|-----|
| 存在確認 | 定数/関数が存在するか | `assert TYPE_VALIDATION_RULES is not None` |
| **統合確認** | 実際に使用されているか | `assert TYPE_VALIDATION_RULES in actual_prompt` |

**重要**: 存在確認だけでは不十分。統合確認テストを必ず含めること。

### 結合テストの必須化

work-plan.md に結合テストタスクがある場合、以下を確認：

1. 結合テストファイルが作成されているか
2. 結合テストが実際に実行されたか
3. 新機能がワークフロー全体で動作するか

---

## 🧪 受入テスト必須化ルール（Issue #333教訓）

### Issue実装時の必須テスト

| テスト種別 | 配置場所 | 必須条件 | 検証方法 |
|-----------|---------|---------|---------|
| 単体テスト | `{project}/tests/unit/` | カバレッジ90%以上 | CI自動実行 |
| 結合テスト | `{project}/tests/integration/` | グラフ/API統合確認 | CI自動実行 |
| **受入テスト** | **`{project}/tests/acceptance/`** | **実API呼び出しでE2E確認** | **ローカル手動実行** |

### 受入テストファイルの必須要件

1. **ファイル命名規則**: `test_issue_{番号}_acceptance.py`
2. **配置場所**: `{project}/tests/acceptance/`
3. **存在確認コマンド**:
   ```bash
   ls {project}/tests/acceptance/test_issue_{番号}_*.py
   ```

### 受入テストの内容要件

| 要件 | 説明 | 禁止事項 |
|-----|------|---------|
| **実API呼び出し** | 実際のAPIエンドポイントを呼び出して検証 | モックのみのテストは受入テストではない |
| **E2E確認** | 機能の開始から終了まで一連のフローを確認 | 単体テスト結果の引用は不可 |
| **受入条件の検証** | Issue の受入条件を1つずつ検証 | 「単体テストで検証済み」は禁止 |
| **実データ使用** | 可能な限り実際のデータで検証 | テストデータのみでの検証は不十分 |

### 受入テストが不要なケース

以下の場合のみ、受入テストを省略可能：

- リファクタリングのみ（外部インターフェース変更なし）
- ドキュメント修正のみ
- テストコード修正のみ
- 内部実装の変更で外部動作に影響なし

**省略する場合は、work-plan.md に理由を明記すること。**

### 受入テスト未作成時のアクション

受入テストファイルが存在しない場合：

1. **PM Auto-Dev**: Phase 3 を再実行
2. **手動開発**: 受入テストを作成してから完了報告
3. **レビュー時**: 受入テストがないPRはマージ不可

---

## 🔄 変更影響テスト必須化ルール（Issue #402教訓）

### 背景

Issue #402で `topological_sort.py` を追加した際、依存する `mock_helpers.py` を使用する既存テスト（11件）が実行されずにマージされ、後に全11件が `ValueError: invalid literal for int()` で失敗しました。

**根本原因**: TDD実装時に「新規テストのみ」を実行し、変更影響を受ける既存テストを実行していなかった。

### 必須ルール

| チェック項目 | 実行タイミング | 確認コマンド |
|-------------|---------------|-------------|
| **変更影響テスト実行** | TDD完了後、受入テスト前 | 下記参照 |
| **全単体テストパス** | Issue完了前 | `uv run pytest tests/unit/ -v` |

### 変更影響テストの実行手順

```bash
# 1. 変更ファイルを特定
git diff --name-only HEAD~1

# 2. 依存テストを検索（変更ファイルをimportしているテスト）
CHANGED_FILE="path/to/changed_file.py"
BASENAME=$(basename "$CHANGED_FILE" .py)
grep -rl "from.*${BASENAME}\|import.*${BASENAME}" tests/

# 3. 依存テストを実行
uv run pytest [検出されたテストファイル] -v

# 4. 全単体テストを実行（推奨）
uv run pytest tests/unit/ -v --ignore=tests/acceptance/
```

### 典型的な失敗パターンと対処

| エラー | 原因 | 対処 |
|--------|------|------|
| `ValueError: invalid literal for int()` | 型不整合（文字列→整数等） | モックデータの型を更新 |
| `AttributeError: 'NoneType'` | 必須フィールドの欠落 | モックデータにフィールド追加 |
| `KeyError: 'field_name'` | 必須キーの欠落 | モックデータにキー追加 |

### PM Auto-Devでの自動化

PM Auto-Devを使用する場合、Phase 2.9（変更影響テスト実行）で自動的に実行されます。

---

**モジュール化により、このファイルのサイズを1,758行から約200行に削減しました。詳細情報は各モジュールファイルを参照してください。**
