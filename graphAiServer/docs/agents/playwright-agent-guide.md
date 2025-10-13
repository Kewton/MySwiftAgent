# Playwright Agent 完全ガイド

## 概要

Playwright Agentは、Webブラウザを自動操作してWebページからデータを抽出・処理するエージェントです。expertAgent API経由でLangGraph ReAct agentパターンで統合されており、Playwright MCPの20種類以上のツールを活用できます。

**⚠️ 重要な制限事項:**
- **Webサイトからの情報抽出には不向き**: ブラウザの構造化データ取得の精度が低く、特定要素の抽出が困難
- **推奨用途**: フォーム操作、スクリーンショット取得、JavaScript実行など、ブラウザ操作が必要な場合のみ
- **代替手段**: Webページからのテキスト・情報抽出には **Explorer Agent（html2markdown MCP）** の使用を強く推奨

## コア機能

### 1. **Webページの遷移・操作**

- **ページナビゲーション**: URL遷移、戻る操作
- **フォーム操作**: テキスト入力、ボタンクリック、ドロップダウン選択
- **インタラクション**: ドラッグ&ドロップ、ホバー、キーボード入力
- **タブ管理**: 新規タブ作成、タブ切替、タブクローズ

### 2. **Webページからのデータ抽出**

- **ページ全体のテキスト取得**: `browser_snapshot`でアクセシビリティツリー形式で構造化されたテキストを取得
- **特定要素のテキスト抽出**: セレクタ指定で特定部分のみ抽出
- **ファイルリンクの一括抽出**: PDFリンク、画像リンク、ダウンロードリンク等を自動収集
- **スクリーンショット取得**: ページ全体または特定要素のスクリーンショット

### 3. **動的コンテンツ対応**

- **要素の出現待機**: 特定のテキストや要素が表示されるまで待機
- **JavaScript実行**: カスタムJavaScriptをページ上で実行
- **ネットワーク監視**: HTTPリクエスト/レスポンスの記録
- **コンソールログ取得**: ブラウザコンソールのログ・エラーを取得

## GraphAI YML統合パターン

### パターン1: Webページからテキスト抽出

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

### パターン2: PDFリンク一括抽出

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

### パターン3: 複数ページから情報収集

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

## 利用可能なPlaywright MCPツール（主要20種類）

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

## 技術的注意事項

### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/playwright`
- **推奨モデル**: `gpt-4o-mini`（Playwright指示理解に最適、コスト効率良好）
- **最大イテレーション**: 5回（デフォルト）

### Bot検出対策

expertAgentでは以下の対策が実装済み:

- **User-Agent設定**: Chrome 131相当の現実的なUser-Agentを自動設定
- **Headlessモード**: `--headless`オプション有効
- **並列数制限**: mapAgent使用時は`concurrency: 2`推奨（同時アクセス過多を回避）

**対応例**:
- ✅ `https://japancredit.go.jp/data/` - 403エラーを回避（User-Agent設定により解決済み）
- ✅ 一般的な企業サイト - 問題なくアクセス可能

### Docker要件

- **共有メモリ**: `shm_size: 2gb` 必須（Chromiumブラウザ動作に必要）
- **設定場所**: `docker-compose.yml`の`expertagent`サービス

```yaml
services:
  expertagent:
    shm_size: 2gb  # Playwright動作に必須
```

### タイムアウト設定

- **グローバルタイムアウト**: 300秒（5分）
- **ページロードタイムアウト**: 30秒（Playwright MCP内部設定）
- **並列処理時の注意**: 重いLLM（gpt-oss:120b）使用時はconcurrency:1-2推奨

## よくある使用パターン

### 使用例1: 競合他社の価格調査

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

### 使用例2: 公開資料の自動収集

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

**参照**: [GraphAI Workflow Generation Rules - expertAgent API統合](../GRAPHAI_WORKFLOW_GENERATION_RULES.md#expertagent-api統合)
