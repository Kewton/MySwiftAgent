# Explorer Agent 完全ガイド

## 概要

Explorer Agentは、Web検索とWebページコンテンツ抽出に特化したエージェントです。Google検索、WebサイトのHTML→Markdown変換、Gmail検索など、情報収集タスクに最適化されています。

## コア機能

### 1. **Web検索（Google Custom Search API）**

- **キーワード検索**: Google検索で情報を収集
- **結果フィルタリング**: 件数指定、ドメイン制限
- **構造化出力**: タイトル、URL、スニペット

### 2. **Webページコンテンツ抽出（html2markdown MCP）** 🆕

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

### 3. **Gmail検索（Gmail MCP）** 🆕

- **メール検索**: Gmail検索クエリでメールを検索
- **フィルタリング**: 送信者、件名、日付範囲などで絞り込み
- **本文取得**: メール本文の取得・解析
- **OAuth2認証**: MyVault経由で安全にアクセス

## GraphAI YML統合パターン

### パターン1: Webページからテキスト抽出（html2markdown）

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

### パターン2: Google検索とコンテンツ収集

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

### パターン3: Gmail検索とメール解析

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

## 利用可能なMCPツール

Explorer Agent内部で使用可能なツール一覧:

| ツール名 | 機能 | 使用例 |
|---------|------|-------|
| **html2markdown** 🆕 | HTMLをMarkdownに変換 | Webページのテキスト抽出 |
| **google_search** | Google Custom Search | キーワード検索、情報収集 |
| **gmail_search** 🆕 | Gmail検索 | メール検索、受信トレイ管理 |

**重要**: これらのツールはLLMエージェントが自動選択します。ワークフロー作成者が直接指定する必要はありません。

## 技術的注意事項

### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/explorer`
- **推奨モデル**: `gpt-4o-mini`（指示理解に最適、コスト効率良好）

### html2markdown MCP

- **出力形式**: Markdown（見出し `#`, リスト `-`, リンク `[text](url)` など）
- **文字コード**: UTF-8
- **エラー処理**: ページ取得失敗時はエラーメッセージを返す

### Gmail MCP

- **認証**: MyVault経由でOAuth2トークン取得
- **権限**: Gmail読み取り専用スコープ
- **事前準備**: ユーザーがMyVaultでGoogle認証を完了している必要あり

## よくある使用パターン

### 使用例1: 競合他社のブログ記事分析

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

### 使用例2: Gmail受信トレイの自動トリアージ

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

## レスポンス形式とサンプル

### 基本レスポンス構造

```json
{
  "result": "LLMエージェントによる処理結果（文字列）",
  "text": null,
  "type": "explorer",
  "chathistory": null
}
```

### Gmail検索レスポンスサンプル

#### サンプル1: GitHubキーワード検索（3件、要約あり）

**リクエスト**:
```json
{
  "user_input": "gmailから「GitHub」というキーワードでメールを3件検索して、その内容を要約してください",
  "model_name": "gpt-4o-mini",
  "force_json": false
}
```

**レスポンス**:
```json
{
  "result": "以下は「GitHub」に関する最近のメールの要約です。\n\n### Kewton/MySwiftAgent CI ワークフローの状況 (2025/10/14)\n\n**概要:**\n- Kewton/MySwiftAgentのCIワークフロー（Feature/Fix Branches）で、2025年10月14日に2回の実行が確認されました。\n- 両方の実行では、テストスイート(3.12)がexpertAgentに対して失敗しました（1つのアノテーションあり）。\n\n**詳細:**\n1. **実行1 (2025-10-14 04:58:13 UTC)**\n   - Duration: 1分12秒\n   - 成功したジョブ: Detect Changes, Security Scan, Documentation Check, Dependency Security Check\n   - 失敗したジョブ: Test Suite (3.12, expertAgent)\n\n2. **実行2 (2025-10-14 04:45:41 UTC)**\n   - Duration: 1分8秒\n   - 成功したジョブ: Detect Changes, Test Suite (myscheduler, jobqueue), Security Scan, Documentation Check\n   - 失敗したジョブ: Test Suite (3.12, expertAgent)\n\n**要点:**\n- Test Suite (3.12, expertAgent) における継続的な失敗が確認されています。原因の調査が必要です。",
  "text": null,
  "type": "explorer",
  "chathistory": null
}
```

**パフォーマンス**:
- **レスポンスタイム**: 84.55秒
- **レスポンスサイズ**: 1,438 bytes

#### サンプル2: CI関連メール検索（5件、デフォルト）

**リクエスト**:
```json
{
  "user_input": "gmailから「CI」に関するメールを検索して、重要な情報を抜き出してください",
  "model_name": "gpt-4o-mini",
  "force_json": false
}
```

**レスポンス**:
```json
{
  "result": "検索結果から得られた「CI」に関する重要な情報は以下の通りです。\n\n- **CI 失敗:** `expertAgent` のテストスイートと、`Develop Integration` ワークフローにおける `Integration Tests` が失敗。\n- **リリース:** `expertAgent`, `docs`, `graphAiServer`, `jobqueue` がリリース (マイナーバージョンアップ)。リリースブランチ `release/multi/v2025.10.12` が作成。\n- **変更点:** 多数のファイルが変更。特に `expertAgent`, `graphAiServer`, `jobqueue` で大規模な変更が見られる。\n- **ワークフロー:** `Feature/Fix Branches` と `Develop Integration` ワークフローが実行された。\n- **主な変更内容:** LLMワークフロー生成機能の追加と改善、および関連するドキュメントの更新。",
  "text": null,
  "type": "explorer",
  "chathistory": null
}
```

**パフォーマンス**:
- **レスポンスタイム**: 28.22秒
- **レスポンスサイズ**: 889 bytes

#### サンプル3: JSON出力形式（force_json: true）

**リクエスト**:
```json
{
  "user_input": "gmailから「test」というキーワードでメールを2件検索してください",
  "model_name": "gpt-4o-mini",
  "force_json": true
}
```

**レスポンス**:
```json
{
  "result": "以下が「test」というキーワードで検索したメールの結果です。\n\n1. **リポジトリ:** Kewton/MySwiftAgent\n   **ワークフロー:** CI - Feature/Fix Branches\n   **結果:** 2回の実行で、Test Suite (3.12, expertAgent) が失敗。\n   **失敗箇所:** expertAgent のテストスイート (1つのアノテーションあり)\n   **その他:** 依存関係のセキュリティチェック、ドキュメントチェック、変更の検出は成功。ビルドチェックはスキップ。",
  "error": "Failed to convert to JSON format",
  "is_json_guaranteed": true,
  "error_detail": "Failed to extract JSON block from content. Content must be valid JSON or contain ```json...``` block",
  "error_context": "explorer agent after 3 attempts"
}
```

**注意**: `force_json: true` の場合、LLMがJSON形式で応答しない場合はエラー情報が追加されますが、`result`フィールドには自然言語での結果が含まれます。

**パフォーマンス**:
- **レスポンスタイム**: 41.67秒
- **レスポンスサイズ**: 963 bytes

### パフォーマンス目安

| 操作 | レスポンスタイム | 備考 |
|------|----------------|------|
| **Gmail検索（3-5件）** | 30-90秒 | Gmail API呼び出し + LLM推論 |
| **Webページ抽出** | 20-40秒 | HTML取得 + Markdown変換 + LLM処理 |
| **Google検索** | 15-30秒 | API呼び出し + LLM整形 |

**最適化のヒント**:
- 検索件数を減らす（`top`パラメータ）
- より高速なモデルを使用（`gpt-4o-mini`推奨）
- 不要な要約処理を省略

---

**参照**: [GraphAI Workflow Generation Rules - expertAgent API統合](../GRAPHAI_WORKFLOW_GENERATION_RULES.md#expertagent-api統合)
