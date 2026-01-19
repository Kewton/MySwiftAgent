# Capability Catalog

**Version**: 1.0.0
**Generated**: 2026-01-19T16:02:57.667Z

## Summary

- **Total Capabilities**: 4
- **With Response Schema**: 4
- **Without Response Schema**: 0

### By Category

- **ai_agent**: 2
- **utility**: 1
- **search**: 1

### By Status

- **Available**: 4
- **Unavailable**: 0
- **Deprecated**: 0

## Capabilities

### Direct LLM (`direct_llm`)

**Description**: 直接LLM呼び出し（システムプロンプト指定可能）- カスタムシステムプロンプトでLLM実行、複数モデル対応（GPT, Gemini, Ollama）

- **Version**: 1.0.0
- **Category**: ai_agent
- **Status**: available
- **Tags**: ai, llm, gpt, gemini, ollama

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_input` | string | Yes | ユーザー入力メッセージ |
| `system_prompt` | string | No | システムプロンプト |
| `model` | string | No | 使用するLLMモデル |

#### Response Schema

```yaml
result:
  type: string
  description: LLMからの応答

```

---

### Gmail送信 (`gmail_send`)

**Description**: メール送信（高速・Direct API）- 宛先、件名、本文を指定してメール送信、HTML形式メール対応

- **Version**: 1.0.0
- **Category**: utility
- **Status**: available
- **Tags**: email, gmail, send, utility

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `to` | string | Yes | 宛先メールアドレス |
| `subject` | string | Yes | 件名 |
| `body` | string | Yes | メール本文（プレーンテキスト） |
| `html_body` | string | No | HTML本文（html_bodyを指定した場合、bodyより優先される） |
| `project` | string | No | MyVaultプロジェクト名（認証情報取得用） |

#### Response Schema

```yaml
result:
  type: string
  description: 送信結果メッセージ
message_id:
  type: string
  description: 送信されたメールのID

```

---

### Google検索 (`google_search`)

**Description**: Web検索（Serper API使用）- LLMによるナレッジ抽出を含むため処理時間が長い。キーワード検索、複数クエリ一括検索対応

- **Version**: 1.0.0
- **Category**: search
- **Status**: available
- **Tags**: search, web, google, serper, knowledge-extraction

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `queries` | array | Yes | 検索クエリのリスト |
| `num` | number | No | 各クエリの検索結果件数 |

#### Response Schema

```yaml
search_results:
  type: array
  description: 検索結果のリスト（クエリごとに1つのオブジェクト）
  items:
    type: object
    properties:
      title:
        type: string
        description: 検索結果のタイトル
      link:
        type: string
        description: 検索結果のURL
      knowledge:
        type: string
        description: LLMが抽出したナレッジ情報
      original_query:
        type: string
        description: 元の検索クエリ
search_results_count:
  type: integer
  description: 検索結果の件数
status:
  type: string
  description: ステータス（通常 'ok'）

```

---

### JSON Output Agent (`json_output_agent`)

**Description**: 構造化JSON出力専用エージェント - 自然言語→JSON変換、常にJSON形式で返却、force_json不要（常にJSON）

- **Version**: 1.0.0
- **Category**: ai_agent
- **Status**: available
- **Tags**: ai, agent, json, structured-output

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `user_input` | string | Yes | ユーザー入力（自然言語またはJSON変換対象テキスト） |
| `system_prompt` | string | No | システムプロンプト（JSON構造を指定） |
| `model` | string | No | 使用するLLMモデル |

#### Response Schema

```yaml
result:
  type: object
  description: JSON形式の構造化出力

```

---
