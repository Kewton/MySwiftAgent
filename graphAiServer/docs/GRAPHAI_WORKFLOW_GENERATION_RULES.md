# GraphAI Workflow Generation Rules

このドキュメントは、GraphAI YMLワークフローファイルを自動生成する際のルールと設計指針をまとめています。

## 目次

1. [基本構造](#基本構造)
2. [必須要素](#必須要素)
3. [エージェント種別](#エージェント種別)
4. [データフローパターン](#データフローパターン)
5. [Agent選択指針](#agent選択指針)
6. [モデル選択指針](#モデル選択指針)
7. [expertAgent API統合](#expertagent-api統合)
   - [共通APIスキーマ](#共通apiスキーマ)
   - [テストモード機能](#テストモード機能)
8. [エラー回避パターン](#エラー回避パターン)
9. [パフォーマンスと並列処理の最適化](#パフォーマンスと並列処理の最適化)
10. [命名規則](#命名規則)
11. [デバッグとログ](#デバッグとログ)
12. [実装例](#実装例)
13. [YMLファイルのヘッダーコメント規約](#ymlファイルのヘッダーコメント規約)
14. [LLMワークフロー作成手順](#llmワークフロー作成手順)
15. [動作確認とトラブルシューティング](#動作確認とトラブルシューティング)
16. [ワークフロー作成時の動作確認方法](#ワークフロー作成時の動作確認方法)
17. [付録](#付録)
    - [付録A: Playwright Agent 完全ガイド](#付録a-playwright-agent-完全ガイド)
    - [付録B: Explorer Agent 完全ガイド](#付録b-explorer-agent-完全ガイド)
    - [付録C: File Reader Agent 完全ガイド](#付録c-file-reader-agent-完全ガイド)

---

## 基本構造

### ファイルフォーマット

```yaml
version: 0.5
nodes:
  # ノード定義
  node_name:
    agent: agentType
    inputs:
      # 入力定義
    params:
      # パラメータ定義
    console:
      # デバッグログ設定
    isResult: true  # 最終出力ノードの場合
```

### 必須項目

- `version`: GraphAIバージョン（現在は `0.5` 固定）
- `nodes`: ノード定義オブジェクト
- 最低1つの `isResult: true` を持つ出力ノード

---

## 必須要素

### 1. sourceノード

ユーザー入力を受け取るエントリーポイント。

```yaml
nodes:
  source: {}
```

**重要**: `source` は実行時に文字列が直接注入される。プロパティアクセスは不要。

**正しい参照**:
```yaml
inputs:
  keywords: :source  # ✅ 正しい
```

**誤った参照**:
```yaml
inputs:
  keywords: :source.text  # ❌ 間違い（undefinedになる）
```

### 2. outputノード

最終結果を出力するノード。必ず `isResult: true` を設定。

```yaml
output:
  agent: copyAgent
  params:
    namedKey: text
  inputs:
    text: :previous_node.result
  isResult: true
```

---

## エージェント種別

### fetchAgent

外部API（expertAgent含む）を呼び出すエージェント。expertAgentだけでなく、**任意の外部APIも呼び出し可能**です。

```yaml
node_name:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/endpoint
    method: POST  # GET, POST, PUT, DELETEなど
    body:
      user_input: :previous_node
      model_name: gpt-oss:20b
  timeout: 30  # オプション: タイムアウト（秒）
  retry: 0     # オプション: リトライ回数
```

**外部API利用時の注意**:
- インターフェース（リクエスト/レスポンス形式）を明確に定義すること
- タイムアウト値を適切に設定すること
- エラーハンドリングを考慮すること

### anthropicAgent

Claude APIを直接呼び出すGraphAI標準エージェント。

```yaml
node_name:
  agent: anthropicAgent
  inputs:
    prompt: :previous_node
  params:
    model: claude-sonnet-4.5  # Claude Sonnet 4.5（最新）
    # または claude-opus-4.1（エージェントタスク特化）
```

### geminiAgent

Google Gemini APIを直接呼び出すGraphAI標準エージェント。

```yaml
node_name:
  agent: geminiAgent
  inputs:
    prompt: :previous_node
  params:
    model: gemini-2.5-pro  # Gemini 2.5 Pro（最新・最高精度）
    # または gemini-2.5-flash（高速・バランス型）
    # または gemini-2.5-flash-lite（超高速・低コスト）
```

### stringTemplateAgent

テンプレート文字列を生成するエージェント。

```yaml
prompt_builder:
  agent: stringTemplateAgent
  inputs:
    variable1: :source
    variable2: :other_node.result
  params:
    template: |-
      # プロンプトテンプレート
      ユーザー入力: ${variable1}
      追加情報: ${variable2}
```

### mapAgent

配列の各要素に対して並列処理を実行するエージェント。

```yaml
mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline  # 配列データ
  params:
    compositeResult: true  # 結果を統合
  graph:
    nodes:
      # 各要素に対して実行されるサブグラフ
      process_item:
        agent: fetchAgent
        inputs:
          url: http://127.0.0.1:8104/api/endpoint
          body:
            data: :row.field  # 各要素にアクセス
```

### arrayJoinAgent

配列を結合するエージェント。

```yaml
join_results:
  agent: arrayJoinAgent
  params:
    separator: \n---\n
  inputs:
    array: :mapper.result_field
```

### copyAgent

データをコピー・変換するエージェント。

```yaml
output:
  agent: copyAgent
  params:
    namedKey: text  # 特定のキーを抽出
  inputs:
    text: :previous_node.result
  isResult: true
```

---

## データフローパターン

### パターン1: シンプルな順次処理

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_process_step1(process_step1<br/>fetchAgent)
  n_source --> n_process_step1
  n_process_step2(process_step2<br/>fetchAgent)
  n_process_step1 -- result --> n_process_step2
  n_output(output<br/>copyAgent)
  n_process_step2 -- result --> n_output
  class n_source staticNode
  class n_process_step1,n_process_step2,n_output computedNode
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  process_step1:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/api/step1
      body:
        input: :source

  process_step2:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/api/step2
      body:
        input: :process_step1.result

  output:
    agent: copyAgent
    inputs:
      text: :process_step2.result
    isResult: true
```

### パターン2: プロンプトビルダーパターン

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_common_param(common_param)
  n_prompt_builder(prompt_builder<br/>stringTemplateAgent)
  n_source --> n_prompt_builder
  n_common_param -- target --> n_prompt_builder
  n_llm_execution(llm_execution<br/>fetchAgent)
  n_prompt_builder --> n_llm_execution
  n_output(output<br/>copyAgent)
  n_llm_execution -- text --> n_output
  class n_source,n_common_param staticNode
  class n_prompt_builder,n_llm_execution,n_output computedNode
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  # パラメータ定義
  common_param:
    value:
      target: 39歳、男性
      tone: 深掘り討論

  # プロンプト構築
  prompt_builder:
    agent: stringTemplateAgent
    inputs:
      user_input: :source
      target: :common_param.target
    params:
      template: |-
        # 指示書
        対象ユーザー: ${target}

        # ユーザー入力
        ${user_input}

  # LLM実行
  llm_execution:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/mylllm
      method: POST
      body:
        user_input: :prompt_builder
        model_name: gpt-oss:20b

  output:
    agent: copyAgent
    inputs:
      text: :llm_execution.text
    isResult: true
```

### パターン3: 並列処理パターン（MapAgent）

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_planner(planner<br/>fetchAgent)
  n_source --> n_planner
  subgraph n_process_mapper[process_mapper: mapAgent]
    n_process_mapper_search(search<br/>fetchAgent)
    n_process_mapper_row -- query_hint --> n_process_mapper_search
    n_process_mapper_explorer(explorer<br/>fetchAgent)
    n_process_mapper_row -- overview --> n_process_mapper_explorer
    n_process_mapper_search -- result --> n_process_mapper_explorer
    n_process_mapper_summary(summary<br/>stringTemplateAgent)
    n_process_mapper_row -- title --> n_process_mapper_summary
    n_process_mapper_explorer -- result --> n_process_mapper_summary
  end
  n_planner -- result.outline --> n_process_mapper
  n_join_results(join_results<br/>arrayJoinAgent)
  n_process_mapper -- summary --> n_join_results
  n_output(output<br/>copyAgent)
  n_join_results -- text --> n_output
  class n_source staticNode
  class n_planner,n_process_mapper_search,n_process_mapper_explorer,n_process_mapper_summary,n_join_results,n_output computedNode
  class n_process_mapper nestedGraph
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  # プランナー: タスクを複数の章に分割
  planner:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source
        model_name: gpt-oss:20b

  # 各章を並列処理
  process_mapper:
    agent: mapAgent
    inputs:
      rows: :planner.result.outline
    params:
      compositeResult: true
    graph:
      nodes:
        # Google検索
        search:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
            method: POST
            body:
              queries: :row.query_hint

        # 情報収集
        explorer:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
            method: POST
            body:
              user_input: :row.overview
              search_result: :search.result
              model_name: gpt-oss:20b

        # 結果サマリー
        summary:
          agent: stringTemplateAgent
          inputs:
            title: :row.title
            content: :explorer.result
          params:
            template: |-
              ### ${title}
              ${content}
          isResult: true

  # 結果統合
  join_results:
    agent: arrayJoinAgent
    params:
      separator: \n---\n
    inputs:
      array: :process_mapper.summary

  output:
    agent: copyAgent
    inputs:
      text: :join_results.text
    isResult: true
```

---

## Agent選択指針

このセクションでは、タスクに応じて最適なAgentを選択するための指針を提供します。

### 選択フローチャート

```
タスクを分析
  │
  ├─ Web情報収集が必要？
  │   YES → Explorer Agent or Playwright Agent
  │          （詳細は下記比較表参照）
  │   NO → 次へ
  │
  ├─ ファイル読み込みが必要？
  │   YES → File Reader Agent
  │   NO → 次へ
  │
  ├─ 構造化JSON出力が必要？
  │   YES → jsonoutput Agent
  │   NO → 次へ
  │
  ├─ Gmail/カレンダー操作が必要？
  │   YES → Action Agent
  │   NO → 次へ
  │
  └─ その他のLLM処理
      → mylllm Agent（汎用LLM呼び出し）
```

### Web情報収集: Explorer Agent vs Playwright Agent

**重要**: Webページからの情報抽出には **Explorer Agent（html2markdown MCP）** の使用を強く推奨します。

| 観点 | Explorer Agent | Playwright Agent |
|------|---------------|------------------|
| **推奨用途** | ✅ **Webページのテキスト・情報抽出** | ⚠️ ブラウザ操作・スクリーンショット |
| **テキスト抽出精度** | ⭐⭐⭐⭐⭐ 高精度<br>（html2markdown MCP） | ⭐⭐ 低精度<br>（アクセシビリティツリー） |
| **構造保持** | ⭐⭐⭐⭐⭐ Markdown形式<br>（見出し、リスト、表を保持） | ⭐⭐ アクセシビリティツリー<br>（構造が崩れやすい） |
| **処理速度** | ⭐⭐⭐⭐⭐ 高速 | ⭐⭐⭐ 中速 |
| **コスト** | $ 低コスト | $$ 中コスト |
| **典型的なユースケース** | ・ニュース記事の本文抽出<br>・ブログ記事の取得<br>・PDFリンクの一括抽出<br>・技術ドキュメントの解析<br>・Google検索結果の詳細取得 | ・フォーム操作（入力、送信）<br>・スクリーンショット取得<br>・JavaScript実行 |

**判断基準**:
- **テキスト抽出が主目的** → **Explorer Agent**
- **ブラウザ操作が必要** → Playwright Agent
- **迷ったら** → まず**Explorer Agent**を試す

**例: ニュース記事の抽出**
```yaml
# ✅ 推奨: Explorer Agent
news_extractor:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
    method: "POST"
    body:
      user_input: "下記サイトの記事本文をMarkdown形式で抽出してください。\nhttps://example.com/news/article-123"
      model_name: "gpt-4o-mini"

# ⚠️ 非推奨: Playwright Agent（精度が低い）
news_extractor_playwright:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
    method: "POST"
    body:
      user_input: "下記サイトから記事のタイトルと本文を抽出してください。\nhttps://example.com/news/article-123"
      model_name: "gpt-4o-mini"
```

### ファイル処理: File Reader Agent

**対応ファイル形式**:

| ファイル形式 | 処理方法 | コスト | 備考 |
|------------|---------|--------|------|
| **PDF** | PyPDF2で全文抽出 | 無料 | 要約なし、原文そのまま |
| **画像** (PNG/JPG) | OpenAI Vision API | $$$ | gpt-4o使用 |
| **音声** (MP3/WAV) | OpenAI Whisper API | $ | whisper-1使用 |
| **テキスト/CSV** | Python標準ライブラリ | 無料 | 複数エンコーディング対応 |

**データソース**:
- ✅ インターネットURL（HTTP/HTTPS）
- ✅ Google Drive（OAuth2認証、MyVault管理）
- ✅ ローカルファイル（セキュリティ制限あり: `/tmp`, `~/Downloads`, `~/Documents`）

**重要な注意点**:

1. **画像処理時の必須表現**:
   ```yaml
   # ❌ NG: LLMがツール呼び出しを拒否
   user_input: "テキストを抽出してください。\nhttps://example.com/image.png"

   # ✅ OK: 「画像ファイルの」を明記
   user_input: "下記画像ファイルのテキストを抽出してください。\nhttps://example.com/image.png"
   ```

2. **Google Driveアクセス**:
   - ユーザーがMyVaultでGoogle認証を完了している必要あり
   - 権限エラー発生時は「リンクを知っている全員」に共有設定

**例: PDF全文抽出**
```yaml
pdf_extractor:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    body:
      user_input: "下記PDFファイルのテキストを全て抽出してください。\nhttps://example.com/whitepaper.pdf"
      model_name: "gpt-4o-mini"
```

### 構造化JSON出力: jsonoutput Agent

**用途**: LLMの出力を特定のJSON構造に整形する必要がある場合

**典型的なユースケース**:
- アウトライン生成（章立て、見出し構造）
- プランナーとして複数タスクのリストを生成
- MapAgentの入力データ作成

**例: アウトライン生成**
```yaml
planner:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput"
    method: "POST"
    body:
      user_input: |
        下記トピックについて、4-6章構成のアウトラインを作成してください。
        各章には title, overview, query_hint を含めてください。

        トピック: :source
      model_name: "gpt-oss:120b"
```

### Gmail/カレンダー操作: Action Agent

**用途**: Gmail送信、Googleカレンダー操作など、外部サービスとの連携

**典型的なユースケース**:
- メール送信
- カレンダーイベント作成
- Google Drive操作

**例: メール送信**
```yaml
send_notification:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/action"
    method: "POST"
    body:
      user_input: |
        下記の内容でメールを送信してください。
        宛先: user@example.com
        件名: レポート完成のお知らせ
        本文: :report_result
      model_name: "gpt-4o-mini"
```

### Wikipedia検索: wikipedia Agent

**用途**: Wikipedia記事の検索と要約取得

**典型的なユースケース**:
- 基礎知識の取得
- 用語の定義確認
- 概要情報の収集

**例: Wikipedia検索**
```yaml
wiki_search:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/wikipedia"
    method: "POST"
    body:
      user_input: "量子コンピュータについて調べてください"
      model_name: "gpt-4o-mini"
```

---

## モデル選択指針

このセクションでは、タスクに応じて最適なLLMモデルを選択するための指針を提供します。

### 推奨モデル一覧

| モデル | 推奨度 | 特徴 | 使用ケース | コスト |
|--------|--------|------|-----------|--------|
| **gpt-oss:20b** | ⭐⭐⭐ | 軽量・高速、ローカル実行 | 単純なタスク、リアルタイム応答 | 無料 |
| **gpt-oss:120b** | ⭐⭐⭐ | 高精度、ローカル実行 | 複雑な推論、レポート生成 | 無料 |
| **gpt-4o-mini** | ⭐⭐⭐ | バランス型、API | Agent統合（Playwright/Explorer） | $ |
| **Gemini 2.5 Flash** | ⭐⭐⭐ | 高速、100万トークン | 大規模文書処理 | $ |
| **Gemini 2.5 Pro** | ⭐⭐ | 最高精度、思考プロセス付き | 極めて複雑なタスク | $$$ |
| **Claude Sonnet 4.5** | ⭐⭐ | コーディング最高精度 | ワークフロー生成、コード生成 | $$ |

### タスク別推奨モデル

#### 1. ワークフロー生成・コーディング

- **第1選択**: Claude Sonnet 4.5
- **第2選択**: Gemini 2.5 Flash
- **理由**: YML構造の正確な理解、長文コンテキスト対応

#### 2. レポート生成・要約

- **第1選択**: gpt-oss:120b（ローカル）
- **第2選択**: Gemini 2.5 Flash
- **理由**: コスト無料、高精度

#### 3. Agent統合（Playwright/Explorer/File Reader）

- **第1選択**: gpt-4o-mini
- **理由**: Agent指示理解に最適、コスト効率良好

**重要**: Agent統合時は必ず **gpt-4o-mini** を使用してください。他のモデルではツール呼び出しが正常に動作しない場合があります。

#### 4. リアルタイム対話

- **第1選択**: gpt-oss:20b（ローカル）
- **理由**: 高速応答、コスト無料

#### 5. 大規模文書処理（100ページ以上のPDF等）

- **第1選択**: Gemini 2.5 Flash
- **理由**: 100万トークンコンテキスト

### コスト最適化戦略

1. **ローカルLLM優先**: まず **gpt-oss:20b/120b** を試す
2. **Agent統合は gpt-4o-mini**: Playwright/Explorer/File Reader統合時は必須
3. **高精度が必要な場合のみクラウドLLM**: Gemini/Claude
4. **段階的スケールアップ**: 20b → 120b → gpt-4o-mini → Gemini Flash → Gemini Pro

### expertAgent APIでのモデル指定方法

```yaml
# ローカルLLM（推奨・無料）
model_name: "gpt-oss:20b"    # 軽量・高速
model_name: "gpt-oss:120b"   # 高精度

# クラウドLLM（有料）
model_name: "gpt-4o-mini"       # Agent統合時に推奨
model_name: "gemini-2.5-flash"  # 大規模文書処理
model_name: "gemini-2.5-pro"    # 最高精度
model_name: "claude-sonnet-4-5" # コーディング
```

### モデル選択の実践例

#### 例1: ニュース記事の要約

```yaml
# ✅ 推奨: ローカルLLM（無料）
summarizer:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/mylllm"
    method: "POST"
    body:
      user_input: "下記記事を3行で要約してください。\n:article_content"
      model_name: "gpt-oss:120b"  # 高精度、無料
```

#### 例2: Playwright Agentでのスクレイピング

```yaml
# ⚠️ 必須: gpt-4o-mini を使用
web_scraper:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
    method: "POST"
    body:
      user_input: "下記サイトからタイトルを抽出してください。\nhttps://example.com"
      model_name: "gpt-4o-mini"  # Agent統合時は必須
```

#### 例3: 大規模PDF処理

```yaml
# ✅ 推奨: Gemini 2.5 Flash（100万トークン対応）
pdf_processor:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    body:
      user_input: "下記200ページのPDFから重要ポイントを抽出してください。\n:pdf_url"
      model_name: "gemini-2.5-flash"  # 長文対応
```

---

## expertAgent API統合

### 重要: ポート番号とエンドポイント

**正しいポート番号**: `8104`（expertAgent）

```yaml
# ✅ 正しい
url: http://127.0.0.1:8104/aiagent-api/v1/endpoint

# ❌ 間違い
url: http://127.0.0.1:8000/aiagent-api/v1/endpoint  # ポート8000は使用不可
```

### 共通APIスキーマ

expertAgent APIのエンドポイントは、以下の2種類のスキーマを使用します。

#### 標準LLMエンドポイント用スキーマ

`/aiagent-api/v1/mylllm`、`/aiagent-api/v1/aiagent/utility/jsonoutput` が使用。

**リクエストボディ（ExpertAiAgentRequest）**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `user_input` | string | ✅ | - | ユーザーからの指示・プロンプト |
| `system_imput` | string | ❌ | null | システムプロンプト（注: typo "imput"） |
| `model_name` | string | ❌ | `gpt-oss:20b` | 使用するLLMモデル名 |
| `project` | string | ❌ | null | MyVaultプロジェクト名 |
| `test_mode` | boolean | ❌ | false | テストモードフラグ |
| `test_response` | dict/string | ❌ | null | テストモード用モックレスポンス |

**レスポンスボディ（ExpertAiAgentResponse）**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | string | LLM生成結果（jsonoutputの場合はJSONオブジェクト） |
| `text` | string | `result`と同じ（互換性のため） |
| `type` | string | レスポンスタイプ（オプション） |
| `chathistory` | array | チャット履歴（オプション） |

#### Utilityエンドポイント用スキーマ

`/aiagent-api/v1/aiagent/utility/explorer`、`action`、`playwright`、`wikipedia`、`file_reader` が使用。

**リクエストボディ（UtilityRequest）**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `user_input` | string | ✅ | - | 実行する指示・タスク |
| `project` | string | ❌ | null | MyVaultプロジェクト名（認証情報取得用） |
| `test_mode` | boolean | ❌ | false | テストモードフラグ |
| `test_response` | dict/string | ❌ | null | テストモード用モックレスポンス |

**レスポンスボディ（UtilityResponse）**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | string | 実行結果・生成されたレポート |

#### Google検索エンドポイント用スキーマ

`/aiagent-api/v1/utility/google_search`、`google_search_overview` が使用。

**リクエストボディ（SearchUtilityRequest）**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `queries` | array[string] | ✅ | - | 検索クエリのリスト |
| `num` | integer | ❌ | 3 | 検索結果数（1クエリあたり） |
| `project` | string | ❌ | null | MyVaultプロジェクト名 |

**レスポンスボディ（SearchUtilityResponse）**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | array | 検索結果のリスト（タイトル、URL、スニペット含む） |

---

### 主要エンドポイント

#### 1. `/aiagent-api/v1/mylllm` - 汎用LLM実行

**提供サービス**: 任意のLLMモデルを指定してテキスト生成を実行。ローカルLLM（gpt-oss、Ollama）およびクラウドLLM（Gemini、Claude、GPT）に対応。

**用途**: シンプルなテキスト生成、要約、翻訳、質問応答など基本的なLLMタスク。

**リクエストボディスキーマ**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `user_input` | string | ✅ | - | ユーザーからの指示・プロンプト |
| `system_imput` | string | ❌ | null | システムプロンプト（typo注意: "imput"） |
| `model_name` | string | ❌ | `gpt-oss:20b` | 使用するLLMモデル名 |
| `project` | string | ❌ | null | MyVaultプロジェクト名（秘密情報用） |
| `test_mode` | boolean | ❌ | false | テストモードフラグ（開発用） |
| `test_response` | dict/string | ❌ | null | テストモード用モックレスポンス |

**レスポンスボディスキーマ**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | string | LLMの生成結果テキスト（主要フィールド） |
| `text` | string | `result`と同じ内容（互換性のため） |
| `type` | string | レスポンスタイプ（オプション） |
| `chathistory` | array | チャット履歴（オプション） |

**使用例**:
```yaml
llm_node:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/mylllm
    method: POST
    body:
      user_input: :prompt_builder
      model_name: gpt-oss:20b  # モデル指定（後述）
      system_imput: システムプロンプト（オプション）
```

#### 2. `/aiagent-api/v1/aiagent/utility/jsonoutput` - JSON構造化出力

**提供サービス**: LLMにJSON形式での出力を指示し、生成されたテキストをJSONとしてパース・検証して返却。構造化データの確実な生成を保証。

**用途**: アウトライン生成、タスク分割リスト、データベース挿入用構造化データ、API連携用フォーマット変換。

**リクエストボディスキーマ**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `user_input` | string | ✅ | - | JSON出力を指示するプロンプト |
| `model_name` | string | ❌ | `gpt-oss:20b` | 使用するLLMモデル名 |
| `project` | string | ❌ | null | MyVaultプロジェクト名 |
| `test_mode` | boolean | ❌ | false | テストモードフラグ |
| `test_response` | dict/string | ❌ | null | テストモード用モックレスポンス |

**レスポンスボディスキーマ**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | object | パース済みJSON（LLM出力をJSON解析した結果） |
| `text` | string | 元のLLM出力テキスト |

**使用例**:
```yaml
json_output:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
    method: POST
    body:
      user_input: :prompt_with_json_format
      model_name: gpt-oss:120b
```

#### 3. `/aiagent-api/v1/aiagent/utility/explorer` - 情報収集エージェント

**提供サービス**: 複数の情報源から情報を収集・分析し、詳細なレポートを生成。検索結果の深掘り調査、情報の統合・整理、エビデンスベースの分析を実行。

**用途**: 市場調査レポート、技術動向分析、競合分析、学術的調査、複数情報源からの包括的な情報整理。

**🆕 利用可能なMCPツール**:
- **html2markdown**: WebページをMarkdown形式に変換（Webページからのテキスト・情報抽出に最適、Playwright Agentより高精度）
- **google_search**: Google Custom Search APIでキーワード検索
- **gmail_search**: Gmail検索（OAuth2認証、MyVault経由）

**推奨用途**: Webページからのテキスト抽出は **html2markdown** を使用することで、Playwright Agentより高精度な結果が得られます。

**リクエストボディスキーマ**:
| パラメータ | 型 | 必須 | デフォルト | 説明 |
|----------|-----|------|-----------|------|
| `user_input` | string | ✅ | - | 情報収集・調査の指示 |
| `project` | string | ❌ | null | MyVaultプロジェクト名（MCPツール認証用） |
| `test_mode` | boolean | ❌ | false | テストモードフラグ |
| `test_response` | dict/string | ❌ | null | テストモード用モックレスポンス |

**レスポンスボディスキーマ**:
| フィールド | 型 | 説明 |
|-----------|-----|------|
| `result` | string | 情報収集・分析結果のレポート |

**使用例**:
```yaml
explorer:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
    method: POST
    body:
      user_input: :prompt_builder
      project: default_project  # MCPツール認証用
```

#### 4. `/aiagent-api/v1/aiagent/utility/action` - アクション実行エージェント

**提供サービス**: ユーザーの指示に基づき、メール送信、ファイル操作、外部API呼び出しなど実世界のアクションを実行。LangGraphベースのエージェントが利用可能なツールを自動選択・実行。

**用途**: Gmail経由のメール送信、Google Driveファイル操作、カレンダー操作、自動化されたワークフロー実行、外部サービスとの統合。

**注意: 利用可能なツールの制約**
`action` エージェントが内部で使用するツールには、それぞれ固有の制約が存在する場合があります。

**例: `send_email_tool` の場合**
- **宛先の固定**: 現在の実装では、メールの宛先はツール内部で設定された固定のアドレスとなっており、プロンプトから動的に宛先を指定することはできません。

ワークフロー設計時には、このようなツールの制約を考慮する必要があります。

```yaml
action:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/action
    method: POST
    body:
      user_input: :action_prompt
      model_name: gpt-oss:20b
      project: default_project  # オプション: プロジェクト指定
```

#### 5. `/aiagent-api/v1/aiagent/utility/playwright` - Webブラウザ操作エージェント

**提供サービス**: Playwrightを使用した高度なWebブラウザ自動操作。フォーム入力・送信、ボタンクリック、スクリーンショット取得、JavaScript実行に対応。

**⚠️ 重要な制限事項**:
- **Webサイトからの情報抽出には不向き**: ブラウザの構造化データ取得の精度が低く、特定要素の抽出が困難
- **推奨用途**: フォーム操作、スクリーンショット取得、JavaScript実行など、ブラウザ操作が必要な場合のみ
- **代替手段**: Webページからのテキスト・情報抽出には **Explorer Agent（html2markdown）** の使用を強く推奨

**適切な用途**: ログイン必須サイトへのアクセス、フォーム自動入力、UI操作の自動化、スクリーンショット取得、JavaScript実行。

```yaml
playwright:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright
    method: POST
    body:
      user_input: :scraping_instruction  # 自然言語での操作指示
      model_name: gpt-oss:20b  # 操作プラン生成用モデル
      # 返却: { "result": "抽出されたデータ", "screenshot": "base64画像（オプション）" }
```

#### 6. `/aiagent-api/v1/aiagent/utility/wikipedia` - Wikipedia検索エージェント

**提供サービス**: Wikipedia APIを使用した百科事典情報の検索・要約。指定言語（日本語・英語など）でのページ内容取得と、LLMによる分かりやすい要約を提供。

**用途**: 用語の基礎知識調査、歴史的背景の理解、専門用語の説明、学術研究の前提知識収集、教育コンテンツ作成。

```yaml
wikipedia:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/wikipedia
    method: POST
    body:
      user_input: :search_query  # 検索キーワードまたは質問
      model_name: gpt-oss:20b
      language: ja  # 言語コード（ja, en等、デフォルト: ja）
      # 返却: { "summary": "Wikipediaの要約", "source_url": "元記事URL" }
```

#### 7. `/aiagent-api/v1/utility/google_search` - Google検索

**提供サービス**: Google Serper APIを使用して複数クエリのWeb検索を一括実行。検索結果（タイトル、URL、スニペット）を構造化データとして返却。

**用途**: 最新ニュース収集、市場調査、トレンド分析、複数トピックの並列調査、情報収集エージェントの前段処理。

```yaml
search:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
    method: POST
    body:
      queries: :query_list  # List[str] - 検索クエリのリスト
      num: 3  # 各クエリの取得結果数（デフォルト: 3）
      # 返却: { "results": [{ "title": "...", "link": "...", "snippet": "..." }, ...] }
```

#### 8. `/aiagent-api/v1/utility/google_search_overview` - Google検索概要

**提供サービス**: Google検索結果を取得し、LLMによる要約・サマリーを生成。検索結果の簡潔な概要を自然言語で提供。

**用途**: クイックリサーチ、トピックの即時理解、検索結果の効率的な把握、プレゼンテーション用サマリー作成。

```yaml
search_overview:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search_overview
    method: POST
    body:
      queries: :query_list  # List[str]
      num: 3  # 各クエリの取得結果数（オプション）
      model_name: gpt-oss:20b  # サマリー生成用モデル
      # 返却: { "summary": "検索結果の要約テキスト" }
```

#### 9. `/aiagent-api/v1/utility/tts_and_upload_drive` - 音声合成＆Google Drive連携

**提供サービス**: テキスト台本を音声合成（Text-to-Speech）でMP3/MP4ファイルに変換し、Google Driveにアップロード。アップロード完了後、共有可能なリンクURLを返却。

**用途**: ポッドキャスト台本の音声化、プレゼンテーション音声作成、教育コンテンツの音声版生成、音声配信コンテンツの自動生成・公開。

```yaml
tts_upload:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/utility/tts_and_upload_drive
    method: POST
    body:
      user_input: :podcast_script  # 音声化する台本テキスト
      # 返却: { "drive_link": "https://drive.google.com/...", "file_id": "..." }
```

#### 10. `/aiagent-api/v1/aiagent/sample` - サンプルエージェント

LangGraphベースのサンプルエージェント実行。

```yaml
sample:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/sample
    method: POST
    body:
      user_input: :instruction
      project: default_project  # プロジェクト名（オプション）
```

### テストモード機能

**🆕 すべてのexpertAgentエンドポイントでテストモードが利用可能です。**

テストモードを使用すると、実際のLLM呼び出しや外部API呼び出しを行わず、事前に定義したモックレスポンスを返却できます。これにより、ワークフロー開発時のトライアンドエラーを大幅に削減できます。

#### テストモードの利点

1. **開発時間の短縮**: LLM呼び出しなしでレスポンス構造を確認可能
2. **コスト削減**: テスト時のLLM API呼び出しコストが不要
3. **エラー特定の効率化**: レスポンス構造の問題とYML記述ミスを明確に分離
4. **高速な反復開発**: 即座にレスポンスが返るため、ワークフロー構造のみを素早く検証可能

#### 使用方法

すべてのexpertAgentエンドポイントで以下の2つのパラメータが使用可能です：

- **`test_mode`**: `true` に設定するとテストモードが有効化されます（デフォルト: `false`）
- **`test_response`**: テストモード時に返却するモックレスポンス（文字列または辞書）

#### テストレスポンスの形式

**文字列レスポンス** - 簡単なテキスト返却:
```yaml
body:
  user_input: :source
  test_mode: true
  test_response: "これはテストレスポンスです"
```

返却されるレスポンス:
```json
{
  "result": "これはテストレスポンスです",
  "text": "これはテストレスポンスです",
  "type": "mylllm_test"
}
```

**辞書型レスポンス** - カスタムフィールドを含む構造化データ（推奨）:
```yaml
body:
  user_input: :source
  test_mode: true
  test_response:
    result:
      outline:
        - title: "第1章"
          overview: "概要1"
          query_hint: ["クエリ1", "クエリ2"]
        - title: "第2章"
          overview: "概要2"
          query_hint: ["クエリ3", "クエリ4"]
```

返却されるレスポンス:
```json
{
  "result": {
    "outline": [
      {"title": "第1章", "overview": "概要1", "query_hint": ["クエリ1", "クエリ2"]},
      {"title": "第2章", "overview": "概要2", "query_hint": ["クエリ3", "クエリ4"]}
    ]
  }
}
```

**辞書型の利点**: GraphAIワークフローで `:node.field` アクセスが可能になり、複雑なデータフロー検証ができます。

#### 実践例1: プランナーのテスト

jsonoutputエンドポイントでアウトライン構造をテスト:

```yaml
planner_test:
  agent: fetchAgent
  inputs:
    url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
    method: POST
    body:
      user_input: :source
      test_mode: true
      test_response:
        result:
          outline:
            - title: "【序論】量子コンピュータとは"
              overview: "量子コンピュータの基本原理を説明"
              query_hint: ["量子コンピュータ 基本", "量子ビット"]
            - title: "【本論】最新動向"
              overview: "2025年の技術動向"
              query_hint: ["量子コンピュータ 2025", "量子超越性"]
```

データアクセス:
- `:planner_test.result.outline` → 配列全体にアクセス
- mapAgentで `:row.title`, `:row.overview`, `:row.query_hint` にアクセス可能

#### 実践例2: MapAgentと組み合わせたテスト

プランナー + マッパー + エクスプローラーの全体をテストモードで検証:

```yaml
version: 0.5
nodes:
  source: {}

  # プランナー（テストモード）
  planner:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source
        test_mode: true
        test_response:
          result:
            outline:
              - title: "Chapter 1"
                overview: "Overview 1"
                query_hint: ["query 1", "query 2"]
              - title: "Chapter 2"
                overview: "Overview 2"
                query_hint: ["query 3", "query 4"]

  # マッパー（各章を並列処理）
  mapper:
    agent: mapAgent
    inputs:
      rows: :planner.result.outline  # テストレスポンスの配列にアクセス
    graph:
      nodes:
        # 検索（テストモード）
        search:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
            method: POST
            body:
              queries: :row.query_hint  # テストレスポンスのフィールドにアクセス
              test_mode: true
              test_response:
                results:
                  - title: "Search Result"
                    url: "https://example.com"

        # エクスプローラー（テストモード）
        explorer:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
            method: POST
            body:
              user_input: :row.overview  # テストレスポンスのフィールドにアクセス
              test_mode: true
              test_response:
                result: "詳細レポートのテキスト"
          isResult: true

  output:
    agent: copyAgent
    inputs:
      text: :mapper
    isResult: true
```

このワークフローでは：
1. プランナーがモックのアウトラインを返却
2. マッパーが各章に対してループ処理
3. 検索とエクスプローラーがそれぞれテストレスポンスを返却
4. すべてLLM呼び出しなしで、ワークフロー構造を素早く検証可能

#### 実践例3: 段階的な本番移行

開発段階に応じてテストモードと本番モードを組み合わせ:

```yaml
# フェーズ1: 全体をテストモードで構造検証
planner:
  inputs:
    body:
      test_mode: true
      test_response: { ... }

# フェーズ2: プランナーのみ本番実行、後続はテスト
planner:
  inputs:
    body:
      test_mode: false  # 本番LLM実行

explorer:
  inputs:
    body:
      test_mode: true  # まだテスト
      test_response: "..."

# フェーズ3: 全体を本番実行
# test_mode パラメータを削除またはfalse設定
```

#### 対応エンドポイント

以下のすべてのエンドポイントでテストモードが利用可能です：

- `/aiagent-api/v1/mylllm`
- `/aiagent-api/v1/aiagent/sample`
- `/aiagent-api/v1/aiagent/utility/jsonoutput`
- `/aiagent-api/v1/aiagent/utility/explorer`
- `/aiagent-api/v1/aiagent/utility/action`
- `/aiagent-api/v1/aiagent/utility/playwright`
- `/aiagent-api/v1/aiagent/utility/wikipedia`
- `/aiagent-api/v1/aiagent/utility/file_reader`
- `/aiagent-api/v1/utility/google_search`
- `/aiagent-api/v1/utility/google_search_overview`
- `/aiagent-api/v1/utility/tts_and_upload_drive`

#### 注意事項

- `test_mode: false` または省略時は通常の本番実行になります
- `test_response` が `null` の場合はデフォルトメッセージが返却されます
- 文字列レスポンスは自動で標準レスポンス形式にラップされます
- 辞書型レスポンスはそのまま返却されるため、GraphAIでの柔軟なデータアクセスが可能です

### 利用可能なモデル

expertAgentのすべてのエンドポイントで `model_name` パラメータによりモデルを指定できます。

#### ローカルLLMモデル（推奨）

| モデル名 | 用途 | 特徴 | パラメータ数 |
|---------|------|------|------------|
| **gpt-oss:120b** | 複雑な処理 | 高精度、詳細な分析、複雑な推論 | 120B |
| **gpt-oss:20b** | 通常の処理 | バランス型、日常的なタスク | 20B |
| **pielee/qwen3-4b-thinking-2507_q8** | 軽量処理 | 高速、シンプルなタスク | 4B  |

**ローカルLLMの利点**:
- API料金不要
- プライバシー保護
- レスポンス速度の安定性

#### クラウドLLMモデル

| モデル名 | プロバイダー | 特徴 | リリース |
|---------|------------|------|---------|
| **gemini-2.5-pro** | Google | 最高精度、思考プロセス付き、100万トークンコンテキスト | 2025年3月 |
| **gemini-2.5-flash** | Google | 高速、コスト効率、バランス型 | 2025年6月 |
| **gemini-2.5-flash-lite** | Google | 超高速、最小コスト | 2025年6月 |
| **claude-sonnet-4.5** | Anthropic | コーディング世界最高、複雑なエージェント構築に最適 | 2025年9月 |
| **claude-opus-4.1** | Anthropic | エージェントタスク・実世界コーディング・推論に特化 | 2025年発表 |
| **gpt-5** | OpenAI | 統合システム、27万トークン入力、コーディング・数学に優れる | 2025年8月 |
| **gpt-5-mini** | OpenAI | バランス型、コスト効率重視 | 2025年8月 |
| **gpt-5-nano** | OpenAI | 軽量・超低コスト | 2025年8月 |

#### その他のローカルモデル（Ollama）

- **qwen3-next-80b-a3b-thinking-mlx**: 80Bパラメータ、思考プロセス付き
- **gemma3n:latest**: Google Gemma系軽量モデル

#### モデル選択ガイドライン

| タスクの種類 | 推奨モデル | 理由 |
|------------|----------|------|
| **複雑な推論・分析** | gpt-oss:120b | パラメータ数が多く詳細な処理が可能 |
| **レポート生成** | gpt-oss:120b | 長文生成、文脈理解に優れる |
| **情報収集・要約** | gpt-oss:20b | バランスが良く、実用的 |
| **JSON出力** | gpt-oss:20b | 構造化出力に十分な性能 |
| **簡単な変換** | pielee/qwen3-4b-thinking-2507_q8 | 高速処理、軽量タスク向け |
| **クリエイティブ作業** | gemini-2.5-pro / claude-sonnet-4.5 | クラウドモデルの強み |

---

## エラー回避パターン

### 1. sourceノードの参照エラー

**エラー**: `undefined` が出力に含まれる

**原因**: `:source.text` のように存在しないプロパティを参照

**解決策**:
```yaml
# ❌ 間違い
inputs:
  keywords: :source.text

# ✅ 正しい
inputs:
  keywords: :source
```

### 2. 非同期関数のawait漏れ

**エラー**: `RuntimeWarning: coroutine was never awaited`

**原因**: MCP toolsで非同期関数を同期的に呼び出している

**解決策**: expertAgent側のPythonコードで `await` を追加
```python
# ❌ 間違い
return get_overview_by_google_serper(input_query)

# ✅ 正しい
return await get_overview_by_google_serper(input_query)
```

### 3. ポート番号の誤り

**エラー**: `fetch failed` - connection refused

**原因**: 間違ったポート番号を使用（8000など）

**解決策**:
```yaml
# ❌ 間違い
url: http://127.0.0.1:8000/api/endpoint

# ✅ 正しい
url: http://127.0.0.1:8104/api/endpoint
```

### 4. mapAgentでのデータ参照エラー

**エラー**: `:row.field` が undefined

**原因**: 配列要素の構造を正しく理解していない

**解決策**:
```yaml
# planner が以下を返す場合:
# { "outline": [{"title": "...", "query_hint": ["..."]}] }

mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline  # ✅ .outline まで指定
  graph:
    nodes:
      process:
        inputs:
          title: :row.title        # ✅ 各要素のフィールドにアクセス
          queries: :row.query_hint # ✅
```

### 5. APIエンドポイントの不一致

**エラー**: `Cannot POST /api/v1/workflow/execute`

**原因**: ドキュメント等で参照したエンドポイントが、実際の `graphAiServer` の実装と異なっている。

**解決策**: `graphAiServer/src/app.ts` などのルーティング定義ファイルを確認し、正しいエンドポイントを使用する。2025年10月現在、ワークフロー実行用のエンドポイントは以下の通りです：

```bash
# ❌ 間違い
curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute

# ✅ 正しい（新形式推奨: モデル名をURLパスに含める）
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{workflow_name} \
  -H "Content-Type: application/json" \
  -d '{"user_input": "..."}'

# ✅ 正しい（旧形式: 後方互換性のためサポート継続）
curl -X POST http://127.0.0.1:8105/api/v1/myagent \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llmwork/{workflow_name}", "user_input": "..."}'
```

---

## パフォーマンスと並列処理の最適化

### 並列処理における注意事項

mapAgentで大量の並列処理を実行する際、以下のパフォーマンス問題が発生する可能性があります：

1. **expertAgentサービスの過負荷**
2. **HTTPタイムアウトエラー（fetch failed）**
3. **リクエストキューイングによる遅延**

### 問題発生パターンの例

以下のような並列処理YAMLは問題を引き起こす可能性があります：

```yaml
# ❌ 問題あり: 並列数の制限なし
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline  # 仮に4章のデータ
  params:
    compositeResult: true
  graph:
    nodes:
      explorer:
        agent: fetchAgent
        inputs:
          url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
          method: POST
          body:
            user_input: :row.overview
            model_name: gpt-oss:20b  # 重い処理
```

**問題点**:
- 4章すべてが同時にexpertAgentへリクエスト
- expertAgent（デフォルトは1ワーカー）が過負荷
- 4番目のリクエストがタイムアウト（fetch failed）

### 解決策1: mapAgentの並列数制限

`concurrency` パラメータで並列実行数を制限します：

```yaml
# ✅ 改善版: 並列数を2に制限
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline
  params:
    compositeResult: true
    concurrency: 2  # 同時実行を2つまでに制限
  graph:
    nodes:
      explorer:
        agent: fetchAgent
        inputs:
          url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
          method: POST
          body:
            user_input: :row.overview
            model_name: gpt-oss:20b
```

**効果**:
- 4章を2つずつ順次処理（バッチ処理）
- expertAgentへの同時リクエストが2つまで
- サービス過負荷を防止

**concurrency値の決め方**:
| 処理の重さ | 推奨並列数 | 説明 |
|----------|----------|------|
| **軽量** (Google検索のみ) | 4-8 | expertAgentへの負荷が小さい |
| **中程度** (explorer, jsonoutput) | 2-3 | LLM処理あり、中程度の負荷 |
| **重い** (gpt-oss:120b等の大型モデル) | 1-2 | 大型LLMモデル使用時 |

### 解決策2: グローバルfetchタイムアウトの延長

Node.jsのデフォルトHTTPタイムアウト（約10秒）は、LLM処理には短すぎます。

**graphAiServer起動時の設定** (src/index.ts):

```typescript
// Configure global fetch timeout (300 seconds)
const originalFetch = global.fetch;
global.fetch = async (url: RequestInfo | URL, options?: RequestInit): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000); // 300 seconds

  try {
    const response = await originalFetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
};
```

**効果**:
- すべてのfetchAgent呼び出しに300秒タイムアウトが適用
- LLM処理の長時間実行に対応
- タイムアウトエラー（fetch failed）を防止

**タイムアウト値の選択**:
- **30秒**: 軽量なAPI呼び出し（Google検索、単純な応答）
- **60秒**: 中程度のLLM処理（gpt-oss:20b, gemini-2.5-flash）
- **300秒**: 大型LLM処理（gpt-oss:120b, gemini-2.5-pro, 複雑なexplorer処理）

### 解決策3: expertAgentのワーカー数増加

expertAgentはデフォルトで1ワーカーで起動します。並列リクエストに対応するには、ワーカー数を増やす必要があります。

**dev-start.shでの設定**:

```bash
# ❌ デフォルト: 1ワーカー
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104

# ✅ 改善版: 4ワーカー
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4
```

**ワーカー数の決め方**:
- **基本方針**: `ワーカー数 ≥ mapAgent の concurrency`
- **推奨設定**:
  - concurrency: 2 → workers: 4（余裕を持たせる）
  - concurrency: 4 → workers: 4-8
  - concurrency: 8 → workers: 8-16

**注意点**:
- ワーカー数を増やすとメモリ使用量が増加
- CPU コア数も考慮する（コア数 × 2 程度が上限目安）

### 3層アーキテクチャでの最適化

並列処理の安定性を確保するには、3層すべてで対策が必要です：

| 層 | 対策 | 設定場所 | 効果 |
|----|------|---------|------|
| **Layer 1: Client** | 並列数制限 | YAMLファイル (`concurrency: 2`) | リクエスト過負荷防止 |
| **Layer 2: Transport** | タイムアウト延長 | graphAiServer/src/index.ts | 長時間処理対応 |
| **Layer 3: Server** | ワーカー増加 | dev-start.sh (`--workers 4`) | 真の並列処理実現 |

### トラブルシューティング: "fetch failed" エラー

#### 症状

```
TypeError: fetch failed
    at node:internal/deps/undici/undici:15363:13
```

並列処理の途中（例: 4章中の4番目）で発生

#### 診断手順

1. **ログのタイムスタンプ確認**:
```bash
grep "explorer_mapper start" logs/graphaiserver.log
# すべてのリクエストが同時刻に集中していないか確認
```

2. **expertAgentのワーカー数確認**:
```bash
grep "Started server process" logs/expertagent.log | wc -l
# 1の場合は並列処理に対応できていない
```

3. **並列数確認**:
YAMLファイルでmapAgentに `concurrency` パラメータがあるか確認

#### 解決手順

```yaml
# 1. YAMLに並列数制限を追加
explorer_mapper:
  agent: mapAgent
  params:
    concurrency: 2  # ← 追加
```

```typescript
// 2. graphAiServer/src/index.ts でタイムアウト延長
// （上記「解決策2」のコード参照）
```

```bash
# 3. expertAgentのワーカー数増加
# dev-start.sh を編集して --workers 4 を追加

# 4. サービス再起動
./scripts/dev-start.sh restart
```

### ベストプラクティス

#### 新規ワークフロー設計時

1. **並列処理の規模を見積もる**:
   - 処理する配列の要素数（章数、アイテム数）
   - 各要素の処理時間（LLMモデルの種類）

2. **concurrency値を設定**:
   - 軽量処理: 4-8
   - 中程度: 2-3
   - 重い処理: 1-2

3. **expertAgentのワーカー数を調整**:
   - `workers ≥ concurrency` を確保

4. **タイムアウトを確認**:
   - グローバルタイムアウトが300秒に設定済みか確認

#### 既存ワークフローの改善

以下のエラーが発生する場合は並列処理の最適化を検討：

- ❌ `TypeError: fetch failed`
- ❌ タイムアウトエラー
- ❌ 4番目以降の処理が失敗
- ❌ expertAgentのログに処理記録がない

**チェックリスト**:
- [ ] mapAgentに `concurrency` パラメータがある
- [ ] graphAiServer/src/index.ts でグローバルタイムアウト設定済み
- [ ] dev-start.sh で expertAgent に `--workers 4` 以上を設定
- [ ] 負荷テストで4-8並列処理が成功する

---

## 命名規則

### ノード名

- **小文字スネークケース**: `node_name`, `prompt_builder`
- **意味のある名前**: 処理内容が分かる名前を使用
- **接尾辞の使用**:
  - `_builder`: プロンプト構築ノード
  - `_mapper`: mapAgentノード
  - `_search`: 検索ノード
  - `_output`: 結果統合ノード

### 例

```yaml
nodes:
  source: {}

  # プロンプト構築
  pre_planner_prompt_builder:
    agent: stringTemplateAgent

  # プランニング
  pre_planner:
    agent: fetchAgent

  # 検索
  pre_explorer_search:
    agent: fetchAgent

  # 情報収集
  pre_explorer:
    agent: fetchAgent

  # 本処理のプロンプト
  planner_prompt_builder:
    agent: stringTemplateAgent

  # 本処理
  planner:
    agent: fetchAgent

  # 並列処理
  explorer_mapper:
    agent: mapAgent

  # 結果統合
  explorer_mapper_output:
    agent: arrayJoinAgent

  # 最終生成
  generator:
    agent: fetchAgent

  # アクション実行
  action:
    agent: fetchAgent

  # 最終出力
  output:
    agent: copyAgent
    isResult: true
```

---

## デバッグとログ

### consoleログの設定

```yaml
node_name:
  agent: fetchAgent
  console:
    before: node_name start  # 実行前ログ
    after: true              # 実行後に結果を出力
  inputs:
    # ...
```

### テンプレート変数のデバッグ

```yaml
prompt_builder:
  agent: stringTemplateAgent
  console:
    before: prompt_builder start
    after: true  # テンプレート展開結果を確認
  inputs:
    variable1: :source
  params:
    template: |-
      変数1: ${variable1}
```

### 推奨ログ設定

- **開発時**: すべてのノードで `after: true` を設定
- **本番**: 重要なノード（planner, generator, action）のみ `after: true`

---

## 実装例

### 例1: シンプルなLLM呼び出し

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_llm_call(llm_call<br/>fetchAgent)
  n_source --> n_llm_call
  n_output(output<br/>copyAgent)
  n_llm_call -- text --> n_output
  class n_source staticNode
  class n_llm_call,n_output computedNode
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  llm_call:
    agent: fetchAgent
    console:
      before: llm_call start
      after: true
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/mylllm
      method: POST
      body:
        user_input: :source
        model_name: gpt-oss:20b

  output:
    agent: copyAgent
    console:
      before: output start
    inputs:
      text: :llm_call.text
    isResult: true
```

### 例2: Google検索 → 情報整理 → レポート生成

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_query_builder(query_builder<br/>stringTemplateAgent)
  n_source --> n_query_builder
  n_query_generator(query_generator<br/>fetchAgent)
  n_query_builder --> n_query_generator
  n_search(search<br/>fetchAgent)
  n_query_generator -- result.querylist --> n_search
  n_info_organizer_prompt(info_organizer_prompt<br/>stringTemplateAgent)
  n_source --> n_info_organizer_prompt
  n_search -- result --> n_info_organizer_prompt
  n_info_organizer(info_organizer<br/>fetchAgent)
  n_info_organizer_prompt --> n_info_organizer
  n_report_generator_prompt(report_generator_prompt<br/>stringTemplateAgent)
  n_source --> n_report_generator_prompt
  n_info_organizer -- result --> n_report_generator_prompt
  n_report_generator(report_generator<br/>fetchAgent)
  n_report_generator_prompt --> n_report_generator
  n_output(output<br/>copyAgent)
  n_report_generator -- text --> n_output
  class n_source staticNode
  class n_query_builder,n_query_generator,n_search,n_info_organizer_prompt,n_info_organizer,n_report_generator_prompt,n_report_generator,n_output computedNode
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  # 検索クエリ生成
  query_builder:
    agent: stringTemplateAgent
    inputs:
      topic: :source
    params:
      template: |-
        # 指示書
        以下のトピックに関する検索クエリを3つ生成してください。

        トピック: ${topic}

        # 出力形式（JSON）
        {
          "querylist": ["クエリ1", "クエリ2", "クエリ3"]
        }

  query_generator:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :query_builder
        model_name: gpt-oss:20b

  # Google検索実行
  search:
    agent: fetchAgent
    console:
      after: true
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
      method: POST
      body:
        queries: :query_generator.result.querylist
        num: 3

  # 情報整理
  info_organizer_prompt:
    agent: stringTemplateAgent
    inputs:
      topic: :source
      search_result: :search.result
    params:
      template: |-
        # 指示書
        以下の検索結果を整理し、重要な情報を箇条書きでまとめてください。

        トピック: ${topic}

        検索結果:
        ${search_result}

  info_organizer:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
      method: POST
      body:
        user_input: :info_organizer_prompt
        model_name: gpt-oss:120b

  # レポート生成
  report_generator_prompt:
    agent: stringTemplateAgent
    inputs:
      topic: :source
      organized_info: :info_organizer.result
    params:
      template: |-
        # 指示書
        以下の情報を元に、包括的なレポートを作成してください。

        トピック: ${topic}

        整理された情報:
        ${organized_info}

  report_generator:
    agent: fetchAgent
    console:
      after: true
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/mylllm
      method: POST
      body:
        user_input: :report_generator_prompt
        model_name: gpt-oss:120b

  output:
    agent: copyAgent
    inputs:
      text: :report_generator.text
    isResult: true
```

### 例3: ポッドキャスト台本生成（複雑な並列処理）

**データフロー図**:
```mermaid
flowchart TD
  n_source(source)
  n_common_param(common_param)
  n_pre_planner_prompt_builder(pre_planner_prompt_builder<br/>stringTemplateAgent)
  n_source --> n_pre_planner_prompt_builder
  n_pre_planner(pre_planner<br/>fetchAgent)
  n_pre_planner_prompt_builder --> n_pre_planner
  n_pre_explorer_search(pre_explorer_search<br/>fetchAgent)
  n_pre_planner -- result.querylist --> n_pre_explorer_search
  n_pre_explorer_prompt_builder(pre_explorer_prompt_builder<br/>stringTemplateAgent)
  n_source --> n_pre_explorer_prompt_builder
  n_common_param -- target --> n_pre_explorer_prompt_builder
  n_pre_explorer_search -- result --> n_pre_explorer_prompt_builder
  n_pre_explorer(pre_explorer<br/>fetchAgent)
  n_pre_explorer_prompt_builder --> n_pre_explorer
  n_planner_prompt_builder(planner_prompt_builder<br/>stringTemplateAgent)
  n_source --> n_planner_prompt_builder
  n_common_param -- target --> n_planner_prompt_builder
  n_pre_explorer -- result --> n_planner_prompt_builder
  n_planner(planner<br/>fetchAgent)
  n_planner_prompt_builder --> n_planner
  subgraph n_explorer_mapper[explorer_mapper: mapAgent]
    n_explorer_mapper_explorer_search(explorer_search<br/>fetchAgent)
    n_explorer_mapper_row -- query_hint --> n_explorer_mapper_explorer_search
    n_explorer_mapper_explorer_prompt_builder(explorer_prompt_builder<br/>stringTemplateAgent)
    n_explorer_mapper_row -- title --> n_explorer_mapper_explorer_prompt_builder
    n_explorer_mapper_row -- overview --> n_explorer_mapper_explorer_prompt_builder
    n_explorer_mapper_explorer_search -- result --> n_explorer_mapper_explorer_prompt_builder
    n_explorer_mapper_explorer(explorer<br/>fetchAgent)
    n_explorer_mapper_explorer_prompt_builder --> n_explorer_mapper_explorer
    n_explorer_mapper_explorer_result_summary(explorer_result_summary<br/>stringTemplateAgent)
    n_explorer_mapper_row -- title --> n_explorer_mapper_explorer_result_summary
    n_explorer_mapper_explorer -- result --> n_explorer_mapper_explorer_result_summary
  end
  n_planner -- result.outline --> n_explorer_mapper
  n_explorer_mapper_output(explorer_mapper_output<br/>arrayJoinAgent)
  n_explorer_mapper -- explorer_result_summary --> n_explorer_mapper_output
  n_generator_prompt_builder(generator_prompt_builder<br/>stringTemplateAgent)
  n_source --> n_generator_prompt_builder
  n_common_param -- target --> n_generator_prompt_builder
  n_pre_explorer -- result --> n_generator_prompt_builder
  n_explorer_mapper_output -- text --> n_generator_prompt_builder
  n_generator(generator<br/>fetchAgent)
  n_generator_prompt_builder --> n_generator
  n_output(output<br/>copyAgent)
  n_generator -- text --> n_output
  class n_source,n_common_param staticNode
  class n_pre_planner_prompt_builder,n_pre_planner,n_pre_explorer_search,n_pre_explorer_prompt_builder,n_pre_explorer,n_planner_prompt_builder,n_planner,n_explorer_mapper_explorer_search,n_explorer_mapper_explorer_prompt_builder,n_explorer_mapper_explorer,n_explorer_mapper_explorer_result_summary,n_explorer_mapper_output,n_generator_prompt_builder,n_generator,n_output computedNode
  class n_explorer_mapper nestedGraph
```

**YAML定義**:
```yaml
version: 0.5
nodes:
  source: {}

  common_param:
    value:
      target: 39歳、男性

  # 検索クエリ生成
  pre_planner_prompt_builder:
    agent: stringTemplateAgent
    inputs:
      keywords: :source
    params:
      template: |-
        # 指示書
        以下のキーワードに関するGoogle検索クエリを2-3個生成してください。

        キーワード: ${keywords}

        # 出力形式（JSON）
        {
          "querylist": ["クエリ1", "クエリ2", "クエリ3"]
        }

  pre_planner:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :pre_planner_prompt_builder
        model_name: gpt-oss:120b

  # 事前検索
  pre_explorer_search:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
      method: POST
      body:
        queries: :pre_planner.result.querylist
        num: 3

  # 事前情報収集
  pre_explorer_prompt_builder:
    agent: stringTemplateAgent
    inputs:
      keywords: :source
      target: :common_param.target
      search_result: :pre_explorer_search.result
    params:
      template: |-
        # 指示書
        以下の検索結果から重要な用語と事実を抽出してください。

        対象: ${target}
        キーワード: ${keywords}

        検索結果:
        ${search_result}

  pre_explorer:
    agent: fetchAgent
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
      method: POST
      body:
        user_input: :pre_explorer_prompt_builder
        model_name: gpt-oss:120b

  # アウトライン生成
  planner_prompt_builder:
    agent: stringTemplateAgent
    inputs:
      keywords: :source
      target: :common_param.target
      infolist: :pre_explorer.result
    params:
      template: |-
        # 指示書
        以下の情報を元に、ポッドキャスト台本のアウトラインを生成してください。

        対象: ${target}
        キーワード: ${keywords}

        収集情報:
        ${infolist}

        # 出力形式（JSON）
        {
          "outline": [
            {
              "title": "序論タイトル",
              "overview": "概要",
              "query_hint": ["検索クエリ1", "検索クエリ2"]
            }
          ]
        }

  planner:
    agent: fetchAgent
    console:
      after: true
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :planner_prompt_builder
        model_name: gpt-oss:20b

  # 各章の情報収集（並列処理）
  explorer_mapper:
    agent: mapAgent
    inputs:
      rows: :planner.result.outline
    params:
      compositeResult: true
    graph:
      nodes:
        explorer_search:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/utility/google_search
            method: POST
            body:
              queries: :row.query_hint

        explorer_prompt_builder:
          agent: stringTemplateAgent
          inputs:
            title: :row.title
            overview: :row.overview
            search_result: :explorer_search.result
          params:
            template: |-
              # 指示書
              以下の情報を元に台本の初版を作成してください。

              タイトル: ${title}
              概要: ${overview}

              検索結果:
              ${search_result}

        explorer:
          agent: fetchAgent
          inputs:
            url: http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer
            method: POST
            body:
              user_input: :explorer_prompt_builder
              model_name: gpt-oss:20b

        explorer_result_summary:
          agent: stringTemplateAgent
          inputs:
            title: :row.title
            content: :explorer.result
          params:
            template: |-
              ### ${title}
              ${content}
          isResult: true

  # 結果統合
  explorer_mapper_output:
    agent: arrayJoinAgent
    params:
      separator: \n---\n
    inputs:
      array: :explorer_mapper.explorer_result_summary

  # 最終台本生成
  generator_prompt_builder:
    agent: stringTemplateAgent
    inputs:
      source: :source
      target: :common_param.target
      infolist: :pre_explorer.result
      explorer_result: :explorer_mapper_output.text
    params:
      template: |-
        # 指示書
        以下の情報を統合してポッドキャスト台本を作成してください。

        対象: ${target}
        キーワード: ${source}

        事前情報:
        ${infolist}

        各章の情報:
        ${explorer_result}

  generator:
    agent: fetchAgent
    console:
      after: true
    inputs:
      url: http://127.0.0.1:8104/aiagent-api/v1/mylllm
      method: POST
      body:
        user_input: :generator_prompt_builder
        model_name: gpt-oss:120b

  output:
    agent: copyAgent
    inputs:
      text: :generator.text
    isResult: true
```

---

## LLMプロンプト生成時の推奨事項

AIエージェントがYMLファイルを自動生成する際、以下のルールに従ってください：

### 1. 基本構造の確認

- [ ] `version: 0.5` を含む
- [ ] `nodes:` セクションがある
- [ ] `source: {}` ノードがある
- [ ] 最低1つの `isResult: true` ノードがある

### 2. データフローの検証

- [ ] すべてのノード間のデータ参照が正しい（`:node_name.field`）
- [ ] `source` ノードは直接参照（`:source`）している
- [ ] `mapAgent` 内では `:row.field` でアクセスしている

### 3. エージェント選択の検証

#### fetchAgent vs GraphAI標準エージェント

- [ ] **fetchAgent**: expertAgentの高度な機能が必要な場合（情報収集、アクション実行など）
- [ ] **anthropicAgent**: Claude APIの直接利用（高度な推論、長文生成）
- [ ] **geminiAgent**: Gemini APIの直接利用（高速処理、コスト効率）

#### エージェント選択基準

| タスク | 推奨エージェント | 理由 |
|-------|----------------|------|
| **情報収集・検索** | fetchAgent (expertAgent) | Google検索、Wikipedia、Webスクレイピング機能 |
| **複雑な推論** | anthropicAgent / fetchAgent | Claude or gpt-oss:120bの高度な推論能力 |
| **高速処理** | geminiAgent / fetchAgent | 低レイテンシー、リアルタイム応答 |
| **アクション実行** | fetchAgent (expertAgent) | メール送信、ファイル操作などのツール統合 |
| **構造化出力** | fetchAgent (expertAgent) | jsonoutputエンドポイントによる確実なJSON生成 |

### 4. expertAgent API統合の検証

- [ ] すべてのAPI URLが `http://127.0.0.1:8104` を使用
- [ ] 使用するエンドポイントが存在する（10種類のエンドポイントを確認）
- [ ] `model_name` パラメータが有効なモデル名

#### エンドポイント選択基準

| タスク | 推奨エンドポイント | 理由 |
|-------|----------------|------|
| **シンプルなLLM呼び出し** | `/mylllm` | 最も基本的、直接的なLLM実行 |
| **JSON形式の出力** | `/utility/jsonoutput` | 構造化データ生成に特化 |
| **情報収集** | `/utility/explorer` | 複雑な調査・レポート作成 |
| **Web検索** | `/utility/google_search` | 最新情報の取得 |
| **Webスクレイピング** | `/utility/playwright` | 動的サイトの情報取得 |
| **百科事典情報** | `/utility/wikipedia` | 基礎知識の調査 |
| **アクション実行** | `/utility/action` | メール送信、ファイル操作 |
| **音声合成** | `/utility/tts_and_upload_drive` | ポッドキャスト作成 |

### 5. モデル選択の検証

#### ローカルLLM優先原則

- [ ] **デフォルト**: ローカルLLMモデルを優先的に使用
- [ ] **gpt-oss:120b**: 複雑な推論・分析が必要な場合
- [ ] **gpt-oss:20b**: 通常の処理・バランス型タスク
- [ ] **pielee/qwen3-4b-thinking-2507_q8**: 軽量・高速処理が必要な場合

#### クラウドLLM使用条件

- [ ] **gemini-2.5-pro**: 最高精度、思考プロセス必要時、100万トークンコンテキスト活用時
- [ ] **gemini-2.5-flash**: 高速処理、コスト重視、バランス型タスク
- [ ] **claude-sonnet-4.5**: コーディング、複雑なエージェント構築、最高品質のクリエイティブ作業
- [ ] **claude-opus-4.1**: エージェントタスク、実世界コーディング、詳細な推論が必要な場合
- [ ] **gpt-5**: OpenAI最高精度、コーディング・数学タスク、27万トークン入力必要時
- [ ] **gpt-5-mini**: バランス型、コスト効率重視の汎用タスク

#### モデル選択チェックリスト

- [ ] タスクの複雑度を評価した
- [ ] 処理時間の要件を確認した
- [ ] コスト（ローカル vs クラウド）を考慮した
- [ ] 並列処理の規模に応じたモデルを選択した

### 6. エラー処理

- [ ] タイムアウトが適切に設定されている
- [ ] 重要なノードで `console.after: true` を設定
- [ ] 並列処理に `concurrency` パラメータを設定

### 7. 命名規則

- [ ] ノード名が意味のある名前
- [ ] 小文字スネークケースを使用
- [ ] 適切な接尾辞（`_builder`, `_mapper` など）を使用

---

## YMLファイルのヘッダーコメント規約

すべてのGraphAI YMLワークフローファイルには、以下の形式のヘッダーコメントを記載してください。

### ヘッダーフォーマット

```yaml
# =============================================================================
# GraphAI Workflow File
# =============================================================================
# Created: YYYY-MM-DD HH:MM:SS
# User Request:
#   [ユーザーからの要求を簡潔に記述]
#   [複数行にわたる場合は、適切にインデントして記載]
#
# Test Results:
#   - [YYYY-MM-DD HH:MM] Status: SUCCESS - [動作確認の詳細]
#   - [YYYY-MM-DD HH:MM] Status: FAILED - [エラー内容と原因]
#   - [YYYY-MM-DD HH:MM] Status: SUCCESS - [修正後の動作確認]
#
# Description:
#   [ワークフローの目的と概要を簡潔に記述]
#   [主要な処理フロー、使用するエージェント、期待される出力など]
#
# Notes:
#   - [実装時の注意点や制約事項]
#   - [今後の改善点や検討事項]
# =============================================================================

version: 0.5
nodes:
  # ワークフロー定義
```

### ヘッダー項目の説明

| 項目 | 必須 | 説明 |
|-----|------|------|
| **Created** | ✅ | ワークフロー作成日時（ISO 8601形式推奨） |
| **User Request** | ✅ | ユーザーからの要求内容を明確に記述 |
| **Test Results** | ✅ | 動作確認の履歴（日時、ステータス、結果） |
| **Description** | ✅ | ワークフローの目的・概要・主要処理フロー |
| **Notes** | ⭕ | 実装時の注意点、制約事項、改善点（任意） |

### Test Resultsステータス一覧

| ステータス | 意味 | 使用例 |
|----------|------|--------|
| **SUCCESS** | 正常動作確認完了 | `Status: SUCCESS - 全ノードが正常に実行され、期待通りの出力を確認` |
| **FAILED** | エラー・不具合発生 | `Status: FAILED - mapAgentでタイムアウト、concurrency未設定が原因` |
| **PARTIAL** | 一部動作確認 | `Status: PARTIAL - 前半ノードは正常、後半ノードは未検証` |
| **SKIP** | スキップ（検証不要） | `Status: SKIP - ユーザー環境での検証を推奨` |

### ヘッダー記載例

#### 例1: シンプルなワークフロー

```yaml
# =============================================================================
# GraphAI Workflow File
# =============================================================================
# Created: 2025-10-12 14:30:00
# User Request:
#   Google検索結果をもとに、技術トレンドレポートを生成する
#
# Test Results:
#   - [2025-10-12 14:45] Status: SUCCESS - 検索からレポート生成まで正常動作
#   - [2025-10-12 15:00] Status: SUCCESS - 複数トピックでの動作確認完了
#
# Description:
#   ユーザー入力トピックに対し、Google検索→情報整理→レポート生成を実行。
#   gpt-oss:120bモデルで詳細な分析レポートを出力。
# =============================================================================

version: 0.5
nodes:
  source: {}
  # ...
```

#### 例2: 複雑な並列処理ワークフロー

```yaml
# =============================================================================
# GraphAI Workflow File
# =============================================================================
# Created: 2025-10-12 16:00:00
# User Request:
#   ポッドキャスト台本を自動生成する。
#   - 事前調査（Google検索、Wikipedia）
#   - アウトライン生成（4-6章構成）
#   - 各章を並列で詳細調査・執筆
#   - 最終統合・音声ファイル化
#
# Test Results:
#   - [2025-10-12 16:30] Status: FAILED - mapAgentでfetch failed、concurrency未設定
#   - [2025-10-12 16:45] Status: FAILED - expertAgentワーカー数不足（1→4に変更必要）
#   - [2025-10-12 17:00] Status: SUCCESS - concurrency:2、workers:4で全4章正常処理
#   - [2025-10-12 17:15] Status: SUCCESS - 音声合成・Google Driveアップロード確認
#
# Description:
#   複雑な並列処理ワークフロー。事前調査→プランニング→並列執筆→統合→音声化。
#   mapAgentでconcurrency:2を設定し、expertAgentは4ワーカーで運用。
#   最終的にGoogle DriveへMP3ファイルをアップロードし、共有リンクを返却。
#
# Notes:
#   - expertAgent起動時は必ず --workers 4 を指定すること
#   - 大型モデル（gpt-oss:120b）使用時はタイムアウト300秒を確認
#   - concurrency値は処理の重さに応じて調整（軽量:4-8、中程度:2-3、重い:1-2）
# =============================================================================

version: 0.5
nodes:
  source: {}
  # ...
```

### ヘッダー記載のベストプラクティス

1. **User Request**: ユーザーの意図を正確に記録
   - 技術的な実装詳細ではなく、「何をしたいか」を記載
   - 複雑な要求は箇条書きで整理

2. **Test Results**: 時系列で動作確認履歴を記録
   - 失敗時はエラー内容と原因を必ず記載
   - 成功時も簡潔に動作確認内容を記載
   - 日時は `YYYY-MM-DD HH:MM` 形式推奨

3. **Description**: 技術的な概要を記載
   - 使用するエージェント・エンドポイント
   - データフローの概略
   - 期待される出力形式

4. **Notes**: 運用時の重要情報を記載
   - 前提条件（expertAgentのワーカー数など）
   - 制約事項（タイムアウト、並列数など）
   - 今後の改善点

---

## LLMワークフロー作成手順

AIエージェント（Claude、Gemini等）がGraphAI YMLワークフローファイルを作成する際の標準手順を示します。

### 全体フロー図

```mermaid
graph TD
  A[ユーザー要求受領] --> B[フェーズ1: 要件分析と設計合意]
  B --> C[フェーズ2: 実現可能性評価]
  C --> D{不足機能あり?}
  D -->|Yes| E[ユーザーへ機能追加提案]
  E --> F{提案承認?}
  F -->|No| A
  F -->|Yes| G[expertAgentへ機能追加]
  G --> H[フェーズ3: ワークフロー初期実装]
  D -->|No| H
  H --> I[フェーズ4: 動作確認と改善サイクル]
  I --> J{動作確認}
  J -->|SUCCESS| K[フェーズ5: 最終化]
  J -->|FAILED| L[エラー原因調査]
  L --> M[ルール更新・YML修正]
  M --> N{イテレーション回数}
  N -->|< 5回| I
  N -->|≥ 5回| O[ユーザーへフィードバック依頼]
  O --> P{ユーザー確認結果}
  P -->|動作OK| K
  P -->|動作NG| L
  K --> Q[ヘッダー更新・完了]
```

---

### フェーズ1: 要件分析と設計合意

#### 目的
ユーザーの要求を正確に理解し、実装すべきワークフローの全体像を合意する。

#### 実施内容

1. **ユーザー要求の確認**
   - 入力データ形式
   - 期待される出力形式
   - 処理フロー（順次処理 or 並列処理）
   - 品質要件（精度、速度、コスト）

2. **大まかな処理フローの提示**
   ```
   例：
   1. ユーザー入力（キーワード）
   2. Google検索でクエリ生成
   3. 検索実行（3件取得）
   4. 情報整理（explorerエージェント）
   5. レポート生成（LLM）
   6. 結果出力
   ```

3. **ユーザーとの合意形成**
   - 処理フローが要求に合致しているか確認
   - 必要に応じてフローを調整
   - 処理時間の目安を提示（軽量: 1-2分、中程度: 5-10分、重い: 20-30分）

---

### フェーズ2: 実現可能性評価

#### 目的
現在のexpertAgent機能で要求を実現できるか評価し、不足機能があればユーザーに提案する。

#### 評価項目と判定基準

| 評価項目 | 判定基準 | 対応 |
|---------|---------|------|
| **エンドポイントの存在** | 必要なAPIエンドポイントがexpertAgentに実装済みか | 未実装なら機能追加提案 |
| **データ形式の互換性** | 入力/出力データ形式が既存エンドポイントと互換性があるか | 不整合なら中間変換処理を追加 |
| **並列処理の必要性** | 大量データ処理でmapAgentが必要か | 必要ならconcurrency設定を計画 |
| **タイムアウトリスク** | 処理時間が長く、タイムアウトのリスクがあるか | リスクあればユーザーに事前通知 |

#### 不足機能の例と提案方法

**例1: YouTube字幕取得機能が必要な場合**

```
【実現可能性評価結果】

ユーザー要求: YouTubeの動画URLから字幕テキストを取得し、要約レポートを生成

評価結果:
  ✅ Google検索: 実装済み (/utility/google_search)
  ✅ LLM要約: 実装済み (/mylllm)
  ❌ YouTube字幕取得: 未実装

【機能追加提案】

expertAgentに以下のエンドポイント追加を推奨します：

エンドポイント: /utility/youtube_transcript
機能: YouTubeのURLまたは動画IDから字幕テキストを取得
実装方法: youtube-transcript-api パッケージを使用
処理時間: 約5-10秒（動画長により変動）

追加実装の工数: 約1-2時間

このまま進めますか？
  A) 機能追加を実施してから続行
  B) 現在の機能でできる範囲で代替案を検討
  C) 要求を見直す
```

**例2: 外部API連携が必要な場合**

```
【実現可能性評価結果】

ユーザー要求: 株価データを取得して投資レポートを生成

評価結果:
  ✅ Google検索: 実装済み
  ✅ LLM分析: 実装済み
  ⚠️ 株価データ取得: fetchAgentで外部API呼び出しは可能だが、
                      専用エンドポイントがないため、YMLファイルで
                      直接APIを指定する必要がある

【実装方針提案】

方針A（推奨）: Yahoo Finance APIを直接fetchAgentで呼び出す
  - YMLファイルで以下を記述:
    url: https://query1.finance.yahoo.com/v8/finance/chart/{symbol}
  - expertAgentへの変更: 不要
  - 制約: API仕様変更リスクあり

方針B: expertAgentに専用エンドポイント追加
  - エンドポイント: /utility/stock_data
  - 工数: 約2-3時間
  - メリット: エラーハンドリング、キャッシュ機能を実装可能

どちらで進めますか？
```

#### 機能追加が必要な場合の対応フロー

1. **ユーザーへ提案を提示**（上記例を参照）
2. **承認待ち**
   - 承認された場合: expertAgentへの機能追加を実施
   - 却下された場合: 代替案を検討、または要求を見直し
3. **機能追加後の確認**
   - 新エンドポイントの動作テスト
   - ドキュメント更新（本ルールファイルへの追記）

---

### フェーズ3: ワークフロー初期実装

#### 目的
`./graphAiServer/config/graphai/llmwork` ディレクトリにYMLファイルを作成し、初期実装を行う。

#### 実施内容

1. **ファイル命名**
   ```
   命名規則: {purpose}_{timestamp}.yml
   例: podcast_generation_20251012.yml
       stock_report_20251012.yml
   ```

2. **ヘッダーコメント記載**（前述の規約に従う）
   ```yaml
   # =============================================================================
   # GraphAI Workflow File
   # =============================================================================
   # Created: 2025-10-12 16:00:00
   # User Request:
   #   [フェーズ1で合意した内容を記載]
   #
   # Test Results:
   #   - [初期実装時点では空欄]
   #
   # Description:
   #   [フェーズ1で設計した処理フローを記載]
   # =============================================================================
   ```

3. **ワークフロー実装のチェックリスト**

   - [ ] `version: 0.5` を記載
   - [ ] `source: {}` ノードを定義
   - [ ] 最低1つの `isResult: true` ノードを定義
   - [ ] データフロー参照が正しい（`:source`, `:node_name.field`）
   - [ ] mapAgent使用時は `concurrency` を設定（推奨: 2-3）
   - [ ] 重要ノードに `console.after: true` を設定
   - [ ] モデル選択が適切（軽量: 4B、通常: 20B、複雑: 120B）
   - [ ] エンドポイントURLが正しい（ポート8104）

4. **実装時の注意点**

   | 注意項目 | 推奨事項 |
   |---------|---------|
   | **sourceノード参照** | `:source` で直接参照（`:source.text` は NG） |
   | **mapAgent並列数** | 軽量:4-8、中程度:2-3、重い:1-2 |
   | **タイムアウト** | graphAiServerでグローバル300秒設定を確認 |
   | **expertAgentワーカー** | 並列処理時は `--workers 4` 以上を推奨 |

---

### フェーズ4: 動作確認と改善サイクル（最大5イテレーション）

#### 目的
graphAiServer経由で動作確認を行い、エラーがあれば原因を調査・修正する。

#### イテレーションフロー

```
イテレーション N (N = 1, 2, 3, 4, 5)
├─ ステップ1: graphAiServerで実行
├─ ステップ2: 結果判定
│   ├─ SUCCESS → フェーズ5へ
│   └─ FAILED → ステップ3へ
├─ ステップ3: エラー原因調査
│   ├─ ログ確認（graphAiServer、expertAgent）
│   ├─ YMLファイル検証
│   └─ エンドポイント動作確認
├─ ステップ4: ルール更新・YML修正
│   ├─ 本ドキュメント（GRAPHAI_WORKFLOW_GENERATION_RULES.md）更新
│   ├─ YMLファイル修正
│   └─ expertAgent側の修正（必要に応じて）
└─ ステップ5: Test Resultsヘッダー更新
    └─ YMLファイルのヘッダーに動作確認結果を追記
```

#### ステップ1: graphAiServerで実行

**実行コマンド例**:
```bash
# graphAiServerが起動していることを確認
curl http://127.0.0.1:8105/health

# ワークフロー実行（新形式: モデル名をURLパスに含める）
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{your_workflow_name_without_extension} \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "ユーザー入力テキスト"
  }'
```

**確認ポイント**:
- HTTPステータスコード（200 OK / 500 Internal Server Error）
- レスポンスボディの内容
- 処理時間

#### ステップ2: 結果判定

| 判定 | 条件 | 次のアクション |
|-----|------|--------------|
| **SUCCESS** | - HTTPステータス200<br>- 期待通りの出力<br>- エラーログなし | フェーズ5へ進む |
| **FAILED** | - HTTPエラー<br>- 出力が不正<br>- タイムアウト<br>- エラーログあり | ステップ3（原因調査）へ |

#### ステップ3: エラー原因調査

**調査手順**:

1. **graphAiServerログ確認**
   ```bash
   tail -n 100 logs/graphaiserver.log | grep -i error
   ```

2. **expertAgentログ確認**
   ```bash
   tail -n 100 logs/expertagent.log | grep -i error
   ```

3. **YMLファイル構文検証**
   - sourceノード参照が正しいか
   - mapAgent使用時に `concurrency` があるか
   - エンドポイントURLが正しいか（ポート8104）

4. **エンドポイント動作確認**
   ```bash
   # expertAgentエンドポイントを直接テスト
   curl -X POST http://127.0.0.1:8104/aiagent-api/v1/mylllm \
     -H "Content-Type: application/json" \
     -d '{"user_input": "test", "model_name": "gpt-oss:20b"}'
   ```

**よくあるエラーと対応**:

| エラーパターン | 原因 | 対応 |
|-------------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | - expertAgent起動確認<br>- ポート番号確認（8104）<br>- ワーカー数確認（`--workers 4`） |
| `undefined` が出力に含まれる | sourceノード参照エラー | `:source.text` → `:source` に修正 |
| `RuntimeWarning: coroutine was never awaited` | expertAgent側のawait漏れ | expertAgentのPythonコードに `await` 追加 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | YMLに `concurrency: 2` 追加 |

#### ステップ4: ルール更新・YML修正

**ルール更新の判断基準**:

| 状況 | ルール更新の必要性 | 更新内容 |
|-----|----------------|---------|
| **新しいエラーパターン発見** | ✅ 必要 | 「エラー回避パターン」セクションに追記 |
| **新機能追加** | ✅ 必要 | 「expertAgent API統合」セクションに追記 |
| **既知のエラー** | ⭕ 不要 | YMLファイルのみ修正 |
| **ユーザー固有のエラー** | ⭕ 不要 | YMLファイルのNotesに記載 |

**YML修正例**:

```yaml
# 修正前（エラー発生）
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline
  params:
    compositeResult: true
  # ← concurrency がない

# 修正後（エラー解消）
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline
  params:
    compositeResult: true
    concurrency: 2  # ← 追加
```

#### ステップ5: Test Resultsヘッダー更新

**YMLファイルのヘッダーに動作確認結果を追記**:

```yaml
# Test Results:
#   - [2025-10-12 16:30] Status: FAILED - mapAgentでfetch failed、concurrency未設定
#   - [2025-10-12 16:45] Status: SUCCESS - concurrency:2追加で全ノード正常動作
```

#### イテレーション終了条件

| 条件 | 判定 | 次のアクション |
|-----|------|--------------|
| **SUCCESS判定** | ✅ | フェーズ5へ進む |
| **イテレーション回数 < 5** | ⏩ | 次のイテレーションへ |
| **イテレーション回数 ≥ 5** | ⚠️ | フェーズ4.1（ユーザーフィードバック依頼）へ |

---

### フェーズ4.1: ユーザーフィードバック依頼（イテレーション5回超過時）

#### 目的
5回のイテレーションで解決できない場合、ユーザーに動作確認を依頼し、フィードバックを得る。

#### 実施内容

1. **現状報告**
   ```
   【動作確認依頼】

   5回のイテレーションを実施しましたが、以下の課題が未解決です：

   問題点:
     - [具体的なエラー内容]
     - [再現手順]
     - [試した対策]

   確認依頼事項:
     1. 以下のコマンドでワークフローを実行してください
        $ curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute ...

     2. 実行結果（成功 or 失敗）を教えてください

     3. 失敗した場合、エラーログを共有してください
        $ tail -n 50 logs/graphaiserver.log
        $ tail -n 50 logs/expertagent.log
   ```

2. **ユーザーからのフィードバック受領**
   - 成功した場合: フェーズ5へ進む
   - 失敗した場合: 新しいエラー情報をもとに再度原因調査

3. **フィードバックをもとにした修正**
   - ユーザー環境固有の問題であれば、YMLファイルのNotesに記載
   - 一般的な問題であれば、ルール更新を実施

---

### フェーズ5: 最終化

#### 目的
動作確認が完了したワークフローを最終化し、ヘッダー情報を更新する。

#### 実施内容

1. **Test Resultsヘッダーの最終更新**
   ```yaml
   # Test Results:
   #   - [2025-10-12 16:30] Status: FAILED - mapAgentでfetch failed、concurrency未設定
   #   - [2025-10-12 16:45] Status: SUCCESS - concurrency:2追加で全4章正常処理
   #   - [2025-10-12 17:00] Status: SUCCESS - 音声合成・Google Driveアップロード確認
   #   - [2025-10-12 17:15] Status: SUCCESS - ユーザー環境での最終動作確認完了
   ```

2. **Notesセクションの追加（必要に応じて）**
   ```yaml
   # Notes:
   #   - expertAgent起動時は必ず --workers 4 を指定すること
   #   - 大型モデル（gpt-oss:120b）使用時はタイムアウト300秒を確認
   #   - YouTube動画URLの場合、字幕が存在しない動画ではエラーになる
   ```

3. **ファイル配置の確認**
   - 初期実装時: `./graphAiServer/config/graphai/llmwork/` に配置
   - 本番運用時: `./graphAiServer/config/graphai/default/` または `./graphAiServer/config/graphai/tutorial/` に移動（用途に応じて）

4. **ドキュメント更新（必要に応じて）**
   - 新しいエンドポイントを追加した場合: 本ドキュメントの「expertAgent API統合」セクションに追記
   - 新しいエラーパターンを発見した場合: 「エラー回避パターン」セクションに追記

5. **ユーザーへの完了報告**
   ```
   【ワークフロー作成完了】

   ファイル: ./graphAiServer/config/graphai/llmwork/podcast_generation_20251012.yml

   動作確認結果: SUCCESS
   - 全ノードが正常に動作
   - 期待通りの出力を確認
   - 処理時間: 約15分（4章構成の場合）

   使用方法:
     $ curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute \
       -H "Content-Type: application/json" \
       -d '{"workflow_file": "llmwork/podcast_generation_20251012.yml", "input": "量子コンピュータの最新動向"}'

   注意事項:
     - expertAgentは --workers 4 で起動してください
     - 処理時間は入力内容により変動します（10-30分程度）
   ```

---

### 作成手順のチェックリスト（全フェーズ共通）

AIエージェントは以下のチェックリストを参照し、各フェーズで必要な確認を実施してください。

#### フェーズ1: 要件分析と設計合意

- [ ] ユーザー要求の入力データ形式を確認した
- [ ] 期待される出力形式を確認した
- [ ] 処理フロー（順次 or 並列）を確認した
- [ ] 品質要件（精度、速度、コスト）を確認した
- [ ] 大まかな処理フローをユーザーに提示した
- [ ] ユーザーから設計合意を得た

#### フェーズ2: 実現可能性評価

- [ ] 必要なエンドポイントがexpertAgentに実装済みか確認した
- [ ] データ形式の互換性を確認した
- [ ] 並列処理の必要性を評価した
- [ ] タイムアウトリスクを評価した
- [ ] 不足機能がある場合、ユーザーに提案を提示した
- [ ] 提案が承認された場合、expertAgentへの機能追加を実施した

#### フェーズ3: ワークフロー初期実装

- [ ] ファイル名を適切に命名した（`{purpose}_{timestamp}.yml`）
- [ ] ヘッダーコメントを規約に従って記載した
- [ ] `version: 0.5` を記載した
- [ ] `source: {}` ノードを定義した
- [ ] 最低1つの `isResult: true` ノードを定義した
- [ ] データフロー参照が正しい（`:source`, `:node_name.field`）
- [ ] mapAgent使用時は `concurrency` を設定した
- [ ] 重要ノードに `console.after: true` を設定した
- [ ] モデル選択が適切（軽量: 4B、通常: 20B、複雑: 120B）
- [ ] エンドポイントURLが正しい（ポート8104）

#### フェーズ4: 動作確認と改善サイクル

- [ ] graphAiServer経由でワークフローを実行した
- [ ] 実行結果を判定した（SUCCESS or FAILED）
- [ ] FAILED時、エラー原因を調査した
- [ ] 必要に応じてルールを更新した
- [ ] YMLファイルを修正した
- [ ] Test Resultsヘッダーに動作確認結果を追記した
- [ ] イテレーション回数を確認した（最大5回）
- [ ] 5回超過時、ユーザーにフィードバック依頼を送信した

#### フェーズ5: 最終化

- [ ] Test Resultsヘッダーを最終更新した
- [ ] Notesセクションに注意事項を記載した（必要に応じて）
- [ ] ファイル配置が適切か確認した
- [ ] ドキュメント更新を実施した（必要に応じて）
- [ ] ユーザーへ完了報告を送信した

---

## 動作確認とトラブルシューティング

GraphAI YMLワークフローの動作確認を行う際の標準手順と、エラー発生時のトラブルシューティング方法を提供します。

### サービス起動確認

ワークフローを実行する前に、必要なサービスが正常に起動しているか確認してください。

#### 1. graphAiServerの起動確認

**ポート**: 8105

**確認方法**:
```bash
# ヘルスチェック
curl http://127.0.0.1:8105/health

# 期待されるレスポンス
# {"status": "healthy", "service": "graphAiServer"}
```

**起動方法（未起動の場合）**:
```bash
# プロジェクトルートから実行
./scripts/dev-start.sh

# またはgraphAiServerディレクトリから実行
cd graphAiServer
npm run dev
```

**ログ確認**:
```bash
# graphAiServerのログを確認
tail -f logs/graphaiserver.log
```

#### 2. expertAgentの起動確認

**ポート**: 8104

**確認方法**:
```bash
# ヘルスチェック
curl http://127.0.0.1:8104/health

# 期待されるレスポンス
# {"status": "healthy", "service": "expertAgent"}
```

**起動方法（未起動の場合）**:
```bash
# expertAgentディレクトリから実行
cd expertAgent

# 並列処理対応のため、4ワーカー推奨
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4
```

**ワーカー数の重要性**:
- **ワーカー数 = 1**: 並列処理（mapAgent）が実行されない
- **ワーカー数 ≥ 4**: 推奨設定（並列処理に対応）
- **concurrency値との関係**: `workers ≥ concurrency` を確保すること

**ログ確認**:
```bash
# expertAgentのログを確認
tail -f logs/expertagent.log

# ワーカー数確認
grep "Started server process" logs/expertagent.log | wc -l
# 出力が4以上であればOK
```

---

### ワークフロー実行方法

#### 基本的な実行コマンド

```bash
# 開発用エンドポイントで実行（新形式: モデル名をURLパスに含める）
curl -X POST http://127.0.0.1:8105/api/v1/myagent/llmwork/{your_workflow_name_without_extension} \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "ユーザー入力テキスト"
  }'
```

**パラメータ説明**:
- **URLパス**: `/api/v1/myagent/{category}/{model}`
  - `category`: ワークフローのカテゴリ（例: `llmwork`）
  - `model`: YMLファイル名（拡張子なし、例: `podcast_generation_20251012`）
- **リクエストボディ**:
  - `user_input`: sourceノードに渡される入力文字列（必須）
  - `project`: プロジェクト名（オプション）

**後方互換性**: 旧形式（`model_name`をリクエストボディに含める）も引き続きサポートされています：
```bash
# 旧形式（非推奨だが動作する）
curl -X POST http://127.0.0.1:8105/api/v1/myagent \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "llmwork/podcast_generation_20251012",
    "user_input": "ユーザー入力テキスト"
  }'
```

#### レスポンス確認

**成功時のレスポンス例**:
```json
{
  "status": "success",
  "result": {
    "text": "ワークフローの最終出力結果"
  },
  "execution_time": 123.45
}
```

**失敗時のレスポンス例**:
```json
{
  "status": "error",
  "error_message": "TypeError: fetch failed",
  "node": "explorer_mapper"
}
```

---

### ログ確認

#### 1. graphAiServerログ

```bash
# リアルタイムでログを表示
tail -f logs/graphaiserver.log

# 最新100行を確認
tail -n 100 logs/graphaiserver.log

# エラーのみ抽出
tail -n 100 logs/graphaiserver.log | grep -i error

# 特定ノードのログを抽出
grep "node_name start" logs/graphaiserver.log
```

**確認ポイント**:
- ノード実行の開始・終了タイムスタンプ
- エラーメッセージとスタックトレース
- データフロー参照エラー（`undefined` など）

#### 2. expertAgentログ

```bash
# リアルタイムでログを表示
tail -f logs/expertagent.log

# 最新100行を確認
tail -n 100 logs/expertagent.log

# エラーのみ抽出
tail -n 100 logs/expertagent.log | grep -i error

# ワーカー起動確認
grep "Started server process" logs/expertagent.log
```

**確認ポイント**:
- API呼び出しの成功・失敗
- モデルのロード状況
- RuntimeWarning（coroutine never awaited 等）
- タイムアウトエラー

---

### よくあるエラーと対応

| エラー | 原因 | 対応 |
|-------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | - expertAgent起動確認<br>- ポート番号確認（8104）<br>- ワーカー数確認（`--workers 4`） |
| `undefined` が出力に含まれる | sourceノード参照エラー | YMLファイルで `:source.text` → `:source` に修正 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | YMLに `concurrency: 2` パラメータを追加 |
| `RuntimeWarning: coroutine was never awaited` | expertAgent側のawait漏れ | expertAgentのPythonコードに `await` 追加 |
| `Connection refused (port 8104)` | expertAgentが起動していない | expertAgentを起動（`--workers 4`） |
| `HTTP 500 Internal Server Error` | graphAiServer内部エラー | - graphAiServerログ確認<br>- YML構文エラーをチェック |
| `Model not found: gpt-oss:xxx` | 指定モデルが存在しない | - モデル名のタイポ確認<br>- 利用可能なモデルリスト確認 |

詳細なエラー回避パターンは「[エラー回避パターン](#エラー回避パターン)」セクションを参照してください。

---

### エラー発生時の診断手順

エラーが発生した場合、以下の手順で原因を特定してください。

#### ステップ1: ログのタイムスタンプ確認

```bash
grep "node_name start" logs/graphaiserver.log
# リクエストが同時刻に集中していないか確認
```

**確認ポイント**:
- 並列処理（mapAgent）でリクエストが集中していないか
- expertAgentへのリクエスト間隔が適切か

#### ステップ2: expertAgentのワーカー数確認

```bash
grep "Started server process" logs/expertagent.log | wc -l
# 出力が1の場合は並列処理に対応できていない
```

**判定基準**:
- ワーカー数 = 1 → **NG**: 並列処理不可、起動オプションに `--workers 4` を追加
- ワーカー数 ≥ 4 → **OK**: 並列処理対応

#### ステップ3: 並列数（concurrency）確認

YMLファイルでmapAgentに `concurrency` パラメータがあるか確認してください。

```yaml
# ❌ NG: concurrency がない
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline
  params:
    compositeResult: true
  # ← concurrency がない

# ✅ OK: concurrency が設定されている
explorer_mapper:
  agent: mapAgent
  inputs:
    rows: :planner.result.outline
  params:
    compositeResult: true
    concurrency: 2  # ← 追加
```

**推奨concurrency値**:
| 処理の重さ | concurrency推奨値 | 説明 |
|-----------|-----------------|------|
| **軽量** | 4-8 | gpt-oss:4b 等、軽量モデル使用時 |
| **中程度** | 2-3 | gpt-oss:20b、gpt-4o-mini 等 |
| **重い** | 1-2 | gpt-oss:120b、gpt-4o 等、大型モデル使用時 |

#### ステップ4: データフロー参照の確認

YMLファイルのデータフロー参照が正しいか確認してください。

**よくある誤り**:
```yaml
# ❌ NG: source.text としている
inputs:
  keywords: :source.text  # ← undefined になる

# ✅ OK: source を直接参照
inputs:
  keywords: :source  # ← 正しい
```

#### ステップ5: エンドポイント動作確認

expertAgentのエンドポイントが正常に動作するか直接テストしてください。

```bash
# expertAgentエンドポイントを直接テスト
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/mylllm \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test", "model_name": "gpt-oss:20b"}'
```

**期待されるレスポンス**:
```json
{
  "response": "テストレスポンス内容",
  "model": "gpt-oss:20b"
}
```

---

### ルール更新の判断基準

エラー修正後、本ドキュメント（GRAPHAI_WORKFLOW_GENERATION_RULES.md）の更新が必要か判断してください。

| 状況 | ルール更新の必要性 | 更新内容 |
|-----|----------------|---------|
| **新しいエラーパターン発見** | ✅ 必要 | 「エラー回避パターン」セクションに追記 |
| **新機能追加** | ✅ 必要 | 「expertAgent API統合」セクションに追記 |
| **既知のエラー** | ⭕ 不要 | YMLファイルのみ修正 |
| **ユーザー固有のエラー** | ⭕ 不要 | YMLファイルのNotesに記載 |

**ルール更新の例**:

**新しいエラーパターン発見時**:
```markdown
### エラー回避パターン

#### [追加] sourceノード参照エラー

**問題**: `:source.text` として参照すると `undefined` が出力される

**原因**: sourceノードは文字列が直接注入されるため、プロパティアクセス不要

**解決策**: `:source` で直接参照する
```

**新機能追加時**:
```markdown
### expertAgent API統合

#### [追加] /utility/youtube_transcript エンドポイント

**機能**: YouTubeの動画URLから字幕テキストを取得

**使用例**:
\`\`\`yaml
youtube_fetcher:
  agent: fetchAgent
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/utility/youtube_transcript"
    method: "POST"
    data:
      video_url: ":source"
\`\`\`
```

---

## ワークフロー作成時の動作確認方法

GraphAI YMLワークフローを実行する前に、必要なサービスが正常に起動しているか確認し、適切な方法でワークフローを実行してください。

### 前提条件の確認

#### 1. graphAiServerの起動確認

**ポート**: 8105

**確認方法**:
```bash
# ヘルスチェック
curl http://127.0.0.1:8105/health

# 期待されるレスポンス
# {"status": "healthy", "service": "graphAiServer"}
```

**起動方法（未起動の場合）**:
```bash
# プロジェクトルートから実行
./scripts/dev-start.sh

# またはgraphAiServerディレクトリから実行
cd graphAiServer
npm run dev
```

**ログ確認**:
```bash
# graphAiServerのログを確認
tail -f logs/graphaiserver.log
```

#### 2. expertAgentの起動確認

**ポート**: 8104

**確認方法**:
```bash
# ヘルスチェック
curl http://127.0.0.1:8104/health

# 期待されるレスポンス
# {"status": "healthy", "service": "expertAgent"}
```

**起動方法（未起動の場合）**:
```bash
# プロジェクトルートから実行
./scripts/dev-start.sh

# または手動でワーカー数を指定して起動
cd expertAgent
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4
```

**ワーカー数の確認**:
```bash
# expertAgentのプロセス一覧を確認
ps aux | grep "uvicorn.*8104"

# 並列処理を行う場合は --workers 4 以上を推奨
# 1ワーカーのみの場合、mapAgentで並列処理がタイムアウトする可能性がある
```

**ログ確認**:
```bash
# expertAgentのログを確認
tail -f logs/expertagent.log

# エラーログのみ確認
tail -f logs/expertagent.log | grep -i error
```

#### 3. myVaultの起動確認

**ポート**: 8103

**確認方法**:
```bash
# ヘルスチェック
curl http://127.0.0.1:8103/health

# 期待されるレスポンス
# {"status": "healthy", "service": "myVault"}
```

**起動方法（未起動の場合）**:
```bash
# プロジェクトルートから実行
./scripts/dev-start.sh

# または手動で起動
cd myVault
uv run uvicorn app.main:app --host 0.0.0.0 --port 8103
```

**ログ確認**:
```bash
# myVaultのログを確認
tail -f logs/myvault.log
```

### LLMワークフローの実行方法

#### 方法1: graphAiServer経由での実行（推奨）

graphAiServerは、YMLワークフローファイルを読み込み、GraphAIエンジンで実行します。

**実行コマンド例**:
```bash
# graphAiServerのAPIエンドポイント経由で実行
curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_file": "llmwork/podcast_generation_20251012.yml",
    "input": "量子コンピュータの最新動向"
  }'
```

**パラメータ説明**:
- `workflow_file`: `./graphAiServer/config/graphai/` 以下の相対パス
  - 例: `llmwork/sample.yml` → `./graphAiServer/config/graphai/llmwork/sample.yml`
  - 例: `default/test.yml` → `./graphAiServer/config/graphai/default/test.yml`
- `input`: sourceノードに注入される文字列データ

**成功時のレスポンス例**:
```json
{
  "status": "success",
  "result": {
    "text": "生成された最終テキスト..."
  },
  "execution_time_ms": 45000
}
```

**エラー時のレスポンス例**:
```json
{
  "status": "error",
  "error": "TypeError: fetch failed",
  "details": "expertAgentへの接続失敗。ポート8104が起動しているか確認してください。"
}
```

#### 方法2: expertAgentのエンドポイント直接呼び出し

expertAgentの個別機能を単体テストする場合に使用します。

**mylllmエンドポイント（汎用LLM実行）**:
```bash
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/mylllm \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "量子コンピュータの最新動向を教えてください",
    "model_name": "gpt-oss:20b"
  }'
```

**jsonoutputエンドポイント（JSON構造化出力）**:
```bash
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/jsonoutput \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "以下の形式でアウトラインを生成してください: {\"outline\": [{\"title\": \"章タイトル\", \"overview\": \"概要\"}]}",
    "model_name": "gpt-oss:20b"
  }'
```

**google_searchエンドポイント（Google検索）**:
```bash
curl -X POST http://127.0.0.1:8104/aiagent-api/v1/utility/google_search \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["量子コンピュータ 2025", "量子ビット 最新技術"],
    "num": 3
  }'
```

### トラブルシューティング

#### エラーパターン1: サービス起動失敗

**症状**:
```bash
curl: (7) Failed to connect to 127.0.0.1 port 8104: Connection refused
```

**原因**: expertAgentが起動していない

**対応**:
```bash
# expertAgentを起動
cd expertAgent
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4

# または dev-start.sh で全サービス起動
./scripts/dev-start.sh
```

#### エラーパターン2: fetch failed（並列処理時）

**症状**:
```
TypeError: fetch failed
    at node:internal/deps/undici/undici:15363:13
```

**原因**:
1. expertAgentのワーカー数不足（1ワーカーで並列リクエスト処理不可）
2. mapAgentの`concurrency`設定なし

**対応**:
```yaml
# YMLファイルに concurrency を追加
explorer_mapper:
  agent: mapAgent
  params:
    concurrency: 2  # ← 追加
```

```bash
# expertAgentをワーカー数4で再起動
pkill -f "uvicorn.*8104"
cd expertAgent
uv run uvicorn app.main:app --host 0.0.0.0 --port 8104 --workers 4
```

#### エラーパターン3: タイムアウトエラー

**症状**:
```
Error: Request timeout after 30000ms
```

**原因**: graphAiServerのグローバルfetchタイムアウトが短い

**対応**:
graphAiServer/src/index.ts で以下を確認:
```typescript
// グローバルfetchタイムアウト設定（300秒）
const originalFetch = global.fetch;
global.fetch = async (url: RequestInfo | URL, options?: RequestInit): Promise<Response> => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 300000); // 300秒

  try {
    const response = await originalFetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
};
```

設定後、graphAiServerを再起動:
```bash
./scripts/dev-start.sh restart
```

### 動作確認チェックリスト

ワークフローを実行する前に、以下を確認してください：

- [ ] graphAiServerが起動している（ポート8105）
- [ ] expertAgentが起動している（ポート8104）
- [ ] myVaultが起動している（ポート8103）
- [ ] expertAgentは `--workers 4` 以上で起動している（並列処理を行う場合）
- [ ] YMLファイルが正しいディレクトリに配置されている（`./graphAiServer/config/graphai/`）
- [ ] YMLファイルに `concurrency` パラメータが設定されている（mapAgent使用時）
- [ ] graphAiServerのグローバルfetchタイムアウトが300秒に設定されている

### ログ監視方法

ワークフロー実行中は、以下のコマンドで各サービスのログをリアルタイム監視してください：

```bash
# graphAiServerのログ監視（新しいターミナル）
tail -f logs/graphaiserver.log

# expertAgentのログ監視（新しいターミナル）
tail -f logs/expertagent.log

# エラーログのみ監視
tail -f logs/graphaiserver.log | grep -i error
tail -f logs/expertagent.log | grep -i error
```

---

## まとめ

このルールに従うことで、GraphAI YMLワークフローファイルを効率的かつエラーなく生成できます。

### 最重要ポイント

#### 基本設定

1. **ポート番号**: expertAgentは `8104`
2. **sourceノード**: `:source` で直接参照（`.text` は不要）
3. **mapAgent**: `:row.field` でデータアクセス

#### パフォーマンス最適化

4. **並列処理**: mapAgentに `concurrency` を設定（推奨: 2-3）
5. **タイムアウト**: グローバルfetchタイムアウト300秒を確認
6. **ワーカー数**: expertAgentは `--workers 4` 以上で起動

#### エージェントとモデル選択

7. **エージェント選択**:
   - 情報収集・アクション実行: fetchAgent (expertAgent)
   - 高度な推論: anthropicAgent / fetchAgent (gpt-oss:120b)
   - 高速処理: geminiAgent / fetchAgent

8. **モデル選択**:
   - 複雑な処理: `gpt-oss:120b`
   - 通常の処理: `gpt-oss:20b`（デフォルト推奨）
   - 軽量処理: `pielee/qwen3-4b-thinking-2507_q8`

9. **外部API統合**: fetchAgentは任意の外部APIを呼び出し可能（インターフェース定義が必要）

10. **デバッグログ**: `console.after: true` を活用

### 次のステップ

- 既存のYMLファイルを参考に新しいワークフローを設計
- 小さなワークフローから始めて段階的に複雑化
- デバッグログを活用して動作確認
- エラーが発生したら本ドキュメントのエラー回避パターンを確認

---

## 付録A: Playwright Agent 完全ガイド

### 概要

Playwright Agentは、Webブラウザを自動操作してWebページからデータを抽出・処理するエージェントです。expertAgent API経由でLangGraph ReAct agentパターンで統合されており、Playwright MCPの20種類以上のツールを活用できます。

**⚠️ 重要な制限事項:**
- **Webサイトからの情報抽出には不向き**: ブラウザの構造化データ取得の精度が低く、特定要素の抽出が困難
- **推奨用途**: フォーム操作、スクリーンショット取得、JavaScript実行など、ブラウザ操作が必要な場合のみ
- **代替手段**: Webページからのテキスト・情報抽出には **Explorer Agent（html2markdown MCP）** の使用を強く推奨

### コア機能

#### 1. **Webページの遷移・操作**

- **ページナビゲーション**: URL遷移、戻る操作
- **フォーム操作**: テキスト入力、ボタンクリック、ドロップダウン選択
- **インタラクション**: ドラッグ&ドロップ、ホバー、キーボード入力
- **タブ管理**: 新規タブ作成、タブ切替、タブクローズ

#### 2. **Webページからのデータ抽出**

- **ページ全体のテキスト取得**: `browser_snapshot`でアクセシビリティツリー形式で構造化されたテキストを取得
- **特定要素のテキスト抽出**: セレクタ指定で特定部分のみ抽出
- **ファイルリンクの一括抽出**: PDFリンク、画像リンク、ダウンロードリンク等を自動収集
- **スクリーンショット取得**: ページ全体または特定要素のスクリーンショット

#### 3. **動的コンテンツ対応**

- **要素の出現待機**: 特定のテキストや要素が表示されるまで待機
- **JavaScript実行**: カスタムJavaScriptをページ上で実行
- **ネットワーク監視**: HTTPリクエスト/レスポンスの記録
- **コンソールログ取得**: ブラウザコンソールのログ・エラーを取得

### GraphAI YML統合パターン

#### パターン1: Webページからテキスト抽出

```yaml
# ニュースサイトから記事本文を抽出
web_scraper:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
    method: "POST"
    data:
      user_input: "下記サイトから記事のタイトルと本文を抽出してください。\nhttps://example.com/news/article-123"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン2: PDFリンク一括抽出

```yaml
# 政府サイトから公開資料のPDFリンクを全て抽出
pdf_link_extractor:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
    method: "POST"
    data:
      user_input: "下記サイトから全てのPDFファイルのURLリンクを抽出してください。\nhttps://japancredit.go.jp/data/"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン3: 複数ページから情報収集

```yaml
# 複数の製品ページから価格情報を収集
price_collector:
  agent: "mapAgent"
  inputs:
    rows: [":product_urls"]
  params:
    concurrency: 2  # 並列数制限（Bot検出回避）
  graph:
    nodes:
      fetch_price:
        agent: "fetchAgent"
        params:
          url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
          method: "POST"
          data:
            user_input: "下記製品ページから製品名と価格を抽出してください。\n:row"
            model_name: "gpt-4o-mini"
        isResult: true
```

### 利用可能なPlaywright MCPツール（主要20種類）

expertAgent内部で使用可能なツール一覧（使用頻度順）:

| ツール名 | 機能 | 使用例 |
|---------|------|-------|
| `browser_snapshot` | ページ全体の構造・テキスト取得 | テキスト抽出、構造解析 |
| `browser_navigate` | URL遷移 | ページ移動、初回アクセス |
| `browser_click` | 要素クリック | ボタン押下、リンククリック |
| `browser_type` | テキスト入力 | フォーム入力、検索ボックス |
| `browser_take_screenshot` | スクリーンショット | ページキャプチャ、証拠保存 |
| `browser_wait_for` | 要素の出現待機 | 動的コンテンツ読込待ち |
| `browser_evaluate` | JavaScript実行 | カスタム処理、データ抽出 |
| `browser_fill_form` | フォーム一括入力 | 複数フィールド入力 |
| `browser_network_requests` | ネットワーク監視 | API呼び出し確認 |
| `browser_console_messages` | コンソールログ取得 | エラー確認、デバッグ |
| その他10種類 | select_option, hover, drag, tabs等 | - |

**重要**: これらのツールはLLMエージェントが自動選択します。ワークフロー作成者が直接指定する必要はありません。

### 技術的注意事項

#### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/playwright`
- **推奨モデル**: `gpt-4o-mini`（Playwright指示理解に最適、コスト効率良好）
- **最大イテレーション**: 5回（デフォルト）

#### Bot検出対策

expertAgentでは以下の対策が実装済み:

- **User-Agent設定**: Chrome 131相当の現実的なUser-Agentを自動設定
- **Headlessモード**: `--headless`オプション有効
- **並列数制限**: mapAgent使用時は`concurrency: 2`推奨（同時アクセス過多を回避）

**対応例**:
- ✅ `https://japancredit.go.jp/data/` - 403エラーを回避（User-Agent設定により解決済み）
- ✅ 一般的な企業サイト - 問題なくアクセス可能

#### Docker要件

- **共有メモリ**: `shm_size: 2gb` 必須（Chromiumブラウザ動作に必要）
- **設定場所**: `docker-compose.yml`の`expertagent`サービス

```yaml
services:
  expertagent:
    shm_size: 2gb  # Playwright動作に必須
```

#### タイムアウト設定

- **グローバルタイムアウト**: 300秒（5分）
- **ページロードタイムアウト**: 30秒（Playwright MCP内部設定）
- **並列処理時の注意**: 重いLLM（gpt-oss:120b）使用時はconcurrency:1-2推奨

### よくある使用パターン

#### 使用例1: 競合他社の価格調査

```yaml
version: 0.5
nodes:
  source:
    value:
      competitors:
        - "https://competitor-a.com/product"
        - "https://competitor-b.com/product"

  price_research:
    agent: "mapAgent"
    inputs:
      rows: [":source.competitors"]
    params:
      concurrency: 2
    graph:
      nodes:
        scrape:
          agent: "fetchAgent"
          params:
            url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
            method: "POST"
            data:
              user_input: "下記ページから製品名、価格、在庫状況を抽出してください。\n:row"
              model_name: "gpt-4o-mini"
          isResult: true
    isResult: true
```

#### 使用例2: 公開資料の自動収集

```yaml
version: 0.5
nodes:
  source:
    value:
      target_url: "https://example.gov.jp/reports/"

  collect_pdf_links:
    agent: "fetchAgent"
    inputs:
      url: [":source.target_url"]
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/playwright"
      method: "POST"
      data:
        user_input: "下記サイトから全てのPDFファイルのURLリンクを抽出してください。\n:source.target_url"
        model_name: "gpt-4o-mini"
    console:
      after: true
    isResult: true
```

---

## 付録B: Explorer Agent 完全ガイド

### 概要

Explorer Agentは、Web検索とWebページコンテンツ抽出に特化したエージェントです。Google検索、WebサイトのHTML→Markdown変換、Gmail検索など、情報収集タスクに最適化されています。

### コア機能

#### 1. **Web検索（Google Custom Search API）**

- **キーワード検索**: Google検索で情報を収集
- **結果フィルタリング**: 件数指定、ドメイン制限
- **構造化出力**: タイトル、URL、スニペット

#### 2. **Webページコンテンツ抽出（html2markdown MCP）** 🆕

- **HTMLをMarkdownに変換**: Webページの内容を構造化されたMarkdown形式で取得
- **高精度**: Playwright Agentと比較して、テキスト抽出精度が大幅に向上
- **推奨用途**: ニュース記事、ブログ記事、ドキュメントページなど、テキストコンテンツの抽出
- **対応形式**: HTML → Markdown（見出し、リスト、リンク、表などを保持）

**Playwright Agentとの比較:**

| 項目 | Explorer Agent (html2markdown) | Playwright Agent |
|------|-------------------------------|------------------|
| **テキスト抽出精度** | ⭐⭐⭐⭐⭐ 高精度 | ⭐⭐ 低精度 |
| **構造保持** | ⭐⭐⭐⭐⭐ Markdown形式 | ⭐⭐ アクセシビリティツリー |
| **推奨用途** | **Webページの情報抽出** | ブラウザ操作・スクリーンショット |
| **処理速度** | ⭐⭐⭐⭐⭐ 高速 | ⭐⭐⭐ 中速 |

#### 3. **Gmail検索（Gmail MCP）** 🆕

- **メール検索**: Gmail検索クエリでメールを検索
- **フィルタリング**: 送信者、件名、日付範囲などで絞り込み
- **本文取得**: メール本文の取得・解析
- **OAuth2認証**: MyVault経由で安全にアクセス

### GraphAI YML統合パターン

#### パターン1: Webページからテキスト抽出（html2markdown）

```yaml
# ニュースサイトから記事本文を抽出
web_content_extractor:
  agent: fetchAgent
  inputs:
    url: :source
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
    method: "POST"
    body:
      user_input: "下記サイトの記事本文をMarkdown形式で抽出してください。\nhttps://example.com/news/article-123"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン2: Google検索とコンテンツ収集

```yaml
# Google検索で上位5件の記事を取得し、各記事の本文を抽出
research_workflow:
  agent: fetchAgent
  inputs:
    query: :source
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
    method: "POST"
    body:
      user_input: "下記キーワードでGoogle検索し、上位5件の記事の本文を抽出してMarkdownで出力してください。\n:query"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン3: Gmail検索とメール解析

```yaml
# 特定の送信者からの未読メールを検索・要約
gmail_search:
  agent: fetchAgent
  inputs:
    search_query: :source
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
    method: "POST"
    body:
      user_input: "Gmailで下記条件のメールを検索し、件名と本文の要約を出力してください。\n検索条件: from:boss@example.com is:unread"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

### 利用可能なMCPツール

Explorer Agent内部で使用可能なツール一覧:

| ツール名 | 機能 | 使用例 |
|---------|------|-------|
| **html2markdown** 🆕 | HTMLをMarkdownに変換 | Webページのテキスト抽出 |
| **google_search** | Google Custom Search | キーワード検索、情報収集 |
| **gmail_search** 🆕 | Gmail検索 | メール検索、受信トレイ管理 |

**重要**: これらのツールはLLMエージェントが自動選択します。ワークフロー作成者が直接指定する必要はありません。

### 技術的注意事項

#### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/explorer`
- **推奨モデル**: `gpt-4o-mini`（指示理解に最適、コスト効率良好）

#### html2markdown MCP

- **出力形式**: Markdown（見出し `#`, リスト `-`, リンク `[text](url)` など）
- **文字コード**: UTF-8
- **エラー処理**: ページ取得失敗時はエラーメッセージを返す

#### Gmail MCP

- **認証**: MyVault経由でOAuth2トークン取得
- **権限**: Gmail読み取り専用スコープ
- **事前準備**: ユーザーがMyVaultでGoogle認証を完了している必要あり

### よくある使用パターン

#### 使用例1: 競合他社のブログ記事分析

```yaml
version: 0.5
nodes:
  source:
    value:
      competitor_url: "https://competitor.com/blog/new-product"

  extract_article:
    agent: fetchAgent
    inputs:
      url: :source.competitor_url
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
      method: "POST"
      body:
        user_input: "下記ブログ記事の本文をMarkdown形式で抽出してください。\n:source.competitor_url"
        model_name: "gpt-4o-mini"
    console:
      after: true

  analyze:
    agent: fetchAgent
    inputs:
      content: :extract_article.result
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/mylllm"
      method: "POST"
      body:
        user_input: "以下のブログ記事を分析し、主要なポイントを3つ挙げてください。\n:content"
        model_name: "gpt-oss:120b"
    isResult: true
```

#### 使用例2: Gmail受信トレイの自動トリアージ

```yaml
version: 0.5
nodes:
  source:
    value:
      search_condition: "is:unread newer_than:1d"

  search_emails:
    agent: fetchAgent
    inputs:
      query: :source.search_condition
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/explorer"
      method: "POST"
      body:
        user_input: "Gmailで下記条件のメールを検索し、各メールの送信者、件名、重要度を判定してください。\n検索条件: :query"
        model_name: "gpt-4o-mini"
    console:
      after: true
    isResult: true
```

---

## 付録C: File Reader Agent 完全ガイド

### 概要

File Reader Agentは、Web上やローカルのファイルを読み込み、内容を抽出するエージェントです。PDF、画像、音声、テキストなど様々なファイル形式に対応しており、expertAgent API経由でFastMCP stdioトランスポートで統合されています。

### コア機能

#### 1. **マルチフォーマット対応**

- **PDF処理**: PyPDF2で全ページのテキストを抽出（要約なし、原文そのまま）
- **画像処理**: OpenAI Vision API（gpt-4o）でOCR・画像解析
- **音声処理**: OpenAI Whisper API（whisper-1）で音声文字起こし
- **テキスト処理**: UTF-8/Shift-JIS/EUC-JP等、複数エンコーディング対応
- **CSV処理**: 解析・整形してテキスト化

#### 2. **多様なデータソース対応**

- **インターネットURL**: HTTP/HTTPS経由でファイルをダウンロード（タイムアウト30秒）
- **Google Drive**: OAuth2認証でプライベートファイルにアクセス（MyVault管理）
- **ローカルファイル**: セキュリティ制限付きで許可ディレクトリ内のファイルを読込

#### 3. **自動処理判定**

ユーザーの指示文の内容に応じて、最適な処理方法を自動選択:

- "テキストを抽出してください" → PDF全文抽出（PyPDF2）
- "画像の内容を説明してください" → Vision API解析（gpt-4o）
- "文字起こししてください" → Whisper API文字起こし（whisper-1）

### GraphAI YML統合パターン

#### パターン1: PDF全文抽出

```yaml
# Google DriveのPDFホワイトペーパーから全文を抽出
pdf_extractor:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    data:
      user_input: "下記ファイルのテキスト情報を全て抽出してください。可能な限り元のファイルに忠実にしてください。\nhttps://drive.google.com/file/d/1ABC123XYZ/view"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン2: 画像からのOCR

```yaml
# スクリーンショット画像からテキストを抽出
image_ocr:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    data:
      user_input: "下記画像ファイルのテキストを抽出してください（OCR）。\nhttps://example.com/screenshot.png"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン3: 音声文字起こし

```yaml
# ポッドキャスト音声を文字起こし
audio_transcription:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    data:
      user_input: "下記音声ファイルを文字起こししてください。\nhttps://example.com/podcast/episode-01.mp3"
      model_name: "gpt-4o-mini"
  console:
    after: true
```

#### パターン4: 複数PDFの一括処理

```yaml
# 複数のレポートPDFから情報を抽出・要約
pdf_batch_processor:
  agent: "mapAgent"
  inputs:
    rows: [":pdf_urls"]  # PDFのURLリスト
  params:
    concurrency: 3  # 3ファイル並列処理
  graph:
    nodes:
      extract_and_summarize:
        agent: "fetchAgent"
        params:
          url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
          method: "POST"
          data:
            user_input: "下記PDFファイルから重要なポイントを3つ抽出してください。\n:row"
            model_name: "gpt-4o-mini"
        isResult: true
```

### 対応形式一覧表

| ファイル形式 | 処理方法 | API/ライブラリ | 出力形式 | タイムアウト |
|------------|---------|-------------|---------|------------|
| **PDF** | 全ページテキスト抽出 | PyPDF2 | `--- Page N ---` 区切り付き全文 | - |
| **PNG/JPG/JPEG** | Vision API解析 | OpenAI gpt-4o | ユーザー指示に応じた結果 | - |
| **MP3/MP4/WAV** | 音声文字起こし | OpenAI whisper-1 | 全文テキスト | - |
| **TXT/MD** | 直接読込 | Python標準 | 全文テキスト | - |
| **CSV** | 解析・整形 | Python CSV | 整形済みテキスト | - |

**処理特性:**
- **PDF**: 要約せず、全ページの原文をそのまま返す
- **画像**: max_tokens=1000（Vision API制限）
- **音声**: response_format="text"（Whisper API）

### 重要な使用上の注意

#### ❗ 画像ファイル指定時の必須表現

画像ファイルを処理する場合、指示文に**必ず「画像」「画像ファイル」という表現を含める**必要があります。

**失敗例:**
```yaml
# ❌ NG: LLMがツール呼び出しを拒否
data:
  user_input: "テキストを抽出してください。\nhttps://drive.google.com/file/d/IMAGE_ID/view"
```

**成功例:**
```yaml
# ✅ OK: 「画像ファイルの」を明記
data:
  user_input: "下記画像ファイルのテキストを抽出してください。\nhttps://drive.google.com/file/d/IMAGE_ID/view"

# ✅ OK: 「画像の内容を」を明記
data:
  user_input: "下記画像の内容を説明してください。\nhttps://example.com/screenshot.png"
```

**理由**: LLMが「テキスト抽出」=「PDF」と解釈し、画像ファイルに対してツール呼び出しを拒否するため。

#### Google Drive認証

- **認証方法**: MyVault経由でOAuth2トークンを自動取得
- **事前準備**: ユーザーがMyVaultでGoogle認証を完了している必要あり
- **対応URL形式**:
  - `https://drive.google.com/file/d/FILE_ID/view`
  - `https://drive.google.com/open?id=FILE_ID`

**権限エラーが発生する場合:**
1. Google Drive側で「リンクを知っている全員」に共有設定
2. MyVaultでGoogle認証を再実行

#### ローカルファイルのセキュリティ制限

**許可ディレクトリ:**
- `/tmp`, `/var/tmp`
- `~/Downloads`, `~/Documents`

**使用例:**
```yaml
local_file_reader:
  agent: "fetchAgent"
  params:
    url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
    method: "POST"
    data:
      user_input: "下記ファイルの内容を表示してください。\n/tmp/document.pdf"
      model_name: "gpt-4o-mini"
```

**エラー例:**
```
Error: File path is outside allowed directories
```

### 技術的注意事項

#### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/file_reader`
- **推奨モデル**: `gpt-4o-mini`（指示理解に最適、コスト効率良好）

#### ファイル処理の制限

| 項目 | 制限値 | 備考 |
|------|--------|------|
| **ファイルサイズ** | 50MB | デフォルト設定、変更可能 |
| **HTTPタイムアウト** | 30秒 | ダウンロード時 |
| **Vision API max_tokens** | 1000トークン | 画像解析の出力長 |

#### 一時ファイル管理

- **保存先**: `/tmp/tmpXXXXXX.tmp`
- **クリーンアップ**: 処理完了後に自動削除
- **セキュリティ**: Path Traversal攻撃対策実装済み

#### 使用API

| 処理 | API | モデル | コスト |
|------|-----|--------|--------|
| **画像解析** | OpenAI Vision API | gpt-4o | $$$ |
| **音声文字起こし** | OpenAI Whisper API | whisper-1 | $ |
| **PDF抽出** | PyPDF2（ローカル） | - | 無料 |

**コスト最適化**: PDFはローカル処理のため無料。画像・音声はOpenAI API使用のためコスト発生。

### よくある使用パターン

#### 使用例1: 技術ドキュメントの内容抽出→要約

```yaml
version: 0.5
nodes:
  source:
    value:
      pdf_url: "https://example.com/technical-whitepaper.pdf"

  extract_pdf:
    agent: "fetchAgent"
    inputs:
      url: [":source.pdf_url"]
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
      method: "POST"
      data:
        user_input: "下記PDFファイルのテキストを全て抽出してください。\n:source.pdf_url"
        model_name: "gpt-4o-mini"
    console:
      after: true

  summarize:
    agent: "openAIAgent"
    inputs:
      content: [":extract_pdf"]
    params:
      model: "gpt-oss:120b"  # ローカルLLM使用
      system: "技術ドキュメントを読み、重要なポイントを3つ挙げてください。"
      prompt: ":content"
    isResult: true
```

#### 使用例2: 画像ベースの議事録作成

```yaml
version: 0.5
nodes:
  source:
    value:
      screenshot_url: "https://drive.google.com/file/d/SCREENSHOT_ID/view"

  ocr_screenshot:
    agent: "fetchAgent"
    inputs:
      url: [":source.screenshot_url"]
    params:
      url: "http://127.0.0.1:8104/aiagent-api/v1/aiagent/utility/file_reader"
      method: "POST"
      data:
        user_input: "下記画像ファイルのテキストを抽出してください（ホワイトボードの議事録）。\n:source.screenshot_url"
        model_name: "gpt-4o-mini"
    console:
      after: true

  format_minutes:
    agent: "openAIAgent"
    inputs:
      ocr_text: [":ocr_screenshot"]
    params:
      model: "gpt-oss:20b"
      system: "議事録を整形し、決定事項、アクションアイテム、次回予定を抽出してください。"
      prompt: ":ocr_text"
    isResult: true
```
