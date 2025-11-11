# PR作成スキル

## 概要
ユーザーの動作確認後、Pull Request作成を自動実行するスキルです。Issue情報から自動でタイトル・説明を生成し、高品質なPRを作成します。

## 使用方法
- `/pm-create-pr`（Issue番号は自動検出）
- `/pm-create-pr [Issue番号]`（明示的に指定）
- `/pm-create-pr --draft`（Draft PRとして作成）
- 「PRを作成してください」
- 「Pull Requestを作成してください」

## 実行内容

あなたはPR作成の専門家として、高品質なPull Requestを自動生成します。

### 📋 パラメータ

- **issue_number**: Issue番号（省略時は現在のブランチから自動検出）
- **base_branch**: マージ先ブランチ（デフォルト: develop）
- **draft**: Draft PRとして作成（デフォルト: false）
- **auto_assign**: 自分を自動アサイン（デフォルト: true）

---

## 🔄 実行フェーズ

### Phase 1: ブランチとIssue情報の取得

#### 1-1. base_branchの初期化

まず、マージ先ブランチを設定します：

```bash
# パラメータで指定されていない場合、developをデフォルトとする
base_branch="${base_branch:-develop}"
```

**重要**: このプロジェクトのブランチ戦略では、`feature/*`, `fix/*`, `vibe/*` ブランチは **必ず `develop` ブランチにマージ** します。`main` ブランチへの直接マージは禁止されています。

詳細: [docs/claude/03-branch-strategy.md](../../docs/claude/03-branch-strategy.md)

#### 1-2. 現在のブランチ確認

```bash
git branch --show-current
```

期待されるブランチ名: `feature/issue/{issue_number}`

#### 1-3. Issue番号の検出

パラメータで`issue_number`が指定されていない場合、ブランチ名から抽出：

- `feature/issue/145` → Issue #145
- `fix/issue/127` → Issue #127
- `hotfix/issue/89` → Issue #89

ブランチ名から検出できない場合はエラー：
```
❌ エラー: Issue番号を検出できませんでした。

現在のブランチ: {branch_name}

以下のいずれかを実施してください:
1. パラメータで明示的に指定: /pm-create-pr 145
2. feature/issue/[番号] 形式のブランチに切り替え
```

#### 1-3. Issue情報取得

```bash
gh issue view {issue_number} --json title,body,labels,assignees
```

取得する情報:
- タイトル
- 本文（受入条件含む）
- ラベル
- アサインされている人

#### 1-4. 進捗報告の確認

```bash
cat dev-reports/feature/issue/{issue_number}/progress-report.md
```

ファイルが存在しない場合は警告：
```
⚠️ 警告: 進捗報告が見つかりません。

/pm-auto-dev {issue_number} を実行してから PR作成してください。
```

---

### Phase 2: PR作成前の最終チェック

#### 2-1. ブランチの最新性確認

```bash
# base_branchが未設定の場合、developをデフォルトとする
base_branch="${base_branch:-develop}"

git fetch origin "${base_branch}"
git merge-base --is-ancestor origin/"${base_branch}" HEAD
```

最新でない場合は警告：
```
⚠️ 警告: 現在のブランチが${base_branch}の最新から分岐していません。

推奨アクション:
1. ${base_branch}ブランチの最新を取り込む:
   git fetch origin ${base_branch}
   git rebase origin/${base_branch}

2. コンフリクト解決後に再度 /pm-create-pr を実行
```

#### 2-2. 未コミットの変更確認

```bash
git status --porcelain
```

未コミットの変更がある場合はエラー：
```
❌ エラー: 未コミットの変更があります。

変更ファイル:
{files}

以下を実施してください:
1. 変更をコミット
2. 再度 /pm-create-pr を実行
```

#### 2-3. 全チェックスクリプト実行

```bash
./scripts/pre-push-check-all.sh
```

**重要**: このチェックが失敗した場合はPR作成を中止：
```
❌ エラー: pre-push-checkが失敗しました。

失敗内容:
{error_log}

PR作成を中止しました。以下を実施してください:
1. エラーを修正
2. /pm-auto-dev {issue_number} --mode=fix で是正
3. 修正後に再度 /pm-create-pr を実行
```

---

### Phase 3: PRタイトルの生成

#### 3-1. ラベルからプレフィックス判定

| Issue Label | PR Prefix |
|-------------|-----------|
| feature | feat |
| bugfix, bug | fix |
| hotfix | hotfix |
| refactor | refactor |
| docs | docs |
| test | test |
| chore | chore |
| vibe | vibe |

複数ラベルがある場合は最初のラベルを使用。

#### 3-2. プロジェクト名判定

変更ファイルから主要プロジェクトを判定：

```bash
# base_branchが未設定の場合、developをデフォルトとする
base_branch="${base_branch:-develop}"

git diff --name-status origin/"${base_branch}"...HEAD
```

判定ルール:
- `expertAgent/` の変更が多い → expertAgent
- `myVault/` の変更が多い → myVault
- `myAgentDesk/` の変更が多い → myAgentDesk
- `myscheduler/` の変更が多い → myscheduler
- `jobqueue/` の変更が多い → jobqueue
- `graphAiServer/` の変更が多い → graphAiServer
- `scripts/` の変更が多い → scripts
- `docs/` のみ変更 → docs
- 複数プロジェクトにまたがる → multi

#### 3-3. タイトル生成

**形式**: `[prefix](project): [簡潔な説明]`

**例**:
- `feat(scripts): 複数Worktree並列起動サポート`
- `fix(expertAgent): ジョブタスク生成のエラーハンドリング修正`
- `refactor(myVault): シークレット暗号化処理の改善`

**ルール**:
- 50文字以内
- 命令形（"Add" not "Added"）
- Issueタイトルから冗長な部分を削除（[#140-5]等）

---

### Phase 4: PR説明の生成

#### 4-1. 変更内容の分析

```bash
# base_branchが未設定の場合、developをデフォルトとする
base_branch="${base_branch:-develop}"

# 変更ファイル一覧
git diff --name-status origin/"${base_branch}"...HEAD

# ファイルごとの追加/削除行数
git diff --stat origin/"${base_branch}"...HEAD

# コミットメッセージ一覧
git log --oneline origin/"${base_branch}"...HEAD
```

#### 4-2. PR説明文生成

以下の構成でMarkdownを生成：

```markdown
## 概要

[Issueの概要を1-2文で簡潔に記述]

Closes #{issue_number}

## 変更内容

### 追加機能
- [主要な追加機能1]
- [主要な追加機能2]

### 変更・改善
- [変更した既存機能1]

### バグ修正 (該当する場合)
- [修正したバグ1]

## 実装詳細

### 主要な変更ファイル

| ファイル | 変更内容 | 行数 |
|---------|---------|------|
| {file_1} | {description} | +{added}/-{deleted} |
| {file_2} | {description} | +{added}/-{deleted} |

## テスト結果

### 単体テスト

```
Tests passed: {unit_test_count}/{unit_test_count}
Coverage: {unit_coverage}%
```

### 受入テスト

```
Tests passed: {acceptance_test_count}/{acceptance_test_count}
```

**受入条件検証**:
- [x] {acceptance_criterion_1}
- [x] {acceptance_criterion_2}

### 静的解析

- Ruff (Lint): ✅ エラー0件
- Ruff (Format): ✅ 全ファイルフォーマット済み
- MyPy (Type Check): ✅ エラー0件

### 統合チェック

```bash
./scripts/pre-push-check-all.sh
```

**結果**: ✅ 全チェック成功

## チェックリスト

### コード品質
- [x] 単体テストカバレッジ 90%以上
- [x] 受入テスト全件合格
- [x] 静的解析エラー0件
- [x] pre-push-check-all.sh 全パス

### ドキュメント
- [x] 作業計画書作成済み
- [x] 進捗報告書作成済み

### レビュー準備
- [x] コミットメッセージが規約に従っている
- [x] 不要なコメントアウト削除
- [x] デバッグコード削除
- [x] コンフリクトなし

### 動作確認
- [x] ローカル環境で動作確認完了

## 関連ドキュメント

- 📋 作業計画: `dev-reports/feature/issue/{issue_number}/work-plan.md`
- 📊 進捗報告: `dev-reports/feature/issue/{issue_number}/progress-report.md`

## レビュー観点

レビュアーの方は以下の観点で確認をお願いします:

1. **機能要件**: 受入条件が満たされているか
2. **コード品質**: SOLID原則に従っているか
3. **テストカバレッジ**: 十分なテストがあるか
4. **セキュリティ**: 脆弱性がないか

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Phase 5: PR作成実行

#### 5-1. ラベル設定

Issueのラベルを継承：

```bash
labels=$(gh issue view {issue_number} --json labels --jq '.labels[].name' | tr '\n' ',')
```

#### 5-2. PR作成コマンド実行

```bash
# base_branchが未設定の場合、developをデフォルトとする
base_branch="${base_branch:-develop}"

gh pr create \
  --base "${base_branch}" \
  --title "${pr_title}" \
  --body "${pr_body}" \
  --label "${labels}" \
  ${draft_flag} \
  ${assignee_flag}
```

**重要な注意事項**:
- **base_branch は必ず `develop` に設定されます**（デフォルト値）
- `feature/*`, `fix/*`, `vibe/*` ブランチからのPRは `develop` ブランチへマージするのがプロジェクトルールです
- `main` ブランチへの直接PRは禁止されています（[ブランチ戦略](../../docs/claude/03-branch-strategy.md)参照）

**オプション**:
- `--draft`: Draft PRとして作成（`draft=true`の場合）
- `--assignee @me`: 自分をアサイン（`auto_assign=true`の場合）

#### 5-3. PR URL取得

```bash
pr_url=$(gh pr view --json url --jq '.url')
```

---

### Phase 6: 完了報告

ターミナルに以下を出力：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pull Request作成完了！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PR情報:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  URL:      {pr_url}
  タイトル:  {pr_title}
  ベース:    {base_branch}
  ステータス: {draft ? "Draft" : "Ready for review"}
  ラベル:    {labels}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 CI/CD状況:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GitHub Actions: 実行中...

  結果確認: gh pr checks
  ログ確認: gh run view --log-failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 次のステップ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. PR画面でCI結果を確認
     {pr_url}

  2. レビュアーをアサイン

  3. レビュー承認後にマージ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔍 品質基準

### PRタイトル

- ✅ Conventional Commits形式に従う
- ✅ プロジェクト名を明記
- ✅ 50文字以内
- ✅ 命令形（"Add" not "Added"）

### PR説明

- ✅ 概要が明確（1-2文）
- ✅ Closes #xxx で自動クローズ設定
- ✅ 変更内容が箇条書きで明確
- ✅ テスト結果を含む
- ✅ チェックリストが全てチェック済み

### 実行前条件

- ✅ `/pm-auto-dev` 完了済み
- ✅ ユーザーの動作確認完了
- ✅ `pre-push-check-all.sh` 全パス
- ✅ 未コミットの変更なし

## 🚨 エラーハンドリング

### Issue番号が検出できない

明確なエラーメッセージを表示し、対処方法を提示。

### pre-push-check失敗

PR作成を中止し、修正方法を提示：
1. エラー内容を確認
2. `/pm-auto-dev {issue_number} --mode=fix` で是正
3. 修正後に再度 `/pm-create-pr` を実行

### developブランチが古い

rebaseを推奨し、手順を提示。

## 📚 参照ドキュメント

- [ブランチ戦略](../../docs/claude/03-branch-strategy.md)
- [品質基準](../../docs/claude/04-quality-standards.md)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

それでは、PR作成を開始します！
