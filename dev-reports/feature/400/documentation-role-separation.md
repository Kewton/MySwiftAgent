# ドキュメント役割分担ルール

## 1. 現状の問題点

### 1.1 役割が曖昧なドキュメント

| ドキュメント | 現在の場所 | 問題点 |
|-------------|-----------|--------|
| `job-generation-workflow.md` | `docs/spec/` | expertAgent固有なのに全体docsにある |
| `myvault-integration.md` | `docs/design/` | myVault固有なのに全体docsにある |
| `langfuse-integration.md` | `docs/design/` | 複数プロジェクトに関係するが全体設計か不明 |
| `graphai-env-vars.md` | `docs/design/` | graphAiServer固有なのに全体docsにある |
| `valkey-integration.md` | `expertAgent/docs/` | 複数プロジェクトで使うのにexpertAgentにある |

### 1.2 プロジェクト間の不整合

| プロジェクト | docs/有無 | API_REFERENCE | arch/ | spec/ | ops/ |
|-------------|----------|---------------|-------|-------|------|
| expertAgent | ✅ | ✅ | 📄 README only | 📄 README only | 📄 README only |
| graphAiServer | ✅ | ✅ (API_ENDPOINTS.md) | 📄 README only | 📄 README only | 📄 README only |
| mySwiftAgentCore | ❌ | ❌ | - | - | - |
| jobqueue | ✅ | ❌ | ❌ | ❌ | ❌ |
| myVault | ✅ | ❌ | 📄 README only | 📄 README only | 📄 README only |
| myAgentDesk | ❌ | ❌ | - | - | - |
| myscheduler | ❌ | ❌ | - | - | - |
| commonUI | ❌ | ❌ | - | - | - |

---

## 2. 役割分担ルール

### 2.1 基本原則

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
│  │ • プロジェクト固有の運用・トラブルシューティング               ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 判断フローチャート

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
                        └─ No → 運用・デプロイに関する内容？
                                  │
                                  ├─ Yes → docs/operations/ に配置
                                  │
                                  └─ No → docs/reference/ に配置
```

### 2.3 配置ルール詳細

#### docs/ (全体ドキュメント) に置くもの

| カテゴリ | 内容 | 例 |
|---------|------|-----|
| **architecture/** | システム全体構成、サービス間連携 | `overview.md`, `service-dependencies.md`, `data-flow.md` |
| **development/** | 開発プロセス、コーディング規約、品質基準 | `workflow.md`, `branch-strategy.md`, `quality-standards.md` |
| **operations/** | 共通の運用手順、デプロイ、環境構築 | `local-development.md`, `deployment.md`, `troubleshooting.md` |
| **reference/** | 共通設定、環境変数、用語集 | `environment-variables.md`, `glossary.md` |
| **getting-started/** | 新規参加者向け導入ガイド | `quick-start.md`, `installation.md` |

#### {project}/docs/ (プロジェクト固有) に置くもの

| カテゴリ | 内容 | 例 |
|---------|------|-----|
| **API_REFERENCE.md** | そのプロジェクトのAPI仕様（必須） | エンドポイント、リクエスト/レスポンス |
| **features/** | プロジェクト固有の機能仕様 | `job-generator.md`, `workflow-execution.md` |
| **internals/** | 内部設計・アーキテクチャ | `state-management.md`, `error-handling.md` |
| **guides/** | プロジェクト固有の使い方ガイド | `agent-development.md`, `prompt-writing.md` |

---

## 3. 具体的な移行マッピング

### 3.1 全体docs → プロジェクトdocs への移行

| 現在の場所 | 移行先 | 理由 |
|-----------|--------|------|
| `docs/spec/job-generation-workflow.md` | `expertAgent/docs/features/job-generation.md` | expertAgent固有の機能 |
| `docs/design/graphai-env-vars.md` | `graphAiServer/docs/configuration.md` | graphAiServer固有の設定 |
| `docs/design/node-execution-context.md` | `mySwiftAgentCore/docs/internals/node-execution.md` | mySwiftAgentCore固有の設計 |

### 3.2 プロジェクトdocs → 全体docs への移行

| 現在の場所 | 移行先 | 理由 |
|-----------|--------|------|
| `expertAgent/docs/valkey-integration.md` | `docs/architecture/valkey-integration.md` | 複数プロジェクトで使用 |

### 3.3 全体docs内での再編成

| 現在の場所 | 移行先 | 理由 |
|-----------|--------|------|
| `docs/design/architecture-overview.md` | `docs/architecture/overview.md` | カテゴリ統合 |
| `docs/design/myvault-integration.md` | `docs/architecture/myvault-integration.md` | 複数プロジェクト関連 |
| `docs/design/langfuse-integration.md` | `docs/architecture/langfuse-integration.md` | 複数プロジェクト関連 |
| `docs/design/environment-variables.md` | `docs/reference/environment-variables.md` | リファレンス |
| `docs/design/logging-policy.md` | `docs/development/logging-policy.md` | 開発ルール |
| `docs/arch/service-dependencies.md` | `docs/architecture/service-dependencies.md` | カテゴリ統合 |
| `docs/spec/acceptance-testing.md` | `docs/development/testing-guide.md` に統合 | 開発ガイド |
| `docs/spec/taskchain-data-contract.md` | `docs/architecture/taskchain-contract.md` | サービス間契約 |
| `docs/claude/*` | `docs/development/*` | カテゴリ統合 |
| `docs/ops/*` | `docs/operations/*` | カテゴリ統合 |
| `docs/procedures/*` | `docs/operations/*` | カテゴリ統合 |
| `docs/guide/*` | `docs/getting-started/*` または `docs/development/*` | カテゴリ統合 |
| `docs/rule/*` | `docs/development/*` | カテゴリ統合 |

### 3.4 プロジェクトdocs内での再編成

| プロジェクト | 現在 | 変更後 |
|-------------|------|--------|
| expertAgent | `job_generator_v2.md` | `features/job-generator-v2.md` |
| expertAgent | `file-reader-usage-guide.md` | `guides/file-reader.md` |
| expertAgent | `prompt-management.md` | `guides/prompt-management.md` |
| graphAiServer | `GRAPHAI_WORKFLOW_GENERATION_RULES.md` | `features/workflow-generation.md` |
| graphAiServer | `TASKFLOW_GENERATION_RULES.md` | `features/taskflow-generation.md` |
| graphAiServer | `AVAILABLE_AGENTS.md` | `reference/available-agents.md` |
| graphAiServer | `COMMON_ERRORS.md` | `troubleshooting.md` |
| graphAiServer | `agents/*` | `guides/agents/*` |

---

## 4. プロジェクトdocs標準構造

### 4.1 必須ファイル

```
{project}/
├── README.md                    # プロジェクト概要（必須）
└── docs/
    ├── API_REFERENCE.md         # API仕様（APIがある場合必須）
    └── ...
```

### 4.2 推奨構造（大規模プロジェクト）

```
{project}/docs/
├── API_REFERENCE.md             # API仕様
├── features/                    # 機能仕様
│   ├── feature-a.md
│   └── feature-b.md
├── internals/                   # 内部設計
│   └── architecture.md
├── guides/                      # 使い方ガイド
│   └── getting-started.md
└── troubleshooting.md           # トラブルシューティング
```

### 4.3 簡易構造（小規模プロジェクト）

```
{project}/docs/
├── API_REFERENCE.md             # API仕様
└── README.md                    # その他すべて
```

---

## 5. README.md標準テンプレート

### 5.1 プロジェクトREADME.md

```markdown
# {プロジェクト名}

## 概要
{1-2文でプロジェクトの目的を説明}

## システム内での役割
{全体アーキテクチャ内での位置づけ}

## 技術スタック
| 項目 | 技術 |
|------|------|
| 言語 | {言語} |
| フレームワーク | {フレームワーク} |
| データベース | {あれば} |

## クイックスタート

### 起動
```bash
{起動コマンド}
```

### ヘルスチェック
```bash
curl http://localhost:{port}/health
```

## API
→ 詳細は [API_REFERENCE.md](./docs/API_REFERENCE.md) を参照

## 設定

### 環境変数
| 変数名 | 説明 | 必須 | デフォルト |
|--------|------|------|-----------|

### 依存サービス
| サービス | 用途 | 必須 |
|---------|------|------|

## ディレクトリ構成
```
{project}/
├── src/          # ソースコード
├── tests/        # テスト
└── docs/         # ドキュメント
```

## 関連ドキュメント
- [システム全体アーキテクチャ](../docs/architecture/overview.md)
- [サービス間依存関係](../docs/architecture/service-dependencies.md)
- [ローカル開発環境](../docs/operations/local-development.md)
```

---

## 6. ドキュメント所有者ルール

### 6.1 所有者の定義

| ドキュメント種別 | 所有者 | 更新責任 |
|----------------|--------|---------|
| `docs/architecture/*` | アーキテクト / テックリード | アーキテクチャ変更時 |
| `docs/development/*` | 開発チーム全体 | プロセス変更時 |
| `docs/operations/*` | DevOps / 開発チーム | 運用変更時 |
| `docs/reference/*` | 設定変更した人 | 設定追加・変更時 |
| `{project}/docs/*` | プロジェクト担当者 | 機能変更時 |
| `{project}/README.md` | プロジェクト担当者 | 概要変更時 |

### 6.2 更新トリガー

| イベント | 更新対象 |
|---------|---------|
| 新規API追加 | `{project}/docs/API_REFERENCE.md` |
| API変更（破壊的） | `{project}/docs/API_REFERENCE.md` + CHANGELOG |
| 環境変数追加 | `docs/reference/environment-variables.md` |
| サービス間連携変更 | `docs/architecture/service-dependencies.md` |
| 新規プロジェクト追加 | `docs/architecture/overview.md` + 新プロジェクトREADME |
| 開発プロセス変更 | `docs/development/` 関連ファイル |

---

## 7. 削除対象（空ディレクトリ・不要ファイル）

| 対象 | 理由 |
|------|------|
| `expertAgent/docs/arch/README.md` | 空のプレースホルダー |
| `expertAgent/docs/spec/README.md` | 空のプレースホルダー |
| `expertAgent/docs/ops/README.md` | 空のプレースホルダー |
| `graphAiServer/docs/arch/README.md` | 空のプレースホルダー |
| `graphAiServer/docs/spec/README.md` | 空のプレースホルダー |
| `graphAiServer/docs/ops/README.md` | 空のプレースホルダー |
| `myVault/docs/arch/README.md` | 空のプレースホルダー |
| `myVault/docs/spec/README.md` | 空のプレースホルダー |
| `myVault/docs/ops/README.md` | 空のプレースホルダー |
| `docs/rule/README.md` | 空のプレースホルダー |
| `docs/arch/README.md` | 空のプレースホルダー |
| `docs/spec/README.md` | 空のプレースホルダー |
| `docs/ops/README.md` | 空のプレースホルダー |
| `workspace/*` | 古い作業ファイル → `.archive/` へ |

---

## 8. CLAUDE.mdへの反映

CLAUDE.mdに以下のセクションを追加：

```markdown
## 📚 ドキュメント配置ルール

### 全体ドキュメント (docs/) に置くもの
- **複数プロジェクトに関係する内容**
- システム全体のアーキテクチャ
- 開発プロセス・ルール
- 共通の運用手順
- 共通設定・環境変数

### プロジェクトドキュメント ({project}/docs/) に置くもの
- **そのプロジェクトでしか使わない内容**
- API仕様（API_REFERENCE.md）必須
- プロジェクト固有の機能仕様
- プロジェクト固有の設計

### 判断基準
「このドキュメントは他のプロジェクトでも参照される？」
- Yes → docs/
- No → {project}/docs/
```

---

**作成日**: 2026-01-25
