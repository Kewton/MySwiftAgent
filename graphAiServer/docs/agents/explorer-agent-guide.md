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

**参照**: [GraphAI Workflow Generation Rules - expertAgent API統合](../GRAPHAI_WORKFLOW_GENERATION_RULES.md#expertagent-api統合)
