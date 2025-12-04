# Expert Agent Service

🤖 Expert Agent Service is a Python/FastAPI microservice for MySwiftAgent that provides expert AI agent functionality using LangGraph.

## Features

- ⚡ Fast and lightweight FastAPI server
- 🧠 LangGraph-based AI agents (sample, utility, explorer, action, playwright, wikipedia, file_reader)
- 🔧 MCP (Model Context Protocol) servers and tools
- 🎭 **Playwright MCP integration** for web automation and scraping
- 📚 **Wikipedia MCP integration** for knowledge retrieval and research
- 📄 **File Reader MCP integration** for multi-format file processing (PDF/Image/Audio/Text/CSV)
- 🔐 **MyVault integration** for centralized secret management with cache
- 🌐 Multiple AI provider support (OpenAI, Google Gemini, Anthropic, Ollama)
- 🔒 CORS-enabled for cross-origin requests
- 🧪 Comprehensive testing with pytest (44 File Reader tests + 30 MyVault tests)
- 🐳 Docker-ready with uv package manager
- 📊 Health check endpoint for monitoring
- 🎯 Type-safe with Pydantic models

## Project Structure

```
expertAgent/
├── app/                    # FastAPI application
│   ├── main.py            # FastAPI entry point
│   ├── api/v1/            # API endpoints
│   │   ├── agent_endpoints.py       # AI agent endpoints
│   │   ├── utility_endpoints.py     # Utility endpoints
│   │   └── google_auth_endpoints.py # 🔐 Google OAuth2 endpoints
│   ├── schemas/           # Pydantic schemas
│   ├── core/              # Core functionality
│   └── models/            # Database models
├── aiagent/               # LangGraph AI agents
│   └── langgraph/
│       ├── common.py              # Common agent logic
│       ├── util.py                # Utilities
│       ├── sampleagent/           # Sample agents
│       └── utilityaiagents/       # Utility agents
│           ├── explorer_agent.py
│           ├── jsonOutput_agent.py
│           ├── action_agent.py
│           ├── playwright_agent.py  # 🎭 Playwright web automation
│           ├── wikipedia_agent.py   # 📚 Wikipedia knowledge retrieval
│           └── file_reader_agent.py # 📄 File processing
├── mymcp/                 # MCP servers and tools
│   ├── stdioall.py               # MCP server
│   ├── stdio_explorer.py         # Explorer MCP
│   ├── stdio_file_reader.py      # 📄 File Reader MCP (FastMCP)
│   ├── tool/                     # General tools
│   │   ├── file_reader_utils.py      # 📄 File Reader utilities
│   │   ├── file_reader_sources.py    # 📄 URL/Drive/Local file download
│   │   └── file_reader_processors.py # 📄 PDF/Image/Audio/Text/CSV processing
│   ├── specializedtool/          # Specialized tools
│   └── googleapis/               # Google API tools
│       └── googleapi_services.py # 🔐 Google API service builder
├── core/                  # Core configuration
│   ├── config.py          # Settings and configuration
│   ├── logger.py          # Logging setup
│   ├── secrets.py         # 🔐 SecretsManager with MyVault integration
│   ├── myvault_client.py  # 🔐 MyVault HTTP client
│   └── google_creds.py    # 🔐 Google OAuth2 credentials manager
├── tests/                 # Test files
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- uv (recommended) or pip

### Installation

```bash
# Install dependencies with uv
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Running the Server

```bash
# Development mode
uv run uvicorn app.main:app --reload

# Production mode
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/integration/test_api.py -v
```

### API Examples

#### Sample Agent
```bash
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/sample" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "葛飾区の人口をメールして"
    }'
```

#### Playwright Agent (Web Automation)
```bash
# Webページのスクレイピング
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/playwright" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "https://example.com のページ内容を取得してください"
    }'

# モデル指定でファイルダウンロード
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/playwright" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "https://example.com/document.pdf をダウンロードしてください",
      "model_name": "gemini-2.5-flash"
    }'
```

### Code Quality

```bash
# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Run type checking
uv run mypy app/
```

### Docker

```bash
# Build Docker image
docker build -t expert-agent:latest .

# Run container
docker run -p 8000:8000 expert-agent:latest
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status (used by CI/CD).

**Example:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "expertAgent"
}
```

### Root

```bash
GET /
```

Welcome message and basic service info.

**Example:**
```bash
curl http://localhost:8000/
```

### API v1 Root

```bash
GET /api/v1/
```

API version information.

**Example:**
```bash
curl http://localhost:8000/api/v1/
```

## Development

### Project Structure

```
expertAgent/
├── app/                    # Application code
│   ├── main.py            # FastAPI entry point
│   ├── core/              # Core functionality
│   ├── api/               # API endpoints
│   ├── models/            # Database models
│   └── schemas/           # Pydantic schemas
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── Dockerfile            # Docker configuration
├── pyproject.toml        # Project configuration
└── README.md             # This file
```

### Playwright MCP Integration

🎭 **Playwright Agent** provides browser automation capabilities using Microsoft's Playwright MCP server.

**Capabilities:**
- 📄 Web page scraping and content extraction
- 📥 File downloads from web pages
- 🌐 Browser automation with Chromium
- 🔍 DOM navigation and interaction

**Usage Example:**

```python
from aiagent.langgraph.utilityaiagents.playwright_agent import playwrightagent

# Web scraping example
result = await playwrightagent(
    "https://example.com のページ内容を取得してください",
    "gemini-2.5-flash"
)

# File download example
result = await playwrightagent(
    "https://example.com/document.pdf をダウンロードしてください",
    "gpt-4o-mini"
)
```

**Technical Details:**
- Uses `@playwright/mcp@latest` via npx
- Chromium browser pre-installed in Docker
- Integrated with LangGraph ReAct agent pattern
- Configurable max iterations (default: 5)
- **User-Agent configured** to avoid bot detection (resolves 403 Forbidden issues on some sites)
- **Docker requirement**: Needs `shm_size: 2gb` for browser operation (configured in docker-compose.yml)

**Development Setup:**

For local development with `dev-start.sh`, ensure Node.js and Playwright are installed:

```bash
# Install Node.js (v20+)
# macOS
brew install node

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Playwright browsers
npx playwright install chromium
```

### Wikipedia MCP Integration

📚 **Wikipedia Agent** provides knowledge retrieval and research capabilities using Wikipedia MCP server.

**Capabilities:**
- 🔍 Search Wikipedia articles
- 📖 Retrieve full article content
- 📝 Get article summaries
- 📑 Extract specific sections
- 🔗 Discover article links and related topics
- 🌍 Multi-language support (140+ languages)

**Usage Example:**

```python
from aiagent.langgraph.utilityaiagents.wikipedia_agent import wikipediaagent

# Japanese Wikipedia search
result = await wikipediaagent(
    "日本の歴史について教えてください",
    "gemini-2.5-flash",
    "ja"
)

# English Wikipedia search
result = await wikipediaagent(
    "Tell me about artificial intelligence",
    "gpt-4o-mini",
    "en"
)
```

**API Example:**

```bash
# Japanese Wikipedia (default)
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/wikipedia" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "量子コンピュータについて詳しく教えてください"
    }'

# English Wikipedia
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/wikipedia" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "Explain quantum computing in detail",
      "language": "en"
    }'
```

**Technical Details:**
- Uses Wikipedia MCP Python package
- Supports 140+ languages and country codes
- Integrated with LangGraph ReAct agent pattern
- Configurable max iterations (default: 15)
- Language parameter: ISO 639-1 codes (ja, en, fr, de, etc.)

**Development Setup:**

Wikipedia MCP is Python-based and installed via pip in Docker:

```bash
# Already installed in Docker via Dockerfile
pip install wikipedia-mcp

# Test Wikipedia MCP locally
wikipedia-mcp --language ja
```

### File Reader MCP Integration

📄 **File Reader Agent** provides multi-format file processing capabilities using FastMCP server.

**Capabilities:**
- 📑 PDF text extraction (full page content, no summarization)
- 🖼️ Image analysis and OCR (OpenAI Vision API)
- 🎵 Audio transcription (OpenAI Whisper API)
- 📝 Text/Markdown file reading
- 📊 CSV file parsing
- 🌐 Web URL downloads (HTTP/HTTPS)
- ☁️ Google Drive integration (OAuth2)
- 💻 Local file system access (secure)

**Usage Example:**

```python
from aiagent.langgraph.utilityaiagents.file_reader_agent import filereaderagent

# PDF text extraction
result = await filereaderagent(
    "下記ファイルのテキストを全て抽出してください。\nhttps://example.com/document.pdf",
    "gpt-4o-mini"
)

# Image OCR (IMPORTANT: must specify "image file" or "image")
result = await filereaderagent(
    "下記画像ファイルのテキストを抽出してください。\nhttps://drive.google.com/file/d/FILE_ID/view",
    "gpt-4o"
)

# Audio transcription
result = await filereaderagent(
    "下記音声ファイルを文字起こししてください。\nhttps://example.com/audio.mp3",
    "gpt-4o-mini"
)
```

**API Example:**

```bash
# PDF full text extraction
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/file_reader" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "下記ファイルのテキストを全て抽出してください。\nhttps://drive.google.com/file/d/FILE_ID/view"
    }'

# Image OCR (note: must specify "image file")
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/file_reader" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "下記画像ファイルのテキストを抽出してください。\nhttps://example.com/screenshot.png"
    }'

# Local file reading
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/utility/file_reader" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "下記ファイルの内容を表示してください。\n/tmp/document.pdf"
    }'
```

**Technical Details:**
- **MCP Server**: FastMCP with stdio transport
- **PDF Processing**: PyPDF2 for text extraction (all pages, no summarization)
- **Image Processing**: Base64 encoding + OpenAI Vision API (gpt-4o)
- **Audio Processing**: OpenAI Whisper API (whisper-1)
- **File Sources**:
  - HTTP/HTTPS URLs (timeout: 30s)
  - Google Drive (OAuth2 via MyVault)
  - Local files (secure path validation)
- **Security**:
  - Max file size: 50MB (default)
  - Path traversal protection
  - Allowed directories: `/tmp`, `/var/tmp`, `~/Downloads`, `~/Documents`
  - Auto cleanup of temporary files
- **Test Coverage**: 44 unit tests, 85.5% coverage

**Important Usage Notes:**

⚠️ **For Image Files**: Always specify "image file" or "image content" in your instruction
- ❌ Wrong: "下記ファイルのテキストを抽出してください" (will be rejected as "not PDF")
- ✅ Correct: "下記**画像ファイル**のテキストを抽出してください"
- ✅ Correct: "下記**画像の内容**を説明してください"

**Supported File Formats:**

| Format | MIME Type | Tool Used | Output |
|--------|-----------|-----------|--------|
| PDF | `application/pdf` | PyPDF2 | Full text (all pages) |
| PNG/JPG | `image/png`, `image/jpeg` | Vision API | OCR or description |
| TXT/MD | `text/plain`, `text/markdown` | Direct read | Full content |
| CSV | `text/csv` | csv.reader | Formatted text |
| MP3/MP4/WAV | `audio/*`, `video/mp4` | Whisper API | Transcription |

**Development Setup:**

File Reader requires OpenAI API keys in MyVault:

```bash
# Required MyVault secrets
OPENAI_API_KEY=sk-...  # For Vision and Whisper APIs

# For Google Drive support
GOOGLE_CREDENTIALS_JSON={...}  # OAuth2 credentials
GOOGLE_TOKEN_JSON={...}  # OAuth2 tokens
```

**Documentation:**
- Full usage guide: `docs/file-reader-usage-guide.md`
- Implementation plan: `docs/file-reader-implementation-plan.md`
- Progress log: `docs/file-reader-progress.md`

### Environment Variables

Create a `.env` file in the project root:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# MyVault Configuration (recommended for secret management)
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8105
MYVAULT_SERVICE_NAME=expertAgent
MYVAULT_SERVICE_TOKEN=your-service-token
MYVAULT_DEFAULT_PROJECT=your-project-name
SECRETS_CACHE_TTL=300  # Cache TTL in seconds (default: 300)

# API Keys (fallback if MyVault is unavailable)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
```

### MyVault Integration

🔐 **SecretsManager** provides centralized secret management with MyVault priority and environment variable fallback.

**Features:**
- 🔒 Priority-based secret retrieval: MyVault → Environment Variables → Error
- ⚡ TTL-based caching (default 300s) for performance
- 🔄 Manual cache reload via admin API
- 📁 Project-level secret grouping
- 🛡️ Comprehensive error handling

**Usage Example:**

```python
from core.secrets import secrets_manager

# Get secret (tries MyVault first, falls back to env var)
api_key = secrets_manager.get_secret("OPENAI_API_KEY")

# Get secret from specific project
api_key = secrets_manager.get_secret("OPENAI_API_KEY", project="my-project")

# Get all secrets for a project
secrets = secrets_manager.get_secrets_for_project("my-project")

# Clear cache (manual reload)
secrets_manager.clear_cache()  # Clear all cache
secrets_manager.clear_cache("my-project")  # Clear specific project
```

**Admin API for Cache Reload:**

```bash
# Reload secrets cache (requires X-Admin-Token header)
curl -X POST "http://localhost:8103/aiagent-api/v1/admin/reload-secrets" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{"project": null}'

# Reload specific project cache
curl -X POST "http://localhost:8103/aiagent-api/v1/admin/reload-secrets" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{"project": "my-project"}'
```

**Secret Retrieval Priority:**

1. **MyVault** (if `MYVAULT_ENABLED=true`)
   - Checks cache first (if within TTL)
   - Fetches from MyVault API if cache miss
   - Uses specified project or default project
2. **Environment Variable** (fallback)
   - Falls back to `.env` or system environment
3. **Error** (if not found anywhere)
   - Raises `ValueError` with descriptive message

**Test Coverage:**

The MyVault integration includes comprehensive tests:
- `tests/unit/test_myvault_client.py` - 11 tests for MyVault HTTP client
- `tests/unit/test_secrets_manager.py` - 11 tests for SecretsManager logic
- `tests/unit/test_admin_endpoints.py` - 8 tests for admin API endpoints

Run tests: `uv run pytest tests/unit/test_myvault_client.py tests/unit/test_secrets_manager.py tests/unit/test_admin_endpoints.py -v`

### Google Authentication Management

🔑 **Google Credentials Manager** provides project-based Google OAuth 2.0 credentials management with encrypted local caching.

**Features:**
- 🔒 Project-level credential isolation
- 🔐 Fernet symmetric encryption for local credentials cache
- 📁 Integrated with MyVault for centralized storage
- 🔄 Automatic token refresh with OAuth 2.0 flow
- 🌐 Support for Gmail, Drive, and Sheets APIs
- 🛡️ Secure file permissions (0o600)
- 🔑 Global encryption key management
- 🗑️ Automatic temp file cleanup

**Architecture:**

1. **Storage Layer:**
   - MyVault: Source of truth for credentials (GOOGLE_CREDENTIALS_JSON, GOOGLE_TOKEN_JSON)
   - Local Cache: `.google_credentials/{project}/` with encrypted files (*.enc)
   - Global Encryption Key: Stored in MyVault as `GOOGLE_CREDS_ENCRYPTION_KEY`

2. **Authentication Flow:**
   - Credentials synced from MyVault → Encrypted locally
   - Decrypted to temp files when needed
   - Google OAuth 2.0 flow (browser-based for first-time auth)
   - Token auto-refresh with refresh_token
   - Refreshed tokens saved locally (manual MyVault update recommended)

**Usage Example:**

```python
from mymcp.googleapis.googleapi_services import get_googleapis_service

# Get Gmail service for specific project
gmail_service = get_googleapis_service("gmail", project="my-project")

# Get Drive service for default project
drive_service = get_googleapis_service("drive")

# Get Sheets service
sheets_service = get_googleapis_service("sheets", project="another-project")
```

**API Endpoints:**

```bash
# Check token status for a project
curl -X GET "http://localhost:8000/v1/google-auth/token-status?project=my-project" \
    -H "X-Admin-Token: your-admin-token"

# Sync credentials from MyVault to local cache
curl -X POST "http://localhost:8000/v1/google-auth/sync-from-myvault" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{"project": "my-project"}'

# List all projects with cached credentials
curl -X GET "http://localhost:8000/v1/google-auth/list-projects" \
    -H "X-Admin-Token: your-admin-token"

# Start OAuth2 flow (for Web Application)
curl -X POST "http://localhost:8000/v1/google-auth/oauth2-start" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "my-project",
      "redirect_uri": "http://localhost:8501"
    }'

# Complete OAuth2 flow with authorization code
curl -X POST "http://localhost:8000/v1/google-auth/oauth2-callback" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{
      "state": "state-from-oauth2-start",
      "code": "authorization-code-from-google",
      "project": "my-project"
    }'

# Get token data for backup or viewing
curl -X GET "http://localhost:8000/v1/google-auth/token-data?project=my-project" \
    -H "X-Admin-Token: your-admin-token"

# Save token manually (with optional MyVault sync)
curl -X POST "http://localhost:8000/v1/google-auth/save-token" \
    -H "X-Admin-Token: your-admin-token" \
    -H "Content-Type: application/json" \
    -d '{
      "project": "my-project",
      "token_json": "{\"token\": \"...\", \"refresh_token\": \"...\"}",
      "save_to_myvault": true
    }'
```

**commonUI Integration:**

The `commonUI` provides a web interface for Google credential management with OAuth2 Web Application flow:

1. Navigate to **MyVault → Google認証** tab
2. Select a project from the dropdown
3. Paste `credentials.json` content from Google Cloud Console (Web Application type)
4. Click "Save to MyVault" → Credentials stored in MyVault
5. Click "Start OAuth2 Flow" → Browser window opens for authentication
6. Grant permissions in Google OAuth consent screen
7. You'll be redirected back to commonUI (http://localhost:8501)
8. Token is automatically saved to MyVault and encrypted locally
9. Status indicator shows "✅ Token valid" when authentication is complete

**Two Authentication Methods:**

1. **Web Application Flow (Recommended for commonUI):**
   - OAuth2 callback handled by commonUI
   - redirect_uri: `http://localhost:8501`
   - No browser popup blocking issues
   - Automatic token save to MyVault

2. **Desktop Application Flow (Legacy):**
   - Browser-based authentication on first API call
   - Uses `run_local_server()` from google-auth-oauthlib
   - Manual MyVault update recommended after token refresh

**Security Features:**

- **Encryption:** Fernet (AES-128-CBC) for local credential files
- **File Permissions:** 0o600 (owner read/write only)
- **Temp Files:** Auto-cleanup on process exit with `atexit`
- **Token Storage:** Encrypted at rest in `.google_credentials/{project}/token.json.enc`
- **No Hardcoded Keys:** Encryption key stored in MyVault

**Google API Scopes:**

Default scopes configured in `core/google_creds.py`:
- `https://www.googleapis.com/auth/gmail.readonly` - Read Gmail messages
- `https://www.googleapis.com/auth/gmail.send` - Send emails
- `https://www.googleapis.com/auth/drive` - Full Drive access
- `https://www.googleapis.com/auth/spreadsheets` - Sheets access

**Environment Variables:**

```env
# MyVault Configuration (required)
MYVAULT_ENABLED=true
MYVAULT_BASE_URL=http://localhost:8105
MYVAULT_SERVICE_NAME=expertAgent
MYVAULT_SERVICE_TOKEN=your-service-token
MYVAULT_DEFAULT_PROJECT=your-project-name

# Admin Token (required for Google Auth API)
ADMIN_TOKEN=your-admin-token
```

**Setup Guide:**

1. **Encryption Key (Auto-generated):**
   - `GOOGLE_CREDS_ENCRYPTION_KEY` is **automatically created** by MyVault when you create a new project
   - This global encryption key is used to encrypt all project credentials locally
   - **No manual setup required** - MyVault handles this in `app/api/projects.py:create_project()`
   - The key is **hidden from commonUI** - cannot be viewed or edited by users

2. **Get Google Credentials:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 Client ID (**Web application** - not Desktop app)
   - Configure OAuth consent screen if not already done
   - **重要**: 以下の設定が必要です（[公式ガイド](https://developers.google.com/workspace/guides/create-credentials?hl=ja#desktop-app)参照）
     - **承認済みの JavaScript 生成元**: `http://localhost:8501`
     - **承認済みのリダイレクト URI**: `http://localhost:8501`
   - Download `credentials.json` (Webアプリケーションのクライアントシークレット)

3. **Add Credentials to MyVault via commonUI:**
   - Open commonUI → MyVault → Google認証 tab
   - Select your project (encryption key auto-generated when project was created)
   - Paste `credentials.json` content
   - Click "Save to MyVault"

4. **Authenticate with Google:**
   - Click "Start OAuth2 Flow" in commonUI
   - Grant permissions in the browser window
   - Token is automatically saved to MyVault and encrypted locally
   - Status updates to "✅ Token valid"

5. **Token Management:**
   - Tokens are auto-refreshed when expired (if refresh_token available)
   - Refreshed tokens are saved locally and **should be manually synced to MyVault**
   - Use "Check Token Status" in commonUI to verify validity

**Troubleshooting:**

- **Token expired:** Run sync-from-myvault API to refresh local cache
- **Encryption key missing:** Add `GOOGLE_CREDS_ENCRYPTION_KEY` to MyVault (global, not project-specific)
- **Credentials not found:** Check MyVault has `GOOGLE_CREDENTIALS_JSON` for the project
- **Permission denied:** Check `.google_credentials/` directory has correct permissions (0o700)

## CI/CD Integration

This project is integrated with MySwiftAgent's multi-release workflow:

- **Feature branches** → `develop` (with appropriate labels for version bump)
- **Release branches** → `release/expertAgent/vX.Y.Z`
- **Releases** → `main` (automatic tagging and GitHub Release)

See [CLAUDE.md](../CLAUDE.md) for detailed workflow information.

## Version

Current version: 0.2.1

**Recent Updates:**
- v0.2.1 (2025-10): Google OAuth2 Web Application flow with encrypted credential management
- v0.2.0: Playwright MCP and Wikipedia MCP integration

## License

MIT
