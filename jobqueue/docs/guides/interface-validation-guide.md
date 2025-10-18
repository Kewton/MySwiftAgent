# Interface Validation ユーザーガイド

このガイドでは、JobQueue の Interface Validation 機能を使用してタスク間のデータ互換性を保証する方法を説明します。

---

## 目次

1. [概要](#概要)
2. [なぜ Interface Validation が必要か](#なぜ-interface-validation-が必要か)
3. [基本概念](#基本概念)
4. [セットアップガイド](#セットアップガイド)
5. [実践チュートリアル](#実践チュートリアル)
6. [トラブルシューティング](#トラブルシューティング)
7. [ベストプラクティス](#ベストプラクティス)

---

## 概要

**Interface Validation** は、ジョブ内の複数タスクを連鎖実行する際に、タスク間のデータ互換性を自動検証する機能です。

### 主な機能

✅ **作成時検証**: ジョブ作成時にタスク間の互換性を事前チェック
✅ **実行時検証**: Worker がタスクの入出力データを JSON Schema で検証
✅ **詳細なエラーレポート**: 互換性エラーの原因と箇所を明確に表示
✅ **実行ブロック**: 検証失敗したジョブの実行を防止

---

## なぜ Interface Validation が必要か

### 問題: 実行時エラーの発見が遅い

従来のジョブキューでは、タスク間のデータ不整合は**実行時にしか検出できません**でした。

**例: 検索 → 分析ジョブ**

```
タスク1 (検索API):
  出力: {"items": [...], "total": 10}

タスク2 (分析API):
  期待入力: {"results": [...], "count": 10}

結果: タスク2 が実行時エラー!
```

この場合、以下の問題が発生します:

- ❌ ジョブが途中で失敗
- ❌ タスク1 の処理コストが無駄になる
- ❌ エラー原因の特定に時間がかかる

### 解決: Interface Validation による事前検証

Interface Validation を使用すると、**ジョブ作成時に互換性を検証**できます:

```
POST /api/v1/jobs
{
  "tasks": [...],
  "validate_interfaces": true  ← 検証を有効化
}

→ レスポンス:
{
  "validation_result": {
    "is_valid": false,
    "warnings": [
      "Task 1 output 'items' does not match Task 2 input 'results'"
    ]
  }
}
```

✅ ジョブ作成時にエラーを発見
✅ 実行前に修正可能
✅ 無駄なリソース消費を防止

---

## 基本概念

### 1. InterfaceMaster (インターフェースマスター)

タスクの入出力データ構造を **JSON Schema** で定義したテンプレートです。

**例: 検索結果インターフェース**

```json
{
  "name": "SearchResultInterface",
  "output_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": {"type": "string"},
            "url": {"type": "string"}
          }
        }
      }
    },
    "required": ["results"]
  }
}
```

### 2. TaskMaster Interface Association (関連付け)

TaskMaster に InterfaceMaster を関連付けることで、「このタスクはこのデータ構造を出力する」と宣言します。

```
TaskMaster "google_search"
  ↓ 関連付け
InterfaceMaster "SearchResultInterface"
```

### 3. Job Validation (ジョブ検証)

ジョブ作成時に、連続するタスクの出力と入力が互換性があるかチェックします。

```
Task 1 (output_interface) → Task 2 (input_interface)
                         ↓
                  互換性チェック
```

---

## セットアップガイド

### ステップ 1: InterfaceMaster を作成

```bash
curl -X POST http://localhost:8000/api/v1/interface-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SearchResultInterface",
    "description": "Google検索結果のデータ構造",
    "output_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "results": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": {"type": "string"},
              "url": {"type": "string"},
              "snippet": {"type": "string"}
            },
            "required": ["title", "url"]
          }
        },
        "total_count": {"type": "integer"}
      },
      "required": ["results"]
    }
  }'
```

**レスポンス:**

```json
{
  "interface_id": "if_01HXYZ...",
  "name": "SearchResultInterface"
}
```

### ステップ 2: TaskMaster に InterfaceMaster を関連付け

```bash
curl -X POST http://localhost:8000/api/v1/task-masters/tm_google_search/interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "interface_id": "if_01HXYZ...",
    "required": true
  }'
```

### ステップ 3: ジョブ作成時に検証を有効化

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Search and Analyze Job",
    "method": "GET",
    "url": "https://api.example.com/start",
    "tasks": [
      {"master_id": "tm_google_search", "sequence": 0},
      {"master_id": "tm_text_analyzer", "sequence": 1}
    ],
    "validate_interfaces": true
  }'
```

**検証成功時:**

```json
{
  "job_id": "j_01WXYZ...",
  "status": "queued",
  "validation_result": {
    "is_valid": true,
    "error_count": 0
  }
}
```

**検証失敗時:**

```json
{
  "job_id": "j_01WXYZ...",
  "status": "queued",
  "validation_result": {
    "is_valid": false,
    "error_count": 1,
    "warnings": [
      {
        "task_index": 0,
        "error": "Output schema incompatible with next task input"
      }
    ]
  }
}
```

---

## 実践チュートリアル

### チュートリアル 1: 検索 → メール送信ジョブ

このチュートリアルでは、Google検索結果を取得し、その結果をメールで送信するジョブを作成します。

#### ステップ 1: InterfaceMaster を2つ作成

**1.1 検索結果インターフェース**

```bash
curl -X POST http://localhost:8000/api/v1/interface-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SearchResultInterface",
    "output_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "results": {"type": "array"},
        "count": {"type": "integer"}
      },
      "required": ["results"]
    }
  }'
```

**1.2 メール入力インターフェース**

```bash
curl -X POST http://localhost:8000/api/v1/interface-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EmailInterface",
    "input_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "to": {"type": "string", "format": "email"},
        "subject": {"type": "string"},
        "body": {"type": "string"}
      },
      "required": ["to", "subject", "body"]
    },
    "output_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "message_id": {"type": "string"},
        "status": {"type": "string", "enum": ["sent", "failed"]}
      },
      "required": ["message_id", "status"]
    }
  }'
```

#### ステップ 2: TaskMaster を作成・関連付け

**2.1 検索タスク作成**

```bash
curl -X POST http://localhost:8000/api/v1/task-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "google_search_task",
    "method": "GET",
    "url": "https://api.example.com/search",
    "timeout_sec": 30
  }'
# → master_id: tm_01SEARCH...
```

**2.2 検索タスクに SearchResultInterface を関連付け**

```bash
curl -X POST http://localhost:8000/api/v1/task-masters/tm_01SEARCH.../interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "interface_id": "if_01SEARCH...",
    "required": true
  }'
```

**2.3 メール送信タスク作成 & 関連付け**

```bash
# TaskMaster 作成
curl -X POST http://localhost:8000/api/v1/task-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "email_sender_task",
    "method": "POST",
    "url": "https://api.example.com/send-email",
    "timeout_sec": 15
  }'
# → master_id: tm_01EMAIL...

# EmailInterface を関連付け
curl -X POST http://localhost:8000/api/v1/task-masters/tm_01EMAIL.../interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "interface_id": "if_01EMAIL...",
    "required": true
  }'
```

#### ステップ 3: ジョブ作成 (検証付き)

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Search and Email Notification",
    "method": "GET",
    "url": "https://api.example.com/start",
    "tasks": [
      {"master_id": "tm_01SEARCH...", "sequence": 0},
      {"master_id": "tm_01EMAIL...", "sequence": 1}
    ],
    "validate_interfaces": true
  }'
```

**期待される結果:**

```json
{
  "job_id": "j_01JOB...",
  "status": "queued",
  "validation_result": {
    "is_valid": false,
    "error_count": 1,
    "warnings": [
      {
        "task_index": 0,
        "error": "Task 'google_search_task' output does not match 'email_sender_task' input",
        "details": [
          "Output schema has 'results' but input expects 'to', 'subject', 'body'"
        ]
      }
    ]
  }
}
```

**問題点**: 検索結果の `results` フィールドとメール送信の `to/subject/body` が不一致!

#### ステップ 4: データ変換タスクを追加

不一致を解決するため、中間にデータ変換タスクを追加します:

```bash
# 変換タスク用 InterfaceMaster 作成
curl -X POST http://localhost:8000/api/v1/interface-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SearchToEmailInterface",
    "input_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "results": {"type": "array"}
      },
      "required": ["results"]
    },
    "output_schema": {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "to": {"type": "string", "format": "email"},
        "subject": {"type": "string"},
        "body": {"type": "string"}
      },
      "required": ["to", "subject", "body"]
    }
  }'

# 変換 TaskMaster 作成
curl -X POST http://localhost:8000/api/v1/task-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "search_to_email_transformer",
    "method": "POST",
    "url": "https://api.example.com/transform",
    "timeout_sec": 10
  }'
# → master_id: tm_01TRANS...

# Interface 関連付け
curl -X POST http://localhost:8000/api/v1/task-masters/tm_01TRANS.../interfaces \
  -H "Content-Type: application/json" \
  -d '{
    "interface_id": "if_01TRANS...",
    "required": true
  }'
```

#### ステップ 5: 修正版ジョブ作成

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Search → Transform → Email",
    "method": "GET",
    "url": "https://api.example.com/start",
    "tasks": [
      {"master_id": "tm_01SEARCH...", "sequence": 0},
      {"master_id": "tm_01TRANS...", "sequence": 1},
      {"master_id": "tm_01EMAIL...", "sequence": 2}
    ],
    "validate_interfaces": true
  }'
```

**成功!**

```json
{
  "job_id": "j_01JOB...",
  "status": "queued",
  "validation_result": {
    "is_valid": true,
    "error_count": 0
  }
}
```

---

## トラブルシューティング

### 問題 1: "Property 'XXX' is required but missing"

**エラー例:**

```json
{
  "error": "Property 'email' is required but missing in output schema"
}
```

**原因**: 前のタスクの出力スキーマに、次のタスクの必須フィールドが含まれていない

**解決方法:**

1. 前のタスクの `output_schema` に不足しているプロパティを追加
2. 次のタスクの `input_schema` で `required` から削除（オプションにする）
3. 中間に変換タスクを追加

### 問題 2: "Type mismatch: expected string, got integer"

**エラー例:**

```json
{
  "error": "Type mismatch: output 'count' (integer) vs input 'count' (string)"
}
```

**原因**: プロパティ名は同じだが、型が異なる

**解決方法:**

1. スキーマの型を統一する
2. 型変換タスクを追加する
3. `anyOf` を使用して複数型を許可:

```json
{
  "count": {
    "anyOf": [
      {"type": "string"},
      {"type": "integer"}
    ]
  }
}
```

### 問題 3: "Job execution blocked: failed interface validation"

**エラー例:**

```
ValueError: Job execution blocked: failed interface validation
```

**原因**: 検証失敗 (`is_valid=false`) のジョブを実行しようとした

**解決方法:**

1. ジョブの検証結果を確認:

```bash
curl http://localhost:8000/api/v1/jobs/{job_id}
```

2. `validation_result.warnings` を確認してエラー原因を特定
3. InterfaceMaster または TaskMaster の関連付けを修正
4. 新しいジョブを再作成

### 問題 4: "Invalid input_schema: Property '$schema' is required"

**原因**: JSON Schema に `$schema` フィールドが不足

**解決方法:**

すべてのスキーマに以下を追加:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  ...
}
```

---

## ベストプラクティス

### 1. InterfaceMaster の命名規則

推奨命名パターン:

- **データ種別 + Interface**: `SearchResultInterface`, `UserDataInterface`
- **プロトコル + データ種別**: `HttpSearchResultInterface`, `GrpcUserDataInterface`
- **バージョン付き**: `SearchResultV1Interface`, `SearchResultV2Interface`

### 2. スキーマの粒度

**推奨: 細かすぎず、粗すぎず**

❌ **細かすぎる例**:

```json
{
  "name": "StringOnlyInterface",
  "output_schema": {
    "type": "string"
  }
}
```

→ 汎用すぎて検証が弱い

❌ **粗すぎる例**:

```json
{
  "name": "ComplexInterface",
  "output_schema": {
    "type": "object",
    "properties": {
      "user": { /* 30個のプロパティ */ },
      "order": { /* 20個のプロパティ */ },
      "payment": { /* 15個のプロパティ */ }
    }
  }
}
```

→ 複雑すぎて保守が困難

✅ **適切な粒度**:

```json
{
  "name": "UserSummaryInterface",
  "output_schema": {
    "type": "object",
    "properties": {
      "user_id": {"type": "string"},
      "name": {"type": "string"},
      "email": {"type": "string", "format": "email"}
    },
    "required": ["user_id", "name"]
  }
}
```

→ ドメイン単位で適切にまとめる

### 3. 後方互換性の維持

**破壊的変更を避ける:**

❌ **NG: 既存プロパティの削除**

```json
// 旧バージョン
{
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"}
  }
}

// 新バージョン (破壊的変更!)
{
  "properties": {
    "name": {"type": "string"}
    // age が削除された!
  }
}
```

✅ **OK: 新プロパティの追加 (オプション)**

```json
// 新バージョン (後方互換)
{
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"},
    "email": {"type": "string"}  // 新規追加
  },
  "required": ["name", "age"]  // email はオプション
}
```

✅ **OK: 新しい InterfaceMaster を作成**

```json
// 旧: UserV1Interface
// 新: UserV2Interface (別物として作成)
```

### 4. 検証スキップの適切な使用

**検証をスキップすべきケース:**

- ✅ 内部タスク間の連携 (スキーマが100%保証されている場合)
- ✅ プロトタイプ・開発中のジョブ
- ✅ パフォーマンスが最優先される場合

**スキップ方法:**

```json
{
  "tasks": [...],
  "validate_interfaces": false  // 検証をスキップ
}
```

**注意**: スキップした場合、実行時エラーのリスクが高まります!

### 5. モニタリングとアラート

**推奨監視項目:**

1. **検証失敗率**: `(validation_result.is_valid=false のジョブ数) / (全ジョブ数)`
2. **検証エラー頻度の高い TaskMaster**: トップ10をダッシュボードに表示
3. **検証パフォーマンス**: 検証処理時間の P50/P95/P99

**アラート設定例:**

- 検証失敗率が 10% を超えたらアラート
- 特定の TaskMaster で検証エラーが 5 回/時間を超えたらアラート

---

## よくある質問 (FAQ)

### Q1: 検証失敗したジョブはどうなりますか?

A: ジョブは作成されますが、`is_valid=false` のタグが付与されます。Worker は実行時にこのタグをチェックし、検証失敗のジョブは実行をブロックします。

### Q2: 既存のジョブに Interface Validation を追加できますか?

A: 新規ジョブのみが検証対象です。既存ジョブは再作成が必要です。

### Q3: JSON Schema V7 以外のバージョンをサポートしていますか?

A: 現在は JSON Schema Draft 7 のみサポートしています。Draft 6 や 2019-09 には対応していません。

### Q4: スキーマ検証のパフォーマンスへの影響は?

A: 検証処理は平均 10-50ms です。複雑なスキーマでも 100ms 以下に収まります。

### Q5: InterfaceMaster を更新した場合、既存のジョブに影響しますか?

A: 影響します。InterfaceMaster を参照する TaskMaster を使用している既存ジョブは、次回実行時に新しいスキーマで検証されます。後方互換性を維持することを強く推奨します。

---

## まとめ

Interface Validation を使用することで:

✅ **事前にエラーを発見**: ジョブ作成時に互換性をチェック
✅ **実行時エラーを防止**: Worker が入出力データを厳密に検証
✅ **開発効率向上**: エラー原因の特定が容易
✅ **運用コスト削減**: 無駄なジョブ実行を防止

**次のステップ:**

- [Interface Validation API リファレンス](../api/interface-validation-api.md) で詳細な API 仕様を確認
- [サンプルプロジェクト](../../examples/interface-validation/) で実践的な使用例を参照
- [JobQueue README](../../README.md) でその他の機能を確認

---

**フィードバック・質問:**

ご不明点や改善要望がある場合は、GitHub Issues までお気軽にお問い合わせください。
