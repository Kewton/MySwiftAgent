# 初めてのワークフロー

MySwiftAgentで最初のワークフローを作成し、実行するガイドです。

## 概要

MySwiftAgentでは、以下の2つの方法でワークフローを実行できます：

1. **mySwiftAgentCore** - TaskFlow形式（推奨）
2. **graphAiServer** - GraphAI OSS形式

基本的には **mySwiftAgentCore** を使用してください。

## 前提条件

- サービスが起動していること（`make dev-all`）
- LLM APIキーが設定されていること

## TaskFlowワークフローの作成

### 1. ワークフロー定義ファイルの作成

`mySwiftAgentCore/config/taskflows/` にJSONファイルを作成：

```json
{
  "name": "hello-world",
  "description": "最初のワークフロー",
  "version": "1.0.0",
  "steps": [
    {
      "id": "step1",
      "type": "llm",
      "config": {
        "model": "gpt-4o-mini",
        "prompt": "Hello! Please introduce yourself briefly."
      }
    }
  ]
}
```

### 2. ワークフローの実行

```bash
curl -X POST http://localhost:8006/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "hello-world",
    "inputs": {}
  }'
```

### 3. 実行結果の確認

```bash
curl http://localhost:8006/api/v1/workflows/runs/{run_id}
```

## Web UI からの実行

### 1. myAgentDesk にアクセス

ブラウザで http://localhost:5173 を開きます。

### 2. ジョブの作成

1. 「新規ジョブ」ボタンをクリック
2. ジョブ名とプロンプトを入力
3. 「作成」をクリック

### 3. ジョブの実行

1. ジョブ一覧から作成したジョブを選択
2. 「実行」ボタンをクリック
3. 実行結果を確認

## 複数ステップのワークフロー

より複雑なワークフローの例：

```json
{
  "name": "search-and-summarize",
  "description": "検索して要約するワークフロー",
  "version": "1.0.0",
  "steps": [
    {
      "id": "search",
      "type": "api",
      "config": {
        "endpoint": "google_search",
        "params": {
          "query": "${inputs.keyword}"
        }
      }
    },
    {
      "id": "summarize",
      "type": "llm",
      "config": {
        "model": "gpt-4o-mini",
        "prompt": "以下の検索結果を要約してください:\n${steps.search.result}"
      },
      "depends_on": ["search"]
    }
  ]
}
```

## ワークフロー変数

| 変数 | 説明 | 例 |
|------|------|-----|
| `${inputs.xxx}` | 入力パラメータ | `${inputs.keyword}` |
| `${steps.xxx.result}` | 前ステップの結果 | `${steps.search.result}` |
| `${env.XXX}` | 環境変数 | `${env.API_KEY}` |

## 次のステップ

- [TaskFlow形式仕様](../reference/taskflow-format.md) - 詳細な仕様
- [開発ワークフロー](../development/workflow.md) - 開発プロセス
- [mySwiftAgentCore README](../../mySwiftAgentCore/README.md) - プロジェクト詳細

---

**トラブルシューティング**:
- ワークフローが実行されない → [トラブルシューティング](../operations/troubleshooting.md)
- LLMエラー → [環境変数一覧](../reference/environment-variables.md) でAPIキーを確認
