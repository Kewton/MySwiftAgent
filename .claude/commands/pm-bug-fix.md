---
model: opus
description: "不具合の調査・対策案提示・修正実施を完全自動化"
phase: "不具合対応"
session: "worktree"
---

# PM Bug Fix スキル

## 概要

不具合（バグ、エラー、予期しない動作）の調査から修正、テスト、報告まで**完全自動化**するプロジェクトマネージャースキルです。ユーザーは不具合の概要を伝えるだけで、原因調査→対策案提示→修正実施を自律的に実行します。

**新アーキテクチャ**: サブエージェント方式を採用し、各フェーズを専門エージェントに委譲します。

## 使用方法
- `/pm-bug-fix [不具合の概要]`
- `/pm-bug-fix "データベース接続エラーが発生"`
- 「ジョブ一覧ページでエラーが表示される問題を調査してください」

## 実行内容

あなたはプロジェクトマネージャーとして、不具合対応を統括します。各フェーズは**専門サブエージェント**に委譲し、結果ファイルを確認しながら修正完了まで導いてください。

### 📋 パラメータ

- **bug_description**: 不具合の概要（必須）
- **error_logs**: エラーログファイルパス（任意）
- **severity**: 重大度（critical/high/medium/low、デフォルト: high）
- **related_issue**: 関連Issue番号（任意）

---

## 🔄 実行フェーズ

### Phase 0: 初期設定とTodoリスト作成

まず、TodoWriteツールで作業計画を作成してください：

```
- [ ] Phase 1: 不具合調査
- [ ] Phase 2: 対策案提示・ユーザーフィードバック
- [ ] Phase 3: 作業計画立案
- [ ] Phase 4: TDD修正実施
- [ ] Phase 5: 受入テスト
- [ ] Phase 6: 進捗報告
```

各フェーズ開始時に`in_progress`に、完了時に`completed`に更新してください。

---

### Phase 1: 不具合調査

#### 1-1. 不具合情報の収集

ユーザーから以下の情報を収集（不足している場合は質問）：

```markdown
## 不具合情報
- **概要**: [ユーザー入力]
- **エラーメッセージ**: [あれば]
- **再現手順**: [あれば]
- **影響範囲**: [全ユーザー / 特定条件のユーザー]
- **環境情報**: [OS, Python, プロジェクト名]
```

#### 1-2. ディレクトリ構造作成

```bash
BRANCH=$(git branch --show-current)
BUG_ID=$(date +%Y%m%d_%H%M%S)  # タイムスタンプでユニークID生成

# ベースディレクトリ作成
BASE_DIR="dev-reports/bug-fix/${BUG_ID}"
mkdir -p "$BASE_DIR"

echo "✅ ディレクトリ作成: $BASE_DIR"
```

#### 1-3. 調査コンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/bug-fix/{bug_id}/investigation-context.json
```

**内容**:
```json
{
  "issue_description": "ユーザーから報告された不具合の概要",
  "error_logs": [
    "エラーログ1",
    "エラーログ2"
  ],
  "affected_files": [
    "app/services/database.py"
  ],
  "reproduction_steps": [
    "1. ユーザーがログインする",
    "2. ジョブ一覧ページにアクセス",
    "3. エラーが表示される"
  ],
  "environment": {
    "os": "macOS 14.1",
    "python_version": "3.11.6",
    "project": "expertAgent",
    "branch": "develop"
  },
  "related_issue_number": null,
  "severity_hint": "high"
}
```

**重要**: ユーザーから収集した情報を正確に転記してください。

#### 1-4. 調査サブエージェント呼び出し

以下のテキストを記述してください（サブエージェントが自動起動されます）：

```
Use issue-investigation-agent to investigate the bug.

Context file: dev-reports/bug-fix/{bug_id}/investigation-context.json
Output file: dev-reports/bug-fix/{bug_id}/investigation-result.json

Please analyze error logs, identify root cause, and recommend actionable solutions.
```

#### 1-5. 調査結果確認

サブエージェントが完了したら、Readツールで結果ファイルを確認：

```bash
cat dev-reports/bug-fix/{bug_id}/investigation-result.json
```

**結果判定**:

##### ケース1: 調査完了 (`status: "completed"`)

```json
{
  "status": "completed",
  "root_cause_analysis": {
    "category": "設定ミス",
    "primary_cause": "データベース接続プールのサイズが小さすぎる"
  },
  "recommended_actions": [
    {"action_id": "1", "priority": "high", "title": "..."},
    {"action_id": "2", "priority": "medium", "title": "..."}
  ]
}
```

→ **Phase 2へ進む**

TodoWriteでPhase 1を`completed`に、Phase 2を`in_progress`に設定。

##### ケース2: 情報不足 (`status: "needs_more_info"`)

```json
{
  "status": "needs_more_info",
  "blockers": [
    "エラーログが不足",
    "再現手順が不明確"
  ],
  "requested_information": [
    "詳細なエラーログ（スタックトレース含む）",
    "再現手順の詳細化"
  ]
}
```

→ **ユーザーに追加情報を要求**:

```
⚠️ 調査に必要な情報が不足しています

## 不足情報
- エラーログが不足
- 再現手順が不明確

## 次のアクション
以下の情報を提供してください：
1. 詳細なエラーログ（スタックトレース含む）
2. 再現手順の詳細化
```

追加情報を取得後、**Phase 1-3に戻る**（調査コンテキストを更新して再実行）。

TodoWriteでPhase 1を`in_progress`のまま維持。

---

### Phase 2: 対策案提示・ユーザーフィードバック

#### 2-1. 対策案の整理

調査結果から `recommended_actions` を抽出し、ユーザーに提示：

```markdown
## 🔍 調査結果サマリー

**根本原因**: データベース接続プールのサイズが小さすぎる（現在: 5）

**影響範囲**: 全ユーザーが影響を受ける（ジョブ一覧ページにアクセス不可）

**重大度**: high

---

## 📋 対策案（優先度順）

### 対策案1: データベース接続プール設定の拡大 [優先度: High]
- **内容**: database.py の pool_size を 5 → 20 に変更
- **工数**: 30分
- **リスク**: 低
- **影響ファイル**: app/services/database.py

### 対策案2: 長時間実行クエリの最適化 [優先度: Medium]
- **内容**: Job.get_all() メソッドでINDEXを使用
- **工数**: 2時間
- **リスク**: 中
- **影響ファイル**: app/models/job.py, migrations/002_add_job_index.sql

### 対策案3: 接続プール監視の追加 [優先度: Low]
- **内容**: Prometheusメトリクスに pool_size, pool_overflow を追加
- **工数**: 1時間
- **リスク**: 低
- **影響ファイル**: app/observability/metrics.py

---

## 💬 どの対策案を実施しますか？

以下から選択してください：
1. **対策案1のみ実施**（最小限の修正、30分）
2. **対策案1+2を実施**（根本的な修正、2.5時間）
3. **全対策案を実施**（完全な修正、3.5時間）
4. **カスタム対応**（別の対策案を提案してください）
```

#### 2-2. ユーザーフィードバックの取得

AskUserQuestionツールを使用してユーザーに確認：

```
どの対策案を実施しますか？

選択肢:
- 対策案1のみ実施（最小限の修正、30分）
- 対策案1+2を実施（根本的な修正、2.5時間）
- 全対策案を実施（完全な修正、3.5時間）
- カスタム対応（別の対策案を提案）
```

ユーザーの選択を記録：

```bash
# ユーザーが「対策案1+2を実施」を選択した場合
SELECTED_ACTIONS="1,2"
echo "✅ ユーザー選択: 対策案1+2を実施"
```

TodoWriteでPhase 2を`completed`に、Phase 3を`in_progress`に設定。

---

### Phase 3: 作業計画立案

#### 3-1. 作業計画コンテキストファイル作成

選択された対策案に基づいて、作業計画を作成：

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/bug-fix/{bug_id}/work-plan-context.json
```

**内容**:
```json
{
  "bug_id": "{bug_id}",
  "bug_description": "データベース接続プールの枯渇によるタイムアウトエラー",
  "selected_actions": [
    {
      "action_id": "1",
      "title": "データベース接続プール設定の拡大",
      "description": "database.py の pool_size を 5 → 20 に変更",
      "files_to_modify": ["app/services/database.py"],
      "estimated_effort": "30分"
    },
    {
      "action_id": "2",
      "title": "長時間実行クエリの最適化",
      "description": "Job.get_all() メソッドでINDEXを使用",
      "files_to_modify": ["app/models/job.py", "migrations/002_add_job_index.sql"],
      "estimated_effort": "2時間"
    }
  ],
  "total_estimated_effort": "2.5時間",
  "deliverables": [
    "app/services/database.py",
    "app/models/job.py",
    "migrations/002_add_job_index.sql",
    "tests/unit/test_database.py",
    "tests/unit/test_job.py"
  ],
  "definition_of_done": [
    "すべての対策が実装される",
    "単体テストカバレッジ 90%以上",
    "結合テスト全シナリオパス",
    "CI/CDグリーン",
    "ステージング環境で動作確認"
  ]
}
```

#### 3-2. 作業計画の表示

作業計画をユーザーに提示：

```markdown
## 📝 作業計画

### タスク1: データベース接続プール設定の拡大
- 所要時間: 30分
- 成果物: app/services/database.py

### タスク2: 長時間実行クエリの最適化
- 所要時間: 2時間
- 成果物: app/models/job.py, migrations/002_add_job_index.sql

### 総作業時間: 2.5時間

### Definition of Done
- [x] すべての対策が実装される
- [x] 単体テストカバレッジ 90%以上
- [x] 結合テスト全シナリオパス
- [x] CI/CDグリーン
- [x] ステージング環境で動作確認
```

TodoWriteでPhase 3を`completed`に、Phase 4を`in_progress`に設定。

---

### Phase 4: TDD修正実施

#### 4-1. TDD修正コンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/bug-fix/{bug_id}/tdd-fix-context.json
```

**内容**:
```json
{
  "bug_id": "{bug_id}",
  "bug_description": "データベース接続プールの枯渇によるタイムアウトエラー",
  "selected_actions": [...],
  "work_plan_tasks": [...],
  "deliverables_checklist": [...],
  "definition_of_done": [...],
  "target_coverage": 90
}
```

#### 4-2. TDD実装サブエージェント呼び出し

以下のテキストを記述してください：

```
Use tdd-impl-agent to fix the bug with TDD approach.

Context file: dev-reports/bug-fix/{bug_id}/tdd-fix-context.json
Output file: dev-reports/bug-fix/{bug_id}/tdd-fix-result.json

Please implement the selected fixes following the Red-Green-Refactor cycle and ensure all tests pass with 90% coverage.
```

#### 4-3. 結果確認

サブエージェントが完了したら、Readツールで結果ファイルを確認：

```bash
cat dev-reports/bug-fix/{bug_id}/tdd-fix-result.json
```

**結果判定**:

##### ケース1: TDD修正成功 (`status: "success"`)

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
  },
  "fixes_applied": [
    "app/services/database.py: pool_size=20に変更",
    "app/models/job.py: INDEX使用に変更"
  ]
}
```

→ **Phase 5へ進む**

TodoWriteでPhase 4を`completed`に、Phase 5を`in_progress`に設定。

##### ケース2: TDD修正失敗 (`status: "failed"`)

ユーザーにエスカレーション：

```
❌ TDD修正が失敗しました

## エラー内容
- カバレッジ: 75.0%（目標: 90%）
- 静的解析エラー: 3件

## 次のアクション
1. 手動でテストを追加する
2. 対策案を再検討する
```

---

### Phase 5: 受入テスト

#### 5-1. 受入テストコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/bug-fix/{bug_id}/acceptance-context.json
```

**内容**:
```json
{
  "bug_id": "{bug_id}",
  "bug_description": "データベース接続プールの枯渇によるタイムアウトエラー",
  "fix_summary": "接続プール設定を拡大し、クエリを最適化",
  "acceptance_criteria": [
    "ジョブ一覧ページが正常に表示される",
    "同時12接続でもエラーが発生しない",
    "レスポンスタイムが3秒以内"
  ],
  "test_scenarios": [
    "シナリオ1: 通常時のジョブ一覧アクセス",
    "シナリオ2: 同時12接続でのジョブ一覧アクセス",
    "シナリオ3: 長時間実行後のジョブ一覧アクセス"
  ]
}
```

#### 5-2. 受入テストサブエージェント呼び出し

以下のテキストを記述してください：

```
Use acceptance-test-agent to verify the bug fix.

Context file: dev-reports/bug-fix/{bug_id}/acceptance-context.json
Output file: dev-reports/bug-fix/{bug_id}/acceptance-result.json

Please execute all test scenarios and verify all acceptance criteria are met.
```

#### 5-3. 結果確認

Readツールで結果ファイルを確認：

```bash
cat dev-reports/bug-fix/{bug_id}/acceptance-result.json
```

**結果判定**:

##### ケース1: 受入テスト成功 (`status: "passed"`)

→ **Phase 6へ進む**

TodoWriteでPhase 5を`completed`に、Phase 6を`in_progress`に設定。

##### ケース2: 受入テスト失敗 (`status: "failed"`)

→ **Phase 4に戻る**（修正が不十分）

---

### Phase 6: 進捗報告

#### 6-1. 進捗レポートコンテキストファイル作成

Writeツールで以下のファイルを作成：

**ファイルパス**:
```
dev-reports/bug-fix/{bug_id}/progress-context.json
```

**内容**:
```json
{
  "bug_id": "{bug_id}",
  "bug_description": "データベース接続プールの枯渇によるタイムアウトエラー",
  "phase_results": {
    "investigation": {
      "status": "completed",
      "root_cause": "接続プール設定が小さすぎる"
    },
    "tdd_fix": {
      "status": "success",
      "coverage": 92.5
    },
    "acceptance": {
      "status": "passed"
    }
  },
  "work_plan_comparison": {
    "planned_tasks": [...],
    "deliverables_status": [...],
    "estimated_vs_actual_hours": {
      "estimated": 2.5,
      "actual": 2.8,
      "variance": "+0.3h"
    }
  }
}
```

#### 6-2. 進捗レポートサブエージェント呼び出し

以下のテキストを記述してください：

```
Use progress-report-agent to generate bug fix report.

Context file: dev-reports/bug-fix/{bug_id}/progress-context.json
Output file: dev-reports/bug-fix/{bug_id}/progress-report.md

Please summarize the bug fix process and results.
```

#### 6-3. レポート表示

サブエージェントが完了したら、Readツールでレポートを読み込んで表示：

```bash
cat dev-reports/bug-fix/{bug_id}/progress-report.md
```

**レポート内容**:
- 不具合サマリー（概要、重大度、影響範囲）
- 根本原因分析
- 実施した対策
- テスト結果（単体、受入）
- 作業計画比較（予定 vs 実績）
- 次のステップ（追加対策があれば）

TodoWriteでPhase 6を`completed`に設定。

---

## 📂 ファイル構造

```
dev-reports/bug-fix/{bug_id}/
├── investigation-context.json    ← 調査の入力
├── investigation-result.json     ← 調査の出力
├── work-plan-context.json        ← 作業計画の入力
├── tdd-fix-context.json          ← TDD修正の入力
├── tdd-fix-result.json           ← TDD修正の出力
├── acceptance-context.json       ← 受入テストの入力
├── acceptance-result.json        ← 受入テストの出力
├── progress-context.json         ← 進捗レポートの入力
└── progress-report.md            ← 進捗レポート（Markdown）
```

---

## 🎯 完了条件

以下をすべて満たすこと：

- ✅ Phase 1: 不具合調査完了（根本原因特定）
- ✅ Phase 2: 対策案提示完了（ユーザーフィードバック取得）
- ✅ Phase 3: 作業計画立案完了
- ✅ Phase 4: TDD修正成功（カバレッジ90%以上、静的解析エラー0件）
- ✅ Phase 5: 受入テスト成功（全シナリオ合格、全受入条件検証済み）
- ✅ Phase 6: 進捗レポート作成完了

---

## 🚨 エラーハンドリング

### サブエージェントがタイムアウトした場合

サブエージェントが10分以上応答しない場合：

```
⚠️ {agent-name} がタイムアウトしました（10分経過）

## 次のアクション
1. サブエージェントを再実行する
2. 手動で該当フェーズを実行する
3. 対策案を簡素化する
```

---

## 📝 使用例

### 基本的な使用方法

```
User: /pm-bug-fix データベース接続エラーが発生

PM Bug Fix:
✅ Phase 1: 不具合調査完了
  - 根本原因: データベース接続プールの枯渇
  - 重大度: high
  - 影響範囲: 全ユーザー

📋 対策案提示:
  1. [High] 接続プール設定の拡大（30分）
  2. [Medium] クエリ最適化（2時間）
  3. [Low] 監視追加（1時間）

💬 どの対策案を実施しますか？
→ ユーザー選択: 対策案1+2を実施

✅ Phase 3: 作業計画立案完了
  - 総作業時間: 2.5時間
  - 成果物: 5ファイル

✅ Phase 4: TDD修正成功
  - カバレッジ: 92.5%
  - テスト: 25/25 passed

✅ Phase 5: 受入テスト成功
  - シナリオ: 3/3 passed

✅ Phase 6: 進捗レポート作成完了

🎉 不具合修正が完了しました！
```

---

## 📚 関連ドキュメント

- [Issue Investigation Agent](../.claude/agents/issue-investigation-agent.md) - 不具合調査専門エージェント
- [TDD Implementation Agent](../.claude/agents/tdd-impl-agent.md) - TDD実装エージェント
- [Acceptance Test Agent](../.claude/agents/acceptance-test-agent.md) - 受入テストエージェント
- [Progress Report Agent](../.claude/agents/progress-report-agent.md) - 進捗報告エージェント
