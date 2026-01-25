# mySwiftAgentCore API Reference

mySwiftAgentCoreが提供するAPIエンドポイントの仕様です。

## 概要

mySwiftAgentCoreはTaskFlow形式のワークフロー実行エンジンです。
ワークフローの生成、実行、結果取得のAPIを提供します。

## ベースURL

```
http://localhost:8006
```

## エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| POST | `/api/v1/taskflow/generate` | ワークフロー生成 |
| POST | `/api/v1/workflows/execute` | ワークフロー実行 |
| GET | `/api/v1/workflows/runs/{run_id}` | 実行結果取得 |
| GET | `/api/v1/workflows/{workflow_id}` | ワークフロー取得 |

---

## ヘルスチェック

### GET /health

サービスの稼働状態を確認します。

**レスポンス**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## ワークフロー生成

### POST /api/v1/taskflow/generate

ユーザーの指示からTaskFlowワークフローを自動生成します。

**リクエスト**:
```json
{
  "task_id": "string",
  "name": "string",
  "description": "string",
  "interface": {
    "input": { "key": "type" },
    "output": { "key": "type" }
  }
}
```

**レスポンス**:
```json
{
  "name": "workflow-name",
  "version": "1.0.0",
  "steps": [
    {
      "id": "step1",
      "type": "llm",
      "config": { ... }
    }
  ]
}
```

**エラーレスポンス**:
```json
{
  "error": "string",
  "detail": "string"
}
```

---

## ワークフロー実行

### POST /api/v1/workflows/execute

指定したワークフローを実行します。

**リクエスト**:
```json
{
  "project": "default_project",
  "workflow": "workflow_name",
  "inputs": {
    "key": "value"
  }
}
```

**レスポンス**:
```json
{
  "run_id": "uuid",
  "status": "running",
  "created_at": "2026-01-25T00:00:00Z"
}
```

---

## 実行結果取得

### GET /api/v1/workflows/runs/{run_id}

ワークフロー実行の結果を取得します。

**パスパラメータ**:
- `run_id`: 実行ID（UUID）

**レスポンス**:
```json
{
  "run_id": "uuid",
  "status": "completed",
  "result": { ... },
  "created_at": "2026-01-25T00:00:00Z",
  "completed_at": "2026-01-25T00:01:00Z"
}
```

**ステータス**:
| ステータス | 説明 |
|-----------|------|
| `pending` | 実行待ち |
| `running` | 実行中 |
| `completed` | 完了 |
| `failed` | 失敗 |

---

## ワークフロー取得

### GET /api/v1/workflows/{workflow_id}

保存されたワークフロー定義を取得します。

**パスパラメータ**:
- `workflow_id`: ワークフローID

**レスポンス**:
```json
{
  "name": "workflow-name",
  "description": "ワークフローの説明",
  "version": "1.0.0",
  "steps": [ ... ]
}
```

---

## エラーコード

| コード | 説明 |
|--------|------|
| 400 | 不正なリクエスト |
| 404 | リソースが見つからない |
| 422 | バリデーションエラー |
| 500 | サーバーエラー |

---

## 関連ドキュメント

- [TaskFlow形式仕様](../../docs/reference/taskflow-format.md)
- [初めてのワークフロー](../../docs/getting-started/first-workflow.md)
- [ノード実行コンテキスト](./internals/node-execution-context.md)
