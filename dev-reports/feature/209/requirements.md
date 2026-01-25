# 要件定義書: Issue #209 - 開発プロセス改善

**Issue番号**: #209
**タイトル**: 開発プロセス改善
**作成日**: 2025-12-02
**ステータス**: 要件定義

---

## 1. ユーザーストーリー

### US-1: CIテストと受入テストの分離
```
As a 開発者
I want to CIで実行されるテストと受入テストを分離したい
So that CI環境の制約に縛られず、より包括的な受入テストを実施できる
```

### US-2: ローカル受入テスト環境
```
As a 開発者
I want to 受入テストをローカル環境で実施し、変更していないレイヤーはコンテナで実行したい
So that APIキーなど実環境依存の設定をセキュアに管理しながら効率的にテストできる
```

### US-3: 単一レイヤー改修の徹底
```
As a プロジェクトリーダー
I want to 1つのIssueでレイヤーを跨いだ改修を禁止したい
So that 改修内容の複雑化を防ぎ、レビューと品質管理を容易にする
```

---

## 2. 受入条件（Acceptance Criteria）

### AC-1: CIテストと受入テストの分離

#### AC-1.1: テスト分類の明確化
```gherkin
Given テストファイルが存在する
When  テストを分類する
Then  以下のディレクトリ構造で分離される:
      【Python プロジェクト（expertAgent, jobqueue, myscheduler, myVault）】
      - {project}/tests/unit/     → CI実行対象（プロジェクト内）
      - tests/integration/python/ → CI実行対象（リポジトリ直下）
      - tests/acceptance/python/  → ローカル実行のみ（リポジトリ直下）

      【TypeScript/SvelteKit プロジェクト（myAgentDesk, graphAiServer）】
      - {project}/src/**/*.test.ts    → CI実行対象（プロジェクト内）
      - tests/integration/typescript/ → CI実行対象（リポジトリ直下）
      - tests/acceptance/typescript/  → ローカル実行のみ（リポジトリ直下）
```

#### AC-1.2: CIワークフローの更新
```gherkin
Given CI設定ファイル (.github/workflows/ci-feature.yml) が存在する
When  CIが実行される
Then  tests/acceptance/ ディレクトリは実行対象から除外される
And   各プロジェクト内の単体テストが実行される
And   tests/integration/ 配下の結合テストが実行される
```

#### AC-1.3: 受入テスト実行スクリプト
```gherkin
Given 受入テストスクリプトが存在する
When  開発者が `./scripts/run-acceptance-tests.sh` を実行する
Then  対象レイヤーの受入テストが実行される
And   必要なコンテナが自動起動される
And   テスト結果がレポートとして出力される
```

### AC-2: ローカル受入テスト環境

#### AC-2.1: レイヤー別コンテナ起動
```gherkin
Given 開発者が特定のレイヤー（例: expertAgent）を改修中である
When  受入テストを実行する
Then  改修中のレイヤーはローカルプロセスで起動される
And   依存する下位レイヤー（myVault, jobqueue等）はDockerコンテナで起動される
```

#### AC-2.2: 環境変数管理
```gherkin
Given ローカルに .env ファイルが存在する
When  受入テスト環境を起動する
Then  APIキーは .env から読み込まれる
And   シークレット情報はCIログに出力されない
And   .env.example でテンプレートが提供される
```

#### AC-2.3: Makeコマンド統合
```gherkin
Given Makefileが存在する
When  開発者が `make acceptance-test-{layer}` を実行する
Then  対象レイヤーの受入テスト環境が構築される
And   依存コンテナが自動起動される
And   テストが実行される
```

### AC-3: 単一レイヤー改修ルールの強制

#### AC-3.1: Issue作成ガイドライン
```gherkin
Given 新しいIssueが作成される
When  Issueのスコープを定義する
Then  以下のレイヤー区分のいずれか1つのみを対象とする:
      - Platform層: valkey, jobqueue, myscheduler, myvault, langfuse
      - Agent層: expertAgent, graphAiServer
      - Frontend層: commonUI, myAgentDesk
      - Docs層: ドキュメントのみ
```

#### AC-3.2: PRラベル検証
```gherkin
Given PRが作成される
When  変更ファイルを検出する
Then  複数レイヤーにまたがる変更がある場合は警告を表示する
And   PRレビュー時に「cross-layer」フラグが付与される
```

#### AC-3.3: 開発ワークフロードキュメント更新
```gherkin
Given 開発ワークフロードキュメントが存在する
When  Issue分割ガイドを参照する
Then  単一レイヤー改修ルールが明記されている
And   レイヤー跨ぎが必要な場合の例外手順が記載されている
```

---

## 3. 機能要件

### 3.1 必須機能（Must Have）

| ID | 機能 | 説明 | 優先度 |
|----|------|------|--------|
| F-001 | テストディレクトリ分離 | `tests/acceptance/` ディレクトリ新設 | 高 |
| F-002 | CI除外設定 | 受入テストをCIから除外 | 高 |
| F-003 | 受入テストスクリプト | レイヤー別受入テスト実行スクリプト | 高 |
| F-004 | Make統合 | `make acceptance-test-{layer}` コマンド | 高 |
| F-005 | ドキュメント更新 | 開発ワークフロー・Issue分割ガイド更新 | 高 |
| F-005a | tests/README.md作成 | テスト実行場所・方法のクイックリファレンス | 高 |

### 3.2 あると良い機能（Nice to Have）

| ID | 機能 | 説明 | 優先度 |
|----|------|------|--------|
| F-006 | PR自動チェック | 複数レイヤー変更の自動検出・警告 | 中 |
| F-007 | レポート出力 | 受入テスト結果のMarkdownレポート生成 | 中 |
| F-008 | 並列実行 | 複数レイヤーの受入テスト並列実行 | 低 |

### 3.3 将来的な拡張（Future Enhancement）

| ID | 機能 | 説明 |
|----|------|------|
| F-009 | 自動Issue分割提案 | AIによるIssueスコープ分析・分割提案 |
| F-010 | E2Eテスト統合 | 全レイヤー統合のE2Eテストフレームワーク |

---

## 4. 非機能要件

### 4.1 パフォーマンス要件

| 項目 | 要件 | 測定方法 |
|------|------|----------|
| 受入テスト環境起動時間 | 3分以内 | `time make acceptance-test-{layer}` |
| 依存コンテナ起動時間 | 2分以内 | ヘルスチェック完了までの時間 |
| テスト実行時間 | レイヤー単位で10分以内 | pytest実行時間 |

### 4.2 セキュリティ要件

| 項目 | 要件 |
|------|------|
| シークレット管理 | APIキーは`.env`でローカル管理、CIログに出力禁止 |
| 環境分離 | 受入テスト環境は本番環境と完全分離 |
| アクセス制御 | myVaultによるシークレット一元管理継続 |

### 4.3 ユーザビリティ要件

| 項目 | 要件 |
|------|------|
| ドキュメント | 新規開発者が30分以内に受入テスト実行可能 |
| エラーメッセージ | 失敗時に原因と対処法を明示 |
| コマンド体系 | 既存の`make dev-{layer}`と一貫したコマンド名 |

### 4.4 互換性要件

| 項目 | 要件 |
|------|------|
| 既存CI | 現行CIワークフローへの影響最小化 |
| 既存テスト | 現行テストの移行パスを提供 |
| Worktree対応 | 既存worktree環境での動作保証 |

---

## 5. 技術的制約

### 5.1 使用する技術スタック

#### Python プロジェクト（expertAgent, jobqueue, myscheduler, myVault）

| カテゴリ | 技術 | バージョン | 用途 |
|----------|------|----------|------|
| テストフレームワーク | pytest | 7.x+ | 単体・結合・受入テスト |
| HTTPクライアント | httpx | 0.25+ | API結合テスト |
| モック | pytest-mock | 3.x+ | 単体テスト |
| カバレッジ | pytest-cov | 4.x+ | カバレッジ測定 |

#### TypeScript/SvelteKit プロジェクト（myAgentDesk, graphAiServer）

| カテゴリ | 技術 | バージョン | 用途 |
|----------|------|----------|------|
| テストフレームワーク | Vitest | 1.x+ | 単体・結合テスト |
| E2Eテスト | Playwright | 1.40+ | 受入テスト |
| コンポーネントテスト | @testing-library/svelte | 4.x+ | UIコンポーネントテスト |

#### 共通インフラ

| カテゴリ | 技術 | バージョン |
|----------|------|----------|
| コンテナ | Docker Compose | v2.20+ |
| ビルドツール | GNU Make | 3.81+ |
| CI/CD | GitHub Actions | N/A |
| シェル | Bash | 4.0+ |

### 5.2 既存システムとの連携

| システム | 連携方法 |
|----------|----------|
| `scripts/unified-start.sh` | 受入テストスクリプトから呼び出し |
| `docker-compose.{layer}.yml` | レイヤー別コンテナ起動に使用 |
| `Makefile` | 新規ターゲット追加 |
| `.github/workflows/ci-feature.yml` | 除外パス追加 |
| `CLAUDE.md` | 開発プロセス変更の反映 |
| `docs/claude/*.md` | ガイドライン更新 |

### 5.3 ディレクトリ構造（変更後）

```
MySwiftAgent/
│
├── 【Pythonプロジェクト - 単体テストはプロジェクト内】
├── expertAgent/
│   └── tests/
│       └── unit/               # 単体テスト（CI実行対象）
├── jobqueue/
│   └── tests/
│       └── unit/               # 単体テスト（CI実行対象）
├── myscheduler/
│   └── tests/
│       └── unit/               # 単体テスト（CI実行対象）
├── myVault/
│   └── tests/
│       └── unit/               # 単体テスト（CI実行対象）
│
├── 【TypeScript/SvelteKitプロジェクト - 単体テストはプロジェクト内】
├── myAgentDesk/
│   └── src/
│       └── **/*.test.ts        # 単体テスト（CI実行対象）
├── graphAiServer/
│   └── src/
│       └── **/*.test.ts        # 単体テスト（CI実行対象）
│
├── 【リポジトリ直下 - 結合・受入テスト】
├── tests/                       # 🆕 リポジトリ直下に集約
│   ├── integration/             # 結合テスト（CI実行対象）
│   │   ├── python/              # Python結合テスト
│   │   │   ├── conftest.py
│   │   │   ├── platform/        # Platform層結合テスト
│   │   │   ├── agent/           # Agent層結合テスト
│   │   │   └── cross_layer/     # レイヤー間結合テスト
│   │   └── typescript/          # TypeScript結合テスト
│   │       ├── vitest.config.ts
│   │       └── **/*.test.ts
│   │
│   └── acceptance/              # 🆕 受入テスト（ローカル実行のみ）
│       ├── python/              # Python受入テスト
│       │   ├── conftest.py
│       │   ├── platform/        # Platform層受入テスト
│       │   ├── agent/           # Agent層受入テスト
│       │   └── e2e/             # E2Eシナリオテスト
│       └── typescript/          # TypeScript受入テスト（Playwright）
│           ├── playwright.config.ts
│           └── **/*.spec.ts
│
├── 【設定・スクリプト】
├── scripts/
│   ├── unified-start.sh         # 既存
│   └── run-acceptance-tests.sh  # 🆕 受入テスト実行スクリプト
├── Makefile                     # 既存（ターゲット追加）
│
├── 【ドキュメント - 更新対象】
├── CLAUDE.md                    # 🔄 開発プロセス変更反映
├── docs/
│   └── claude/
│       ├── 01-development-workflow.md  # 🔄 ワークフロー更新
│       ├── 04-quality-standards.md     # 🔄 テスト方針更新
│       └── 08-issue-split.md           # 🔄 レイヤールール明記
│
└── .github/workflows/
    └── ci-feature.yml           # 既存（除外パス追加）
```

---

## 6. リスクと対策

### 6.1 技術的リスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|---------|--------|------|
| 受入テストの実行漏れ | 中 | 高 | PRテンプレートにチェックリスト追加 |
| コンテナ起動失敗 | 低 | 中 | ヘルスチェック・リトライ機構 |
| 環境差異によるテスト失敗 | 中 | 中 | `.env.example`と詳細セットアップガイド |

### 6.2 ビジネスリスク

| リスク | 発生確率 | 影響度 | 対策 |
|--------|---------|--------|------|
| 開発プロセス変更への抵抗 | 中 | 中 | 段階的導入、ドキュメント充実 |
| 単一レイヤールール違反 | 高 | 低 | 自動チェック・警告の導入 |
| 受入テスト品質のばらつき | 中 | 中 | テストテンプレート・ガイドライン提供 |

### 6.3 対策の優先順位

1. **ドキュメント整備** - 開発ワークフロー更新、ガイドライン明文化
2. **スクリプト開発** - 受入テスト実行スクリプト
3. **CI更新** - 除外設定、警告機能
4. **監視強化** - PR自動チェック（Nice to Have）

---

## 7. Issue分割案

本Feature (#209) は以下のIssueに分割することを推奨:

### Phase 1: ディレクトリ構造・基盤整備

| Issue | タイトル | サイズ | 依存 | 対象 |
|-------|---------|--------|------|------|
| #209-1 | Python結合テストのリポジトリ直下移行 | S | なし | tests/integration/python/ |
| #209-2 | TypeScript結合テストのリポジトリ直下移行 | S | なし | tests/integration/typescript/ |
| #209-3 | 受入テストディレクトリ構造作成 | S | #209-1,2 | tests/acceptance/ |

### Phase 2: CI/テスト実行環境

| Issue | タイトル | サイズ | 依存 | 対象 |
|-------|---------|--------|------|------|
| #209-4 | CI除外設定の追加 | S | #209-3 | .github/workflows/ |
| #209-5 | Python受入テスト実行スクリプト作成 | M | #209-3 | scripts/, Makefile |
| #209-6 | Playwright受入テスト環境構築 | M | #209-3 | tests/acceptance/typescript/ |

### Phase 3: ドキュメント・ガイドライン

| Issue | タイトル | サイズ | 依存 | 対象 |
|-------|---------|--------|------|------|
| #209-7 | CLAUDE.md 開発プロセス更新 | S | #209-4,5,6 | CLAUDE.md |
| #209-8 | 品質基準ドキュメント更新 | S | #209-7 | docs/claude/04-quality-standards.md |
| #209-9 | 開発ワークフロードキュメント更新 | S | #209-7 | docs/claude/01-development-workflow.md |
| #209-10 | Issue分割ガイド更新（レイヤールール） | S | #209-7 | docs/claude/08-issue-split.md |

### Phase 4: 自動化・運用（Optional）

| Issue | タイトル | サイズ | 依存 | 対象 |
|-------|---------|--------|------|------|
| #209-11 | PR自動チェック機能 | M | #209-10 | .github/workflows/ |
| #209-12 | PRテンプレート更新 | S | #209-10 | .github/PULL_REQUEST_TEMPLATE.md |

---

## 8. PO受入テスト方針（ハイブリッド方式）

### 8.1 テスト階層と実施者

```
┌─────────────────────────────────────────────────────────────────┐
│                    テスト階層構造                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐                                          │
│  │ Level 1: CI自動  │  単体テスト + 結合テスト                  │
│  │ (GitHub Actions) │  → 全PR必須、自動実行                     │
│  └────────┬─────────┘                                          │
│           │                                                     │
│  ┌────────▼─────────┐                                          │
│  │ Level 2: 開発者  │  受入テスト（ローカル実行）               │
│  │ 受入テスト       │  → 全PR必須、開発者が手動実行             │
│  └────────┬─────────┘                                          │
│           │                                                     │
│  ┌────────▼─────────┐                                          │
│  │ Level 3: PO      │  重要Issueの受入テスト                    │
│  │ 受入テスト       │  → 条件付き、POが手動実行                 │
│  └────────┬─────────┘                                          │
│           │                                                     │
│  ┌────────▼─────────┐                                          │
│  │ Level 4: PO      │  Feature統合受入テスト                    │
│  │ 最終受入テスト   │  → Feature完了時必須、POが手動実行        │
│  └──────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Issue種別ごとのテストフロー

#### 通常Issue（Standard）
```
開発 → CI自動テスト → 開発者受入テスト → マージ
```
- **対象**: 軽微な修正、内部リファクタリング、ドキュメント更新
- **PO関与**: 不要（開発者判断でマージ可能）

#### 重要Issue（Critical）
```
開発 → CI自動テスト → 開発者受入テスト → PO受入テスト → マージ
```
- **対象**: 以下のいずれかに該当するIssue
  - ユーザー向け機能の新規追加
  - 既存機能の動作変更
  - セキュリティ関連の変更
  - 外部API連携の変更
- **PO関与**: マージ前に必須

#### Feature完了時
```
全Issue マージ完了 → 統合動作確認 → PO最終受入テスト → リリース判定
```
- **対象**: Feature（親Issue）の全子Issueがマージ完了した時点
- **PO関与**: 必須（リリース可否の最終判断）

### 8.3 PO受入テストの実施方法

#### 実施環境
| 環境 | 用途 | 構築方法 |
|------|------|----------|
| **ローカル環境** | 重要Issue受入テスト | `make acceptance-test-{layer}` |
| **Staging環境** | Feature統合受入テスト | `docker compose up -d` (staging) |

#### 実施手順

**Step 1: 環境準備**
```bash
# 重要Issue受入テスト時
cd ~/MySwiftAgent
make acceptance-test-{layer}

# Feature統合受入テスト時
docker compose -f docker-compose.staging.yml up -d
```

**Step 2: テストシナリオ実行**
- Issueの「👤 手動検証が必要な基準」を順次確認
- 操作ログ・スクリーンショットを記録（任意）

**Step 3: 結果記録**
```markdown
## PO受入テスト結果

**Issue**: #XXX
**テスト日**: YYYY-MM-DD
**テスト者**: @PO名

### 確認結果
- [x] UX/UI検証: OK
- [x] ビジネスロジック検証: OK
- [ ] 運用検証: NG（ログ出力不足）

### 指摘事項
1. エラーログにスタックトレースが含まれていない

### 判定
- [ ] 承認（マージ可）
- [x] 要修正（再テスト必要）
```

**Step 4: GitHub Issue/PRへのコメント**
- 承認時: `LGTM` + 承認コメント
- 要修正時: 指摘事項を記載、`changes requested`

### 8.4 重要Issue判定基準

以下のラベルまたは条件でPO受入テスト必須を判定:

| 判定条件 | 自動検出方法 |
|----------|-------------|
| `critical` ラベル付与 | PRラベルチェック |
| `user-facing` ラベル付与 | PRラベルチェック |
| Frontend層の変更を含む | 変更ファイルパス検出 |
| API仕様変更を含む | OpenAPI Spec差分検出 |
| セキュリティ関連ファイル変更 | 特定パス検出（auth/, security/） |

### 8.5 PO受入テストのスキップ条件

以下の場合、PO受入テストをスキップ可能:

- `docs-only` ラベル（ドキュメントのみの変更）
- `internal` ラベル（内部リファクタリング）
- `test-only` ラベル（テストコードのみの変更）
- `ci-fix` ラベル（CI/CD設定の修正）

### 8.6 PRテンプレートへの追加項目

```markdown
## テスト確認

### 自動テスト
- [ ] CI（単体・結合テスト）がパスしている

### 開発者受入テスト
- [ ] ローカルで受入テストを実行した
- [ ] 手動検証項目を全て確認した

### PO受入テスト（該当する場合）
- [ ] このPRはPO受入テストが必要（重要Issue）
- [ ] PO受入テスト完了: @PO名 YYYY-MM-DD
```

---

## 9. 用語集

| 用語 | 定義 |
|------|------|
| CIテスト | GitHub Actionsで自動実行されるテスト（単体・結合） |
| 開発者受入テスト | 開発者がローカル環境で手動実行するテスト（E2E的な検証） |
| PO受入テスト | POがユーザー視点で実施する手動検証（UX/ビジネスロジック確認） |
| 重要Issue | PO受入テストが必須となるIssue（user-facing, critical等） |
| レイヤー | サービスの論理的なグループ（Platform/Agent/Frontend） |
| 単一レイヤー改修 | 1つのIssueで1つのレイヤーのみを変更するルール |

---

## 10. 参照ドキュメント

- [受入テスト効率化機能](../../../docs/spec/acceptance-testing.md)
- [品質基準](../../../docs/claude/04-quality-standards.md)
- [開発ワークフロー](../../../docs/claude/01-development-workflow.md)
- [Issue分割ガイド](../../../docs/claude/08-issue-split.md)
- [レイヤ別docker-compose](../../../README.md#レイヤ別docker-compose)

---

## 11. 承認

| 役割 | 承認者 | 日付 | ステータス |
|------|--------|------|----------|
| プロダクトオーナー | - | - | 待機中 |
| テックリード | - | - | 待機中 |

---

**作成者**: Claude Code
**レビュー待ち**: Yes
