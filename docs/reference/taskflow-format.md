# TaskFlow形式仕様

mySwiftAgentCoreで使用されるワークフロー定義形式（TaskFlow）の仕様です。

## 概要

TaskFlowは、AIエージェントのワークフローをJSON形式で定義するための形式です。
シンプルな構造で、柔軟なワークフロー設計を可能にします。

## 基本構造

```json
{
  "name": "workflow-name",
  "description": "ワークフローの説明",
  "version": "1.0.0",
  "steps": [
    {
      "id": "step1",
      "type": "llm",
      "config": {
        "model": "gpt-4o-mini",
        "prompt": "プロンプトテキスト"
      }
    }
  ]
}
```

## 必須フィールド

| フィールド | 型 | 説明 |
|-----------|------|------|
| `name` | string | ワークフロー名（英数字とハイフン） |
| `description` | string | ワークフローの説明 |
| `version` | string | セマンティックバージョン（例: "1.0.0"） |
| `steps` | array | ステップの配列 |

## ステップ定義

### 共通フィールド

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `id` | string | ✅ | ステップの一意識別子 |
| `type` | string | ✅ | ステップの種類（後述） |
| `config` | object | ✅ | ステップ固有の設定 |
| `depends_on` | array | - | 依存する前ステップのID配列 |
| `condition` | string | - | 実行条件（式） |

### ステップ種類（type）

| type | 説明 | 必須config |
|------|------|------------|
| `llm` | LLM呼び出し | `model`, `prompt` |
| `api` | 外部API呼び出し | `endpoint`, `method` |
| `transform` | データ変換 | `expression` |
| `condition` | 条件分岐 | `expression`, `then`, `else` |
| `loop` | ループ処理 | `items`, `body` |

## ステップ種類の詳細

### LLMステップ

```json
{
  "id": "generate",
  "type": "llm",
  "config": {
    "model": "gpt-4o-mini",
    "prompt": "以下のテキストを要約してください:\n${inputs.text}",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**configフィールド**:

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `model` | string | ✅ | モデル名（gpt-4o-mini, claude-3-5-sonnetなど） |
| `prompt` | string | ✅ | プロンプトテンプレート |
| `temperature` | number | - | 生成温度（0.0-2.0、デフォルト: 0.7） |
| `max_tokens` | number | - | 最大トークン数 |
| `system_prompt` | string | - | システムプロンプト |

### APIステップ

```json
{
  "id": "search",
  "type": "api",
  "config": {
    "endpoint": "google_search",
    "method": "POST",
    "params": {
      "query": "${inputs.keyword}",
      "num": 10
    }
  }
}
```

**configフィールド**:

| フィールド | 型 | 必須 | 説明 |
|-----------|------|------|------|
| `endpoint` | string | ✅ | エンドポイント名またはURL |
| `method` | string | - | HTTPメソッド（デフォルト: GET） |
| `params` | object | - | リクエストパラメータ |
| `headers` | object | - | リクエストヘッダー |
| `body` | object | - | リクエストボディ |

### 条件分岐ステップ

```json
{
  "id": "check_result",
  "type": "condition",
  "config": {
    "expression": "${steps.search.result.count} > 0",
    "then": "process_results",
    "else": "no_results"
  }
}
```

## 変数参照

### 変数の種類

| 変数 | 構文 | 説明 |
|------|------|------|
| 入力パラメータ | `${inputs.xxx}` | ワークフロー実行時の入力値 |
| ステップ結果 | `${steps.xxx.result}` | 前ステップの実行結果 |
| 環境変数 | `${env.XXX}` | 環境変数の値 |
| シークレット | `${secrets.XXX}` | myVaultから取得したシークレット |

### 使用例

```json
{
  "id": "summarize",
  "type": "llm",
  "config": {
    "model": "gpt-4o-mini",
    "prompt": "以下の検索結果を要約:\n${steps.search.result}\n\nキーワード: ${inputs.keyword}"
  },
  "depends_on": ["search"]
}
```

## 依存関係

`depends_on`を使用して、ステップ間の実行順序を制御します。

```json
{
  "steps": [
    {
      "id": "step1",
      "type": "llm",
      "config": { "..." }
    },
    {
      "id": "step2",
      "type": "llm",
      "config": { "..." },
      "depends_on": ["step1"]
    },
    {
      "id": "step3",
      "type": "llm",
      "config": { "..." },
      "depends_on": ["step1", "step2"]
    }
  ]
}
```

## 完全な例

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
      "id": "check_results",
      "type": "condition",
      "config": {
        "expression": "${steps.search.result.items.length} > 0",
        "then": "summarize",
        "else": "no_results"
      },
      "depends_on": ["search"]
    },
    {
      "id": "summarize",
      "type": "llm",
      "config": {
        "model": "gpt-4o-mini",
        "prompt": "以下の検索結果を日本語で要約してください:\n\n${steps.search.result.items}"
      },
      "depends_on": ["check_results"]
    },
    {
      "id": "no_results",
      "type": "transform",
      "config": {
        "expression": "{ \"message\": \"検索結果が見つかりませんでした\" }"
      },
      "depends_on": ["check_results"]
    }
  ]
}
```

## ファイル配置

```
mySwiftAgentCore/
├── config/
│   └── taskflows/
│       └── {project_name}/
│           └── {workflow_name}.json    ← 手動作成ワークフロー
└── generated/
    └── workflows/
        └── {project_name}/
            └── {workflow_name}/
                └── {workflow_name}.json ← 自動生成ワークフロー
```

## バリデーション

ワークフローは以下の条件を満たす必要があります：

1. **一意のステップID**: 全ステップのIDが一意
2. **有効な依存関係**: `depends_on`が既存のステップIDを参照
3. **循環依存なし**: ステップ間に循環参照がない
4. **必須フィールド**: 各ステップタイプの必須configが設定済み

## 関連ドキュメント

- [初めてのワークフロー](../getting-started/first-workflow.md)
- [TaskFlow Generator API](./api/taskflow-generator-api.yaml)
- [mySwiftAgentCore README](../../mySwiftAgentCore/README.md)
