---
model: opus
description: "Issue開発を完全自動化（TDD→テスト→報告）"
phase: "8-11. 自動開発"
session: "worktree"
---

# PM自動開発スキル

## 概要
Issue開発（Phase 8-11: TDD実装 → 受入テスト → リファクタリング → 進捗報告）を**完全自動化**するプロジェクトマネージャースキルです。ユーザーはIssue番号を指定するだけで、開発完了まで自律的に実行します。

## 使用方法
- `/pm-auto-dev [Issue番号]`
- `/pm-auto-dev [Issue番号] --mode=fix`（是正モード）
- `/pm-auto-dev [Issue番号] --max-iterations=5`（イテレーション回数変更）
- 「Issue #145を開発してください」
- 「Issue #145を是正してください」

## 実行内容

あなたはプロジェクトマネージャーとして、Issue開発を統括します。以下のフェーズを**自律的に**実行し、品質基準を満たすまで完了させてください。

### 📋 パラメータ

- **issue_number**: 開発対象のIssue番号（必須）
- **mode**: 実行モード
  - `full`: 新規開発モード（デフォルト）
  - `fix`: 是正モード（動作確認で不具合発見時）
- **max_iterations**: 最大イテレーション回数（デフォルト: 3）
- **skip_refactor**: リファクタリングをスキップ（デフォルト: false）

---

## 🔄 実行フェーズ

### Phase 0: 初期設定とTodoリスト作成

まず、TodoWriteツールで作業計画を作成してください：

```
- [ ] Phase 1: Issue情報収集
- [ ] Phase 2: TDD実装 (イテレーション 0/3)
- [ ] Phase 3: 受入テスト
- [ ] Phase 4: リファクタリング
- [ ] Phase 5: 進捗報告
```

各フェーズ開始時に`in_progress`に、完了時に`completed`に更新してください。

### Phase 1: Issue情報収集

1. **GitHub Issue情報の取得**:
   ```bash
   gh issue view {issue_number} --json title,body,labels,assignees
   ```

2. **作業計画の確認**:
   ```bash
   cat dev-reports/feature/issue/{issue_number}/work-plan.md
   ```

   ファイルが存在しない場合は、Issue本文から要件を抽出してください。

3. **受入条件の抽出**:
   - Issue本文から`## 受入条件`セクションを抽出
   - 各受入条件をリスト化

4. **実装要件の確認**:
   - `## 実装タスク`から実装すべき内容を確認
   - 技術スタック、依存関係を確認

5. **現在のブランチ確認**:
   ```bash
   git branch --show-current
   ```

   `feature/issue/{issue_number}`ブランチで作業していることを確認。異なる場合は警告。

**Phase 1完了条件**:
- Issue情報が取得できた
- 受入条件が明確
- 実装要件が理解できた

TodoWriteでPhase 1を`completed`に更新し、Phase 2を`in_progress`に設定してください。

---

### Phase 2: TDD実装（イテレーション可能）

**最大イテレーション回数**: `{max_iterations}`回（デフォルト: 3回）

現在のイテレーション回数を変数で管理し、Todoリストに表示してください：
```
- [x] Phase 2: TDD実装 (イテレーション 1/3)
```

#### 2-1. Red Phase: 失敗するテストを作成

1. **テストケース設計**:
   - 受入条件から必要なテストケースを設計
   - Given-When-Then形式で整理
   - 正常系・異常系・エッジケースを考慮

2. **テストコード作成**:
   - `tests/unit/test_issue_{issue_number}_*.py`
   - `tests/integration/test_issue_{issue_number}_*.py`
   - Arrange-Act-Assert構造

3. **テスト実行（失敗確認）**:
   ```bash
   uv run pytest tests/unit/test_issue_{issue_number}_*.py -v
   ```

   全テストが失敗することを確認。

#### 2-2. Green Phase: テストを通す最小限の実装

1. **実装ファイル作成・変更**:
   - 作業計画に従って実装
   - テストを通すことだけを考える
   - 過剰な実装はしない

2. **テスト実行（成功確認）**:
   ```bash
   uv run pytest tests/unit/ -v
   ```

   全テストが成功することを確認。

#### 2-3. Refactor Phase: コードを整理

1. **コード品質改善**:
   - 重複コード削除（DRY原則）
   - 命名規則の適用
   - 関数/クラスの分割（単一責任原則）

2. **テスト再実行**:
   ```bash
   uv run pytest tests/unit/ -v
   ```

   リファクタリング後も全テスト成功を確認。

#### 2-4. Coverage Check: カバレッジ確認

1. **カバレッジ測定**:
   ```bash
   uv run pytest --cov=app --cov-report=term-missing --cov-report=html
   ```

2. **カバレッジ判定**:
   - **90%以上**: Phase 2完了 → Phase 3へ
   - **90%未満**: 未カバー箇所を特定し、テスト追加（Phase 2-1へ戻る）

3. **静的解析チェック**:
   ```bash
   uv run ruff check .
   uv run ruff format .
   uv run mypy app/
   ```

   全てエラー0件であることを確認。エラーがあれば修正。

**Phase 2完了条件**:
- ✅ 単体テストカバレッジ 90%以上
- ✅ 全テスト成功
- ✅ 静的解析エラー 0件

TodoWriteでPhase 2を`completed`に、Phase 3を`in_progress`に設定してください。

---

### Phase 3: 受入テスト

#### 3-1. 受入テストケースの生成

1. **受入条件からテストケース化**:
   Issue本文の`## 受入条件`から、各項目をテストケースに変換：

   例：
   ```
   受入条件:
   - [ ] worktreeが自動検出されること

   → テストケース:
   def test_worktree_auto_detection():
       \"\"\"受入条件: worktreeが自動検出されること\"\"\"
       # Given: 3つのworktreeが存在する環境
       # When: worktree検出機能を実行
       # Then: 全3つのworktreeが検出される
   ```

2. **統合テストファイル作成**:
   ```bash
   tests/integration/test_issue_{issue_number}_acceptance.py
   ```

#### 3-2. 受入テスト実行

1. **環境準備**:
   - 必要なサービスが起動しているか確認
   - テストデータの準備

2. **テスト実行**:
   ```bash
   uv run pytest tests/integration/test_issue_{issue_number}_acceptance.py -v
   ```

3. **結果判定**:
   - **全テスト合格**: Phase 4へ進む
   - **テスト不合格**: 以下を実行

#### 3-3. テスト不合格時の処理

1. **イテレーション回数確認**:
   - 現在のイテレーション回数が`{max_iterations}`未満:
     - イテレーション回数を+1
     - Todoリストを更新: `Phase 2: TDD実装 (イテレーション 2/3)`
     - **Phase 2に戻る**（失敗原因を踏まえて再実装）

   - `{max_iterations}`回到達:
     - **エスカレーション**（後述）

2. **失敗分析**:
   失敗したテストケースについて分析し、ユーザーに報告：

   ```
   ❌ 受入テスト不合格（イテレーション 2/3）

   ## 失敗テストケース

   ### test_worktree_auto_detection
   - 期待値: 3個のworktree検出
   - 実際の値: 2個のworktree検出
   - エラー: AssertionError

   ## 原因分析
   symlink経由のworktreeが検出されていない

   ## 修正方針
   `git worktree list`の出力パース処理を修正

   イテレーション 3/3 で再実装します...
   ```

#### 3-4. エスカレーション（イテレーション上限到達時）

```
⚠️ 受入テスト不合格が{max_iterations}回連続しました。

## テスト失敗内容
[失敗したテストケースと原因の詳細]

## 考えられる問題
1. 要件の見直しが必要な可能性
2. テストケースが厳しすぎる可能性
3. アーキテクチャの根本的な見直しが必要な可能性

## 推奨アクション
シニアエンジニアに相談してください。

PM自動開発を中断します。
```

エスカレーション時はTodoリストを更新し、作業を停止してください。

**Phase 3完了条件**:
- ✅ 全受入テスト合格

TodoWriteでPhase 3を`completed`に、Phase 4を`in_progress`に設定してください。

---

### Phase 4: リファクタリング（条件付き）

**スキップ条件**:
- `skip_refactor=true`が指定されている
- コード品質が十分高い（後述の評価で判定）

#### 4-1. コード品質評価

1. **複雑度チェック**:
   - 関数の行数が20行を超えていないか
   - ネストが3段階を超えていないか
   - 引数が5個を超えていないか

2. **コードスメル検出**:
   - 重複コード
   - マジックナンバー
   - 長すぎる変数名/短すぎる変数名
   - 意味不明な命名

3. **リファクタリング要否判定**:
   - 問題なし: Phase 4をスキップ → Phase 5へ
   - 問題あり: リファクタリング実施

#### 4-2. リファクタリング実施

1. **改善実施**:
   - 長い関数の分割
   - 重複コードの共通化
   - マジックナンバーの定数化
   - 命名の改善

2. **テスト再実行**:
   ```bash
   uv run pytest tests/ -v
   ```

   **重要**: リファクタリング後、全テストが成功することを確認。
   失敗した場合はリファクタリングを元に戻す。

3. **カバレッジ確認**:
   ```bash
   uv run pytest --cov=app --cov-report=term-missing
   ```

   カバレッジが下がっていないことを確認。

**Phase 4完了条件**:
- ✅ リファクタリング完了 or スキップ
- ✅ 全テスト引き続き成功
- ✅ カバレッジ維持

TodoWriteでPhase 4を`completed`に、Phase 5を`in_progress`に設定してください。

---

### Phase 5: 進捗報告

#### 5-1. 統計情報収集

1. **変更ファイル統計**:
   ```bash
   git diff --name-status origin/develop...HEAD
   git diff --stat origin/develop...HEAD
   git log --oneline origin/develop...HEAD | wc -l
   ```

2. **テスト結果収集**:
   - 単体テストカバレッジ
   - 受入テスト件数
   - イテレーション回数

3. **静的解析結果**:
   - Ruffエラー数
   - MyPyエラー数

#### 5-2. 進捗報告ファイル作成

**保存先**: `dev-reports/feature/issue/{issue_number}/progress-report.md`

```markdown
# 進捗報告 - Issue #{issue_number}

> **ステータス**: ✅ 完了
> **完了日時**: {completion_date}
> **担当者**: PM Auto-Dev Agent

## 📋 Issue情報

- **タイトル**: {issue_title}
- **ラベル**: {labels}

## 📊 実装サマリ

### 実装内容
{implementation_description}

### 変更統計

| 指標 | 数値 |
|------|------|
| 追加ファイル | {added_files}個 |
| 変更ファイル | {modified_files}個 |
| 追加行数 | +{added_lines}行 |
| 削除行数 | -{deleted_lines}行 |
| コミット数 | {commit_count}件 |

## 🧪 テスト結果

### 単体テスト
- テストケース数: {unit_test_count}件
- 成功: {unit_success}件 ✅
- カバレッジ: {unit_coverage}%

### 受入テスト
- テストケース数: {acceptance_test_count}件
- 成功: {acceptance_success}件 ✅

### 静的解析
- Ruff: ✅ エラー0件
- MyPy: ✅ エラー0件

## 🔄 開発プロセス

### イテレーション履歴
| イテレーション | 結果 | 備考 |
|--------------|------|------|
| 1 | {result_1} | {note_1} |
| ... | ... | ... |

**総イテレーション回数**: {iteration_count}/{max_iterations}

### リファクタリング
{refactoring_performed ? "実施済み" : "スキップ"}

## 🚀 次のステップ

### Phase 12: ユーザー動作確認

**確認手順**:
1. worktree環境でサービスを起動
   ```bash
   cd {worktree_path}
   ./scripts/dev-start.sh
   ```

2. 各機能が正常に動作することを確認

3. 確認結果に応じて:
   - **動作OK**: `/pm-create-pr` でPR作成
   - **不具合あり**: `/pm-auto-dev {issue_number} --mode=fix` で是正

---

**作成日時**: {created_at}
**作成者**: PM Auto-Dev Agent
```

#### 5-3. ユーザーへの完了報告

ターミナルに以下を出力：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Issue #{issue_number} 開発完了！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Issue: {issue_title}

📊 実装サマリ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  変更ファイル:  {changed_files}個
  追加/削除:     +{added_lines}/-{deleted_lines}行
  イテレーション: {iteration_count}/{max_iterations}回
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 テスト結果:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  単体テスト:     {unit_test_count}件成功 ({unit_coverage}%)
  受入テスト:     {acceptance_test_count}件成功
  静的解析:       エラー0件
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 進捗報告: dev-reports/feature/issue/{issue_number}/progress-report.md

🚀 次のステップ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. worktree環境で動作確認を実施してください

  2. 動作確認OK後、PR作成:
     /pm-create-pr

  3. 不具合発見時、是正:
     /pm-auto-dev {issue_number} --mode=fix
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Phase 5完了条件**:
- ✅ 進捗報告ファイル作成完了
- ✅ ユーザーへの完了報告実施

TodoWriteでPhase 5を`completed`に設定し、全Todoを完了状態にしてください。

---

## 🛠️ 是正モード (mode=fix)

ユーザーの動作確認で不具合が見つかった場合に使用します。

### 実行内容

1. **ユーザーからの不具合報告受領**:
   「どのような不具合がありましたか？詳細を教えてください」

2. **不具合の理解**:
   - 再現手順
   - 期待される動作
   - 実際の動作

3. **不具合を再現するテストケース追加**:
   Phase 2-1 (Red Phase) で不具合を再現するテストを作成

4. **Phase 2から再実行**:
   - イテレーションカウントはリセット
   - 不具合修正を含めて再実装

---

## 📊 品質基準

以下を満たすまでPhase 3から先に進まない：

- ✅ 単体テストカバレッジ 90%以上
- ✅ 受入テスト 全件合格
- ✅ 静的解析エラー 0件（Ruff, MyPy）
- ✅ `./scripts/pre-push-check-all.sh` 実行可能

## 🚨 重要な制約

1. **自律性**: ユーザーの介入なしに可能な限り進める
2. **透明性**: 各フェーズの結果をTodoリストとターミナルで報告
3. **品質第一**: 品質基準を満たさない限り次フェーズに進まない
4. **イテレーション制限**: 無限ループを防ぐため上限を設ける
5. **エラーハンドリング**: エラー発生時は明確なメッセージで報告

## 📚 参照ドキュメント

- [開発ワークフロー](../../docs/claude/01-development-workflow.md)
- [品質基準](../../docs/claude/04-quality-standards.md)
- [TDD実装スキル](./tdd-impl.md)
- [受入テストスキル](./acceptance-test.md)

---

それでは、Issue #{issue_number} の開発を開始します！
