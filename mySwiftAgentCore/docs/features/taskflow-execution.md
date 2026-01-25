# TaskFlow実行エンジン

mySwiftAgentCoreのTaskFlow実行エンジンの詳細仕様です。

## 概要

TaskFlow実行エンジンは、JSON形式で定義されたワークフローを解析し、
各ステップを順次または並列に実行するエンジンです。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                    TaskFlow Execution Engine                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Workflow    │  │    Step       │  │    Node       │       │
│  │   Parser      │→ │   Scheduler   │→ │   Executor    │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│          │                  │                  │                │
│          ▼                  ▼                  ▼                │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Validation  │  │  Dependency   │  │    Result     │       │
│  │   Layer       │  │  Resolution   │  │   Collector   │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 実行フロー

1. **ワークフロー解析**: JSON定義を解析し、ステップグラフを構築
2. **バリデーション**: 定義の妥当性を検証
3. **依存解決**: ステップ間の依存関係を解決
4. **実行スケジューリング**: 実行順序を決定
5. **ノード実行**: 各ステップを実行
6. **結果収集**: 実行結果を収集・統合

## ノードタイプ

### LLMノード

LLM（大規模言語モデル）を呼び出すノードです。

```json
{
  "id": "generate",
  "type": "llm",
  "config": {
    "model": "gpt-4o-mini",
    "prompt": "プロンプトテンプレート",
    "temperature": 0.7
  }
}
```

**サポートモデル**:
- `gpt-4o-mini`
- `gpt-4o`
- `claude-3-5-sonnet`
- `claude-3-5-haiku`

### APIノード

外部APIを呼び出すノードです。

```json
{
  "id": "search",
  "type": "api",
  "config": {
    "endpoint": "google_search",
    "params": {
      "query": "${inputs.keyword}"
    }
  }
}
```

### 変換ノード

データを変換するノードです。

```json
{
  "id": "transform",
  "type": "transform",
  "config": {
    "expression": "data.map(item => item.title)"
  }
}
```

## 変数参照

### 構文

| パターン | 説明 | 例 |
|---------|------|-----|
| `${inputs.xxx}` | 入力パラメータ | `${inputs.keyword}` |
| `${steps.xxx.result}` | ステップ結果 | `${steps.search.result}` |
| `${env.XXX}` | 環境変数 | `${env.API_KEY}` |
| `${secrets.XXX}` | シークレット | `${secrets.OPENAI_KEY}` |

### 変数解決タイミング

変数は実行時に解決されます。参照先のステップが完了していない場合、
そのステップの完了を待ちます。

## エラーハンドリング

### リトライ設定

```json
{
  "id": "api_call",
  "type": "api",
  "config": { ... },
  "retry": {
    "max_attempts": 3,
    "backoff_ms": 1000
  }
}
```

### フォールバック

```json
{
  "id": "main",
  "type": "llm",
  "config": { ... },
  "fallback": "fallback_step"
}
```

## パフォーマンス

### 並列実行

依存関係のないステップは自動的に並列実行されます。

```json
{
  "steps": [
    { "id": "step1", "type": "api", ... },
    { "id": "step2", "type": "api", ... },
    { "id": "step3", "type": "llm", "depends_on": ["step1", "step2"] }
  ]
}
```

上記の場合、`step1`と`step2`は並列実行され、両方が完了後に`step3`が実行されます。

### キャッシング

同一パラメータでの再実行時はキャッシュが利用されます。

## 関連ドキュメント

- [API Reference](../API_REFERENCE.md)
- [TaskFlow形式仕様](../../../docs/reference/taskflow-format.md)
- [ノード実行コンテキスト](../internals/node-execution-context.md)
