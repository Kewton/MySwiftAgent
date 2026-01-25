# GraphAI Input Schema 仕様

**最終更新**: 2025-10-16
**対象バージョン**: GraphAI v2.0.15

このドキュメントは、GraphAI APIへのリクエスト形式と`source`ノードへのデータ注入仕様を定義します。

---

## 📡 API Endpoint

### POST /api/v1/myagent/:category/:model

GraphAI ワークフローを実行するメインエンドポイント。

**パスパラメータ**:
- `category`: ワークフローのカテゴリ（例: `llmwork`, `examples`）
- `model`: ワークフロー名（例: `test_workflow`）

**リクエストボディ**:
```json
{
  "user_input": <string | object>,
  "project": "myproject"
}
```

### POST /api/v1/myagent (Legacy)

後方互換性のための旧形式エンドポイント。

**リクエストボディ**:
```json
{
  "user_input": <string | object>,
  "model_name": "category/model",
  "project": "myproject"
}
```

---

## 📥 Request Body Parameters

| フィールド | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|------|-----------|------|
| `user_input` | `string \| object` | ✅ | - | `source`ノードに注入される入力データ |
| `project` | `string` | - | `undefined` | MyVaultプロジェクト名（シークレット管理用） |
| `model_name` | `string` | ✅ (Legacy) | - | ワークフロー名（例: `llmwork/test`） |

---

## 🎯 user_input の仕様

### 型: string または object

`user_input`は**2つの形式**で送信可能です：

#### 1️⃣ オブジェクト形式（推奨）

**リクエスト例**:
```json
{
  "user_input": {
    "url": "https://example.com",
    "path": "/path/to/folder",
    "count": 10,
    "items": ["apple", "banana", "cherry"]
  }
}
```

**ワークフロー内での参照**:
```yaml
nodes:
  source: {}

  # sourceのプロパティに直接アクセス可能
  use_url:
    agent: stringTemplateAgent
    inputs:
      url: :source.url        # ✅ "https://example.com"
      path: :source.path      # ✅ "/path/to/folder"
      count: :source.count    # ✅ 10
    params:
      template: "URL: ${url}, Path: ${path}, Count: ${count}"

  # 配列プロパティの反復処理
  process_items:
    agent: mapAgent
    inputs:
      rows: :source.items     # ✅ ["apple", "banana", "cherry"]
    graph:
      nodes:
        item_node:
          agent: stringTemplateAgent
          inputs:
            item: :row
          params:
            template: "Item: ${item}"
          isResult: true
```

**メリット**:
- ✅ `jsonParserAgent`が不要
- ✅ `:source.property`で直接参照可能
- ✅ 型安全性が向上
- ✅ デバッグが容易
- ✅ IDE補完が効く（APIクライアント側）

---

#### 2️⃣ JSON文字列形式（非推奨）

**リクエスト例**:
```json
{
  "user_input": "{\"url\": \"https://example.com\", \"path\": \"/path/to/folder\"}"
}
```

**ワークフロー内での参照**:
```yaml
nodes:
  source: {}

  # ⚠️ 明示的にJSONパースが必要
  parse_input:
    agent: jsonParserAgent
    inputs:
      json: :source

  # パース後のオブジェクトを参照
  use_url:
    agent: stringTemplateAgent
    inputs:
      url: :parse_input.url
      path: :parse_input.path
    params:
      template: "URL: ${url}, Path: ${path}"
```

**デメリット**:
- ❌ ワークフロー内で`jsonParserAgent`が必要
- ❌ エスケープ処理が必要（`"`を`\"`に）
- ❌ デバッグが困難
- ❌ パースエラーのリスク

**使用を推奨しない理由**:
- Express.jsが自動的にJSONをパースするため、わざわざ文字列化する意味がない
- Gemini CLI報告の通り、デバッグループに陥りやすい

---

## 🔄 sourceノードへのデータ注入フロー

### 内部実装（graphAiServer/src/services/graphai.ts）

```typescript
export const runGraphAI = async (
  user_input: string | Record<string, unknown>,
  model_name: string,
  project?: string
): Promise<GraphAIResponse> => {
  // 1. GraphAIインスタンス生成
  const graph = new GraphAI(graph_data, agents_2);

  // 2. user_inputをそのままsourceノードに注入
  graph.injectValue("source", user_input);

  // 3. ワークフロー実行
  const results = await graph.run(true);

  return { results, errors, logs };
}
```

**重要なポイント**:
- `user_input`は**型変換されずに**そのまま`source`に注入される
- オブジェクト形式で送信 → `source`はオブジェクト
- 文字列形式で送信 → `source`は文字列

---

## 📖 使用例

### 例1: 単純な文字列入力

**リクエスト**:
```json
{
  "user_input": "東京の天気を教えて"
}
```

**ワークフロー**:
```yaml
nodes:
  source: {}

  call_llm:
    agent: geminiAgent
    inputs:
      prompt: :source  # ✅ "東京の天気を教えて"
    params:
      model: gemini-2.0-flash-exp
    isResult: true
```

---

### 例2: 構造化されたオブジェクト入力（推奨）

**リクエスト**:
```json
{
  "user_input": {
    "query": "東京の天気を教えて",
    "language": "ja",
    "format": "detailed"
  }
}
```

**ワークフロー**:
```yaml
nodes:
  source: {}

  build_prompt:
    agent: stringTemplateAgent
    inputs:
      query: :source.query
      lang: :source.language
      format: :source.format
    params:
      template: |
        Query: ${query}
        Language: ${lang}
        Format: ${format}

  call_llm:
    agent: geminiAgent
    inputs:
      prompt: :build_prompt
    params:
      model: gemini-2.0-flash-exp
    isResult: true
```

---

### 例3: 配列データの処理

**リクエスト**:
```json
{
  "user_input": {
    "urls": [
      "https://example.com/page1",
      "https://example.com/page2",
      "https://example.com/page3"
    ],
    "action": "scrape"
  }
}
```

**ワークフロー**:
```yaml
nodes:
  source: {}

  scrape_pages:
    agent: mapAgent
    console:
      after: true
    params:
      compositeResult: true
      concurrency: 2
    inputs:
      rows: :source.urls  # ✅ 配列を直接参照
    graph:
      nodes:
        scrape_one:
          agent: fetchAgent
          inputs:
            url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/aiagent/utility/explorer
            method: POST
            body:
              user_input: :row  # ✅ 各URLが:rowに入る
              model_name: gemini-2.5-flash
          isResult: true

  aggregate:
    agent: arrayJoinAgent
    inputs:
      array: :scrape_pages.scrape_one
    params:
      separator: "\n---\n"
    isResult: true
```

---

### 例4: ネストされたオブジェクト

**リクエスト**:
```json
{
  "user_input": {
    "task": {
      "name": "データ収集",
      "priority": "high"
    },
    "target": {
      "url": "https://example.com",
      "selector": ".content"
    }
  }
}
```

**ワークフロー**:
```yaml
nodes:
  source: {}

  # ネストされたプロパティにアクセス
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      task_name: :source.task.name          # ✅ ネスト可能
      priority: :source.task.priority
      url: :source.target.url
      selector: :source.target.selector
    params:
      template: |
        Task: ${task_name} (Priority: ${priority})
        URL: ${url}
        Selector: ${selector}
```

**注意**: GraphAIの仕様により、ネストレベルは**1階層まで**推奨（`:source.task.name`は動作するが、深いネストは避ける）

---

## ⚠️ よくあるエラーと対策

### エラー1: "Unexpected end of JSON input"

**原因**: オブジェクトを`jsonParserAgent`に渡している

**誤った実装**:
```yaml
# user_input = { "url": "https://example.com" }  ← オブジェクト

nodes:
  source: {}

  parse:
    agent: jsonParserAgent
    inputs:
      json: :source  # ❌ オブジェクトをJSON.parse()しようとしてエラー
```

**対策**: オブジェクト形式の場合は`jsonParserAgent`を削除
```yaml
nodes:
  source: {}

  use_url:
    agent: stringTemplateAgent
    inputs:
      url: :source.url  # ✅ 直接参照
```

---

### エラー2: "undefined" 参照エラー

**原因**: 文字列を`:source.property`で参照している

**誤った実装**:
```yaml
# user_input = "{\"url\": \"https://example.com\"}"  ← 文字列

nodes:
  source: {}

  use_url:
    agent: stringTemplateAgent
    inputs:
      url: :source.url  # ❌ 文字列に.urlプロパティは存在しない → undefined
```

**対策1（推奨）**: リクエストをオブジェクト形式に変更
```json
{
  "user_input": { "url": "https://example.com" }
}
```

**対策2（非推奨）**: `jsonParserAgent`を追加
```yaml
nodes:
  source: {}

  parse:
    agent: jsonParserAgent
    inputs:
      json: :source

  use_url:
    agent: stringTemplateAgent
    inputs:
      url: :parse.url  # ✅ パース後のオブジェクトから参照
```

---

### エラー3: mapAgentで"Cannot read property 'xxx' of undefined"

**原因**: 配列データの参照ミス

**誤った実装**:
```yaml
# user_input = { "items": ["a", "b", "c"] }

nodes:
  source: {}

  process:
    agent: mapAgent
    inputs:
      rows: :source  # ❌ オブジェクト全体を渡している
    graph:
      nodes:
        item:
          agent: stringTemplateAgent
          inputs:
            value: :row.items  # ❌ :rowは配列全体ではなくオブジェクト
```

**正しい実装**:
```yaml
nodes:
  source: {}

  process:
    agent: mapAgent
    inputs:
      rows: :source.items  # ✅ 配列プロパティを指定
    params:
      compositeResult: true
    graph:
      nodes:
        item:
          agent: stringTemplateAgent
          inputs:
            value: :row  # ✅ :rowは配列の各要素（"a", "b", "c"）
          params:
            template: "Item: ${value}"
          isResult: true
```

---

## 🎓 ベストプラクティス

### 1. 常にオブジェクト形式を使用する

**推奨**:
```json
{
  "user_input": {
    "query": "検索クエリ",
    "options": { "limit": 10 }
  }
}
```

**非推奨**:
```json
{
  "user_input": "{\"query\": \"検索クエリ\"}"
}
```

---

### 2. プロパティ名は明確にする

**良い例**:
```json
{
  "user_input": {
    "search_query": "東京",
    "max_results": 10,
    "sort_by": "date"
  }
}
```

**悪い例**:
```json
{
  "user_input": {
    "q": "東京",
    "n": 10,
    "s": "date"
  }
}
```

---

### 3. ワークフロー側でスキーマを明記する

YMLファイルのコメントにInput Schemaを記載することを推奨：

```yaml
# Input Schema:
# {
#   "user_input": {
#     "url": "https://example.com",
#     "count": 10
#   }
# }

version: 0.5
nodes:
  source: {}

  # ...
```

---

### 4. デバッグ時はconsoleログを有効化

```yaml
nodes:
  source:
    console:
      after: true  # ✅ sourceの内容をログ出力

  parse_data:
    agent: jsonParserAgent
    console:
      before: true  # ✅ 入力をログ出力
      after: true   # ✅ 出力をログ出力
    inputs:
      json: :source
```

GraphAiServerのログで`source`の内容を確認できます：
```
=== Source Node Injection ===
user_input type: object
user_input value: {
  "url": "https://example.com",
  "count": 10
}
=============================
```

---

## 🔗 関連ドキュメント

- [GraphAI Workflow Generation Rules](./GRAPHAI_WORKFLOW_GENERATION_RULES.md)
- [Available Agents List](./AVAILABLE_AGENTS.md)
- [GraphAI公式ドキュメント](https://github.com/receptron/graphai)

---

## 📝 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-10-16 | 初版作成（Gemini CLI PDF Workflow失敗報告を受けて） |

---

**注意**: このドキュメントは実際の`graphAiServer/src/services/graphai.ts`と`graphAiServer/src/app.ts`の実装に基づいています。GraphAIバージョンアップ時は仕様変更の可能性があるため、公式ドキュメントも併せて参照してください。
