# Graph AI Server

🚀 Graph AI Server is a TypeScript/Node.js microservice for MySwiftAgent that provides graph-based AI functionality using GraphAI framework.

## Features

- ⚡ Fast and lightweight Express server
- 🧠 GraphAI framework integration for complex AI workflows
- 🔒 Security-first with Helmet middleware
- 🌐 CORS-enabled for cross-origin requests
- 🧪 Comprehensive testing with Jest and Supertest
- 🐳 Docker-ready with multi-stage build
- 📊 Health check endpoint for monitoring
- 📝 YAML-based workflow configuration

## Getting Started

### Prerequisites

- Node.js 20+
- npm

### Installation

```bash
# Install dependencies
npm ci

# Run in development mode
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Running Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run linting
npm run lint

# Run type checking
npm run type-check
```

### Docker

```bash
# Build Docker image
docker build -t graph-ai-server:latest .

# Run container
docker run -p 8000:8000 graph-ai-server:latest
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
  "service": "graphAiServer"
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

### GraphAI Test Endpoint

```bash
GET /api/v1/test
```

Executes a test GraphAI workflow (uses `test.yml`).

**Example:**
```bash
curl http://localhost:8000/api/v1/test
```

**Response:**
```json
{
  "result": "..."
}
```

### GraphAI Agent Endpoint

```bash
POST /api/v1/myagent
```

Executes a custom GraphAI workflow with user input.

**Request Body:**
```json
{
  "user_input": "Your input text here",
  "model_name": "podcast_map_test"
}
```

**Example:**
```bash
# Basic example
curl -X POST http://localhost:8000/api/v1/myagent \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "GraphAIについて教えて",
    "model_name": "test"
  }'
```

**Response:**
```json
{
  "result": "..."
}
```

## Development

### Project Structure

```
graphAiServer/
├── src/                    # Source code
│   ├── app.ts             # Express application
│   ├── index.ts           # Entry point
│   └── services/          # Service layer
│       └── graphai.ts     # GraphAI service
├── config/                # Configuration files
│   └── graphai/          # GraphAI workflow YAML files
│       └── test.yml
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── dist/                  # Build output
├── Dockerfile            # Docker configuration
├── package.json          # Dependencies and scripts
└── tsconfig.json         # TypeScript configuration
```

### Environment Variables

Create a `.env` file in the project root (or copy from `.env.example`):

```env
PORT=8000
NODE_ENV=development

# GraphAI Configuration
MODEL_BASE_PATH=./config/graphai/

OPENAI_API_KEY=your_openai_api_key_here
```

### GraphAI Workflows

GraphAI workflows are defined in YAML files under `config/graphai/`. You can create custom workflows by:

1. Creating a new `.yml` file in `config/graphai/`
2. Defining nodes, agents, and connections
3. Referencing the workflow name in the API request

**Example workflow structure:**
```yaml
version: 0.5
nodes:
  source: {}
  expertAgent:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: POST
      body:
        user_input: :source
  output:
    agent: copyAgent
    inputs:
      text: :expertAgent.text
    isResult: true
```

## CI/CD Integration

This project is integrated with MySwiftAgent's multi-release workflow:

- **Feature branches** → `develop` (with `feature` label for minor version bump)
- **Release branches** → `release/graphAiServer/vX.Y.Z`
- **Releases** → `main` (automatic tagging and GitHub Release)

See [CLAUDE.md](../CLAUDE.md) for detailed workflow information.

## Version

Current version: 0.1.0

## License

MIT
