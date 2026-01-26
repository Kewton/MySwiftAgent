# Expert Agent API Reference

## Overview

Expert Agent Service provides REST API endpoints for AI agent execution, utility functions, and Google Drive file operations.

## Base URL and Root Path

**Development Server:**
```
http://localhost:8104
```

**FastAPI Root Path:**
```
/aiagent-api
```

**Complete Base URL (for external access):**
```
http://localhost:8104/aiagent-api
```

**Important:** All endpoint paths shown in this document are relative to the FastAPI `root_path` (`/aiagent-api`). When accessing from external services (e.g., GraphAI workflows, curl commands), prepend `/aiagent-api` to the endpoint path.

**Example:**
- **Endpoint**: `/v1/utility/tts_and_upload_drive`
- **Full URL**: `http://localhost:8104/aiagent-api/v1/utility/tts_and_upload_drive`

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

**POST** `/v1/utility/tts_and_upload_drive`

**Full URL:** `http://localhost:8104/aiagent-api/v1/utility/tts_and_upload_drive`

Converts text to speech (MP3) and uploads the audio file to Google Drive.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_input` | string | Yes | 音声合成するテキストメッセージ |
| `test_mode` | boolean | No | テストモード（デフォルト: false） |
| `test_response` | dict/str | No | テストモード時のレスポンス |

#### Request Example

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/utility/tts_and_upload_drive \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "こんにちは、これはテスト音声です。"
  }'
```

#### GraphAI Workflow Example

```yaml
generate_podcast:
  agent: fetchAgent
  params:
    url: http://localhost:8104/aiagent-api/v1/utility/tts_and_upload_drive
    headers:
      Content-Type: application/json
    body:
      user_input: :summarize_email
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

#### Response

| Field | Type | Description |
|-------|------|-------------|
| `search_results` | array | 検索結果の配列 |
| `search_results_count` | integer | 検索結果の件数 |
| `status` | string | ステータス（通常は "ok"） |

#### Response Example

```json
{
  "search_results": [
    {
      "title": "FastAPI Tutorial",
      "link": "https://fastapi.tiangolo.com/tutorial/",
      "knowledge": "FastAPIの公式チュートリアル...",
      "original_query": "Python FastAPI tutorial"
    },
    {
      "title": "Google Drive API Overview",
      "link": "https://developers.google.com/drive/api",
      "knowledge": "Google Drive APIの概要...",
      "original_query": "Google Drive API"
    }
  ],
  "search_results_count": 2,
  "status": "ok"
}
```

#### ワークフローでの参照方法

```yaml
# 検索結果配列へのアクセス
results: :fetch_search_results.search_results

# 検索結果件数へのアクセス
count: :fetch_search_results.search_results_count
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

## Job Generator API

### Generate Job and Tasks (Async)

**POST** `/api/v1/job-generator`

Asynchronously generates Job and Tasks from natural language requirements using LangGraph agent. Returns job_id immediately and processes in background.

#### Features

- 自然言語要求からJob/Task自動生成
- 非同期バックグラウンド処理
- 実現可能性評価と代替案提案
- 要求緩和提案（Requirement Relaxation Suggestions）
- リトライ機能付きLangGraphエージェント実行
- Langfuseトレーシング統合（Issue #278）

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_requirement` | string | Yes | 自然言語で記述したJob/Task生成要求 |
| `max_retry` | integer | No | 評価・検証の最大リトライ回数（デフォルト: 5、範囲: 1-10） |

#### Request Example

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/job-generator \
  -H "Content-Type: application/json" \
  -d '{
    "user_requirement": "PDFファイルをGoogle Driveにアップロードして、完了をメール通知する",
    "max_retry": 5
  }'
```

#### Response

**Success Response (200 OK - Creating):**

```json
{
  "status": "creating",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_master_id": null,
  "task_breakdown": null,
  "evaluation_result": null,
  "infeasible_tasks": [],
  "alternative_proposals": [],
  "api_extension_proposals": [],
  "requirement_relaxation_suggestions": [],
  "validation_errors": [],
  "error_message": "Job creation started. Use GET /api/v1/jobs/{job_id}/status to check progress.",
  "langfuse_trace_id": null,
  "user_input_schema": null
}
```

**Note (Issue #278):** When the job completes, `langfuse_trace_id` will contain the Langfuse trace ID if Langfuse is enabled. Use this ID to view the LLM call traces in the Langfuse dashboard.

**Error Response (500 Internal Server Error):**

```json
{
  "detail": "ANTHROPIC_API_KEY not configured in myVault. Please add it via CommonUI."
}
```

#### Notes

- ジョブ作成は非同期で実行されます
- レスポンスの`job_id`を使用して`GET /api/v1/jobs/{job_id}/status`でステータスを確認してください
- ANTHROPIC_API_KEYがmyVaultに設定されている必要があります

---

### Get Job Creation Status

**GET** `/api/v1/jobs/{job_id}/status`

Check the status of an async job creation process.

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (path) | Yes | ジョブID（POST /job-generatorで取得） |

#### Request Example

```bash
curl -X GET http://localhost:8104/aiagent-api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/status
```

#### Response

**Success Response (200 OK - Completed):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "start_time": "2025-10-15T10:30:00Z",
  "end_time": "2025-10-15T10:31:45Z",
  "job_master_id": "jm_01K89W9DBHAPWMMZVHWT2N7GX9",
  "result": {
    "status": "success",
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "job_master_id": "jm_01K89W9DBHAPWMMZVHWT2N7GX9",
    "task_breakdown": [...],
    "evaluation_result": {...},
    "user_input_schema": {
      "type": "object",
      "properties": {
        "keyword": {"type": "string", "description": "検索キーワード"},
        "email": {"type": "string", "format": "email", "description": "通知先メールアドレス"}
      },
      "required": ["keyword", "email"]
    }
  }
}
```

**Response (200 OK - Creating):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "creating",
  "progress": 45,
  "start_time": "2025-10-15T10:30:00Z",
  "end_time": null,
  "job_master_id": null,
  "result": null
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Job ID 550e8400-e29b-41d4-a716-446655440000 not found. Job may have been cleaned up or never existed."
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | ジョブID |
| `status` | string | ステータス（"creating", "completed", "failed"） |
| `progress` | integer | 進捗率（0-100） |
| `start_time` | string | 開始時刻（ISO 8601形式） |
| `end_time` | string | 終了時刻（ISO 8601形式、未完了時はnull） |
| `job_master_id` | string | JobMaster ID（完了時のみ） |
| `result` | object | ジョブ生成結果（完了時のみ） |
| `error_message` | string | エラーメッセージ（失敗時のみ） |
| `user_input_schema` | object | ユーザー入力スキーマ（Issue #410）。LLMが生成したJSON Schema形式のユーザー入力フィールド定義。完了時のみ。フロントエンドで入力フォームの動的生成に使用。 |

---

## Workflow Generator API

### Generate GraphAI Workflow YAML

**POST** `/api/v1/workflow-generator`

Generate GraphAI workflow YAML files from JobMaster or TaskMaster using LangGraph agent.

#### Features

- JobMaster単位または個別TaskMaster単位でのワークフロー生成
- LangGraphエージェントによる自動YAML生成
- 自己修復ループ（バリデーションエラー時の自動リトライ）
- ULID/整数ID両対応
- バッチ処理（Job内の全タスク一括生成）
- Langfuseトレーシング統合（Issue #278）

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_master_id` | string/int | XOR | JobMaster ID（全タスクのワークフローを生成） |
| `task_master_id` | string/int | XOR | TaskMaster ID（単一タスクのワークフローを生成） |

**Note**: `job_master_id`と`task_master_id`は排他的（XOR）です。どちらか一方のみ指定してください。

#### Request Examples

**Example 1: Generate workflows for all tasks in a job**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/workflow-generator \
  -H "Content-Type: application/json" \
  -d '{
    "job_master_id": "jm_01K8DXE62NFJNB0SHJZPAWQWVT"
  }'
```

**Example 2: Generate workflow for single task**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/workflow-generator \
  -H "Content-Type: application/json" \
  -d '{
    "task_master_id": "tm_01K8DXE601HMZWW0K5HR9FDYCQ"
  }'
```

#### Response

**Success Response (200 OK):**

```json
{
  "status": "success",
  "workflows": [
    {
      "task_master_id": "tm_01K8K13NC8PRJ3V4R35C1AP2JP",
      "task_name": "Send email notification",
      "workflow_name": "send_email_notification",
      "yaml_content": "version: 0.5\nnodes:\n  send_email:\n    agent: fetchAgent\n    ...",
      "status": "success",
      "validation_result": {
        "is_valid": true
      },
      "error_message": null,
      "retry_count": 0
    }
  ],
  "total_tasks": 3,
  "successful_tasks": 3,
  "failed_tasks": 0,
  "generation_time_ms": 5432.1,
  "langfuse_trace_id": "trace-abc123-def456"
}
```

**Note (Issue #278):** The `langfuse_trace_id` field contains the Langfuse trace ID if Langfuse is enabled. Use this ID to view the LLM call traces in the Langfuse dashboard. The field is `null` when Langfuse is disabled.

**Partial Success Response (200 OK):**

```json
{
  "status": "partial_success",
  "workflows": [
    {
      "task_master_id": "tm_01K8K13NC8PRJ3V4R35C1AP2JP",
      "task_name": "Complex task",
      "workflow_name": "complex_task",
      "yaml_content": "",
      "status": "failed",
      "validation_result": null,
      "error_message": "Max retries exceeded (3 attempts)",
      "retry_count": 3
    }
  ],
  "total_tasks": 2,
  "successful_tasks": 1,
  "failed_tasks": 1,
  "generation_time_ms": 8234.5,
  "langfuse_trace_id": "trace-xyz789"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "JobMaster or TaskMaster not found: Job ID jm_notfound not found"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Exactly one of 'job_master_id' or 'task_master_id' must be provided"
}
```

---

## Chat API

### Requirement Definition Chat (SSE)

**POST** `/api/v1/chat/requirement-definition`

Stream requirement clarification chat using Server-Sent Events (SSE) for real-time AI responses.

#### Features

- リアルタイムチャット形式での要求明確化
- Server-Sent Events (SSE)によるストリーミング応答
- 要求完成度（completeness）の自動計算
- 会話履歴の保存
- 構造化された要求状態管理

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | string | Yes | 会話セッションID |
| `user_message` | string | Yes | ユーザーメッセージ |
| `context` | object | Yes | 会話コンテキスト |
| `context.previous_messages` | array | Yes | 過去のメッセージ履歴 |
| `context.current_requirements` | object | Yes | 現在の要求状態 |

#### Request Example

```bash
curl -N -X POST http://localhost:8104/aiagent-api/v1/chat/requirement-definition \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "user_message": "売上データを分析したい",
    "context": {
      "previous_messages": [],
      "current_requirements": {
        "data_source": null,
        "process_description": null,
        "output_format": null,
        "schedule": null,
        "completeness": 0.0
      }
    }
  }'
```

#### Response (SSE Events)

**Event 1: Message chunk**

```
event: message
data: {"type": "message", "data": {"content": "データソースは"}}
```

**Event 2: Requirement update**

```
event: message
data: {"type": "requirement_update", "data": {"requirements": {"data_source": "CSVファイル", "completeness": 0.25}}}
```

**Event 3: Requirements ready**

```
event: message
data: {"type": "requirements_ready", "data": {}}
```

**Event 4: Done**

```
event: message
data: {"type": "done"}
```

**Error Event:**

```
event: message
data: {"type": "error", "data": {"message": "エラーが発生しました。もう一度お試しください。"}}
```

#### Notes

- SSE接続のため、`curl -N`オプションまたはEventSource APIを使用してください
- completeness ≥ 0.8（80%）でジョブ作成可能になります
- 会話履歴は自動的に保存されます

---

### Create Job from Requirements

**POST** `/api/v1/chat/create-job`

Create job from clarified requirements gathered through chat dialogue.

#### Features

- チャットで明確化した要求からJob/Task自動生成
- 要求完成度の検証（80%以上必須）
- 既存Job Generator APIとの統合
- 自然言語要求への自動変換

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | string | Yes | 会話セッションID |
| `requirements` | object | Yes | 明確化された要求状態 |
| `requirements.data_source` | string | No | データソース |
| `requirements.process_description` | string | No | 処理内容 |
| `requirements.output_format` | string | No | 出力形式 |
| `requirements.schedule` | string | No | 実行スケジュール |
| `requirements.completeness` | float | Yes | 完成度（0.0-1.0、≥0.8必須） |

#### Request Example

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/chat/create-job \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "requirements": {
      "data_source": "CSVファイル",
      "process_description": "売上データの月別集計",
      "output_format": "Excelレポート",
      "schedule": "毎日朝9時",
      "completeness": 0.95
    }
  }'
```

#### Response

**Success Response (200 OK):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_master_id": "jm_01K89W9DBHAPWMMZVHWT2N7GX9",
  "status": "success",
  "message": "ジョブを作成しました"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Requirements not sufficiently clarified (60% < 80%)"
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "detail": "ジョブの作成に失敗しました: Job Generator error"
}
```

---

### Select Candidate (Issue #173)

**POST** `/v1/chat/select-candidate`

Select a candidate interpretation from multiple options presented during requirement clarification.

#### Features

- SSE candidate_selection イベントで提示された候補から選択
- 選択した候補の要件が以降の対話に使用される
- 候補の保存・追跡機能

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | string | Yes | 会話セッションID |
| `selected_candidate_id` | string | Yes | 選択する候補ID（A, B など） |

#### Request Example

```bash
curl -X POST http://localhost:8004/v1/chat/select-candidate \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "selected_candidate_id": "A"
  }'
```

#### Response (200 OK)

```json
{
  "conversation_id": "conv_001",
  "selected_candidate_id": "A",
  "requirements": {
    "data_source": "CSVファイル",
    "process_description": "売上データの月別集計",
    "output_format": "Excelレポート",
    "schedule": "オンデマンド",
    "completeness": 0.75
  },
  "message": "候補A（売上データ集計）を選択しました。追加の詳細を確認させてください。"
}
```

#### Error Response (404 Not Found)

```json
{
  "detail": "No candidates found for conversation: conv_001"
}
```

#### Error Response (400 Bad Request)

```json
{
  "detail": "Candidate 'C' not found. Available: ['A', 'B']"
}
```

---

### Submit Feedback (Issue #172)

**POST** `/v1/chat/feedback`

Submit feedback scores for a requirement clarification conversation. Scores are stored in Langfuse for observability analysis.

#### Features

- 4種類のスコア（1-5段階）で会話品質を評価
- Langfuseへのスコア送信・保存
- オプションのコメント機能

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `conversation_id` | string | Yes | 会話セッションID |
| `requirement_clarity` | int | No | 要件の明確さ（1-5） |
| `interpretation_accuracy` | int | No | 解釈の正確さ（1-5） |
| `response_helpfulness` | int | No | 回答の有用性（1-5） |
| `overall_satisfaction` | int | No | 総合満足度（1-5） |
| `comment` | string | No | 自由コメント |

#### Score Mapping

スコアは1-5からLangfuseの0.0-1.0スケールに変換されます:

| Score (1-5) | Langfuse Value |
|-------------|----------------|
| 1 | 0.0 |
| 2 | 0.25 |
| 3 | 0.5 |
| 4 | 0.75 |
| 5 | 1.0 |

#### Langfuse Score Names

| Request Field | Langfuse Score Name |
|---------------|---------------------|
| requirement_clarity | req_def_clarity |
| interpretation_accuracy | req_def_accuracy |
| response_helpfulness | req_def_helpfulness |
| overall_satisfaction | req_def_overall |

#### Request Example

```bash
curl -X POST http://localhost:8004/v1/chat/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_001",
    "requirement_clarity": 5,
    "interpretation_accuracy": 4,
    "response_helpfulness": 5,
    "overall_satisfaction": 5,
    "comment": "Very helpful!"
  }'
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "Feedback submitted successfully. 4 of 4 scores recorded.",
  "feedback_id": null,
  "scores_submitted": 4
}
```

#### Error Response (500 Internal Server Error)

```json
{
  "detail": "フィードバックの送信に失敗しました: Langfuse is not enabled"
}
```

---

## Marp Report API

### Generate Marp Presentation

**POST** `/api/v1/marp-report`

Generate Marp presentation slides from Job Generator result for visual reporting.

#### Features

- Job Generator結果からMarpプレゼンテーション自動生成
- 要求緩和提案（Requirement Relaxation Suggestions）の可視化
- 3つのテーマ選択（default, gaia, uncover）
- 実装ステップの表示/非表示切り替え
- タスク別の提案グルーピング

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_result` | object | XOR | Job Generator実行結果JSON |
| `json_file_path` | string | XOR | Job Generator結果JSONファイルパス |
| `theme` | string | No | Marpテーマ（"default", "gaia", "uncover"、デフォルト: "default"） |
| `include_implementation_steps` | boolean | No | 実装ステップを含めるか（デフォルト: true） |

**Note**: `job_result`と`json_file_path`は排他的（XOR）です。どちらか一方のみ指定してください。

#### Request Examples

**Example 1: Generate from inline JSON**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/marp-report \
  -H "Content-Type: application/json" \
  -d '{
    "job_result": {
      "status": "partial_success",
      "infeasible_tasks": [...],
      "requirement_relaxation_suggestions": [...]
    },
    "theme": "gaia",
    "include_implementation_steps": true
  }'
```

**Example 2: Generate from file**

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/marp-report \
  -H "Content-Type: application/json" \
  -d '{
    "json_file_path": "/tmp/job_result.json",
    "theme": "default",
    "include_implementation_steps": false
  }'
```

#### Response

**Success Response (200 OK):**

```json
{
  "marp_markdown": "---\nmarp: true\ntheme: default\n---\n\n# Job/Task Generation Report\n...",
  "slide_count": 15,
  "suggestions_count": 6,
  "generation_time_ms": 45.3
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "JSON file not found: /tmp/nonexistent.json"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Either job_result or json_file_path must be provided"
}
```

---

### Get Marp Report by Job ID

**GET** `/api/v1/marp-report/{job_id}`

Get Marp presentation report by job ID from job creation status.

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string (path) | Yes | ジョブID |
| `format` | string (query) | No | 出力形式（"html", "pdf", "png"、デフォルト: "html"） |

#### Request Example

```bash
curl -X GET "http://localhost:8104/aiagent-api/v1/marp-report/550e8400-e29b-41d4-a716-446655440000?format=html"
```

#### Response

**Success Response (200 OK):**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "markdown": "---\nmarp: true\ntheme: default\n---\n\n# Job/Task Generation Report\n...",
  "html": "",
  "pdf_url": null,
  "png_urls": null,
  "slide_count": 15
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Job ID not found: 550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Job is not completed yet. Current status: creating"
}
```

#### Notes

- ジョブが完了状態（status: "completed"）である必要があります
- HTML/PDF/PNGレンダリングはクライアントサイド推奨（現在html/pdf_url/png_urlsは未実装）
- Marp CLIまたはMarp for VS Codeでプレビュー可能

---

## Observability API

### Data Privacy Notice (Issue #278)

When Langfuse integration is enabled, the following data is transmitted to the Langfuse server for LLM observability:

#### Data Sent to Langfuse

| Data Type | Description | Example |
|-----------|-------------|---------|
| **LLM Prompts** | Input messages sent to LLM | User requirements, system prompts |
| **LLM Responses** | Output generated by LLM | Task breakdowns, workflow definitions |
| **Model Parameters** | Configuration for LLM calls | temperature, max_tokens, model_name |
| **Timing Information** | Request latency, processing time | start_time, end_time, duration_ms |
| **Token Usage** | Input/output token counts | prompt_tokens, completion_tokens |
| **Trace Metadata** | Session/user identifiers | session_id, user_id, trace_id |

#### Security Recommendations

1. **Self-hosted Langfuse Recommended**
   - For sensitive or confidential data, deploy Langfuse on your own infrastructure
   - See: [Langfuse Self-hosted Deployment](https://langfuse.com/docs/deployment/self-host)

2. **Data Retention**
   - Configure appropriate retention policies in Langfuse settings
   - Default retention may store data indefinitely

3. **Access Control**
   - Restrict Langfuse dashboard access to authorized personnel
   - Use Langfuse's RBAC features for team access management

4. **Network Security**
   - Use HTTPS for all Langfuse communications
   - Consider VPN/private network for self-hosted deployments

#### Disabling Langfuse

To disable Langfuse integration (no data sent):

```bash
# Remove or unset these environment variables
unset LANGFUSE_PUBLIC_KEY
unset LANGFUSE_SECRET_KEY

# Or delete from myVault
curl -X DELETE "http://localhost:8103/api/v1/secrets/expertagent/default_project/LANGFUSE_PUBLIC_KEY"
curl -X DELETE "http://localhost:8103/api/v1/secrets/expertagent/default_project/LANGFUSE_SECRET_KEY"
```

When Langfuse is disabled:
- All API endpoints continue to function normally
- `langfuse_trace_id` fields return `null`
- No performance degradation

---

### Get Trace List

**GET** `/api/v1/observability/traces`

Get list of Langfuse traces with filtering and pagination support.

#### Features

- Langfuseトレース一覧取得
- user_id, session_id, tagsによるフィルタリング
- ページネーション対応
- LangfuseダッシュボードURLリンク

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | No | ユーザーIDでフィルタ |
| `session_id` | string | No | セッションIDでフィルタ |
| `tags` | string | No | タグでフィルタ（カンマ区切り） |
| `limit` | integer | No | 取得件数（デフォルト: 50、範囲: 1-1000） |
| `offset` | integer | No | ページネーション用オフセット（デフォルト: 0） |

#### Request Examples

**Example 1: Get recent traces**

```bash
curl -X GET "http://localhost:8104/aiagent-api/v1/observability/traces?limit=10"
```

**Example 2: Filter by user and tags**

```bash
curl -X GET "http://localhost:8104/aiagent-api/v1/observability/traces?user_id=user_123&tags=production,job-generator&limit=20"
```

#### Response

**Success Response (200 OK):**

```json
{
  "traces": [
    {
      "id": "trace_abc123",
      "name": "Job Generator Execution",
      "user_id": "user_123",
      "session_id": "session_456",
      "timestamp": "2025-10-15T10:30:00Z",
      "tags": ["production", "job-generator"],
      "metadata": {"version": "1.0"},
      "langfuse_url": "https://langfuse.example.com/trace/trace_abc123"
    }
  ],
  "total": 100,
  "limit": 10,
  "offset": 0
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Invalid limit value"
}
```

---

### Get Trace Detail

**GET** `/api/v1/observability/traces/{trace_id}`

Get detailed information for a specific trace including observations (spans, generations, events).

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trace_id` | string (path) | Yes | トレースID |

#### Request Example

```bash
curl -X GET http://localhost:8104/aiagent-api/v1/observability/traces/trace_abc123
```

#### Response

**Success Response (200 OK):**

```json
{
  "id": "trace_abc123",
  "name": "Job Generator Execution",
  "user_id": "user_123",
  "session_id": "session_456",
  "timestamp": "2025-10-15T10:30:00Z",
  "tags": ["production"],
  "metadata": {"version": "1.0"},
  "observations": [
    {
      "id": "obs_generation_001",
      "type": "generation",
      "name": "Claude API Call",
      "start_time": "2025-10-15T10:30:05Z",
      "end_time": "2025-10-15T10:30:15Z",
      "input": "Generate job from requirement...",
      "output": "Job created successfully",
      "metadata": {},
      "model": "claude-3-haiku-20240307",
      "usage": {
        "input_tokens": 150,
        "output_tokens": 200,
        "total_tokens": 350
      }
    }
  ],
  "langfuse_url": "https://langfuse.example.com/trace/trace_abc123"
}
```

**Error Response (404 Not Found):**

```json
{
  "detail": "Trace not found: trace_abc123"
}
```

---

### Submit Feedback Score

**POST** `/api/v1/observability/scores`

Submit feedback score for a trace (e.g., user rating, accuracy score).

#### Features

- トレースへのフィードバック送信
- 0.0-1.0のスコア値
- カスタムスコア名（user_rating, accuracy等）
- オプションコメント

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trace_id` | string | Yes | トレースID |
| `name` | string | Yes | スコア名（例: "user_rating", "accuracy"） |
| `value` | float | Yes | スコア値（0.0-1.0） |
| `comment` | string | No | オプションコメント |

#### Request Example

```bash
curl -X POST http://localhost:8104/aiagent-api/v1/observability/scores \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "trace_abc123",
    "name": "user_rating",
    "value": 0.9,
    "comment": "Very helpful response"
  }'
```

#### Response

**Success Response (200 OK):**

```json
{
  "success": true,
  "score_id": "score_xyz789",
  "message": "Score submitted successfully"
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "success": false,
  "score_id": null,
  "message": "Failed to submit score: API error"
}
```

**Error Response (400 Bad Request):**

```json
{
  "detail": "Score value must be between 0.0 and 1.0"
}
```

---

### Get Requirement Definition Metrics (Issue #175)

**GET** `/v1/observability/requirement-definition-metrics`

Get aggregated quality metrics for requirement definition conversations.

#### Features

- 平均スコア、対話ターン数、完了率の集計
- モデル使用率の分析
- 日付範囲によるフィルタリング
- Langfuseデータの集計

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_date` | datetime | No | 開始日（デフォルト: 30日前） |
| `to_date` | datetime | No | 終了日（デフォルト: 今日） |

#### Request Example

```bash
curl -X GET "http://localhost:8004/v1/observability/requirement-definition-metrics?from_date=2025-11-01T00:00:00Z&to_date=2025-11-30T23:59:59Z"
```

#### Response (200 OK)

```json
{
  "metrics": {
    "average_score": 0.78,
    "total_turns": 1250,
    "success_rate": 0.85,
    "average_latency": 2.3,
    "total_sessions": 156,
    "completion_rate": 0.92
  },
  "model_usage": [
    {"model": "gpt-4", "count": 450, "percentage": 36.0},
    {"model": "gemini-2.5-flash", "count": 800, "percentage": 64.0}
  ],
  "period": {
    "from_date": "2025-11-01T00:00:00Z",
    "to_date": "2025-11-30T23:59:59Z"
  },
  "cache_hit": false
}
```

---

### Real-time Dashboard Stream (Issue #176)

**GET** `/v1/observability/dashboard/stream`

Stream real-time dashboard metrics using Server-Sent Events (SSE).

#### Features

- 5秒ごとにメトリクス更新
- 30秒ごとにハートビート送信
- 差分データのみ送信（帯域幅最適化）
- 最大100クライアント同時接続対応

#### SSE Event Types

| Event Type | Description |
|------------|-------------|
| `connected` | 接続確立時に送信 |
| `metrics_update` | メトリクス更新時に送信 |
| `heartbeat` | 接続維持用（30秒ごと） |
| `error` | エラー発生時に送信 |

#### Request Example

```bash
curl -N "http://localhost:8004/v1/observability/dashboard/stream"
```

#### Response (SSE Stream)

```
event: message
data: {"event_type": "connected", "timestamp": "2025-11-27T10:30:00Z", "data": {"client_id": "abc-123"}}

event: message
data: {"event_type": "metrics_update", "timestamp": "2025-11-27T10:30:05Z", "data": {"metrics": {"average_score": 0.78, "total_turns": 1250, "completion_rate": 0.92, "total_sessions": 156, "model_usage": [...]}, "is_full_snapshot": true}}

event: message
data: {"event_type": "heartbeat", "timestamp": "2025-11-27T10:30:30Z", "data": {}}
```

---

## Diagnostic API (Issue #171)

Diagnostic API provides endpoints for retrieving conversation diagnostic information from Valkey storage.

### Get Diagnostic Info

**GET** `/v1/chat/diagnostics/{conversation_id}`

Get diagnostic information for a single conversation.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | string | Unique conversation identifier |

#### Request Example

```bash
curl -X GET "http://localhost:8004/v1/chat/diagnostics/conv-abc123"
```

#### Response (200 OK)

```json
{
  "conversation_id": "conv-abc123",
  "user_id": "user-789",
  "project_id": "project-456",
  "job_id": "job-12345",
  "workflow_id": "workflow-321",
  "start_time": "2025-11-27T10:00:00Z",
  "end_time": "2025-11-27T10:15:00Z",
  "turn_count": 8,
  "messages": [...],
  "langfuse_trace_url": "http://localhost:3001/trace/trace_abc123",
  "metadata": {
    "model": "gpt-4",
    "total_tokens": 2500
  }
}
```

#### Error Response (404 Not Found)

```json
{
  "detail": "Conversation not found: conv-abc123"
}
```

---

### List Diagnostics

**GET** `/v1/chat/diagnostics`

List diagnostic information with optional filtering and pagination.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | string | No | Filter by job ID |
| `user_id` | string | No | Filter by user ID |
| `project_id` | string | No | Filter by project ID |
| `workflow_id` | string | No | Filter by workflow ID |
| `start_date` | datetime | No | Filter by start date |
| `end_date` | datetime | No | Filter by end date |
| `limit` | int | No | Maximum results (default: 100, max: 1000) |
| `offset` | int | No | Pagination offset (default: 0) |

#### Request Example

```bash
curl -X GET "http://localhost:8004/v1/chat/diagnostics?job_id=job-12345&limit=50"
```

#### Response (200 OK)

```json
{
  "items": [
    {
      "conversation_id": "conv-abc123",
      "user_id": "user-789",
      "start_time": "2025-11-27T10:00:00Z",
      "turn_count": 8
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

## AB Testing API

AB Testing API provides endpoints for creating and managing A/B tests, assigning variants to users, collecting metrics, and generating statistical reports.

### Create AB Test

**POST** `/v1/ab-tests`

Create a new AB test configuration.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | テスト名 |
| `description` | string | No | テストの説明 |
| `variants` | array | Yes | バリアント定義（2つ以上必須） |
| `variants[].name` | string | Yes | バリアント名（例: "control", "treatment"） |
| `variants[].weight` | float | Yes | 割り当て重み（0.0〜1.0、合計1.0） |

#### Request Example

```bash
curl -X POST http://localhost:8004/v1/ab-tests \
  -H "Content-Type: application/json" \
  -d '{
    "name": "prompt_v2_test",
    "description": "Test new prompt template",
    "variants": [
      {"name": "control", "weight": 0.5},
      {"name": "treatment", "weight": 0.5}
    ]
  }'
```

#### Response (201 Created)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "prompt_v2_test",
  "description": "Test new prompt template",
  "status": "draft",
  "variants": [
    {"name": "control", "weight": 0.5},
    {"name": "treatment", "weight": 0.5}
  ],
  "created_at": "2025-11-27T10:30:00Z",
  "updated_at": "2025-11-27T10:30:00Z"
}
```

---

### Get AB Test

**GET** `/v1/ab-tests/{test_id}`

Get details of a specific AB test.

#### Response (200 OK)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "prompt_v2_test",
  "status": "running",
  "variants": [...],
  "created_at": "2025-11-27T10:30:00Z"
}
```

---

### List AB Tests

**GET** `/v1/ab-tests`

List all AB tests with optional filtering.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (draft, running, paused, completed) |
| `limit` | int | Maximum number of results (default: 100) |
| `offset` | int | Pagination offset (default: 0) |

#### Response (200 OK)

```json
{
  "items": [...],
  "total": 10,
  "limit": 100,
  "offset": 0
}
```

---

### Update AB Test Status

**PUT** `/v1/ab-tests/{test_id}/status`

Update the status of an AB test.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | Yes | New status (running, paused, completed) |

#### Request Example

```bash
curl -X PUT http://localhost:8004/v1/ab-tests/{test_id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "running"}'
```

#### Response (200 OK)

```json
{
  "old_status": "draft",
  "new_status": "running",
  "updated_at": "2025-11-27T10:35:00Z"
}
```

---

### Assign Variant

**POST** `/v1/ab-tests/{test_id}/assignment`

Assign a variant to a session. Assignment is idempotent - the same session always gets the same variant.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | Unique session identifier |

#### Request Example

```bash
curl -X POST http://localhost:8004/v1/ab-tests/{test_id}/assignment \
  -H "Content-Type: application/json" \
  -d '{"session_id": "user-session-123"}'
```

#### Response (200 OK)

```json
{
  "test_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "user-session-123",
  "variant_name": "treatment",
  "is_new": true,
  "assigned_at": "2025-11-27T10:40:00Z"
}
```

---

### Collect Metrics

**POST** `/v1/ab-tests/{test_id}/metrics`

Record a metric value for a session.

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier (must have variant assignment) |
| `value` | float | Yes | Metric value (e.g., quality score 0.0-1.0) |
| `metric_name` | string | No | Metric name (default: "quality_score") |

#### Request Example

```bash
curl -X POST "http://localhost:8004/v1/ab-tests/{test_id}/metrics?session_id=user-session-123&value=0.85&metric_name=quality_score"
```

#### Response (201 Created)

```json
{
  "test_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "user-session-123",
  "variant_name": "treatment",
  "metric_name": "quality_score",
  "value": 0.85,
  "recorded_at": "2025-11-27T10:45:00Z"
}
```

---

### Generate Report

**POST** `/v1/ab-tests/{test_id}/report`

Generate a statistical analysis report comparing variants.

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metric_name` | string | No | Metric to analyze (default: "quality_score") |
| `confidence_level` | float | No | Statistical confidence level (default: 0.95) |

#### Request Example

```bash
curl -X POST http://localhost:8004/v1/ab-tests/{test_id}/report \
  -H "Content-Type: application/json" \
  -d '{"metric_name": "quality_score", "confidence_level": 0.95}'
```

#### Response (200 OK)

```json
{
  "test_id": "550e8400-e29b-41d4-a716-446655440000",
  "test_name": "prompt_v2_test",
  "metric_name": "quality_score",
  "metrics": {
    "control": {
      "sample_size": 100,
      "mean": 0.72,
      "std": 0.08,
      "confidence_interval": [0.70, 0.74]
    },
    "treatment": {
      "sample_size": 100,
      "mean": 0.85,
      "std": 0.06,
      "confidence_interval": [0.84, 0.86]
    }
  },
  "t_test_result": {
    "t_statistic": -12.5,
    "p_value": 0.00001,
    "is_significant": true
  },
  "effect_size": {
    "cohens_d": 1.84,
    "interpretation": "large"
  },
  "winner": "treatment",
  "recommendation": "Variant 'treatment' shows statistically significant improvement"
}
```

#### Effect Size Interpretation

| Cohen's d | Interpretation |
|-----------|----------------|
| < 0.2 | negligible |
| 0.2 - 0.5 | small |
| 0.5 - 0.8 | medium |
| > 0.8 | large |

---

### Delete AB Test

**DELETE** `/v1/ab-tests/{test_id}`

Delete an AB test and all associated data.

#### Response (204 No Content)

No response body.

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
