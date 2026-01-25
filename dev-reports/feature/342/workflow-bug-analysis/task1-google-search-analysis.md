# Task 1: Google検索ワークフロー バグ分析レポート

## 概要

- **タスク名**: Google検索の実行
- **TaskMaster ID**: `tm_01KEF4YWPSJDEDAG5CGMBNSVMN`
- **JobMaster ID**: `jm_01KEF4YWQMF3KG2BNSH0B7YAK3`
- **分析日**: 2026-01-09

## 症状

ジョブ実行時にHTTP 422エラーが発生し、Google検索APIの呼び出しに失敗。

```
HTTP 500: google_search: HTTP error: 422
```

## 根本原因

AIエージェントが生成したワークフローYAMLに複数の問題があった。

---

## 問題点一覧

### 問題1: APIパラメータ名の誤り

| 項目 | AI生成（誤） | 正解 | API仕様 |
|------|-------------|------|---------|
| 検索クエリ | `query` | `queries` | 配列形式で必須 |
| 件数指定 | `num_results` | `num` | 整数、最大3 |

**AI生成コード（誤）**:
```yaml
body:
  query: :source.query
  num_results: :source.num_results
```

**正しいコード**:
```yaml
body:
  queries:
    - :source.user_input.query
  num: 3
```

### 問題2: データ型の誤り

| パラメータ | AI生成（誤） | 正解 |
|-----------|-------------|------|
| queries | 文字列 | 配列（string[]） |

Google Search APIは`queries`パラメータに配列を要求するが、AIは文字列として生成。

### 問題3: sourceパスの誤り

| 項目 | AI生成（誤） | 正解 |
|------|-------------|------|
| パス | `:source.query` | `:source.user_input.query` |

**原因**: JobQueueのTaskMasterが`body_template`でリクエストを変換するため：

```json
// TaskMaster body_template
{
  "user_input": "{{job.body}}",
  "job_params": "{{job.body}}",
  "model_name": "taskmaster/..."
}
```

結果として、GraphAIの`source`に注入されるデータ構造：
```json
{
  "user_input": {"query": "大谷翔平"},
  "job_params": {"query": "大谷翔平"}
}
```

### 問題4: タイムアウト単位の誤り

| 項目 | AI生成（誤） | 正解 | 単位 |
|------|-------------|------|------|
| timeout | `180` | `180000` | ミリ秒 |

GraphAIのtimeoutはミリ秒単位だが、AIは秒単位と誤解して生成。

### 問題5: エンドポイント選択

| 項目 | AI生成 | 推奨 |
|------|-------|------|
| エンドポイント | `google_search` | `google_search_overview` |

`google_search`はLLM処理を含み処理時間が長い。`google_search_overview`はLLM処理なしで高速。

### 問題6: URL形式

| 項目 | AI生成（誤） | 正解 |
|------|-------------|------|
| URL | `${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search` | `http://localhost:8004/aiagent-api/v1/utility/google_search_overview` |

環境変数形式`${...}`はGraphAI実行時に解決されない可能性がある。

---

## 修正前後の比較

### 修正前（AI生成）

```yaml
version: '0.5'
nodes:
  source: {}
  google_search:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search
      method: POST
      body:
        query: :source.query
        num_results: :source.num_results
    console:
      after: true
    timeout: 180
  format_output:
    agent: copyAgent
    inputs:
      search_results: :google_search.result.search_results
    params:
      namedKey: search_results
    isResult: true
```

### 修正後（手動修正）

```yaml
version: '0.5'
nodes:
  source: {}
  google_search:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/utility/google_search_overview
      method: POST
      body:
        queries:
          - :source.user_input.query
        num: 3
    console:
      after: true
    timeout: 180000
  format_output:
    agent: copyAgent
    inputs:
      search_results: :google_search.result.search_results
    params:
      namedKey: search_results
    isResult: true
```

---

## AIエージェント改善提案

### 1. APIスキーマ検証の強化

ワークフロー生成時にexpertAgentのOpenAPI仕様を参照し、リクエストスキーマを検証する。

### 2. Few-shotパターンの拡充

`GRAPHAI_WORKFLOW_GENERATION_RULES.md`に実際に動作するGoogle検索ワークフローの完全なサンプルを追加。

### 3. JobQueue統合のドキュメント明確化

TaskMasterの`body_template`による変換を考慮した`source`パス指定ルールを明示：
- 直接API呼び出し: `:source.query`
- JobQueue経由: `:source.user_input.query`

### 4. タイムアウト値の検証

GraphAIのtimeoutはミリ秒であることを明示し、生成時に検証を追加。

### 5. URL解決の改善

環境変数形式ではなく、直接URLまたは設定から解決済みのURLを使用。

---

## 検証結果

修正後のワークフローでジョブを実行した結果、Task 1は成功：

```json
{
  "status": "SUCCEEDED",
  "output_data": {
    "google_search": {
      "result": {
        "text": "ok",
        "result": [
          {
            "organic": [
              {"title": "大谷翔平", "link": "https://ja.wikipedia.org/wiki/..."},
              {"title": "Shohei Ohtani | 大谷翔平", "link": "https://www.instagram.com/..."},
              {"title": "「大谷翔平」ニュース一覧", "link": "https://news.web.nhk/..."}
            ]
          }
        ]
      }
    }
  },
  "duration_ms": 878
}
```
