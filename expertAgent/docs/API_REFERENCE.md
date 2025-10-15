# Expert Agent API Reference

## Overview

Expert Agent Service provides REST API endpoints for AI agent execution, utility functions, and Google Drive file operations.

## Base URL

```
http://localhost:8000
```

## Authentication

Most endpoints require Google OAuth2 authentication. Admin endpoints require an additional `X-Admin-Token` header.

---

## Google Drive Upload API

### Upload File to Google Drive

**POST** `/api/v1/utility/drive/upload`

Uploads a local file or creates a file from content and uploads it to Google Drive.

#### Features

- ローカルファイルのアップロード
- コンテンツからファイル生成＆アップロード
- サブディレクトリ自動作成
- 重複ファイル名自動回避
- 大ファイル対応（Resumable Upload自動切替）

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | ローカルファイルパスまたは作成先パス |
| `drive_folder_url` | string | No | Google DriveフォルダURL |
| `file_name` | string | No | 保存ファイル名（未指定時は元のファイル名） |
| `sub_directory` | string | No | サブディレクトリパス（例: "reports/2025"） |
| `size_threshold_mb` | integer | No | Resumable Upload閾値（デフォルト: 100MB） |
| `content` | string/bytes | No | ファイル内容（create_file=true時のみ） |
| `file_format` | string | No | 拡張子（create_file=true時のみ、例: "pdf", "txt"） |
| `create_file` | boolean | No | ファイル作成モード（デフォルト: false） |
| `test_mode` | boolean | No | テストモード（CI/CD用、デフォルト: false） |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Examples

**Example 1: Upload local file**

```bash
curl -X POST http://localhost:8000/api/v1/utility/drive/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/tmp/report.pdf",
    "drive_folder_url": "https://drive.google.com/drive/folders/1a2b3c4d5e",
    "file_name": "monthly_report.pdf",
    "sub_directory": "reports/2025"
  }'
```

**Example 2: Create file from content**

```bash
curl -X POST http://localhost:8000/api/v1/utility/drive/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/tmp/generated.txt",
    "content": "Hello, World!",
    "file_format": "txt",
    "create_file": true,
    "drive_folder_url": "https://drive.google.com/drive/folders/1a2b3c4d5e"
  }'
```

**Example 3: Test mode**

```bash
curl -X POST http://localhost:8000/api/v1/utility/drive/upload \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/tmp/test.txt",
    "test_mode": true,
    "test_response": "Test response"
  }'
```

#### Success Response (200 OK)

```json
{
  "status": "success",
  "file_id": "1a2b3c4d5e6f7g8h9i0j",
  "file_name": "monthly_report.pdf",
  "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view",
  "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e6f7g8h9i0j&export=download",
  "folder_path": "reports/2025",
  "file_size_mb": 2.45,
  "upload_method": "normal"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | 処理ステータス（"success" または "error"） |
| `file_id` | string | Google Drive ファイルID |
| `file_name` | string | アップロードされたファイル名 |
| `web_view_link` | string | ファイル閲覧用URL |
| `web_content_link` | string | ファイルダウンロード用URL（null の場合あり） |
| `folder_path` | string | アップロード先フォルダパス |
| `file_size_mb` | number | ファイルサイズ（MB） |
| `upload_method` | string | アップロードメソッド（"normal" または "resumable"） |

#### Error Responses

**400 Bad Request - File not found**

```json
{
  "detail": "指定されたファイルが存在しません: /nonexistent/file.txt"
}
```

**400 Bad Request - Invalid parameters**

```json
{
  "detail": "create_file=True の場合、content パラメータが必須です"
}
```

**500 Internal Server Error - Google API error**

```json
{
  "detail": "An internal server error occurred during file upload"
}
```

#### Upload Method Selection

The API automatically selects the appropriate upload method based on file size:

| File Size | Method | Description |
|-----------|--------|-------------|
| < 100MB (default) | Normal Upload | 標準アップロード（高速） |
| ≥ 100MB (default) | Resumable Upload | レジューム可能なアップロード（大ファイル向け） |

The threshold can be customized with the `size_threshold_mb` parameter.

#### Notes

- ファイル作成モード（`create_file=true`）では、`content` と `file_format` が必須です
- 作成された一時ファイルは自動的に削除されます
- 同名ファイルが存在する場合、自動的に連番が付与されます（例: `file_001_20251015_143022.txt`）
- Google OAuth2認証が必要です

---

## Text-to-Speech (TTS) APIs

### Convert Text to Speech (Base64)

**POST** `/v1/utility/text_to_speech`

Converts text to speech using OpenAI TTS API and returns Base64-encoded audio data.

#### Features

- OpenAI TTS APIによる高品質音声合成
- 複数の音声タイプ選択可能（alloy, echo, fable, onyx, nova, shimmer）
- 2つのモデル選択（tts-1: 標準品質、tts-1-hd: 高品質）
- Base64エンコードでJSON形式で返却
- メモリ効率の良い一時ファイル処理

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | 音声合成するテキスト（最大4096文字） |
| `model` | string | No | TTSモデル (tts-1, tts-1-hd)（デフォルト: tts-1） |
| `voice` | string | No | 音声タイプ (alloy, echo, fable, onyx, nova, shimmer)（デフォルト: alloy） |
| `test_mode` | boolean | No | テストモード（CI/CD用、デフォルト: false） |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8000/v1/utility/text_to_speech \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは、これはテスト音声です。",
    "model": "tts-1",
    "voice": "alloy"
  }'
```

#### Success Response (200 OK)

```json
{
  "audio_content": "SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA...",
  "format": "mp3",
  "size_bytes": 15360
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `audio_content` | string | Base64エンコードされた音声データ（MP3形式） |
| `format` | string | 音声フォーマット（常に "mp3"） |
| `size_bytes` | integer | 元のファイルサイズ（バイト単位） |

#### Error Responses

**400 Bad Request - Text too long**

```json
{
  "detail": "テキストは4096文字以内にしてください"
}
```

**400 Bad Request - Invalid model**

```json
{
  "detail": "モデルは 'tts-1' または 'tts-1-hd' を指定してください"
}
```

**400 Bad Request - Invalid voice**

```json
{
  "detail": "音声タイプは alloy, echo, fable, onyx, nova, shimmer のいずれかを指定してください"
}
```

**500 Internal Server Error - TTS failure**

```json
{
  "detail": "音声ファイルの生成に失敗しました"
}
```

#### Notes

- Base64デコード後、そのままMP3ファイルとして保存可能
- 大きなテキスト（1500文字超）は自動的に分割して処理
- Google OAuth2認証が必要です

---

### Convert Text to Speech and Upload to Drive

**POST** `/v1/utility/text_to_speech_drive`

Converts text to speech using OpenAI TTS API and uploads the audio file directly to Google Drive.

#### Features

- OpenAI TTS APIによる高品質音声合成
- Google Driveへの直接アップロード
- サブディレクトリ自動作成
- 重複ファイル名自動回避
- ファイルリンク返却

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | 音声合成するテキスト（最大4096文字） |
| `drive_folder_url` | string | No | Google DriveフォルダURL |
| `file_name` | string | No | 保存ファイル名（未指定時は自動生成） |
| `sub_directory` | string | No | サブディレクトリパス（例: "podcasts/2025"） |
| `model` | string | No | TTSモデル (tts-1, tts-1-hd)（デフォルト: tts-1） |
| `voice` | string | No | 音声タイプ (alloy, echo, fable, onyx, nova, shimmer)（デフォルト: alloy） |
| `test_mode` | boolean | No | テストモード（CI/CD用、デフォルト: false） |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Examples

**Example 1: Basic upload**

```bash
curl -X POST http://localhost:8000/v1/utility/text_to_speech_drive \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは、これはテスト音声です。"
  }'
```

**Example 2: Upload with subdirectory**

```bash
curl -X POST http://localhost:8000/v1/utility/text_to_speech_drive \
  -H "Content-Type: application/json" \
  -d '{
    "text": "本日のポッドキャストをお届けします。",
    "drive_folder_url": "https://drive.google.com/drive/folders/1a2b3c4d5e",
    "file_name": "podcast_episode_001",
    "sub_directory": "podcasts/2025",
    "model": "tts-1-hd",
    "voice": "nova"
  }'
```

#### Success Response (200 OK)

```json
{
  "file_id": "1a2b3c4d5e6f7g8h9i0j",
  "file_name": "podcast_episode_001.mp3",
  "web_view_link": "https://drive.google.com/file/d/1a2b3c4d5e6f7g8h9i0j/view",
  "web_content_link": "https://drive.google.com/uc?id=1a2b3c4d5e6f7g8h9i0j",
  "folder_path": "podcasts/2025",
  "file_size_mb": 0.15
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | string | Google Drive ファイルID |
| `file_name` | string | アップロードされたファイル名 |
| `web_view_link` | string | ファイル閲覧用URL |
| `web_content_link` | string | ファイルダウンロード用URL（null の場合あり） |
| `folder_path` | string | アップロード先フォルダパス |
| `file_size_mb` | number | ファイルサイズ（MB） |

#### Error Responses

**400 Bad Request - Text too long**

```json
{
  "detail": "テキストは4096文字以内にしてください"
}
```

**400 Bad Request - Invalid Drive folder URL**

```json
{
  "detail": "無効なGoogle DriveフォルダURLです"
}
```

**500 Internal Server Error - TTS or upload failure**

```json
{
  "detail": "音声変換またはアップロード中に予期しないエラーが発生しました"
}
```

#### API Selection Guide

| 要件 | 推奨API | 理由 |
|------|---------|------|
| 音声データをアプリ内で再生 | `/v1/utility/text_to_speech` | Base64デコードで即座に使用可能 |
| 音声ファイルを長期保存 | `/v1/utility/text_to_speech_drive` | Drive URLで恒久的にアクセス可能 |
| 音声ファイルを共有 | `/v1/utility/text_to_speech_drive` | Drive URLで簡単に共有可能 |
| LLMワークフローで音声生成 | `/v1/utility/text_to_speech` + Drive Upload API | 柔軟な処理フロー構築が可能 |

#### Notes

- ファイル名が指定されていない場合は自動生成されます（例: `audio_001_20250101_120000.mp3`）
- 同名ファイルが存在する場合、自動的に連番が付与されます
- 一時ファイルは自動的に削除されます
- Google OAuth2認証が必要です

---

## TTS and Google Drive Upload API (Legacy)

### Convert Text to Speech and Upload

**POST** `/api/v1/utility/tts_and_upload_drive`

Converts text to speech (MP3) and uploads the audio file to Google Drive.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_input` | string | Yes | 音声合成するテキストメッセージ |
| `test_mode` | boolean | No | テストモード（デフォルト: false） |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8000/api/v1/utility/tts_and_upload_drive \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "こんにちは、これはテスト音声です。"
  }'
```

#### Success Response (200 OK)

```json
{
  "result": "アップロード成功: https://drive.google.com/file/d/xxx/view"
}
```

#### Features

- テキストからMP3音声ファイルを自動生成
- タイトル自動生成（最大40文字）
- Google Driveへ自動アップロード
- メール通知機能付き

---

## Gmail Utility APIs

### Search Gmail Messages

**POST** `/api/v1/utility/gmail/search`

Searches Gmail messages based on query criteria.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Gmail検索クエリ（例: "is:unread from:sender@example.com"） |
| `max_results` | integer | No | 最大取得件数（デフォルト: 10） |
| `test_mode` | boolean | No | テストモード |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8000/api/v1/utility/gmail/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "is:unread",
    "max_results": 5
  }'
```

#### Success Response (200 OK)

```json
{
  "messages": [
    {
      "id": "msg123",
      "threadId": "thread123",
      "snippet": "メールの抜粋...",
      "from": "sender@example.com",
      "subject": "件名",
      "date": "2025-10-15T10:30:00Z"
    }
  ],
  "result_count": 5
}
```

---

### Send Gmail Message

**POST** `/api/v1/utility/gmail/send`

Sends an email via Gmail.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | string | Yes | 宛先メールアドレス |
| `subject` | string | Yes | 件名 |
| `body` | string | Yes | メール本文 |
| `test_mode` | boolean | No | テストモード |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8000/api/v1/utility/gmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "テストメール",
    "body": "これはテストメールです。"
  }'
```

#### Success Response (200 OK)

```json
{
  "result": "Email sent successfully",
  "message_id": "msg123"
}
```

---

## Google Search APIs

### Google Search

**POST** `/api/v1/utility/google_search`

Performs Google searches via Serper API.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `queries` | array | Yes | 検索クエリのリスト |
| `num` | integer | No | 結果件数（デフォルト: 10） |
| `test_mode` | boolean | No | テストモード |
| `test_response` | string | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8000/api/v1/utility/google_search \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["Python FastAPI tutorial", "Google Drive API"],
    "num": 5
  }'
```

---

### Google Search Overview

**POST** `/api/v1/utility/google_search_overview`

Gets an overview of Google search results.

#### Request Body

Same as `/api/v1/utility/google_search`

---

## Admin Endpoints

### Reload Secrets Cache

**POST** `/api/v1/admin/reload-secrets`

Clears the secrets cache for a specific project or all projects.

#### Headers

- `X-Admin-Token` (string, required): Admin authentication token

#### Request Body

```json
{
  "project": "project_name"  // Optional: omit to clear all caches
}
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Cache cleared for project: project_name"
}
```

---

### Admin Health Check

**GET** `/api/v1/admin/health`

Returns the health status of admin services.

#### Success Response (200 OK)

```json
{
  "status": "healthy",
  "service": "expertAgent-admin"
}
```

---

## Google OAuth2 Endpoints

### Get Token Status

**GET** `/api/v1/token-status`

Checks Google OAuth2 token status for a project.

#### Headers

- `X-Admin-Token` (string, required): Admin authentication token

#### Query Parameters

- `project` (string, optional): Project name (defaults to default project)

#### Success Response (200 OK)

```json
{
  "project": "default_project",
  "token_exists": true,
  "token_valid": true,
  "expires_at": "2025-10-20T10:30:00Z"
}
```

---

### Start OAuth2 Flow

**POST** `/api/v1/oauth2-start`

Initiates OAuth2 authorization flow.

#### Headers

- `X-Admin-Token` (string, required): Admin authentication token

#### Request Body

```json
{
  "project": "project_name"
}
```

#### Success Response (200 OK)

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

---

### OAuth2 Callback

**POST** `/api/v1/oauth2-callback`

Handles OAuth2 callback and exchanges authorization code for tokens.

#### Headers

- `X-Admin-Token` (string, required): Admin authentication token

#### Request Body

```json
{
  "code": "authorization_code",
  "project": "project_name"
}
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "message": "Token saved successfully"
}
```

---

## Common Health & Info Endpoints

### Health Check

**GET** `/health`

Returns service health status.

#### Success Response (200 OK)

```json
{
  "status": "healthy",
  "service": "expertAgent"
}
```

---

### Root Endpoint

**GET** `/`

Returns welcome message.

#### Success Response (200 OK)

```json
{
  "message": "Welcome to Expert Agent Service"
}
```

---

### API Version

**GET** `/api/v1/`

Returns API version information.

#### Success Response (200 OK)

```json
{
  "version": "1.0",
  "service": "expertAgent"
}
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Invalid admin token |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error - Server error |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Validation Error Format (422)

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "file_path"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Environment Variables

Required environment variables:

```env
# Server Configuration
PORT=8000
LOG_LEVEL=INFO

# MyVault Configuration
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8003
MYVAULT_SERVICE_NAME=expertagent
MYVAULT_SERVICE_TOKEN=your_token_here

# Email Configuration
MAIL_TO=your_email@example.com

# Admin API
ADMIN_TOKEN=your_admin_token_here
```

---

## Testing

Run tests:

```bash
cd expertAgent
uv run pytest tests/
```

Run specific test suite:

```bash
uv run pytest tests/unit/test_drive_endpoints.py
```

Check coverage:

```bash
uv run pytest tests/ --cov=app --cov=core --cov-report=html
open htmlcov/index.html
```
