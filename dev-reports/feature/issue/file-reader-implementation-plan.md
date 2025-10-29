# File Reader Implementation Plan

このドキュメントは、File Reader機能の実装計画と設計方針を記述します。

## 目次

1. [概要](#概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [実装フェーズ](#実装フェーズ)
4. [技術スタック](#技術スタック)
5. [API設計](#api設計)
6. [品質基準](#品質基準)
7. [セキュリティ考慮事項](#セキュリティ考慮事項)
8. [パフォーマンス要件](#パフォーマンス要件)

---

## 概要

### プロジェクト目標

File Readerは、多様なファイル形式を受け取り、その内容をLLMが理解可能なテキスト形式に変換するAIエージェントです。

### 主要機能

1. **マルチフォーマット対応**: 画像、PDF、テキスト、音声など多様なファイル形式をサポート
2. **AI統合**: OpenAI Vision/Whisper APIによる高度な解析
3. **高度なPDF処理**: pypdfベースの本格的なPDF解析 (Phase 7で実装済み)
4. **LLMエージェント**: LangGraphベースの柔軟なワークフロー
5. **RESTful API**: 標準的なHTTP APIでの統合

### 対応ファイル形式

| カテゴリ | 形式 | MIME Type | 処理方法 |
|---------|------|-----------|----------|
| 画像 | JPEG/JPG | image/jpeg | OpenAI Vision API |
| 画像 | PNG | image/png | OpenAI Vision API |
| ドキュメント | PDF | application/pdf | pypdf (シンプル/高度) |
| ドキュメント | TXT | text/plain | 直接読み込み |
| ドキュメント | MD | text/markdown | 直接読み込み |
| ドキュメント | CSV | text/csv | CSVパーサー |
| 音声 | MP4 | video/mp4 | OpenAI Whisper API |
| 音声 | MP3 | audio/mp3 | OpenAI Whisper API |
| 音声 | WAV | audio/wav | OpenAI Whisper API |

---

## アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Application                    │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                │ HTTP POST /api/v1/aiagent/file-reader
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         agent_endpoints.py (API Layer)                │  │
│  │  - File upload handling                               │  │
│  │  - MIME type detection                                │  │
│  │  - Error handling                                     │  │
│  └───────────────────────────┬───────────────────────────┘  │
└────────────────────────────────┼────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│              File Reader Agent (LangGraph)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         filereaderagent.py (Agent Layer)              │  │
│  │  - Workflow orchestration                             │  │
│  │  - State management                                   │  │
│  │  - LLM integration                                    │  │
│  └───────────────────────────┬───────────────────────────┘  │
└────────────────────────────────┼────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│           File Processor Layer (Tool Layer)                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │    file_reader_processors.py (Dispatcher)             │  │
│  │  - process_file() - Format router                     │  │
│  │  - process_image() - Vision API                       │  │
│  │  - process_pdf() - pypdf text extraction              │  │
│  │  - process_text() - Text/MD reader                    │  │
│  │  - process_csv() - CSV parser                         │  │
│  │  - process_audio() - Whisper API                      │  │
│  └───────────────────────────┬───────────────────────────┘  │
│                               │                               │
│  ┌───────────────────────────┴───────────────────────────┐  │
│  │    pdf_processor_advanced.py (Phase 7)                │  │
│  │  - AdvancedPDFProcessor (Orchestrator)                │  │
│  │  - TextNormalizer (NFKC, whitespace, hyphen)          │  │
│  │  - HeaderFooterRemover (Frequency-based)              │  │
│  │  - ParagraphEstimator (6 types)                       │  │
│  │  - ImageExtractor (XObject extraction)                │  │
│  │  - OutlineExtractor (TOC/Bookmarks)                   │  │
│  │  - LinkExtractor (Internal/External)                  │  │
│  │  - AttachmentExtractor (Embedded files)               │  │
│  │  - PDFChunk (Data structure)                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     External Services                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │ OpenAI      │  │ OpenAI      │  │ Google Gemini      │  │
│  │ Vision API  │  │ Whisper API │  │ (LLM)              │  │
│  └─────────────┘  └─────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### データフロー

#### 1. 基本フロー (Phase 1-6)

```
1. Client uploads file → FastAPI endpoint
2. API detects MIME type (python-magic)
3. API saves file to temporary location
4. API calls File Reader Agent
5. Agent routes to appropriate processor:
   - Image → Vision API → Extract text
   - PDF → pypdf → Extract text (simple)
   - Text/CSV → Direct read
   - Audio → Whisper API → Transcribe
6. Agent sends extracted text to LLM
7. LLM analyzes and responds
8. Response returned to client
9. Temporary file cleaned up
```

#### 2. 高度なPDFフロー (Phase 7)

```
1-4. [Same as basic flow]
5. Advanced PDF Processing (use_advanced=True):
   a. Preflight check
      - File existence validation
      - SHA256 hash computation (doc_id)
   b. Metadata extraction
      - PDF info (title, author, etc.)
      - File size, encryption status
   c. Outline extraction (recursive)
      - TOC/Bookmarks with hierarchy
      - Page number mapping
   d. Attachment extraction
      - Embedded files to disk
   e. Full text extraction
      - All pages text
   f. Header/footer detection
      - Frequency-based pattern collection (30% threshold)
      - Pattern matching across pages
   g. Page-by-page processing
      - Text extraction and normalization:
        * Unicode NFKC normalization
        * Whitespace normalization
        * Hyphen joining (line-end hyphens)
      - Header/footer removal
      - Paragraph splitting and type estimation:
        * heading, list, code, quote, table_like, paragraph
      - Image extraction (if enabled):
        * XObject detection
        * Format identification (JPEG/PNG/JP2)
        * Save to output_dir
      - Link extraction:
        * External links (URI)
        * Internal links (page navigation)
   h. Chunk generation
      - PDFChunk dataclass instances
      - Unique chunk_id (doc_id_pNNNN_cMMM)
      - Type-based organization
   i. JSONL output
      - One chunk per line
      - Streaming-friendly format
   j. Metadata JSON output
      - Processing statistics
      - Document metadata
      - File paths
6. Agent sends formatted results to LLM
7. LLM analyzes structured data
8. Response returned to client
9. Cleanup (optional: keep JSONL/images for future use)
```

### コンポーネント責務

#### API Layer (`agent_endpoints.py`)

**責務**:
- HTTPリクエスト/レスポンス処理
- ファイルアップロード管理
- MIME type検出 (python-magic)
- 一時ファイル管理
- エラーハンドリング

**入力**: `multipart/form-data` (file, user_input, model_name)
**出力**: JSON レスポンス (result, status)

#### Agent Layer (`filereaderagent.py`)

**責務**:
- LangGraph ワークフローオーケストレーション
- ステート管理
- LLM統合 (Google Gemini / OpenAI / Anthropic)
- ツール呼び出し管理

**入力**: file_path, mime_type, user_instruction, model_name
**出力**: LLM生成レスポンス

#### Tool Layer (`file_reader_processors.py`)

**責務**:
- ファイル形式別のルーティング (`process_file()`)
- 各形式の処理実装
- 外部API呼び出し (Vision, Whisper)
- エンコーディング処理

**入力**: file_path, mime_type, user_instruction
**出力**: 抽出されたテキスト

#### Advanced PDF Layer (`pdf_processor_advanced.py`) **Phase 7**

**責務**:
- 本格的なPDF解析・処理
- テキスト正規化・品質向上
- ヘッダ/フッタ自動除去
- 段落タイプ推定
- メタデータ抽出 (画像、リンク、アウトライン、添付ファイル)
- RAG/検索向けチャンクデータ生成
- JSONL形式での永続化

**入力**: file_path, extract_images, output_dir
**出力**: 処理結果辞書 (chunks, metadata, statistics, file_paths)

---

## 実装フェーズ

### Phase 1: 基本構造とAPI設計 ✅

**期間**: 初期実装
**目標**: File Reader機能の骨格を構築

**実装項目**:
- [ ] FastAPI エンドポイント実装
- [ ] ファイルアップロード処理
- [ ] MIME type検出
- [ ] 一時ファイル管理
- [ ] 基本エラーハンドリング

**成果物**:
- `app/api/v1/agent_endpoints.py`
- 基本的なAPI仕様

### Phase 2: 画像処理実装 ✅

**期間**: Phase 1完了後
**目標**: OpenAI Vision API統合

**実装項目**:
- [ ] Base64エンコーディング処理
- [ ] Vision API呼び出しロジック
- [ ] 画像形式対応 (JPEG/JPG/PNG)
- [ ] エラーハンドリング (API失敗、ファイル未存在等)

**成果物**:
- `process_image()` 関数
- Vision API統合テスト

**依存関係**:
- OpenAI Python SDK
- OPENAI_API_KEY 環境変数

### Phase 3: PDF処理実装 ✅

**期間**: Phase 2完了後
**目標**: PDF読み込み機能実装

**実装項目 (初期)**:
- [x] PyPDF2統合 (後に廃止)
- [x] ページ単位のテキスト抽出
- [x] 基本的なエラーハンドリング

**Phase 7での大幅改善**:
- [x] pypdfへの移行 (PyPDF2は2023年に開発終了)
- [x] 高度なPDF処理モジュール実装
- [x] テキスト正規化パイプライン
- [x] ヘッダ/フッタ自動除去
- [x] 段落タイプ推定
- [x] メタデータ抽出 (画像、リンク、アウトライン、添付ファイル)
- [x] JSONL形式チャンク出力

**成果物**:
- `process_pdf()` 関数 (シンプルモード/高度なモード)
- `pdf_processor_advanced.py` モジュール (516行) **Phase 7**
- PDF処理テスト (42テスト)

**依存関係**:
- pypdf>=4.0.0 (Phase 7で更新)

### Phase 4: テキスト/CSV処理実装 ✅

**期間**: Phase 3完了後
**目標**: プレーンテキストとCSVのサポート

**実装項目**:
- [ ] TXT/MD読み込み
- [ ] CSV読み込みとパース
- [ ] マルチエンコーディング対応 (UTF-8, Shift_JIS, CP932, EUC_JP)
- [ ] Unicode正規化

**成果物**:
- `process_text()` 関数
- `process_csv()` 関数

### Phase 5: 音声処理実装 ✅

**期間**: Phase 4完了後
**目標**: OpenAI Whisper API統合

**実装項目**:
- [ ] Whisper API呼び出しロジック
- [ ] 音声形式対応 (MP4/MP3/WAV)
- [ ] ストリーミング処理
- [ ] エラーハンドリング

**成果物**:
- `process_audio()` 関数
- Whisper API統合テスト

**依存関係**:
- OpenAI Python SDK
- OPENAI_API_KEY 環境変数

### Phase 6: エラーハンドリング強化 ✅

**期間**: Phase 5完了後
**目標**: ロバストなエラー処理

**実装項目**:
- [ ] 統一されたエラーメッセージ
- [ ] ログ出力の充実
- [ ] リトライロジック (API呼び出し失敗時)
- [ ] ユーザーフレンドリーなエラー通知

**成果物**:
- 包括的なエラーハンドリングテスト
- エラーログ仕様

### Phase 7: pypdf移行と高度なPDF処理 ✅

**期間**: 2025-10-12 完了
**目標**: 本格的なPDF処理機能の実装

**実装項目**:
- [x] PyPDF2からpypdfへの依存関係移行
- [x] 高度なPDF処理モジュール実装 (`pdf_processor_advanced.py`)
  - [x] PDFChunk データ構造
  - [x] TextNormalizer (Unicode NFKC, whitespace, hyphen joining)
  - [x] HeaderFooterRemover (頻度ベース検出、30%閾値)
  - [x] ParagraphEstimator (6タイプ: heading, list, code, quote, table_like, paragraph)
  - [x] ImageExtractor (XObject抽出、JPEG/PNG/JP2対応)
  - [x] OutlineExtractor (しおり/目次、再帰的処理)
  - [x] LinkExtractor (内部/外部リンク)
  - [x] AttachmentExtractor (埋め込みファイル)
  - [x] AdvancedPDFProcessor (統合オーケストレーター)
- [x] 既存コードへの統合 (`file_reader_processors.py`)
  - [x] `use_advanced` パラメータ追加 (後方互換性維持)
  - [x] 整形された結果出力
- [x] 包括的なテスト実装 (26新規テスト)
- [x] 既存テストの互換性確認 (16テスト)

**成果物**:
- `pdf_processor_advanced.py` (516行、9クラス)
- `test_pdf_processor_advanced.py` (397行、26テスト)
- 更新された `file_reader_processors.py`
- 42/42テスト合格 (100%)

**技術的成果**:
- PyPDF2依存関係の除去 (deprecated library)
- pypdf 6.1.1への移行
- RAG/検索アプリケーション向けチャンクデータ生成
- JSONL形式での効率的なデータ永続化
- メタデータ豊富な構造化出力

---

## 技術スタック

### コア技術

| カテゴリ | 技術 | バージョン | 用途 |
|---------|------|-----------|------|
| Web Framework | FastAPI | >=0.100.0 | REST API |
| ASGI Server | uvicorn | >=0.23.0 | アプリケーションサーバー |
| LLM Framework | LangGraph | >=0.2.0 | ワークフローオーケストレーション |
| LLM Provider | OpenAI | >=1.0.0 | Vision/Whisper API |
| LLM Provider | Google Gemini | - | LLMエージェント |
| PDF Processing | pypdf | >=4.0.0 | PDF解析 (Phase 7) |
| MIME Detection | python-magic | >=0.4.27 | ファイル形式検出 |

### 依存関係 (pyproject.toml)

```toml
dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "pydantic>=2.0.0",
    "httpx>=0.24.0",

    # LangGraph and LangChain
    "langgraph>=0.2.0",
    "langchain-openai>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "langchain-anthropic>=0.3.0",

    # AI providers
    "openai>=1.0.0",
    "google-genai>=0.1.0",
    "google-generativeai>=0.8.0",
    "anthropic>=0.34.0",

    # File processing
    "pypdf>=4.0.0",           # Phase 7で追加
    "python-magic>=0.4.27",
    "beautifulsoup4>=4.12.0",
    "pandas>=2.0.0",

    # Utilities
    "cryptography>=41.0.0",
]
```

### 開発ツール

| ツール | 用途 |
|--------|------|
| uv | 依存関係管理・仮想環境 |
| pytest | テストフレームワーク |
| pytest-cov | カバレッジ測定 |
| ruff | Linting & Formatting |
| mypy | 型チェック |

---

## API設計

### エンドポイント

```
POST /api/v1/aiagent/file-reader
```

### リクエスト仕様

**Content-Type**: `multipart/form-data`

**フィールド**:

| フィールド | 型 | 必須 | 説明 | デフォルト |
|-----------|---|------|------|-----------|
| file | File | ✅ | アップロードするファイル | - |
| user_input | string | ✅ | ユーザーからの指示 | - |
| model_name | string | ❌ | 使用するLLMモデル | gpt-4o-mini |

**サポートされるモデル**:
- `gpt-4o-mini` (デフォルト)
- `gpt-4o`
- `gemini-1.5-pro`
- `claude-3-5-sonnet-20241022`

### リクエスト例

#### cURLの例

```bash
curl -X POST "http://localhost:8000/api/v1/aiagent/file-reader" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf" \
  -F "user_input=この文書の要点を3つ挙げてください" \
  -F "model_name=gpt-4o-mini"
```

#### Pythonの例

```python
import requests

url = "http://localhost:8000/api/v1/aiagent/file-reader"

files = {
    'file': open('/path/to/document.pdf', 'rb')
}

data = {
    'user_input': 'この文書の要点を3つ挙げてください',
    'model_name': 'gpt-4o-mini'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### レスポンス仕様

**Content-Type**: `application/json`

**成功時 (200 OK)**:

```json
{
  "result": "LLMが生成したレスポンステキスト",
  "status": "success",
  "metadata": {
    "model": "gpt-4o-mini",
    "file_type": "application/pdf",
    "processing_time_ms": 1234
  }
}
```

**エラー時 (4xx/5xx)**:

```json
{
  "detail": "エラーの詳細メッセージ",
  "status": "error",
  "error_type": "ValidationError | FileProcessingError | APIError"
}
```

### エラーコード

| HTTPステータス | エラータイプ | 説明 |
|--------------|-------------|------|
| 400 | ValidationError | 不正なリクエスト (ファイルなし、MIME type不正等) |
| 413 | PayloadTooLarge | ファイルサイズ超過 |
| 415 | UnsupportedMediaType | サポートされていないファイル形式 |
| 500 | FileProcessingError | ファイル処理中のエラー |
| 502 | APIError | 外部API呼び出しエラー (Vision/Whisper) |
| 503 | ServiceUnavailable | LLMサービス利用不可 |

---

## 品質基準

### テスト要件

#### 単体テスト (Unit Tests)

**目標カバレッジ**: 90%以上

**テスト対象**:
- 各ファイルプロセッサ (`process_image`, `process_pdf`, `process_text`, `process_csv`, `process_audio`)
- PDF処理ユーティリティ (Phase 7):
  - `PDFChunk` データ構造
  - `TextNormalizer` (正規化パイプライン)
  - `HeaderFooterRemover` (パターン検出)
  - `ParagraphEstimator` (タイプ推定)
  - `ImageExtractor` (XObject抽出)
  - `OutlineExtractor` (アウトライン抽出)
  - `LinkExtractor` (リンク抽出)
  - `AttachmentExtractor` (添付ファイル抽出)
  - `AdvancedPDFProcessor` (統合処理)
- エラーハンドリング
- エンコーディング処理
- MIME type検出

**テストケース例**:
- 正常系: ファイル処理成功
- 異常系: ファイル未存在
- 異常系: API呼び出し失敗
- 異常系: サポート外形式
- 境界値: 空ファイル、巨大ファイル

**現在の実績 (Phase 7完了時)**:
- 総テスト数: 42テスト
- 合格率: 100% (42/42 passed)
- 内訳:
  - 既存テスト (Phase 1-6): 16テスト
  - 新規テスト (Phase 7): 26テスト

#### 結合テスト (Integration Tests)

**目標**: 50%以上 (API層のみ測定)

**テスト対象**:
- API エンドポイント (`/api/v1/aiagent/file-reader`)
- LangGraph ワークフロー
- 外部API連携 (Vision, Whisper)
- エンドツーエンドフロー

**テストシナリオ**:
1. 画像アップロード → Vision API → LLM分析 → レスポンス
2. PDFアップロード → テキスト抽出 → LLM要約 → レスポンス
3. 音声アップロード → Whisper文字起こし → LLM処理 → レスポンス
4. サポート外形式 → エラーレスポンス

### 静的解析

**ツール**: Ruff, MyPy

**品質基準**:
- ✅ Ruffエラーゼロ
- ✅ MyPy型チェック合格
- ✅ Docstring完備 (全public関数)
- ✅ Type hints完備 (Python 3.12標準)

**実行コマンド**:
```bash
uv run ruff check .
uv run ruff format . --check
uv run mypy app/
```

### コードレビューチェックリスト

#### 機能性
- [ ] 要件を満たしているか
- [ ] エラーハンドリングは適切か
- [ ] ログ出力は十分か
- [ ] テストは網羅的か (90%カバレッジ)

#### 保守性
- [ ] コードは読みやすいか
- [ ] 関数は単一責任か (SOLID原則)
- [ ] マジックナンバーを避けているか
- [ ] Docstringは明確か

#### パフォーマンス
- [ ] 不要なループはないか
- [ ] メモリリークの可能性はないか
- [ ] ファイル読み込みは効率的か
- [ ] 大量のファイル処理でもスケールするか

#### セキュリティ
- [ ] ファイルパスインジェクション対策
- [ ] ファイルサイズ制限
- [ ] 一時ファイルの適切なクリーンアップ
- [ ] API keyの安全な管理

---

## セキュリティ考慮事項

### ファイルアップロードセキュリティ

#### ファイルサイズ制限

```python
# FastAPI設定
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@app.post("/api/v1/aiagent/file-reader")
async def file_reader(file: UploadFile = File(...)):
    # Check file size
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
```

#### MIME Type検証

```python
import magic

def validate_mime_type(file_path: Path) -> str:
    """Validate and detect MIME type"""
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(str(file_path))

    # Whitelist check
    ALLOWED_TYPES = [
        "image/jpeg", "image/png",
        "application/pdf",
        "text/plain", "text/markdown", "text/csv",
        "audio/mp3", "audio/wav", "video/mp4"
    ]

    if mime_type not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported file type: {mime_type}")

    return mime_type
```

#### パストラバーサル対策

```python
from pathlib import Path

def safe_file_path(base_dir: Path, filename: str) -> Path:
    """Ensure file path is within base directory"""
    file_path = (base_dir / filename).resolve()

    # Check if resolved path is within base directory
    if not file_path.is_relative_to(base_dir):
        raise ValueError("Invalid file path")

    return file_path
```

### API Key管理

**重要**: API keyは環境変数またはMyVault経由で管理

```python
from core.secrets import resolve_runtime_value

# Good: Secure key retrieval
api_key = resolve_runtime_value("OPENAI_API_KEY")

# Bad: Hardcoded key (NEVER DO THIS)
api_key = "sk-xxxxxxxxxxxxx"  # ❌ DANGER
```

**環境変数設定**:
```bash
# .env file (not committed to Git)
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxx
```

### 一時ファイル管理

**原則**: 処理完了後は必ず削除

```python
import tempfile
from pathlib import Path

def process_with_cleanup(uploaded_file):
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = Path(tmp.name)

    try:
        # Process file
        result = process_pdf(tmp_path)
        return result
    finally:
        # Always cleanup
        if tmp_path.exists():
            tmp_path.unlink()
```

### ログ出力の注意事項

**禁止**: ログに機密情報を出力しない

```python
import logging

logger = logging.getLogger(__name__)

# Good: Safe logging
logger.info(f"Processing file: {file_path.name}")

# Bad: Sensitive data in logs
logger.info(f"API key: {api_key}")  # ❌ NEVER LOG API KEYS
logger.info(f"User email: {user_email}")  # ❌ PII
```

---

## パフォーマンス要件

### レスポンスタイム目標

| ファイル形式 | 目標レスポンスタイム | 備考 |
|------------|-------------------|------|
| 画像 (< 5MB) | < 10秒 | Vision API呼び出し含む |
| PDF (< 50ページ) | < 15秒 | シンプルモード |
| PDF (< 50ページ) | < 30秒 | 高度なモード (Phase 7) |
| テキスト (< 1MB) | < 3秒 | 直接読み込み |
| CSV (< 10,000行) | < 5秒 | パース含む |
| 音声 (< 10分) | < 20秒 | Whisper API呼び出し含む |

### スケーラビリティ

#### 並行リクエスト処理

- FastAPIは非同期処理をサポート
- uvicornのworker数で並行度を制御

```bash
# Production deployment
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

#### メモリ管理

**大容量ファイル対策**:
- ストリーミング読み込み (チャンク単位)
- 一時ファイルの即時削除
- メモリ使用量のモニタリング

```python
# Stream file upload (avoid loading entire file in memory)
@app.post("/api/v1/aiagent/file-reader")
async def file_reader(file: UploadFile = File(...)):
    # Chunk-based writing
    with open(tmp_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
```

#### Phase 7でのPDFパフォーマンス最適化

**現在の実装**:
- ページ単位の逐次処理
- メモリ効率的なJSONL出力 (ストリーミング対応)
- SHA256ハッシュによる重複検出

**今後の最適化案**:
1. **並列処理**: マルチプロセスでのページ並列処理
2. **インクリメンタル処理**: 差分検出と部分更新
3. **キャッシング**: 処理済みPDFのハッシュベースキャッシュ

### API Rate Limiting

**OpenAI API制限**:
- Vision API: RPM (Requests Per Minute) 制限あり
- Whisper API: RPM制限あり

**対策**:
- リトライロジック実装 (exponential backoff)
- キュー処理の検討 (大量リクエスト時)

```python
import time
from openai import RateLimitError

def call_api_with_retry(api_func, max_retries=3):
    """Call API with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            return api_func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Rate limit hit, retrying in {wait_time}s...")
            time.sleep(wait_time)
```

---

## 運用・モニタリング

### ログ出力

**ログレベル**:
- `DEBUG`: 詳細なデバッグ情報
- `INFO`: 通常の処理フロー
- `WARNING`: 警告 (リトライ等)
- `ERROR`: エラー (処理失敗、API呼び出し失敗等)
- `CRITICAL`: クリティカルエラー (サービス停止等)

**ログ項目**:
- タイムスタンプ
- ログレベル
- ファイル名・行番号
- メッセージ
- リクエストID (トレーシング用)

### メトリクス

**監視すべき指標**:
- リクエスト数 (per endpoint)
- レスポンスタイム (p50, p95, p99)
- エラー率
- API呼び出し回数 (Vision, Whisper)
- ファイルサイズ分布
- メモリ使用量
- 一時ファイル数

### アラート設定

**アラート条件例**:
- エラー率 > 5% (5分間)
- レスポンスタイム p95 > 30秒 (5分間)
- メモリ使用率 > 80%
- 一時ファイル削除失敗 (ディスク溢れリスク)

---

## トラブルシューティング

### よくある問題と解決策

#### 1. Vision API呼び出し失敗

**症状**: `APIError: Vision API call failed`

**原因**:
- API key未設定または不正
- Rate limit超過
- 画像形式が不正

**解決策**:
```bash
# API key確認
echo $OPENAI_API_KEY

# MyVaultから取得確認
curl -s -H "X-Service: expertagent" \
  -H "X-Token: YOUR_TOKEN" \
  "http://localhost:8003/api/secrets/default_project/OPENAI_API_KEY"

# Rate limit確認
# → リトライロジックが動作しているか確認
```

#### 2. PDF処理でテキストが取得できない

**症状**: 空のテキストが返される

**原因**:
- スキャンPDF (画像化されたPDF)
- フォント埋め込みなし
- 暗号化PDF

**解決策**:
```python
# Check if PDF is encrypted
from pypdf import PdfReader

reader = PdfReader("document.pdf")
if reader.is_encrypted:
    print("PDF is encrypted. Decryption required.")

# For scanned PDFs, OCR is needed (future enhancement)
```

#### 3. 音声文字起こし失敗

**症状**: `APIError: Whisper API error`

**原因**:
- 音声形式が不正
- ファイルサイズ超過 (Whisper上限: 25MB)
- 音声品質が低い

**解決策**:
```bash
# Check file format
file audio.mp4
# → 正しい形式か確認

# Check file size
ls -lh audio.mp4
# → 25MB以下か確認

# Convert to supported format if needed
ffmpeg -i input.m4a -acodec mp3 output.mp3
```

#### 4. メモリ不足エラー

**症状**: `MemoryError` または OOM (Out of Memory)

**原因**:
- 大容量ファイルの一括読み込み
- 一時ファイルの削除漏れ

**解決策**:
```bash
# Check memory usage
free -h

# Check temporary files
ls -lh /tmp/

# Cleanup old temporary files
find /tmp/ -name "tmp*" -mtime +1 -delete
```

#### 5. pypdf移行後のエラー (Phase 7)

**症状**: `ModuleNotFoundError: No module named 'pypdf'`

**原因**:
- 依存関係が未インストール

**解決策**:
```bash
# Install dependencies
uv sync

# Verify installation
uv run python -c "import pypdf; print(pypdf.__version__)"
# Expected: 6.1.1
```

---

## 今後の拡張計画

### 短期 (1-3ヶ月)

1. **OCR統合** (スキャンPDF対応)
   - Tesseract統合
   - 日本語OCR精度向上

2. **Phase 7パフォーマンス最適化**
   - ページ並列処理
   - メモリ使用量削減

3. **カバレッジ向上**
   - Phase 7結合テスト追加
   - CI/CDでのカバレッジ自動測定

### 中期 (3-6ヶ月)

1. **新ファイル形式対応**
   - DOCX (Microsoft Word)
   - PPTX (PowerPoint)
   - XLSX (Excel)

2. **表構造解析**
   - PDF内の表をセル単位で抽出
   - CSV/JSON形式での出力

3. **リアルタイム処理**
   - WebSocket対応
   - ストリーミングレスポンス

### 長期 (6ヶ月以降)

1. **マルチモーダル統合**
   - 画像+テキストの統合解析
   - 音声+画像の同時処理

2. **カスタムモデル対応**
   - ユーザー独自のVision/OCRモデル統合
   - Fine-tuningサポート

3. **大規模文書処理**
   - バッチ処理機能
   - 分散処理対応

---

## 参考資料

### 公式ドキュメント

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [pypdf Documentation](https://pypdf.readthedocs.io/) **Phase 7**
- [Google Gemini API](https://ai.google.dev/docs)

### 内部ドキュメント

- [Architecture Overview](./design/architecture-overview.md)
- [Environment Variables](./design/environment-variables.md)
- [MyVault Integration](./design/myvault-integration.md)
- [File Reader Progress](./file-reader-progress.md)

### 関連Issue/PR

- [#71] Environment Variable Management Refactoring
- [#89] File Reader Implementation (Phase 1-6)
- [#XXX] pypdf Migration and Advanced PDF Processing (Phase 7) **NEW**

---

**最終更新**: 2025-10-12
**作成者**: Claude Code
**バージョン**: 1.1 (Phase 7対応)
**ステータス**: 全フェーズ完了 (Phase 1-7)
