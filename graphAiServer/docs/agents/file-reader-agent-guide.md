# File Reader Agent 完全ガイド

## 概要

File Reader Agentは、Web上やローカルのファイルを読み込み、内容を抽出するエージェントです。PDF、画像、音声、テキストなど様々なファイル形式に対応しており、expertAgent API経由でFastMCP stdioトランスポートで統合されています。

## コア機能

### 1. **マルチフォーマット対応**

- **PDF処理**: PyPDF2で全ページのテキストを抽出（要約なし、原文そのまま）
- **画像処理**: OpenAI Vision API（gpt-4o）でOCR・画像解析
- **音声処理**: OpenAI Whisper API（whisper-1）で音声文字起こし
- **テキスト処理**: UTF-8/Shift-JIS/EUC-JP等、複数エンコーディング対応
- **CSV処理**: 解析・整形してテキスト化

### 2. **多様なデータソース対応**

- **インターネットURL**: HTTP/HTTPS経由でファイルをダウンロード（タイムアウト30秒）
- **Google Drive**: OAuth2認証でプライベートファイルにアクセス（MyVault管理）
- **ローカルファイル**: セキュリティ制限付きで許可ディレクトリ内のファイルを読込

### 3. **自動処理判定**

ユーザーの指示文の内容に応じて、最適な処理方法を自動選択:

- "テキストを抽出してください" → PDF全文抽出（PyPDF2）
- "画像の内容を説明してください" → Vision API解析（gpt-4o）
- "文字起こししてください" → Whisper API文字起こし（whisper-1）

## GraphAI YML統合パターン

### パターン1: PDF全文抽出

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

### パターン2: 画像からのOCR

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

### パターン3: 音声文字起こし

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

### パターン4: 複数PDFの一括処理

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

## 対応形式一覧表

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

## 重要な使用上の注意

### ❗ 画像ファイル指定時の必須表現

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

### Google Drive認証

- **認証方法**: MyVault経由でOAuth2トークンを自動取得
- **事前準備**: ユーザーがMyVaultでGoogle認証を完了している必要あり
- **対応URL形式**:
  - `https://drive.google.com/file/d/FILE_ID/view`
  - `https://drive.google.com/open?id=FILE_ID`

**権限エラーが発生する場合:**
1. Google Drive側で「リンクを知っている全員」に共有設定
2. MyVaultでGoogle認証を再実行

### ローカルファイルのセキュリティ制限

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

## 技術的注意事項

### expertAgent API統合

- **ポート番号**: `127.0.0.1:8104`（expertAgent）
- **エンドポイント**: `/aiagent-api/v1/aiagent/utility/file_reader`
- **推奨モデル**: `gpt-4o-mini`（指示理解に最適、コスト効率良好）

### ファイル処理の制限

| 項目 | 制限値 | 備考 |
|------|--------|------|
| **ファイルサイズ** | 50MB | デフォルト設定、変更可能 |
| **HTTPタイムアウト** | 30秒 | ダウンロード時 |
| **Vision API max_tokens** | 1000トークン | 画像解析の出力長 |

### 一時ファイル管理

- **保存先**: `/tmp/tmpXXXXXX.tmp`
- **クリーンアップ**: 処理完了後に自動削除
- **セキュリティ**: Path Traversal攻撃対策実装済み

### 使用API

| 処理 | API | モデル | コスト |
|------|-----|--------|--------|
| **画像解析** | OpenAI Vision API | gpt-4o | $$$ |
| **音声文字起こし** | OpenAI Whisper API | whisper-1 | $ |
| **PDF抽出** | PyPDF2（ローカル） | - | 無料 |

**コスト最適化**: PDFはローカル処理のため無料。画像・音声はOpenAI API使用のためコスト発生。

## よくある使用パターン

### 使用例1: 技術ドキュメントの内容抽出→要約

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

### 使用例2: 画像ベースの議事録作成

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

---

**参照**: [GraphAI Workflow Generation Rules - expertAgent API統合](../GRAPHAI_WORKFLOW_GENERATION_RULES.md#expertagent-api統合)
