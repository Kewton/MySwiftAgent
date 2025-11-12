# 📝 作業ドキュメント管理

## Claude Code 作業記録ルール

Claude Codeによる開発作業では、以下のドキュメントをリポジトリのルートディレクトリ直下の `./dev-reports/{branch_path}/` ディレクトリにMarkdown形式で保存します。

**ディレクトリ命名規則**: ブランチ名の階層構造を保持
- 例: `feature/issue/104` → `./dev-reports/feature/issue/104/`
- スラッシュで区切られた階層をそのままディレクトリ階層として作成

## **必須ドキュメント一覧**

| ドキュメント名 | 内容 | 作成タイミング | 制約条件チェック |
|-------------|------|-------------|----------------|
| `design-policy.md` | 設計方針・アーキテクチャ判断・技術選定 | 実装開始前 | ✅ 必須 |
| `work-plan.md` | 作業計画・Phase分解・スケジュール | 設計承認後 | ✅ 必須 |
| `phase-{N}-progress.md` | Phase毎の作業内容・課題・決定事項 | 各Phase完了時 | ✅ 必須 |
| `final-report.md` | 作業報告・テスト結果・納品物一覧 | 全作業完了時 | ✅ 必須 |

## **ドキュメント構成例**

```
commonUI/
・・・
dev-reports/
└── feature/
    └── issue/
        └── 104/
            ├── design-policy.md          # 設計方針
            ├── work-plan.md              # 作業計画
            ├── phase-1-progress.md       # Phase 1 作業状況
            ├── phase-2-progress.md       # Phase 2 作業状況
            ├── phase-3-progress.md       # Phase 3 作業状況
            └── final-report.md           # 最終作業報告
```

## 🔍 制約条件チェックルール

### **チェック実施タイミング**

以下のタイミングで**必ず**制約条件チェックを実施すること：

1. **設計方針検討完了時** (`design-policy.md` 作成時)
2. **作業計画立案完了時** (`work-plan.md` 作成時)
3. **各Phase完了時** (`phase-{N}-progress.md` 作成時)
4. **全作業完了時** (`final-report.md` 作成時)

### **チェック対象の制約条件**

#### **1. コード品質原則**
- [ ] **SOLID原則** の遵守
  - Single Responsibility Principle (単一責任原則)
  - Open-Closed Principle (開放/閉鎖原則)
  - Liskov Substitution Principle (リスコフの置換原則)
  - Interface Segregation Principle (インターフェース分離の原則)
  - Dependency Inversion Principle (依存性逆転の原則)
- [ ] **KISS原則** (Keep It Simple, Stupid)
- [ ] **YAGNI原則** (You Aren't Gonna Need It)
- [ ] **DRY原則** (Don't Repeat Yourself)

#### **2. アーキテクチャガイドライン**
- [ ] `./docs/design/architecture-overview.md` に準拠
- [ ] レイヤー分離の原則遵守
- [ ] 依存関係の方向性確認

#### **3. 設定管理ルール**
- [ ] システムパラメータは環境変数で管理（`./docs/design/environment-variables.md` 参照）
- [ ] ユーザーパラメータはmyVaultで管理（`./docs/design/myvault-integration.md` 参照）

#### **4. 品質担保方針**
- [ ] 単体テストカバレッジ **90%以上**
- [ ] 結合テストカバレッジ **50%以上**
- [ ] Ruff linting エラーゼロ
- [ ] MyPy type checking エラーゼロ

#### **5. CI/CD準拠**
- [ ] PRラベルの適切な付与（`feature`, `fix`, `breaking`）
- [ ] コミットメッセージ規約遵守
- [ ] `./scripts/pre-push-check-all.sh` 合格

### **チェック実施方法**

各ドキュメント作成時に、以下のセクションを必ず含めること：

```markdown
## ✅ 制約条件チェック結果

### コード品質原則
- [x] SOLID原則: 遵守 / 各クラスは単一責任
- [x] KISS原則: 遵守 / シンプルな実装
- [x] YAGNI原則: 遵守 / 必要最小限の機能のみ
- [x] DRY原則: 遵守 / 共通処理はユーティリティ化

### アーキテクチャガイドライン
- [x] architecture-overview.md: 準拠 / レイヤー分離を維持
- [ ] **要検討**: 新規エージェントの配置場所

### 設定管理ルール
- [x] 環境変数: 遵守 / DATABASE_URLを使用
- [x] myVault: 遵守 / APIキーはmyVaultで管理

### 品質担保方針
- [x] 単体テストカバレッジ: 92% (目標90%以上)
- [x] 結合テストカバレッジ: 55% (目標50%以上)
- [x] Ruff linting: エラーゼロ
- [x] MyPy type checking: エラーゼロ

### CI/CD準拠
- [x] PRラベル: feature ラベルを付与予定
- [x] コミットメッセージ: 規約に準拠
- [x] pre-push-check-all.sh: 実行予定

### 参照ドキュメント遵守
- [x] 新プロジェクト追加時: NEW_PROJECT_SETUP.md 遵守
- [x] GraphAI ワークフロー開発時: GRAPHAI_WORKFLOW_GENERATION_RULES.md 遵守

### 違反・要検討項目
なし
```

## 🔄 制約条件変更提案フロー

制約条件違反が不可避な場合、以下の手順で対応すること：

### **Step 1: 違反内容の明確化**

ドキュメント内に以下の形式で記載：

```markdown
## ⚠️ 制約条件違反の検出

### 違反項目
- 品質担保方針 > 単体テストカバレッジ 90%以上

### 違反理由
- 外部API連携部分のモック化が困難
- 実機テストが必要なため、単体テストカバレッジが78%にとどまる

### 影響範囲
- expertAgent プロジェクトのみ
- 結合テストで実機検証を実施するため、品質リスクは限定的
```

### **Step 2: 変更方針の提案**

```markdown
## 💡 制約条件変更方針の提案

### 提案内容
**CLAUDE.md の品質担保方針を以下のように変更**:

**変更前**:
- 単体テストカバレッジ **90%以上** (すべてのプロジェクト)

**変更後**:
- 単体テストカバレッジ **90%以上** (原則)
- **例外**: 外部API連携が主体のプロジェクトは **80%以上** を許容
  - 条件: 結合テストで実機検証を実施すること
  - 対象プロジェクト: expertAgent, jobqueue等

### 変更理由
- 外部API依存が強いプロジェクトでは、モック化コストが高い
- 結合テストで実機検証を行うことで、品質を担保可能
- 過度な単体テストは保守コストを増加させる（YAGNI原則）

### 代替案
1. **提案方針を採用** (推奨)
2. モックライブラリ導入で90%を達成（コスト増）
3. 現状維持で例外として承認を得る
```

### **Step 3: ユーザー承認**

```markdown
## 📋 ユーザー承認待ち

以下の選択肢から選んでください：

1. ✅ **変更方針を承認** → CLAUDE.md を更新
2. ❌ **代替案2を採用** → モックライブラリ導入
3. ⏸️ **現状維持** → 今回のみ例外として承認
```

### **Step 4: CLAUDE.md の更新**

承認後、以下の手順でCLAUDE.mdを更新：

1. CLAUDE.md の該当セクションを修正
2. 変更履歴をリポジトリのルートディレクトリ直下 `./dev-reports/{branch_path}/constraint-changes.md` に記録
3. PRのコミットメッセージに変更理由を明記

---

## 📁 完成ドキュメント管理（docs/）

### **作業ドキュメント (dev-reports/) と完成ドキュメント (docs/) の関係**

| ドキュメント種別 | 配置先 | 用途 | ライフサイクル | 管理方法 |
|---------------|-------|------|--------------|---------|
| **作業ドキュメント** | `dev-reports/feature/issue/{number}/` | Issue/Feature開発中の一時的なドキュメント | Issue完了時に削除またはアーカイブ | ブランチ毎に作成 |
| **完成ドキュメント** | `docs/{category}/` または `{service}/docs/{category}/` | 完成した機能の恒久的なドキュメント | 継続的に更新・保守 | `/doc-register` で統合 |

### **ディレクトリ構造**

#### **プロジェクト全体（root/docs/）**

```
docs/
├── rule/                         # ガイドライン
│   ├── Development-Flow.md       # 開発フロー
│   ├── Coding-Convention.md      # コーディング規約
│   └── Git-Workflow.md           # Git戦略
├── arch/                         # アーキテクチャ
│   ├── System-Overview.md        # システム全体構成
│   ├── Database-Schema.md        # DB設計
│   └── Tech-Stack.md             # 技術スタック
├── spec/                         # プロジェクト横断機能
│   ├── User-Account.md           # ユーザー管理
│   └── Payment.md                # 決済機能
└── ops/                          # 運用
    ├── Release-Process.md        # リリース手順
    └── Monitoring.md             # 監視・アラート
```

#### **マイクロサービス固有（{service}/docs/）**

```
expertAgent/docs/
├── arch/
│   ├── LangGraph-Design.md       # LangGraph設計
│   └── Agent-State.md            # エージェント状態管理
├── spec/
│   ├── Job-Generator.md          # Job Generator機能
│   ├── Workflow-Generator.md     # Workflow Generator機能
│   └── MLOps-Features.md         # MLOps機能
└── ops/
    └── Deployment.md             # expertAgent デプロイ手順

myVault/docs/
├── arch/
│   └── Security-Design.md        # セキュリティ設計
├── spec/
│   └── Secret-Management.md      # シークレット管理機能
└── ops/
    └── Backup-Strategy.md        # バックアップ戦略

graphAiServer/docs/
├── arch/
│   └── Workflow-Engine.md        # ワークフロー実行エンジン
├── spec/
│   └── GraphAI-Integration.md    # GraphAI統合仕様
└── ops/
    └── Performance-Tuning.md     # パフォーマンスチューニング
```

### **ドキュメント配置ルール**

| スコープ | 配置先 | 用途 | 例 |
|---------|-------|------|-----|
| **global** | `docs/rule/` | プロジェクト全体のガイドライン | 開発フロー、Git戦略、コーディング規約 |
| **global** | `docs/arch/` | プロジェクト全体のアーキテクチャ | システム構成図、DB設計、技術選定 |
| **global** | `docs/spec/` | プロジェクト横断機能 | ユーザー管理、決済、認証 |
| **global** | `docs/ops/` | プロジェクト全体の運用 | リリース手順、監視、トラブルシュート |
| **{service}** | `{service}/docs/arch/` | マイクロサービス固有設計 | LangGraph設計、状態管理 |
| **{service}** | `{service}/docs/spec/` | マイクロサービス固有機能 | Job Generator、Secret Management |
| **{service}** | `{service}/docs/ops/` | マイクロサービス固有運用 | デプロイ手順、パフォーマンスチューニング |

### **dev-reports から docs/ への移行フロー**

```
dev-reports/feature/issue/152/
  ├── design-policy.md       → expertAgent/docs/arch/ に統合
  ├── work-plan.md           → docs/rule/ に統合（必要に応じて）
  ├── phase-N-progress.md    → （アーカイブ、統合しない）
  └── final-report.md        → expertAgent/docs/spec/ に統合

/doc-register 152 実行
  ↓
expertAgent/docs/spec/MLOps-Features.md
  - Issue #152の概要、ユーザーストーリー、受入基準を追加
  - dev-reports/design-policy.md からアーキテクチャを抽出
  - dev-reports/work-plan.md から実装詳細を抽出
  - dev-reports/final-report.md からテスト結果を抽出
  - 親Issueの場合、子Issue情報も自動統合
  - セクション構造化して既存ドキュメントに追記
```

### **`/doc-register` コマンドの使用方法**

完成したIssue/Featureを恒久的なドキュメントに統合するには、`/doc-register` コマンドを使用します。

#### **基本構文**
```bash
/doc-register <Issue番号> [オプション]
```

#### **オプション**
| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--scope <global\|{service}>` | スコープ（global=ルートdocs/, service=マイクロサービス内） | 自動判定 |
| `--category <rule\|arch\|spec\|ops>` | カテゴリ | 自動判定 |
| `--target <ファイル名>` | 追記先ドキュメント | 自動判定 |
| `--section <セクション名>` | 追記先セクション | 自動判定 |
| `--draft` | ドラフトモード（コミットしない） | false |
| `--no-child` | 子Issue自動処理スキップ | false |

#### **使用例**

**例1: 自動判定で登録**
```bash
/doc-register 152
# → expertAgent/docs/spec/MLOps-Features.md に追記（新規作成）
```

**例2: プロジェクト全体のアーキテクチャに追記**
```bash
/doc-register 152 --scope global --category arch
# → docs/arch/System-Overview.md に追記
```

**例3: expertAgent固有のアーキテクチャに追記**
```bash
/doc-register 169 --scope expertAgent --category arch
# → expertAgent/docs/arch/LangGraph-Design.md に追記
```

**例4: myVault固有の仕様に追記**
```bash
/doc-register 200 --scope myVault --category spec
# → myVault/docs/spec/Secret-Management.md に追記
```

#### **自動判定ロジック**

**スコープ判定**:
- `dev-reports/feature/issue/{number}/` 配下のファイルで、プロジェクト名（expertAgent, myVault等）の言及回数をカウント
- ラベル `project:expertAgent` 等を検出
- タイトルに「プロジェクト全体」が含まれる場合は `global`
- デフォルト: `expertAgent`

**カテゴリ判定**:
- ラベル `architecture`, `tech-debt` → `category=arch`
- ラベル `feature`, `enhancement` → `category=spec`
- ラベル `ops`, `deployment` → `category=ops`
- ラベル `documentation`, `onboarding` → `category=rule`
- タイトルのキーワードマッチング

**ターゲットファイル判定**:
- ベースディレクトリ: `scope=global` → `docs/{category}/`, `scope={service}` → `{service}/docs/{category}/`
- 既存ドキュメントとの類似度計算
- 類似度 > 0.6 → 既存ドキュメントに追記
- 類似度 < 0.6 → 新規ドキュメント作成

#### **生成されるセクション構造**

```markdown
## Issue #{number}: {title}

**ステータス**: ✅ 完了
**完了日**: {closedAt}
**担当者**: {assignees}
**関連PR**: #{pr_number}

---

### 📋 概要

{dev-reports/design-policy.md から抽出}

### 🎯 ユーザーストーリー

{Issue本文から抽出}

### ✅ 受入基準

{Issue本文から抽出}

### 🏗️ アーキテクチャ

{dev-reports/design-policy.md から抽出}

### 🔧 実装詳細

{dev-reports/work-plan.md から抽出}

### 🧪 テスト結果

{dev-reports/final-report.md から抽出}

### 📦 関連子Issue（親Issueの場合）

- ✅ [Issue #{child_num}](../../issues/{child_num}): {child_title}
- ...

---

_最終更新: {datetime.now()} by /doc-register_
```

#### **詳細仕様**

→ [スラッシュコマンド一覧](./02-slash-commands.md) の `/doc-register` セクション
→ [完全版設計方針書](../../workspace/wiki-command-policy-v2.md)

---

## 📋 ドキュメントテンプレート

### **1. design-policy.md**

```markdown
# 設計方針: {機能名}

**作成日**: YYYY-MM-DD
**ブランチ**: {branch_name}
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求
- [ユーザーの要求を記載]

### 機能要件
- [機能要件を箇条書き]

### 非機能要件
- パフォーマンス: [目標値]
- セキュリティ: [要件]
- 可用性: [目標値]

---

## 🏗️ アーキテクチャ設計

### システム構成
[アーキテクチャ図・説明]

### 技術選定
| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| フレームワーク | FastAPI | 非同期処理・高速性能 |
| データベース | PostgreSQL | トランザクション制御 |

### ディレクトリ構成
```
project/
├── app/
│   ├── api/       # APIエンドポイント
│   ├── core/      # ビジネスロジック
│   └── models/    # データモデル
└── tests/
```

---

## ✅ 制約条件チェック結果
[上記のチェックリスト形式で記載]

---

## 📝 設計上の決定事項
1. [決定事項1]
2. [決定事項2]
```

### **2. work-plan.md**

```markdown
# 作業計画: {機能名}

**作成日**: YYYY-MM-DD
**予定工数**: X人日
**完了予定**: YYYY-MM-DD

---

## 📚 参考ドキュメント

**必須参照** (該当する場合):
- [ ] [新プロジェクトセットアップ手順書](../../docs/procedures/NEW_PROJECT_SETUP.md)
- [ ] [GraphAI ワークフロー生成ルール](../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)

**推奨参照**:
- [ ] [アーキテクチャ概要](../../docs/design/architecture-overview.md)
- [ ] [環境変数管理](../../docs/design/environment-variables.md)
- [ ] [myVault連携](../../docs/design/myvault-integration.md)

---

## 📊 Phase分解

**注**: Phase数はプロジェクト規模に応じて調整可能

### Phase 1: 基盤実装 (X日)
- [ ] データベーススキーマ設計
- [ ] モデル実装
- [ ] 単体テスト作成

### Phase 2: API実装 (X日)
- [ ] エンドポイント実装
- [ ] バリデーション実装
- [ ] 結合テスト作成

### Phase 3: 品質担保 (X日)
- [ ] カバレッジ確認
- [ ] パフォーマンステスト
- [ ] ドキュメント作成

---

## ✅ 制約条件チェック結果
[チェックリスト]

---

## 📅 スケジュール
| Phase | 開始予定 | 完了予定 | 状態 |
|-------|---------|---------|------|
| Phase 1 | MM/DD | MM/DD | 予定 |
| Phase 2 | MM/DD | MM/DD | 予定 |
| Phase 3 | MM/DD | MM/DD | 予定 |
```

### **3. phase-{N}-progress.md**

```markdown
# Phase {N} 作業状況: {機能名}

**Phase名**: {Phase名}
**作業日**: YYYY-MM-DD
**所要時間**: X時間

---

## 📝 実装内容
[実装した内容を詳細に記載]

---

## 🐛 発生した課題
| 課題 | 原因 | 解決策 | 状態 |
|------|------|-------|------|
| [課題1] | [原因] | [解決策] | 解決済 |

---

## 💡 技術的決定事項
1. [決定事項1]
2. [決定事項2]

---

## ✅ 制約条件チェック結果
[チェックリスト]

---

## 📊 進捗状況
- Phase {N} タスク完了率: XX%
- 全体進捗: XX%
```

### **4. final-report.md**

```markdown
# 最終作業報告: {機能名}

**完了日**: YYYY-MM-DD
**総工数**: X人日
**ブランチ**: {branch_name}
**PR**: #XXX

---

## ✅ 納品物一覧
- [ ] ソースコード ({project_name}/app/)
- [ ] 単体テスト (tests/unit/)
- [ ] 結合テスト (tests/integration/)
- [ ] ドキュメント (./dev-reports/)　＊リポジトリのルートディレクトリ直下

---

## 📊 品質指標
| 指標 | 目標 | 実績 | 判定 |
|------|------|------|------|
| 単体テストカバレッジ | 90%以上 | XX% | ✅/❌ |
| 結合テストカバレッジ | 50%以上 | XX% | ✅/❌ |
| Ruff linting | エラーゼロ | XX件 | ✅/❌ |
| MyPy type checking | エラーゼロ | XX件 | ✅/❌ |

---

## 🎯 目標達成度
- [x] 機能要件: すべて実装完了
- [x] 非機能要件: パフォーマンス目標達成
- [x] 品質担保: カバレッジ目標達成

---

## ✅ 制約条件チェック結果 (最終)
[最終チェックリスト]

---

## 📚 参考資料
- [参考にしたドキュメント・記事]
```

## 🚀 運用フロー

### **実装開始時**
```bash
# 1. ブランチ作成
git checkout -b feature/issue/104

# 2. ドキュメントディレクトリ作成
mkdir -p ./dev-reports/feature/issue/104

# 3. 設計方針ドキュメント作成
# → design-policy.md を作成し、制約条件チェック実施

# 4. ユーザー承認後、作業計画ドキュメント作成
# → work-plan.md を作成し、制約条件チェック実施
```

### **Phase作業時**
```bash
# 各Phase完了時
# → phase-{N}-progress.md を作成し、制約条件チェック実施
```

### **作業完了時**
```bash
# 全作業完了後
# → final-report.md を作成し、制約条件チェック実施
# → PR作成時にdev-reports/をコミットに含める
```

## 💡 メリット

### **トレーサビリティ向上**
- ✅ ブランチ階層構造で作業履歴を管理
- ✅ 設計判断の根拠を追跡可能
- ✅ Phase毎の進捗を可視化

### **品質担保の強化**
- ✅ 各工程で制約条件チェックを強制
- ✅ 違反の早期発見・早期対応
- ✅ 制約条件変更の透明性確保

### **レビュー性の向上**
- ✅ レビュアーが設計意図を理解しやすい
- ✅ Phase毎の作業内容が明確
- ✅ 最終報告で品質指標を確認可能

### **ナレッジ共有**
- ✅ チーム全体で作業パターンを共有
- ✅ 過去の判断事例を参照可能
- ✅ AI学習による品質向上

---

[← CI/CDエラー防止](./06-ci-cd-prevention.md) | [CLAUDE.md](../../CLAUDE.md)