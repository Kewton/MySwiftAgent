# 設計方針: ブランチ同期とガードレール設定

**作成日**: 2025-10-29
**ブランチ**: feature/branch-sync-and-guardrails
**担当**: Claude Code

---

## 📋 要求・要件

### ビジネス要求
- mainブランチを正（Source of Truth）として、staging/developブランチを同期させる
- CLAUDE.mdに記載のある標準マージフローを徹底し、直push/直マージを防止する
- 本番環境（main）の品質を担保するガードレールを設置する

### 機能要件

#### FR-1: ブランチ同期
- **FR-1.1**: stagingブランチがmainブランチと完全同期していることを確認
- **FR-1.2**: developブランチをmainブランチにfast-forwardマージで同期
- **FR-1.3**: 同期後、全ブランチ（main/staging/develop）が同一コミットを指す

#### FR-2: GitHub Branch Protection Rules設定
- **FR-2.1**: mainブランチへの直push禁止
- **FR-2.2**: stagingブランチへの直push禁止
- **FR-2.3**: release/*ブランチへの直push禁止
- **FR-2.4**: mainブランチへのPRマージ時、CI/CD品質チェック必須
- **FR-2.5**: mainブランチへのPRマージ時、1名以上のレビュー承認必須

#### FR-3: 標準マージフロー徹底
- **FR-3.1**: 全マージをPR経由に強制（CLAUDE.md L60-61準拠）
- **FR-3.2**: 例外対応時のチーム責任者承認フロー（CLAUDE.md L92-94準拠）

### 非機能要件

#### NFR-1: 安全性
- **NFR-1.1**: ブランチ同期時のロールバック手順を確保
- **NFR-1.2**: Branch Protection設定のロールバック手順を確保

#### NFR-2: 追跡性
- **NFR-2.1**: 全ブランチ変更をGit履歴で追跡可能
- **NFR-2.2**: Branch Protection設定変更をGitHub Audit Logで追跡可能

#### NFR-3: 一貫性
- **NFR-3.1**: CLAUDE.mdのブランチ戦略に100%準拠
- **NFR-3.2**: 既存の自動リリースワークフロー（auto-release.yml）と整合

---

## 🏗️ アーキテクチャ設計

### システム構成

```
GitHub Repository: Kewton/MySwiftAgent
│
├── Branches
│   ├── main (本番環境) 🔒 Branch Protection ✅
│   ├── staging (UAT) 🔒 Branch Protection ✅
│   ├── develop (開発統合) 🔓 No Protection
│   └── release/* (リリース準備) 🔒 Branch Protection ✅
│
├── GitHub Branch Protection Rules
│   ├── main: Require PR + Require Review (1) + Require CI/CD
│   ├── staging: Require PR
│   └── release/*: Require PR
│
└── GitHub Actions Workflows
    ├── auto-release.yml (自動リリース・タグ作成)
    ├── cd-develop.yml (develop統合時のデプロイ)
    └── ci-feature.yml (feature PR時の品質チェック)
```

### 技術選定

| 技術要素 | 選定技術 | 選定理由 |
|---------|---------|---------|
| **ブランチ保護** | GitHub Branch Protection Rules | GitHub標準機能、API経由で設定可能 |
| **同期戦略** | Git fast-forward merge | 履歴を保持し、コンフリクトフリー |
| **設定管理** | GitHub REST API (`gh` CLI) | コマンドラインで自動化可能 |
| **検証方法** | 実際の直push試行 | 保護設定の動作確認 |

### ディレクトリ構成

```
MySwiftAgent/
├── .github/
│   └── workflows/
│       ├── auto-release.yml (既存: 自動リリース)
│       ├── cd-develop.yml (既存: develop統合)
│       └── ci-feature.yml (既存: feature品質チェック)
├── dev-reports/
│   └── feature/
│       └── branch-sync-and-guardrails/
│           ├── design-policy.md (本ドキュメント)
│           ├── work-plan.md (作業計画)
│           └── phase-{N}-progress.md (各Phase作業記録)
└── CLAUDE.md (ブランチ戦略定義)
```

---

## 🔍 設計判断

### 判断1: developブランチは保護しない

**判断**: developブランチにはBranch Protectionを設定**しない**

**理由**:
1. **開発速度の維持**: 開発者が頻繁にマージするブランチのため、PRレビュー必須にすると開発速度が低下
2. **CLAUDE.md準拠**: CLAUDE.md L44では「develop」を「開発統合用」と定義し、保護対象には含めていない
3. **品質担保**: developからrelease/*への移行時にCI/CDチェックが実行されるため、品質は担保される

**リスク対策**: developからのPR時にci-feature.ymlで品質チェックを実施

### 判断2: mainブランチのみレビュー必須

**判断**: mainブランチへのPRマージ時のみ、1名以上のレビュー承認を必須とする

**理由**:
1. **本番品質担保**: CLAUDE.md L43で「main」は「本番環境のコードベース」と定義
2. **リリースリスク低減**: 本番環境への反映前に人間の目で確認
3. **stagingは除外**: stagingはUAT用のため、レビューなしでも可（迅速なテストサイクル優先）

**運用**: 緊急時（hotfix）は承認プロセスを短縮可能（CLAUDE.md L92-94の例外対応）

### 判断3: release/*の保護範囲

**判断**: release/*ブランチは「Require PR」のみ設定（レビュー・CI/CDは不要）

**理由**:
1. **柔軟性の確保**: リリース準備中の調整を迅速に実施
2. **最終検証はmain**: mainへのマージ時にCI/CD・レビューが実施されるため、二重チェック不要
3. **CLAUDE.md準拠**: L70-73で「release/* → staging → main」のフローを定義（release/*自体の保護は明記されていない）

### 判断4: fast-forwardマージの採用

**判断**: developブランチの同期にfast-forwardマージを採用

**理由**:
1. **履歴の単純性**: マージコミットを作成せず、線形履歴を維持
2. **コンフリクトなし**: developがmainの直系祖先のため、fast-forward可能
3. **ロールバック容易**: `git reset --hard <commit>` で即座に元に戻せる

**制約**: developがmainより進んでいる場合は適用不可（今回は該当なし）

---

## ✅ 制約条件チェック結果

### コード品質原則
- [x] **SOLID原則**: N/A（コード変更なし）
- [x] **KISS原則**: 遵守 / シンプルなGit操作とGitHub API設定
- [x] **YAGNI原則**: 遵守 / 必要最小限の保護設定（developは保護しない）
- [x] **DRY原則**: N/A（コード変更なし）

### アーキテクチャガイドライン
- [x] **architecture-overview.md**: N/A（インフラ設定のみ）
- [x] **CLAUDE.md ブランチ戦略**: 完全準拠（L37-L95）
  - ✅ L43: main = 本番環境のコードベース
  - ✅ L45: staging = UAT・実機確認用
  - ✅ L44: develop = 開発統合用
  - ✅ L60-61: PRを通じて行うことを厳守
  - ✅ L89: 直push禁止
  - ✅ L92-94: 例外対応フロー

### 設定管理ルール
- [x] **環境変数**: N/A
- [x] **myVault**: N/A

### 品質担保方針
- [x] **単体テスト**: N/A（コード変更なし）
- [x] **結合テスト**: N/A（コード変更なし）
- [x] **Ruff linting**: N/A（Markdown変更のみ）
- [x] **MyPy type checking**: N/A

### CI/CD準拠
- [x] **PRラベル**: `ci` ラベル付与予定（インフラ設定）
- [x] **コミットメッセージ**: `ci: setup branch protection and sync branches` を予定
- [x] **pre-push-check-all.sh**: 実行予定（軽量チェック）

### 参照ドキュメント遵守
- [x] **CLAUDE.md**: 完全準拠
  - ✅ L37-L95: ブランチ構成
  - ✅ L96-L132: 標準マージフロー
  - ✅ L87-L90: 禁止事項

### 違反・要検討項目
**なし**

---

## 📝 設計上の決定事項

### 決定事項1: ブランチ同期の方向性

**決定**: mainブランチを正（Source of Truth）として、staging/developを同期

**背景**:
- PR #116でmainブランチに2025.10.29リリースがマージ済み
- stagingは既に同期済み（PR #115, #116の一連の作業で同期）
- developのみ1コミット遅れ（`8fea368`が欠けている）

**代替案**:
- ❌ developを正として他を同期: 却下（本番環境であるmainが優先）
- ❌ 3ブランチを個別管理: 却下（整合性が保てない）

### 決定事項2: Branch Protection設定の範囲

**決定**: main, staging, release/*のみ保護（developは除外）

**理由**:
- main: 本番環境のため最も厳格な保護
- staging: UAT用だが直pushは禁止（PR経由でトレーサビリティ確保）
- release/*: リリース準備中の誤操作を防止
- develop: 開発速度を優先（feature/*からのPRで品質チェック実施済み）

### 決定事項3: 既存ワークフローとの整合性

**決定**: auto-release.yml, cd-develop.yml等の既存ワークフローは変更しない

**理由**:
1. **動作実績**: 既存ワークフローは正常動作中（PR #115, #116で確認済み）
2. **Branch Protection整合**: 既存ワークフローはすべてPR経由でマージするため、新設定と整合
3. **YAGNI原則**: 不要な変更を避ける

**確認事項**:
- ✅ auto-release.yml: mainへのマージ時に自動実行（PR経由）
- ✅ cd-develop.yml: developへのマージ時に自動実行（PR経由）
- ✅ ci-feature.yml: feature PR時に自動実行

### 決定事項4: 検証方法

**決定**: 実際の直push試行で保護設定を検証

**検証手順**:
```bash
# 1. mainへの直push試行（拒否されるはず）
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "test: direct push"
git push origin main
# Expected: Error - branch protected

# 2. stagingへの直push試行（拒否されるはず）
git checkout staging
echo "test" >> test.txt
git add test.txt
git commit -m "test: direct push"
git push origin staging
# Expected: Error - branch protected
```

**成功基準**: 両方のpushが拒否されること

---

## 🚀 期待される効果

### Before（現状）

| 項目 | 状態 | CLAUDE.md準拠 |
|------|------|--------------|
| mainへの直push | ⚠️ 可能 | ❌ L89違反 |
| stagingへの直push | ⚠️ 可能 | ❌ L89違反 |
| develop同期 | ⚠️ -1コミット | ⚠️ 不整合 |
| PRレビュー | ❌ 不要 | ❌ 品質リスク |

### After（実施後）

| 項目 | 状態 | CLAUDE.md準拠 |
|------|------|--------------|
| mainへの直push | ✅ 禁止 | ✅ L89準拠 |
| stagingへの直push | ✅ 禁止 | ✅ L89準拠 |
| develop同期 | ✅ 同期 | ✅ 整合性確保 |
| PRレビュー（main） | ✅ 必須 | ✅ 品質担保 |

---

## 🔒 セキュリティ・リスク対策

### リスク1: 誤った保護設定でブロッキング

**リスク内容**: Branch Protection設定ミスで正常なワークフローがブロックされる

**対策**:
- Phase 3実施前に設定内容をダブルチェック
- 設定後、即座に検証（Phase 4）
- ロールバック手順を確保（work-plan.md記載）

**影響度**: 中（開発ブロッキング）
**発生確率**: 低（GitHub API標準設定を使用）

### リスク2: developブランチの同期失敗

**リスク内容**: fast-forwardマージ失敗（developがmainより進んでいる場合）

**対策**:
- 事前確認: `git log develop..main` で差分確認済み（1コミットのみ）
- fast-forward専用オプション: `--ff-only` で安全性確保
- ロールバック手順: `git reset --hard 5201e4b` で即座に復旧

**影響度**: 低（即座にロールバック可能）
**発生確率**: 極低（事前確認済み）

### リスク3: 既存ワークフローへの影響

**リスク内容**: Branch Protection設定が既存ワークフローをブロック

**対策**:
- 既存ワークフローはすべてPR経由のため影響なし（事前確認済み）
- Phase 4で全ワークフローの動作確認を実施

**影響度**: 中（CI/CD停止）
**発生確率**: 極低（PR経由ワークフローのみ使用中）

---

## 📊 成功指標

### 定量指標

| 指標 | 目標値 | 測定方法 |
|------|-------|---------|
| develop同期率 | 100% | `git log develop..main` の結果が空 |
| Branch Protection設定成功率 | 100% | `gh api` コマンドの成功 |
| 直push拒否率 | 100% | 実際のpush試行で拒否 |

### 定性指標

- ✅ CLAUDE.mdブランチ戦略への完全準拠
- ✅ 開発ワークフローへの影響ゼロ
- ✅ ロールバック手順の確保

---

## 📚 参考資料

### GitHub公式ドキュメント
- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [GitHub REST API - Branch Protection](https://docs.github.com/en/rest/branches/branch-protection)

### プロジェクト内部ドキュメント
- [CLAUDE.md - ブランチ構成](../../CLAUDE.md#L37-L95)
- [CLAUDE.md - 標準マージフロー](../../CLAUDE.md#L96-L132)
- [auto-release.yml](./.github/workflows/auto-release.yml)

---

**設計承認待ち**

この設計方針に基づき、work-plan.mdの実行計画を進めてよろしいでしょうか？
