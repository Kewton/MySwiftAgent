# LLMワークフロー生成ガイド

このドキュメントは、LLM（大規模言語モデル）を使用してGraphAI YMLワークフローファイルを自動生成する際の方針と手順を提供します。

## 📋 概要

MySwiftAgentプロジェクトでは、自然言語の指示からGraphAI YMLワークフローファイルを自動生成する仕組みを採用しています。これにより、複雑なワークフロー定義を手動で記述する手間を大幅に削減し、開発効率を向上させます。

## 🎯 生成方針

### 基本方針

1. **ルール準拠**: [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) に記載された設計ルールに厳密に従う
2. **品質担保**: 生成されたワークフローは動作確認を経て、本番環境で使用可能な品質を保証
3. **イテレーション改善**: 最大5回のイテレーションで動作確認とエラー修正を実施
4. **ドキュメント化**: 生成されたYMLファイルには必ずヘッダーコメントを付与し、トレーサビリティを確保

### 対象LLM

MySwiftAgentでは以下のLLMを使用したワークフロー生成をサポートしています:

| LLM | 推奨度 | 特徴 | 使用ケース |
|-----|-------|------|-----------|
| **Gemini 2.5 Pro** | ⭐⭐⭐ | 最高精度、思考プロセス付き、100万トークンコンテキスト | 複雑なワークフロー、大規模な処理フロー |
| **Gemini 2.5 Flash** | ⭐⭐⭐ | 高速、コスト効率、バランス型 | 標準的なワークフロー、反復的な改善 |
| **Claude Sonnet 4.5** | ⭐⭐⭐ | コーディング世界最高、複雑なエージェント構築 | 高度なロジック、エージェント統合 |
| **Claude Opus 4.1** | ⭐⭐ | エージェントタスク特化、詳細な推論 | 実世界コーディング、複雑な推論タスク |
| **GPT-5** | ⭐⭐ | 27万トークン入力、コーディング・数学に優れる | 長文コンテキスト、数学的処理 |

**推奨**: Gemini 2.5シリーズ（Pro/Flash）を使用することで、コスト効率と品質のバランスが最適化されます。

## 🚀 Gemini CLI を使用したワークフロー生成

### セットアップ手順

#### 1. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Create API Key」をクリックしてAPIキーを生成
3. 生成されたAPIキーをコピー

#### 2. 環境変数の設定

APIキーを環境変数として設定します:

```bash
# ~/.bashrc または ~/.zshrc に追加
export GOOGLE_API_KEY="your-api-key-here"

# 設定を反映
source ~/.bashrc  # または source ~/.zshrc
```

**セキュリティ注意事項**:
- APIキーはコミットしない（`.gitignore`に`*.env`を追加済み）
- 本番環境では環境変数またはシークレット管理サービスを使用
- APIキーは定期的にローテーション

#### 3. Gemini CLI のインストール

**方法A: Python SDK（推奨）**

```bash
# Python SDKをインストール
pip install google-generativeai

# または uv を使用
uv pip install google-generativeai
```

**方法B: Google Cloud CLI**

```bash
# Google Cloud CLIをインストール（未インストールの場合）
# macOS
brew install --cask google-cloud-sdk

# 認証設定
gcloud auth application-default login
```

#### 4. 動作確認

```bash
# Python SDKでの確認
python3 << 'EOF'
import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Hello, Gemini!")
print(response.text)
EOF
```

成功すると、Geminiからの応答が表示されます。

### 基本的な使用方法

#### Python SDKを使用したワークフロー生成

```python
import google.generativeai as genai
import os

# API設定
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# モデル選択（推奨: gemini-2.5-flash または gemini-2.5-pro）
model = genai.GenerativeModel("gemini-2.5-flash")

# システムプロンプト
system_instruction = """
あなたはGraphAI YMLワークフローファイルを生成する専門エージェントです。

# 必須参照ドキュメント
以下のドキュメントに記載されたルールと設計指針に厳密に従ってください:
- ./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md

# 作業手順
1. フェーズ1: 要件分析と設計合意
2. フェーズ2: 実現可能性評価
3. フェーズ3: ワークフロー初期実装
4. フェーズ4: 動作確認と改善サイクル（最大5イテレーション）
5. フェーズ5: 最終化

# 出力形式
- YMLファイルの完全な内容を出力
- ヘッダーコメントを必ず含める（Created, User Request, Test Results, Description, Notes）
- ファイル保存先: ./graphAiServer/config/graphai/llmwork/{purpose}_{timestamp}.yml

# 品質基準
- version: 0.5 を使用
- sourceノードは直接参照（:source）
- mapAgent使用時はconcurrencyを設定
- 重要ノードにconsole.after: trueを設定
- expertAgent APIのポート番号は8104
- ローカルLLM（gpt-oss:20b, gpt-oss:120b）を優先使用
"""

# ユーザー要求
user_request = """
以下の要件でワークフローを作成してください:
1. ユーザーがトピックを入力
2. Google検索でトピックに関する情報を収集（3件）
3. explorerエージェントで情報を整理
4. gpt-oss:120bで詳細なレポートを生成
5. 結果を出力
"""

# ワークフロー生成
response = model.generate_content(
    system_instruction + "\n\n" + user_request
)

# 生成されたYMLファイルを保存
with open("./graphAiServer/config/graphai/llmwork/report_generation_20251012.yml", "w") as f:
    f.write(response.text)

print("✅ ワークフローファイルを生成しました")
```

### 対話型ワークフロー生成スクリプト

より実用的な対話型スクリプトの例:

```python
#!/usr/bin/env python3
"""
対話型GraphAI YMLワークフロー生成スクリプト
"""
import google.generativeai as genai
import os
from datetime import datetime

def generate_workflow():
    # API設定
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    print("=== GraphAI ワークフロー生成 ===\n")

    # ユーザー要求の入力
    print("ワークフローの要件を入力してください（複数行可、Ctrl+Dで終了）:")
    user_request = ""
    try:
        while True:
            line = input()
            user_request += line + "\n"
    except EOFError:
        pass

    # システムプロンプトの読み込み
    with open("./graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md", "r") as f:
        rules = f.read()

    system_instruction = f"""
あなたはGraphAI YMLワークフローファイルを生成する専門エージェントです。

以下のルールドキュメントに厳密に従ってください:

{rules}

ユーザー要求に対して、完全なYMLファイルを生成してください。
ヘッダーコメント、version、nodes構造をすべて含めること。
"""

    # ワークフロー生成
    print("\n🔄 ワークフロー生成中...\n")
    response = model.generate_content(system_instruction + "\n\n" + user_request)

    # タイムスタンプ付きファイル名生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    purpose = input("\nワークフローの目的を簡潔に入力してください（ファイル名に使用）: ")
    filename = f"./graphAiServer/config/graphai/llmwork/{purpose}_{timestamp}.yml"

    # ファイル保存
    with open(filename, "w") as f:
        f.write(response.text)

    print(f"\n✅ ワークフローファイルを生成しました: {filename}")
    print("\n次のステップ:")
    print("1. ファイル内容を確認")
    print("2. graphAiServerで動作確認")
    print("3. エラーがあれば修正してイテレーション")

if __name__ == "__main__":
    generate_workflow()
```

**使用例**:

```bash
# スクリプトに実行権限を付与
chmod +x scripts/generate-workflow.py

# 実行
./scripts/generate-workflow.py
```

## 📝 ワークフロー生成の5フェーズ

詳細は [GRAPHAI_WORKFLOW_GENERATION_RULES.md - LLMワークフロー作成手順](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#llmワークフロー作成手順) を参照してください。

### フェーズ1: 要件分析と設計合意

- ユーザーの要求を正確に理解
- 処理フローの提示と合意形成
- 処理時間の目安を提示

### フェーズ2: 実現可能性評価

- 現在のexpertAgent機能で実現可能か評価
- 不足機能があればユーザーに提案
- 機能追加が必要な場合は実装後に続行

### フェーズ3: ワークフロー初期実装

- YMLファイルの初期実装
- ヘッダーコメントの記載
- 基本構造のチェックリスト確認

### フェーズ4: 動作確認と改善サイクル（最大5イテレーション）

```
イテレーション N (N = 1, 2, 3, 4, 5)
├─ ステップ1: graphAiServerで実行
├─ ステップ2: 結果判定（SUCCESS/FAILED）
├─ ステップ3: エラー原因調査
├─ ステップ4: ルール更新・YML修正
└─ ステップ5: Test Resultsヘッダー更新
```

5回のイテレーションで解決できない場合は、ユーザーにフィードバックを依頼します。

### フェーズ5: 最終化

- Test Resultsヘッダーの最終更新
- Notesセクションの追加（必要に応じて）
- 運用ドキュメントの更新

## 🔧 動作確認手順

### 1. サービス起動確認

```bash
# graphAiServerが起動していることを確認
curl http://127.0.0.1:8105/health

# expertAgentが起動していることを確認（4ワーカー推奨）
curl http://127.0.0.1:8104/health
```

### 2. ワークフロー実行

```bash
# 開発用エンドポイントで実行（想定）
curl -X POST http://127.0.0.1:8105/api/v1/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_file": "llmwork/{your_workflow}.yml",
    "input": "ユーザー入力テキスト"
  }'
```

### 3. ログ確認

```bash
# graphAiServerログ
tail -f logs/graphaiserver.log

# expertAgentログ
tail -f logs/expertagent.log

# エラーのみ抽出
tail -n 100 logs/graphaiserver.log | grep -i error
tail -n 100 logs/expertagent.log | grep -i error
```

### 4. よくあるエラーと対応

| エラー | 原因 | 対応 |
|-------|------|------|
| `TypeError: fetch failed` | expertAgentへの接続失敗 | ポート番号確認（8104）、ワーカー数確認（`--workers 4`） |
| `undefined` が出力 | sourceノード参照エラー | `:source.text` → `:source` に修正 |
| `mapAgentでタイムアウト` | 並列処理過負荷 | `concurrency: 2` を追加 |
| `RuntimeWarning: coroutine was never awaited` | expertAgent側のawait漏れ | Pythonコードに `await` 追加 |

詳細なエラー回避パターンは [GRAPHAI_WORKFLOW_GENERATION_RULES.md - エラー回避パターン](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md#エラー回避パターン) を参照してください。

## ✅ 生成品質チェックリスト

### 基本構造
- [ ] `version: 0.5` を含む
- [ ] `nodes:` セクションがある
- [ ] `source: {}` ノードがある
- [ ] 最低1つの `isResult: true` ノードがある

### データフロー
- [ ] すべてのノード間のデータ参照が正しい（`:node_name.field`）
- [ ] `source` ノードは直接参照（`:source`）している
- [ ] `mapAgent` 内では `:row.field` でアクセスしている

### expertAgent API統合
- [ ] すべてのAPI URLが `http://127.0.0.1:8104` を使用
- [ ] 使用するエンドポイントが存在する（10種類のエンドポイントを確認）
- [ ] `model_name` パラメータが有効なモデル名

### モデル選択
- [ ] ローカルLLMを優先使用（gpt-oss:20b, gpt-oss:120b）
- [ ] タスクの複雑度に応じたモデルを選択
- [ ] コスト（ローカル vs クラウド）を考慮

### エラー処理
- [ ] タイムアウトが適切に設定されている（グローバル300秒）
- [ ] 重要なノードで `console.after: true` を設定
- [ ] 並列処理に `concurrency` パラメータを設定（軽量:4-8、中程度:2-3、重い:1-2）

### 命名規則
- [ ] ノード名が意味のある名前
- [ ] 小文字スネークケースを使用
- [ ] 適切な接尾辞（`_builder`, `_mapper`, `_search`, `_output` など）を使用

### ヘッダーコメント
- [ ] Created（作成日時）を記載
- [ ] User Request（ユーザー要求）を記載
- [ ] Test Results（動作確認履歴）を記載
- [ ] Description（概要）を記載
- [ ] Notes（注意事項）を記載（必要に応じて）

## 🔄 イテレーション改善のベストプラクティス

### エラー発生時の診断手順

1. **ログのタイムスタンプ確認**:
```bash
grep "node_name start" logs/graphaiserver.log
# リクエストが同時刻に集中していないか確認
```

2. **expertAgentのワーカー数確認**:
```bash
grep "Started server process" logs/expertagent.log | wc -l
# 1の場合は並列処理に対応できていない
```

3. **並列数確認**:
YMLファイルでmapAgentに `concurrency` パラメータがあるか確認

### ルール更新の判断基準

| 状況 | ルール更新の必要性 | 更新内容 |
|-----|----------------|---------|
| **新しいエラーパターン発見** | ✅ 必要 | 「エラー回避パターン」セクションに追記 |
| **新機能追加** | ✅ 必要 | 「expertAgent API統合」セクションに追記 |
| **既知のエラー** | ⭕ 不要 | YMLファイルのみ修正 |
| **ユーザー固有のエラー** | ⭕ 不要 | YMLファイルのNotesに記載 |

## 🌐 Playwright Agent 統合

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

## 🌐 Explorer Agent 統合

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

## 📄 File Reader Agent 統合

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

## 📚 参考ドキュメント

- 📄 **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** - ワークフロー生成の詳細ルール（必須）
- 📄 **[GEMINI.md](../GEMINI.md)** - Gemini CLI使用時の指針
- 📄 **[CLAUDE.md](../CLAUDE.md)** - Claude Code使用時の指針
- 🌐 **[Google AI Studio](https://aistudio.google.com/)** - Gemini API管理
- 🔧 **[GraphAI公式ドキュメント](https://github.com/receptron/graphai)** - GraphAIフレームワーク仕様
- 📖 **[expertAgent API仕様](../expertAgent/docs/)** - expertAgent統合ガイド
- 🌐 **[expertAgent README - Playwright Agent](../expertAgent/README.md#2-playwright-agent統合mcp)** - Playwright Agent詳細仕様
- 📄 **[File Reader利用ガイド](../expertAgent/docs/file-reader-usage-guide.md)** - File Reader Agent完全ガイド

## 🤝 サポート

ワークフロー生成で問題が発生した場合:

1. **[GRAPHAI_WORKFLOW_GENERATION_RULES.md](../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md)** の該当セクションを確認
2. エラーログを確認（graphAiServer、expertAgent）
3. イテレーション改善フローに従って修正
4. 5回のイテレーションで解決しない場合は、チームに相談

## 📊 生成実績とベストプラクティス

### 成功事例

- ✅ **シンプルなLLM呼び出し**: 1イテレーションで完了
- ✅ **Google検索→レポート生成**: 2イテレーション（並列数調整）
- ✅ **ポッドキャスト台本生成（4章）**: 3イテレーション（concurrency設定、ワーカー数調整）

### 学習した教訓

1. **並列処理の規模を事前に見積もる**: 処理する配列の要素数とLLMモデルの種類を考慮
2. **concurrency値を必ず設定**: 軽量:4-8、中程度:2-3、重い:1-2
3. **expertAgentのワーカー数を調整**: `workers ≥ concurrency` を確保
4. **タイムアウトを確認**: グローバルタイムアウトが300秒に設定済みか確認

---

**最終更新日**: 2025-10-12

**バージョン**: 1.0.0
