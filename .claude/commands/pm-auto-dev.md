---
model: opus
description: "Issue開発を完全自動化（TDD→テスト→報告）"
phase: "8-11. 自動開発"
session: "worktree"
---

# PM自動開発スキル

## 概要
Issue開発（Phase 8-11: TDD実装 → 受入テスト → リファクタリング → 進捗報告）を**完全自動化**するプロジェクトマネージャースキルです。ユーザーはIssue番号を指定するだけで、開発完了まで自律的に実行します。

**新アーキテクチャ**: サブエージェント方式を採用し、各フェーズを専門エージェントに委譲します。

## 使用方法
- `/pm-auto-dev [Issue番号]`
- `/pm-auto-dev [Issue番号] --max-iterations=5`（イテレーション回数変更）
- 「Issue #145を開発してください」

## 実行内容

あなたはプロジェクトマネージャーとして、Issue開発を統括します。各フェーズは**専門サブエージェント**に委譲し、結果ファイルを確認しながら品質基準を満たすまで完了させてください。

### 📋 パラメータ

- **issue_number**: 開発対象のIssue番号（必須）
- **max_iterations**: 最大イテレーション回数（デフォルト: 3）
- **target_coverage**: 目標カバレッジ（デフォルト: 90）

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

---

### Phase 1: Issue情報収集

#### 1-1. Issue情報取得

```bash
gh issue view {issue_number} --json number,title,body,labels,assignees
```

#### 1-2. 必要情報の抽出

Issue本文から以下を抽出：

- **タイトル**: Issue件名
- **受入条件** (`## 受入条件`セクション)
- **技術要件** (`## 技術要件`セクション)
- **実装タスク** (`## 実装タスク`セクション)

#### 1-3. ディレクトリ構造作成

```bash
BRANCH=$(git branch --show-current)
ISSUE_NUM=$(echo "$BRANCH" | grep -oE '[0-9]+$')

if [ -z "$ISSUE_NUM" ]; then
  echo "❌ Error: Issue番号がブランチ名から取得できません"
  exit 1
fi

# ベースディレクトリ作成
BASE_DIR="dev-reports/feature/issue/${ISSUE_NUM}/pm-auto-dev/iteration-1"
mkdir -p "$BASE_DIR"

echo "✅ ディレクトリ作成: $BASE_DIR"
```

TodoWriteでPhase 1を`completed`に、Phase 2を`in_progress`に設定してください。

---

### Phase 2: TDD実装（イテレーション可能）

**最大イテレーション回数**: `{max_iterations}`回（デフォルト: 3回）

現在のイテレーション回数を変数で管理し、Todoリストに表示してください：
```
- [x] Phase 2: TDD実装 (イテレーション 1/3)
```

#### 2-1. TDDコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/tdd-context.json
```

**内容**:
```json
{
  "issue_number": {issue_number},
  "acceptance_criteria": [
    "受入条件1",
    "受入条件2"
  ],
  "implementation_tasks": [
    "実装タスク1",
    "実装タスク2"
  ],
  "target_coverage": 90
}
```

**重要**: Phase 1で取得したIssue情報を正確に転記してください。

#### 2-2. TDD実装サブエージェント呼び出し

以下のテキストを記述してください（サブエージェントが自動起動されます）：

```
Use tdd-impl-agent to implement Issue #{issue_number} with TDD approach.

Context file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/tdd-context.json
Output file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/tdd-result.json

Please follow the Red-Green-Refactor cycle and ensure all tests pass with 90% coverage.
```

#### 2-3. 結果確認

サブエージェントが完了したら、Readツールで結果ファイルを確認：

```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/tdd-result.json
```

**結果判定**:

##### ケース1: TDD実装成功 (`status: "success"`)

```json
{
  "status": "success",
  "coverage": 92.5,
  "unit_tests": {
    "total": 25,
    "passed": 25,
    "failed": 0
  },
  "static_analysis": {
    "ruff_errors": 0,
    "mypy_errors": 0
  }
}
```

→ **Phase 3へ進む**

TodoWriteでPhase 2を`completed`に、Phase 3を`in_progress`に設定。

##### ケース2: TDD実装失敗 (`status: "failed"`)

```json
{
  "status": "failed",
  "coverage": 75.0,
  "error": "目標カバレッジ90%に達していません（現在: 75.0%）"
}
```

→ **イテレーション回数確認**:

- **イテレーション回数 < max_iterations**:
  - イテレーション回数を+1
  - Todoリストを更新: `Phase 2: TDD実装 (イテレーション 2/3)`
  - **Phase 2-1に戻る**（新しいコンテキストファイルを作成し、再度サブエージェント呼び出し）

- **イテレーション回数 >= max_iterations**:
  - ユーザーにエスカレーション:
    ```
    ❌ TDD実装が{max_iterations}回のイテレーション後も失敗しました。

    ## 最終エラー
    - カバレッジ: 75.0%（目標: 90%）
    - 静的解析エラー: 3件

    ## 次のアクション
    1. 目標カバレッジを下げる（--target-coverage=80）
    2. 手動でテストを追加する
    3. Issue要件を見直す
    ```

---

### Phase 3: 受入テスト

#### 3-1. 受入テストコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/acceptance-context.json
```

**内容**:
```json
{
  "issue_number": {issue_number},
  "feature_summary": "Issue件名",
  "acceptance_criteria": [
    "受入条件1",
    "受入条件2"
  ],
  "test_scenarios": [
    "シナリオ1: ...",
    "シナリオ2: ..."
  ]
}
```

#### 3-2. 受入テストサブエージェント呼び出し

以下のテキストを記述してください：

```
Use acceptance-test-agent to verify Issue #{issue_number} acceptance criteria.

Context file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/acceptance-context.json
Output file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/acceptance-result.json

Please execute all test scenarios and verify all acceptance criteria are met.
```

#### 3-3. 結果確認

Readツールで結果ファイルを確認：

```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/acceptance-result.json
```

**結果判定**:

##### ケース1: 受入テスト成功 (`status: "passed"`)

```json
{
  "status": "passed",
  "test_cases": [
    {"scenario": "シナリオ1", "result": "passed"},
    {"scenario": "シナリオ2", "result": "passed"}
  ],
  "acceptance_criteria_status": [
    {"criterion": "受入条件1", "verified": true},
    {"criterion": "受入条件2", "verified": true}
  ]
}
```

→ **Phase 4へ進む**

TodoWriteでPhase 3を`completed`に、Phase 4を`in_progress`に設定。

##### ケース2: 受入テスト失敗 (`status: "failed"`)

```json
{
  "status": "failed",
  "test_cases": [
    {"scenario": "シナリオ1", "result": "passed"},
    {"scenario": "シナリオ2", "result": "failed"}
  ],
  "error": "受入テストの一部が失敗しました"
}
```

→ **イテレーション回数確認** → **Phase 2に戻る**（TDD実装からやり直し）

---

### Phase 4: リファクタリング

#### 4-1. リファクタリングコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/refactor-context.json
```

**内容**:
```json
{
  "issue_number": {issue_number},
  "refactor_targets": [
    "app/services/database.py",
    "app/models/job.py"
  ],
  "quality_metrics": {
    "before_coverage": 92.5,
    "complexity_score": 12
  },
  "design_patterns_to_apply": [
    "Repository Pattern",
    "Dependency Injection"
  ],
  "improvement_goals": [
    "カバレッジを95%以上に向上",
    "循環的複雑度を10以下に削減",
    "重複コードの削除"
  ]
}
```

**重要**: TDD結果ファイルから現在のカバレッジを取得して `before_coverage` に設定してください。

#### 4-2. リファクタリングサブエージェント呼び出し

以下のテキストを記述してください：

```
Use refactoring-agent to improve code quality for Issue #{issue_number}.

Context file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/refactor-context.json
Output file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/refactor-result.json

Please apply SOLID principles and design patterns while maintaining all tests passing.
```

#### 4-3. 結果確認

Readツールで結果ファイルを確認：

```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/refactor-result.json
```

**結果判定**:

##### ケース1: リファクタリング成功 (`status: "success"`)

```json
{
  "status": "success",
  "quality_metrics": {
    "before_coverage": 92.5,
    "after_coverage": 95.0,
    "before_complexity": 12,
    "after_complexity": 8
  },
  "refactorings_applied": [
    "Repository Pattern適用",
    "重複コード削除"
  ]
}
```

→ **Phase 5へ進む**

TodoWriteでPhase 4を`completed`に、Phase 5を`in_progress`に設定。

##### ケース2: リファクタリング失敗 (`status: "failed"`)

リファクタリングは任意フェーズのため、失敗してもPhase 5へ進みます。
ただし、失敗理由をユーザーに報告してください。

---

### Phase 5: 進捗報告

#### 5-1. 進捗レポートコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/progress-context.json
```

**内容**:
```json
{
  "issue_number": {issue_number},
  "iteration": 1,
  "phase_results": {
    "tdd": {
      "status": "success",
      "coverage": 92.5
    },
    "acceptance": {
      "status": "passed"
    },
    "refactor": {
      "status": "success"
    }
  }
}
```

**重要**: 各フェーズの実際の結果を正確に転記してください。

#### 5-2. 進捗レポートサブエージェント呼び出し

以下のテキストを記述してください：

```
Use progress-report-agent to generate progress report for Issue #{issue_number} iteration 1.

Context file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/progress-context.json
Output file: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/progress-report.md

Please summarize all phase results and suggest next steps.
```

#### 5-3. レポート表示

サブエージェントが完了したら、Readツールでレポートを読み込んで表示：

```bash
cat dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-1/progress-report.md
```

**レポート内容**:
- 概要（Issue番号、イテレーション、ステータス）
- フェーズ別結果（TDD、受入テスト、リファクタリング）
- 総合品質メトリクス
- ブロッカー（あれば）
- 次のステップ

TodoWriteでPhase 5を`completed`に設定。

---

## 🔄 イテレーション制御ロジック

### イテレーションが必要になるケース

1. **TDD実装失敗** (Phase 2-3):
   - カバレッジ不足
   - 静的解析エラー
   - テスト失敗

2. **受入テスト失敗** (Phase 3-3):
   - テストシナリオ失敗
   - 受入条件未達成

### イテレーション処理フロー

```
Phase 2 → Phase 3 → 受入テスト失敗
  ↓                    ↓
  ←──────────────────┘
  (イテレーション+1)

Phase 2 (イテレーション2) → Phase 3 → ...
```

### 最大イテレーション到達時

```
❌ Issue #{issue_number} の開発が{max_iterations}回のイテレーション後も完了しませんでした。

## 最終状態
- TDD実装: {tdd_status}
- 受入テスト: {acceptance_status}
- カバレッジ: {coverage}%

## 推奨アクション
1. 目標カバレッジを下げる（--target-coverage=80）
2. 最大イテレーション回数を増やす（--max-iterations=5）
3. Issue要件を見直す
4. 手動で実装を修正する

## 作業ファイル
- コンテキストファイル: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/
- 結果ファイル: dev-reports/feature/issue/{issue_number}/pm-auto-dev/iteration-{N}/
```

---

## 📂 ファイル構造

```
dev-reports/feature/issue/{issue_number}/pm-auto-dev/
├── iteration-1/
│   ├── tdd-context.json          ← TDD実装の入力
│   ├── tdd-result.json           ← TDD実装の出力
│   ├── acceptance-context.json   ← 受入テストの入力
│   ├── acceptance-result.json    ← 受入テストの出力
│   ├── refactor-context.json     ← リファクタリングの入力
│   ├── refactor-result.json      ← リファクタリングの出力
│   ├── progress-context.json     ← 進捗レポートの入力
│   └── progress-report.md        ← 進捗レポート（Markdown）
├── iteration-2/                  ← イテレーション2（失敗時）
│   ├── tdd-context.json
│   └── ...
└── iteration-3/                  ← イテレーション3（失敗時）
    └── ...
```

---

## 🎯 完了条件

以下をすべて満たすこと：

- ✅ Phase 1: Issue情報収集完了
- ✅ Phase 2: TDD実装成功（カバレッジ90%以上、静的解析エラー0件）
- ✅ Phase 3: 受入テスト成功（全シナリオ合格、全受入条件検証済み）
- ✅ Phase 4: リファクタリング完了（または失敗時は理由報告）
- ✅ Phase 5: 進捗レポート作成完了

---

## 🚨 エラーハンドリング

### サブエージェントが応答しない場合

サブエージェントが10分以上応答しない場合：

1. **タイムアウト判定**: サブエージェントを中断
2. **ユーザーに報告**:
   ```
   ⚠️ {agent-name} がタイムアウトしました（10分経過）

   ## 次のアクション
   1. サブエージェントを再実行する
   2. 手動で該当フェーズを実行する
   3. Issue要件を簡素化する
   ```

### コンテキストファイル作成失敗

Phase 1でIssue情報が不足している場合：

```
❌ Issue #{issue_number} の情報が不足しています

## 不足情報
- 受入条件（## 受入条件セクションが存在しません）

## 次のアクション
1. Issue本文を修正して受入条件を追加
2. PM Auto-Devを再実行
```

---

## 📝 使用例

### 基本的な使用方法

```
User: /pm-auto-dev 166

PM Auto-Dev:
✅ Phase 1: Issue情報収集完了
  - Issue #166: jobqueueにaiosqlite対応のDATABASE_URL設定
  - 受入条件: 2件
  - 実装タスク: 3件

🔄 Phase 2: TDD実装 (イテレーション 1/3)
  - コンテキストファイル作成完了
  - tdd-impl-agent を起動中...

✅ Phase 2: TDD実装成功
  - カバレッジ: 92.5%
  - テスト: 25/25 passed
  - 静的解析: 0 errors

✅ Phase 3: 受入テスト成功
  - テストシナリオ: 2/2 passed
  - 受入条件: 2/2 verified

✅ Phase 4: リファクタリング成功
  - カバレッジ: 92.5% → 95.0%
  - 複雑度: 12 → 8

✅ Phase 5: 進捗レポート作成完了

🎉 Issue #166 の開発が完了しました！
```

---

## 🔧 トラブルシューティング

### Q1: サブエージェントが見つからない

**エラー**:
```
Error: Subagent 'tdd-impl-agent' not found
```

**対応**:
`.claude/agents/tdd-impl-agent.md` が存在するか確認してください。

### Q2: コンテキストファイルが見つからない

**エラー**:
```
Error: tdd-context.json not found
```

**対応**:
Phase 2-1でWriteツールを使ってコンテキストファイルを作成してください。

### Q3: イテレーションが進まない

**現象**:
Phase 2で失敗しているのにPhase 3に進んでしまう

**対応**:
Phase 2-3の結果判定ロジックを確認し、`status: "failed"` の場合はPhase 2に戻るようにしてください。

---

## 📚 関連ドキュメント

- [サブエージェント設計](../../workspace/pm-auto-dev-design/06-official-subagent-implementation.md)
- [統合仕様](../../workspace/pm-auto-dev-design/07-slash-command-subagent-integration.md)
- [実装完了レポート](../../workspace/pm-auto-dev-design/08-implementation-complete.md)
- [検証レポート](../../workspace/pm-auto-dev-design/09-verification-report.md)
