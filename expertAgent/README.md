# Expert Agent Service

🤖 Expert Agent Service is a Python/FastAPI microservice for MySwiftAgent that provides expert AI agent functionality using LangGraph.

## Features

- ⚡ Fast and lightweight FastAPI server
- 🧠 LangGraph-based AI agents (sample, utility, explorer, action)
- 🔧 MCP (Model Context Protocol) servers and tools
- 🌐 Multiple AI provider support (OpenAI, Google Gemini, Anthropic, Ollama)
- 🔒 CORS-enabled for cross-origin requests
- 🧪 Comprehensive testing with pytest
- 🐳 Docker-ready with uv package manager
- 📊 Health check endpoint for monitoring
- 🎯 Type-safe with Pydantic models

## Project Structure

```
expertAgent/
├── app/                    # FastAPI application
│   ├── main.py            # FastAPI entry point
│   ├── api/v1/            # API endpoints
│   │   ├── agent_endpoints.py     # AI agent endpoints
│   │   └── utility_endpoints.py  # Utility endpoints
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
│           └── action_agent.py
├── mymcp/                 # MCP servers and tools
│   ├── stdioall.py               # MCP server
│   ├── stdio_explorer.py         # Explorer MCP
│   ├── tool/                     # General tools
│   ├── specializedtool/          # Specialized tools
│   └── googleapis/               # Google API tools
├── core/                  # Core configuration
│   ├── config.py
│   └── logger.py
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

### exec
```
curl -X POST "http://127.0.0.1:8103/aiagent-api/v1/aiagent/sample" \
    -H "Content-Type: application/json" \
    -d '{
      "user_input": "葛飾区の人口をメールして"
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

### Environment Variables

Create a `.env` file in the project root:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# Add your environment variables here
```

## CI/CD Integration

This project is integrated with MySwiftAgent's multi-release workflow:

- **Feature branches** → `develop` (with appropriate labels for version bump)
- **Release branches** → `release/expertAgent/vX.Y.Z`
- **Releases** → `main` (automatic tagging and GitHub Release)

See [CLAUDE.md](../CLAUDE.md) for detailed workflow information.

## Version

Current version: 0.1.0

## License

MIT
