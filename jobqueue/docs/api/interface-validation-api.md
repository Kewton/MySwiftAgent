# Interface Validation API リファレンス

JobQueue の Interface Validation 機能は、JSON Schema Draft 7 に基づいてタスク間のデータ互換性を検証します。

---

## 概要

Interface Validation は以下の3つの主要コンポーネントで構成されています:

1. **InterfaceMaster**: タスクの入出力スキーマを定義
2. **TaskMaster**: InterfaceMaster を参照してタスクのインターフェースを宣言
3. **Job Validation**: ジョブ作成時・実行時にタスク間の互換性を検証

---

## InterfaceMaster API

### InterfaceMaster 作成

```http
POST /api/v1/interface-masters
```

**リクエストボディ:**

```json
{
  "name": "SearchResultInterface",
  "description": "検索結果のインターフェース定義",
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "max_results": {"type": "integer", "minimum": 1, "maximum": 100}
    },
    "required": ["query"]
  },
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
            "url": {"type": "string", "format": "uri"},
            "snippet": {"type": "string"}
          },
          "required": ["title", "url"]
        }
      },
      "total_count": {"type": "integer"}
    },
    "required": ["results"]
  }
}
```

**レスポンス (201 Created):**

```json
{
  "interface_id": "if_01HXYZ...",
  "name": "SearchResultInterface"
}
```

**エラー (400 Bad Request):**

```json
{
  "detail": "Invalid output_schema: Property 'type' is required at root"
}
```

---

### InterfaceMaster 一覧取得

```http
GET /api/v1/interface-masters?is_active=true&page=1&size=20
```

**クエリパラメータ:**

| パラメータ | 型 | 説明 | デフォルト |
|-----------|------|------|----------|
| `is_active` | boolean | アクティブ状態でフィルタ | なし (全件) |
| `page` | integer | ページ番号 (1始まり) | 1 |
| `size` | integer | ページサイズ (1-100) | 20 |

**レスポンス (200 OK):**

```json
{
  "interfaces": [
    {
      "id": "if_01HXYZ...",
      "name": "SearchResultInterface",
      "description": "検索結果のインターフェース定義",
      "input_schema": { /* ... */ },
      "output_schema": { /* ... */ },
      "is_active": true,
      "created_at": "2025-09-22T10:00:00Z",
      "updated_at": "2025-09-22T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "size": 20
}
```

---

### InterfaceMaster 詳細取得

```http
GET /api/v1/interface-masters/{interface_id}
```

**レスポンス (200 OK):**

```json
{
  "id": "if_01HXYZ...",
  "name": "SearchResultInterface",
  "description": "検索結果のインターフェース定義",
  "input_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "query": {"type": "string"}
    },
    "required": ["query"]
  },
  "output_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "results": {"type": "array"}
    },
    "required": ["results"]
  },
  "is_active": true,
  "created_at": "2025-09-22T10:00:00Z",
  "updated_at": "2025-09-22T10:00:00Z"
}
```

**エラー (404 Not Found):**

```json
{
  "detail": "Interface master not found"
}
```

---

### InterfaceMaster 更新

```http
PUT /api/v1/interface-masters/{interface_id}
```

**リクエストボディ (すべてオプション):**

```json
{
  "name": "UpdatedSearchInterface",
  "description": "更新された説明",
  "input_schema": { /* 新しいスキーマ */ },
  "output_schema": { /* 新しいスキーマ */ },
  "is_active": true
}
```

**レスポンス (200 OK):**

```json
{
  "interface_id": "if_01HXYZ...",
  "name": "UpdatedSearchInterface"
}
```

---

### InterfaceMaster 削除 (論理削除)

```http
DELETE /api/v1/interface-masters/{interface_id}
```

**レスポンス (200 OK):**

```json
{
  "interface_id": "if_01HXYZ...",
  "name": "SearchResultInterface"
}
```

**Note**: 物理削除ではなく `is_active=false` に設定される論理削除です。

---

## TaskMaster Interface Association API

### TaskMaster に InterfaceMaster を関連付け

```http
POST /api/v1/task-masters/{master_id}/interfaces
```

**リクエストボディ:**

```json
{
  "interface_id": "if_01HXYZ...",
  "required": true
}
```

**レスポンス (201 Created):**

```json
{
  "task_master_id": "tm_01ABCD...",
  "interface_id": "if_01HXYZ...",
  "required": true,
  "created_at": "2025-09-22T10:00:00Z"
}
```

**エラー:**

- **404 Not Found**: TaskMaster または InterfaceMaster が存在しない
- **400 Bad Request**: すでに関連付けられている

---

### TaskMaster に関連付けられた Interface 一覧

```http
GET /api/v1/task-masters/{master_id}/interfaces
```

**レスポンス (200 OK):**

```json
[
  {
    "task_master_id": "tm_01ABCD...",
    "interface_id": "if_01HXYZ...",
    "required": true,
    "created_at": "2025-09-22T10:00:00Z"
  }
]
```

---

## Job Validation API

### ジョブ作成時の Interface Validation

```http
POST /api/v1/jobs
```

**リクエストボディ:**

```json
{
  "name": "Search and Analyze Job",
  "method": "GET",
  "url": "https://api.example.com/start",
  "tasks": [
    {"master_id": "tm_search", "sequence": 0},
    {"master_id": "tm_analyze", "sequence": 1}
  ],
  "validate_interfaces": true
}
```

**検証成功時のレスポンス (201 Created):**

```json
{
  "job_id": "j_01WXYZ...",
  "status": "queued",
  "validation_result": {
    "is_valid": true,
    "error_count": 0,
    "warnings": [],
    "validated_at": "2025-09-22T10:00:00Z"
  }
}
```

**検証失敗時のレスポンス (201 Created - ジョブは作成されるが警告付き):**

```json
{
  "job_id": "j_01WXYZ...",
  "status": "queued",
  "validation_result": {
    "is_valid": false,
    "error_count": 2,
    "warnings": [
      {
        "task_index": 0,
        "task_name": "search_task",
        "error": "Output interface 'if_search_out' is incompatible with next task's input interface 'if_analyze_in'",
        "details": [
          "Property 'results' is required in input schema but not guaranteed in output schema",
          "Type mismatch: output 'results[].score' (number) vs input 'results[].score' (integer)"
        ]
      }
    ],
    "validated_at": "2025-09-22T10:00:00Z"
  }
}
```

**Note**:
- 検証失敗時でもジョブは作成されます (201 Created)
- 実行時に `JobExecutor` が検証タグをチェックし、`is_valid=false` の場合は実行をブロックします

---

### ジョブに保存された Validation タグ

ジョブ詳細取得時に `tags` フィールドに検証結果が含まれます:

```http
GET /api/v1/jobs/{job_id}
```

**レスポンス (200 OK):**

```json
{
  "job_id": "j_01WXYZ...",
  "status": "queued",
  "tags": [
    {
      "type": "interface_validation",
      "is_valid": true,
      "error_count": 0,
      "warnings": [],
      "validated_at": "2025-09-22T10:00:00.123456"
    }
  ]
}
```

---

## Worker 実行時の Interface Validation

Worker (`JobExecutor`) はジョブ実行前に以下の検証を行います:

### 1. タグベースの事前検証

```python
# ジョブ実行前のチェック
if job.tags contains {"type": "interface_validation", "is_valid": false}:
    raise ValueError("Job execution blocked: failed interface validation")
```

### 2. タスク実行時の I/O 検証

```python
# タスク実行前: 入力データ検証
validator.validate_data(task_input, task.input_interface.input_schema)

# タスク実行後: 出力データ検証
validator.validate_data(task_output, task.output_interface.output_schema)
```

**検証エラー例:**

```
InterfaceValidationError: Task 'analyze_task' input validation failed:
  - Property 'results' is required but missing
  - Property 'query' type mismatch: expected string, got integer
```

---

## JSON Schema V7 サポート

### サポート対象の Draft 7 機能

| 機能 | 説明 | 例 |
|------|------|-----|
| **type** | データ型の指定 | `"type": "string"` |
| **properties** | オブジェクトのプロパティ定義 | `"properties": {"name": {"type": "string"}}` |
| **required** | 必須プロパティ | `"required": ["name", "age"]` |
| **format** | 文字列フォーマット検証 | `"format": "email"`, `"format": "date-time"` |
| **minimum/maximum** | 数値の範囲制約 | `"minimum": 0, "maximum": 100` |
| **minLength/maxLength** | 文字列長の制約 | `"minLength": 3, "maxLength": 50` |
| **minItems/maxItems** | 配列長の制約 | `"minItems": 1, "maxItems": 10` |
| **enum** | 列挙値の制約 | `"enum": ["active", "inactive"]` |
| **pattern** | 正規表現パターン | `"pattern": "^[A-Z]{3}$"` |
| **items** | 配列アイテムのスキーマ | `"items": {"type": "string"}` |
| **additionalProperties** | 追加プロパティの許可 | `"additionalProperties": false` |
| **anyOf/oneOf/allOf** | スキーマの組み合わせ | `"anyOf": [{...}, {...}]` |

### スキーマ検証の厳密性

- **$schema フィールド必須**: `"$schema": "http://json-schema.org/draft-07/schema#"`
- **type フィールド必須**: ルートレベルで `"type"` を指定
- **format 検証**: `date-time`, `email`, `uri`, `uuid` など Draft 7 標準フォーマットをサポート

---

## エラーコード一覧

| HTTPステータス | エラー | 説明 |
|--------------|--------|------|
| **400 Bad Request** | Invalid input_schema | 入力スキーマが JSON Schema V7 に準拠していない |
| **400 Bad Request** | Invalid output_schema | 出力スキーマが JSON Schema V7 に準拠していない |
| **400 Bad Request** | Interface already associated | TaskMaster に同じ InterfaceMaster が既に関連付けられている |
| **404 Not Found** | Interface master not found | 指定された InterfaceMaster が存在しない |
| **404 Not Found** | Task master not found | 指定された TaskMaster が存在しない |
| **500 Internal Server Error** | Validation service error | 検証サービスの内部エラー |

---

## セキュリティとベストプラクティス

### 1. スキーマのバージョン管理

InterfaceMaster の更新は既存ジョブに影響するため、以下を推奨:

- 互換性のある変更のみ行う（オプションプロパティの追加など）
- 破壊的変更時は新しい InterfaceMaster を作成
- 古い InterfaceMaster は論理削除 (`is_active=false`) にする

### 2. スキーマの複雑度制限

- ネストの深さは 5 階層まで推奨
- 配列のサイズ制約 (`maxItems`) を設定
- 文字列長の制約 (`maxLength`) を設定

### 3. パフォーマンス考慮

- スキーマのキャッシング: InterfaceMaster はアプリケーション起動時にメモリキャッシュ
- 検証のスキップ: 信頼できる内部タスクには `validate_interfaces=false` を使用可能

### 4. 監視とログ

- 検証失敗率のモニタリング
- 検証エラーの詳細ログ記録
- 検証パフォーマンス (処理時間) の追跡

---

## サンプルコード

### Python クライアント例

```python
import httpx

async def create_interface_and_validate():
    async with httpx.AsyncClient() as client:
        # 1. InterfaceMaster 作成
        interface_response = await client.post(
            "http://localhost:8000/api/v1/interface-masters",
            json={
                "name": "EmailInterface",
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
            }
        )
        interface_id = interface_response.json()["interface_id"]

        # 2. TaskMaster に関連付け
        await client.post(
            f"http://localhost:8000/api/v1/task-masters/tm_email_sender/interfaces",
            json={"interface_id": interface_id, "required": True}
        )

        # 3. ジョブ作成 (検証付き)
        job_response = await client.post(
            "http://localhost:8000/api/v1/jobs",
            json={
                "name": "Email Notification Job",
                "method": "POST",
                "url": "https://api.example.com/notify",
                "tasks": [
                    {"master_id": "tm_data_fetch", "sequence": 0},
                    {"master_id": "tm_email_sender", "sequence": 1}
                ],
                "validate_interfaces": True
            }
        )

        validation_result = job_response.json().get("validation_result")
        if not validation_result["is_valid"]:
            print(f"Validation failed: {validation_result['warnings']}")
```

### cURL 例

```bash
# InterfaceMaster 作成
curl -X POST http://localhost:8000/api/v1/interface-masters \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EmailInterface",
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

# ジョブ作成 (検証付き)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Validated Job",
    "method": "GET",
    "url": "https://api.example.com/start",
    "tasks": [
      {"master_id": "tm_search", "sequence": 0},
      {"master_id": "tm_analyze", "sequence": 1}
    ],
    "validate_interfaces": true
  }'
```

---

## 関連ドキュメント

- [Interface Validation ユーザーガイド](../guides/interface-validation-guide.md)
- [JSON Schema Draft 7 仕様](https://json-schema.org/draft-07/json-schema-release-notes.html)
- [JobQueue README](../../README.md)
