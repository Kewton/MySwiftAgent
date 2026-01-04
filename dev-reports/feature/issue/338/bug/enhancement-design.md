# PM Auto-Dev 強化設計: 実装検証機能の追加

**作成日**: 2026-01-04
**背景**: Issue #338 で関数が定義されたが統合されていない問題が発覚

---

## 1. 問題の根本原因

| 問題 | 原因 | 対策 |
|------|------|------|
| 関数が定義のみで呼び出されていない | 統合確認がない | 実装検証フェーズを追加 |
| 受入テストが「存在確認」のみ | テスト設計が不十分 | 統合確認テストを必須化 |
| サブエージェントの成功報告を過信 | 検証プロセスがない | 実装検証サブエージェントを追加 |

---

## 2. 提案: 新フェーズ追加

### 2.1 Phase 2.6: 実装機能一覧の生成【新規】

TDD実装完了後に、実装した機能の一覧を生成する。

**出力ファイル**: `implemented-features.json`

```json
{
  "issue_number": 338,
  "implemented_features": [
    {
      "feature_id": "F1",
      "name": "_transform_to_interface",
      "type": "function",
      "file_path": "jobqueue/app/core/worker.py",
      "line_number": 606,
      "description": "GraphAI出力をoutput_interface定義に変換",
      "expected_callers": ["_execute_tasks"],
      "expected_call_location": "jobqueue/app/core/worker.py"
    },
    {
      "feature_id": "F2",
      "name": "check_interface_compatibility",
      "type": "function",
      "file_path": "expertAgent/.../nodes/evaluator.py",
      "line_number": 30,
      "description": "タスク間インターフェース整合性検証",
      "expected_callers": ["evaluator_node"],
      "expected_call_location": "expertAgent/.../nodes/evaluator.py"
    },
    {
      "feature_id": "F3",
      "name": "OUTPUT_NODE_NAMING_RULE",
      "type": "prompt_rule",
      "file_path": "expertAgent/prompts/workflow_generation/default.yaml",
      "line_number": 25,
      "description": "出力ノード命名規約ルール",
      "expected_callers": ["LLM via prompt"],
      "expected_call_location": "ワークフロー生成時"
    }
  ],
  "test_mappings": [
    {
      "feature_id": "F1",
      "unit_tests": ["test_transform_to_interface_*"],
      "integration_tests": ["test_worker_calls_transform_to_interface"],
      "test_coverage": "unit_only"
    },
    {
      "feature_id": "F2",
      "unit_tests": ["test_check_interface_compatibility_*"],
      "integration_tests": ["test_evaluator_calls_check_interface_compatibility"],
      "test_coverage": "unit_only"
    }
  ]
}
```

---

### 2.2 Phase 2.7: 実装検証サブエージェント【新規】

実装機能一覧に基づいて、各機能が実際に統合されているかを検証する。

**サブエージェント名**: `implementation-verification-agent`

**入力**: `implemented-features.json`
**出力**: `implementation-verification-result.json`

```json
{
  "status": "failed",
  "verification_results": [
    {
      "feature_id": "F1",
      "name": "_transform_to_interface",
      "checks": {
        "function_exists": {
          "passed": true,
          "evidence": "Found at jobqueue/app/core/worker.py:606"
        },
        "function_called": {
          "passed": false,
          "evidence": "No call found in worker.py",
          "expected_location": "jobqueue/app/core/worker.py:223付近",
          "grep_command": "grep -n '_transform_to_interface(' jobqueue/app/core/worker.py"
        },
        "unit_test_exists": {
          "passed": true,
          "evidence": "Found test_transform_to_interface_* in tests/unit/"
        },
        "integration_test_exists": {
          "passed": false,
          "evidence": "No integration test found",
          "missing_test": "test_worker_calls_transform_to_interface"
        }
      },
      "overall": "FAILED",
      "failure_reason": "Function exists but is NOT called (dead code)"
    },
    {
      "feature_id": "F2",
      "name": "check_interface_compatibility",
      "checks": {
        "function_exists": { "passed": true },
        "function_called": { "passed": false },
        "unit_test_exists": { "passed": true },
        "integration_test_exists": { "passed": false }
      },
      "overall": "FAILED",
      "failure_reason": "Function exists but is NOT called (dead code)"
    },
    {
      "feature_id": "F3",
      "name": "OUTPUT_NODE_NAMING_RULE",
      "checks": {
        "rule_exists": { "passed": true },
        "prompt_includes_rule": { "passed": true }
      },
      "overall": "PASSED"
    }
  ],
  "summary": {
    "total_features": 3,
    "passed": 1,
    "failed": 2,
    "dead_code_detected": 2
  },
  "recommended_actions": [
    {
      "feature_id": "F1",
      "action": "worker.py の _execute_tasks 内で _transform_to_interface を呼び出す",
      "file": "jobqueue/app/core/worker.py",
      "line": 223
    },
    {
      "feature_id": "F2",
      "action": "evaluator_node 内で check_interface_compatibility を呼び出す",
      "file": "expertAgent/.../nodes/evaluator.py",
      "line": 259
    }
  ]
}
```

---

## 3. 検証ロジック

### 3.1 関数/クラスの統合検証

| チェック項目 | 検証方法 | 合格基準 |
|-------------|---------|---------|
| 関数が存在するか | `grep -n "def {func_name}" {file}` | マッチあり |
| 関数が呼び出されているか | `grep -rn "{func_name}(" {project}/` | マッチあり（定義以外で） |
| インポートされているか | `grep -n "from .* import.*{func_name}"` | マッチあり |
| エクスポートされているか | `grep -n "{func_name}" __init__.py` | マッチあり |

### 3.2 プロンプトルールの統合検証

| チェック項目 | 検証方法 | 合格基準 |
|-------------|---------|---------|
| ルールが存在するか | `grep -n "{rule_pattern}" {prompt_file}` | マッチあり |
| LLMに渡されるか | プロンプト生成コードで参照されているか | 参照あり |

### 3.3 テストカバレッジの検証

| チェック項目 | 検証方法 | 合格基準 |
|-------------|---------|---------|
| 単体テストが存在するか | `find tests/unit -name "*{feature}*"` | ファイルあり |
| 統合テストが存在するか | `find tests/integration -name "*{feature}*"` | ファイルあり |
| 統合確認テストがあるか | テスト内で実際の呼び出しを確認 | テストあり |

---

## 4. フロー変更

### 現在のフロー

```
Phase 2: TDD実装
    ↓
Phase 2.5: TDD結果検証（ファイル変更・統合の手動確認）
    ↓
Phase 3: 受入テスト
```

### 新しいフロー

```
Phase 2: TDD実装
    ↓
Phase 2.5: TDD結果検証（既存）
    ↓
Phase 2.6: 実装機能一覧の生成【新規】
    ↓
Phase 2.7: 実装検証サブエージェント【新規】
    ↓
    ├─ PASSED → Phase 3へ
    └─ FAILED → 不足タスクを特定し、Phase 2を再実行
    ↓
Phase 3: 受入テスト
```

---

## 5. サブエージェント定義

### 5.1 implementation-verification-agent.md

```markdown
---
model: sonnet
description: "実装検証: 関数統合・テストカバレッジ・デッドコード検出"
---

# 実装検証エージェント

## 概要
実装機能一覧に基づいて、各機能が実際にコードベースに統合されているかを検証します。

## 入力
- `implemented-features.json`: 実装機能一覧

## 検証項目

### 1. 関数/クラスの統合確認
- 関数が定義されているか（存在確認）
- 関数が呼び出されているか（統合確認）← 最重要
- インポート/エクスポートされているか

### 2. テストカバレッジ確認
- 単体テストが存在するか
- 統合テストが存在するか
- 統合テストで「呼び出し確認」がされているか

### 3. デッドコード検出
- 定義されているが呼び出されていない関数
- インポートされているが使用されていない関数

## 出力
- `implementation-verification-result.json`: 検証結果
```

---

## 6. 期待効果

| 効果 | 説明 |
|------|------|
| **デッドコード検出** | 定義のみで呼び出されていない関数を自動検出 |
| **統合漏れ防止** | 関数が実際に使用されているか検証 |
| **テスト品質向上** | 「存在確認」だけでなく「統合確認」を強制 |
| **早期問題発見** | 受入テスト前に問題を検出 |

---

## 7. 実装スケジュール

| 優先度 | タスク | 工数 |
|:------:|--------|------|
| P0 | implementation-verification-agent 作成 | 2h |
| P0 | pm-auto-dev.md に Phase 2.6, 2.7 追加 | 1h |
| P1 | 既存テストに統合確認テストを追加するガイドライン作成 | 1h |

---

## 8. 承認待ち

この設計で進めてよろしいでしょうか？

- [ ] Phase 2.6: 実装機能一覧の生成
- [ ] Phase 2.7: 実装検証サブエージェント
- [ ] implementation-verification-agent の作成
