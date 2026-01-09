# Task 2: メール内容生成ワークフロー バグ分析レポート

## 概要

- **タスク名**: メール内容の生成
- **TaskMaster ID**: `tm_01KEF4YWQ4ZT6BCANYWF12P5BZ`
- **JobMaster ID**: `jm_01KEF4YWQMF3KG2BNSH0B7YAK3`
- **分析日**: 2026-01-09

## 症状

ジョブ実行時にHTTP 422エラーが発生し、LLM APIの呼び出しに失敗。

```
HTTP 422: Validation Error
```

---

## 問題点一覧

### 問題1: APIエンドポイントの誤り

| 項目 | AI生成（誤） | 正解 |
|------|-------------|------|
| エンドポイント | `/aiagent-api/v1/aiagent/generate` | `/aiagent-api/v1/aiagent/utility/jsonoutput` |

AIは汎用の `generate` エンドポイントを使用しようとしたが、JSON出力が必要な場合は `jsonoutput` エンドポイントを使用すべき。

### 問題2: リクエストボディの構造誤り

| パラメータ | AI生成（誤） | 正解 |
|-----------|-------------|------|
| プロンプト | `prompt: "..."` | `user_input: "..."` |
| スキーマ | `schema: {...}` | 不要（プロンプト内でJSON形式を指示） |
| モデル指定 | なし | `model_name: gemini-2.0-flash` |
| JSON強制 | なし | `force_json: true` |

**AI生成コード（誤）**:
```yaml
body:
  prompt: :format_prompt
  schema:
    email_subject: "string"
    email_body: "string"
```

**正しいコード**:
```yaml
body:
  user_input: :format_prompt
  model_name: gemini-2.0-flash
  force_json: true
```

### 問題3: プロンプト変数参照の誤り

| 項目 | AI生成（誤） | 正解 |
|------|-------------|------|
| キーワード | `:source.query` | `:source.job_params.query` |
| 検索結果 | `:source.search_results` | `:source.user_input.google_search.result.result` |

**原因**: Task 1の出力がTaskMasterの`body_template`で変換され、次のタスクの`source`に注入される構造を理解していない。

TaskMasterの`body_template`:
```json
{
  "user_input": "{{tasks[0].output_data}}",
  "job_params": "{{job.body}}",
  "model_name": "taskmaster/..."
}
```

結果として、Task 2の`source`に注入されるデータ構造：
```json
{
  "user_input": {
    "google_search": {
      "result": {
        "result": [...]
      }
    }
  },
  "job_params": {"query": "大谷翔平"}
}
```

### 問題4: 不要な中間ノードの作成

AI生成ワークフローには不要な`extract_*`ノードが含まれていた。

**AI生成コード（誤）**:
```yaml
extract_search_results:
  agent: copyAgent
  inputs:
    search_results: :source.search_results
  params:
    namedKey: search_results
```

この中間ノードは`namedKey`パラメータの使用方法が誤っており、期待通りに動作しない。

**正しいアプローチ**: 中間ノードを省略し、`stringTemplateAgent`で直接参照する。

### 問題5: タイムアウト単位の誤り（Task 1と同様）

| 項目 | AI生成（誤） | 正解 | 単位 |
|------|-------------|------|------|
| timeout | `120` | `120000` | ミリ秒 |

---

## 修正前後の比較

### 修正前（AI生成）

```yaml
version: '0.5'
nodes:
  source: {}
  extract_search_results:
    agent: copyAgent
    inputs:
      search_results: :source.search_results
    params:
      namedKey: search_results
  format_prompt:
    agent: stringTemplateAgent
    inputs:
      keyword: :source.query
      results: :extract_search_results
    params:
      template: |
        検索結果を要約してメールを作成してください。
        キーワード: ${keyword}
        結果: ${results}
    console:
      after: true
  generate_email_content:
    agent: fetchAgent
    inputs:
      url: ${EXPERTAGENT_BASE_URL}/aiagent-api/v1/aiagent/generate
      method: POST
      body:
        prompt: :format_prompt
        schema:
          email_subject: "string"
          email_body: "string"
    console:
      after: true
    timeout: 120
  output:
    agent: copyAgent
    inputs:
      email_subject: :generate_email_content.result.email_subject
      email_body: :generate_email_content.result.email_body
    isResult: true
```

### 修正後（手動修正）

```yaml
version: '0.5'
nodes:
  source: {}

  # プロンプトを生成
  format_prompt:
    agent: stringTemplateAgent
    inputs:
      keyword: :source.job_params.query
      results: :source.user_input.google_search.result.result
    params:
      template: |
        以下の検索結果を元に、メール送信用の要約文を生成してください。

        【検索キーワード】
        ${keyword}

        【検索結果リスト】
        ${JSON.stringify(results)}

        上記の内容に基づき、日本語で適切な「件名」と「本文」を作成してください。
        件名は簡潔に、本文は検索結果の要点をまとめて読みやすくしてください。

        出力はJSON形式で以下のフォーマットに従ってください：
        {
          "email_subject": "件名をここに記載",
          "email_body": "本文をここに記載"
        }
    console:
      after: true

  # LLMでメール内容を生成
  generate_email_content:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :format_prompt
        model_name: gemini-2.0-flash
        force_json: true
    console:
      after: true
    timeout: 120000

  # 出力をフォーマット
  output:
    agent: copyAgent
    inputs:
      email_subject: :generate_email_content.result.email_subject
      email_body: :generate_email_content.result.email_body
    isResult: true
```

---

## AIエージェント改善提案

### 1. LLM API仕様の学習強化

expertAgentの`/aiagent/utility/jsonoutput`エンドポイントの正確なリクエストスキーマをプロンプトに含める。

### 2. タスクチェーンのデータフロー理解

JobQueueのTaskMaster間でのデータ変換（`body_template`による`user_input`/`job_params`ラッピング）をドキュメント化し、プロンプトに含める。

### 3. 中間ノードの最小化

不要な中間ノード（`extract_*`）を生成しないよう、シンプルなワークフロー設計を推奨。

### 4. プロンプトテンプレートの品質向上

曖昧な指示ではなく、具体的なJSON出力形式を含む詳細なプロンプトテンプレートを生成するよう改善。

---

## 検証結果

修正後のワークフローでジョブを実行した結果、Task 2は成功：

```json
{
  "status": "SUCCEEDED",
  "output_data": {
    "email_subject": "大谷翔平選手 最新ニュースまとめ",
    "email_body": "大谷翔平選手に関する最新情報をお届けします..."
  },
  "duration_ms": 2425
}
```
